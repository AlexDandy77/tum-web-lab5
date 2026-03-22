"""HTTP client over raw TCP sockets."""

import socket
import ssl
from dataclasses import dataclass
from urllib.parse import urlparse

import os

# Prefer system cert bundle, fall back to certifi
if os.path.exists("/etc/ssl/cert.pem"):
    _SSL_CAFILE = "/etc/ssl/cert.pem"
else:
    try:
        import certifi
        _SSL_CAFILE = certifi.where()
    except ImportError:
        _SSL_CAFILE = None


REDIRECT_CODES = {301, 302, 303, 307, 308}


@dataclass
class HTTPResponse:
    status_code: int
    reason: str
    headers: dict
    body: str
    raw_body: bytes
    content_type: str
    url: str  # final URL after redirects


def _parse_url(url: str):
    """Return (scheme, host, port, path_with_query)."""
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    host = parsed.hostname
    port = parsed.port or (443 if scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    return scheme, host, port, path


def _resolve_redirect(base_url: str, location: str) -> str:
    """Resolve a redirect Location relative to the base URL."""
    if location.startswith("http://") or location.startswith("https://"):
        return location
    parsed = urlparse(base_url)
    if location.startswith("/"):
        return f"{parsed.scheme}://{parsed.netloc}{location}"
    # relative path — resolve against current directory
    base_path = parsed.path.rsplit("/", 1)[0] + "/"
    return f"{parsed.scheme}://{parsed.netloc}{base_path}{location}"


def _read_all(sock) -> bytes:
    """Read all bytes from socket until EOF."""
    buf = b""
    while True:
        try:
            chunk = sock.recv(4096)
        except (OSError, ssl.SSLError):
            break
        if not chunk:
            break
        buf += chunk
    return buf


def _decode_chunked(data: bytes) -> bytes:
    """Decode HTTP chunked transfer encoding."""
    result = b""
    pos = 0
    while pos < len(data):
        # Find end of chunk size line
        end = data.find(b"\r\n", pos)
        if end == -1:
            break
        size_line = data[pos:end].decode("latin-1").split(";")[0].strip()
        if not size_line:
            break
        try:
            size = int(size_line, 16)
        except ValueError:
            break
        if size == 0:
            break
        pos = end + 2  # skip \r\n after size
        result += data[pos:pos + size]
        pos += size + 2  # skip \r\n after chunk data
    return result


def _parse_headers(header_bytes: bytes) -> dict:
    """Parse raw header bytes into a lowercase-keyed dict."""
    headers = {}
    lines = header_bytes.decode("latin-1").split("\r\n")
    for line in lines[1:]:  # skip status line
        if ":" in line:
            key, _, value = line.partition(":")
            headers[key.strip().lower()] = value.strip()
    return headers


def _parse_status_line(header_bytes: bytes):
    first_line = header_bytes.decode("latin-1").split("\r\n")[0]
    parts = first_line.split(" ", 2)
    code = int(parts[1])
    reason = parts[2] if len(parts) > 2 else ""
    return code, reason


def _decode_charset(content_type: str, body: bytes) -> str:
    charset = "utf-8"
    if "charset=" in content_type:
        for part in content_type.split(";"):
            part = part.strip()
            if part.startswith("charset="):
                charset = part[len("charset="):].strip().strip('"')
                break
    return body.decode(charset, errors="replace")


def _do_request(url: str, extra_headers: dict = None) -> HTTPResponse:
    """Single HTTP request without redirect following."""
    scheme, host, port, path = _parse_url(url)

    headers_lines = [
        f"GET {path} HTTP/1.1",
        f"Host: {host}",
        "User-Agent: go2web/1.0",
        "Accept: application/json,text/html;q=0.9,*/*;q=0.8",
        "Accept-Encoding: identity",
        "Connection: close",
    ]
    if extra_headers:
        for k, v in extra_headers.items():
            headers_lines.append(f"{k}: {v}")
    request_str = "\r\n".join(headers_lines) + "\r\n\r\n"

    raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    raw_sock.settimeout(15)
    try:
        raw_sock.connect((host, port))
        if scheme == "https":
            context = ssl.create_default_context(cafile=_SSL_CAFILE)
            sock = context.wrap_socket(raw_sock, server_hostname=host)
        else:
            sock = raw_sock

        sock.sendall(request_str.encode("latin-1"))
        raw = _read_all(sock)
    finally:
        raw_sock.close()

    if b"\r\n\r\n" in raw:
        header_part, body_bytes = raw.split(b"\r\n\r\n", 1)
    else:
        header_part = raw
        body_bytes = b""

    status_code, reason = _parse_status_line(header_part)
    headers = _parse_headers(header_part)

    # Decode chunked if needed
    if headers.get("transfer-encoding", "").lower() == "chunked":
        body_bytes = _decode_chunked(body_bytes)

    content_type = headers.get("content-type", "")
    body = _decode_charset(content_type, body_bytes)

    return HTTPResponse(
        status_code=status_code,
        reason=reason,
        headers=headers,
        body=body,
        raw_body=body_bytes,
        content_type=content_type,
        url=url,
    )


class HTTPClient:
    def __init__(self, cache=None):
        self.cache = cache

    def _response_from_cache(self, entry, url: str) -> HTTPResponse:
        content_type = entry.headers.get("content-type", "")
        return HTTPResponse(
            status_code=entry.status_code,
            reason="OK (cached)",
            headers=entry.headers,
            body=entry.body,
            raw_body=entry.body.encode("utf-8", errors="replace"),
            content_type=content_type,
            url=url,
        )

    def request(self, url: str, extra_headers: dict = None, max_redirects: int = 10) -> HTTPResponse:
        """Make a GET request, following redirects, using cache when available."""
        final_url = url

        # Check cache before making any network request
        if self.cache:
            entry = self.cache.get(url)
            if entry and self.cache.is_fresh(entry):
                return self._response_from_cache(entry, url)

        for _ in range(max_redirects + 1):
            response = _do_request(final_url, extra_headers)
            if response.status_code in REDIRECT_CODES:
                location = response.headers.get("location", "")
                if not location:
                    break
                final_url = _resolve_redirect(final_url, location)
                response.url = final_url
            else:
                break
        else:
            raise RuntimeError(f"Too many redirects (>{max_redirects})")

        # Store in cache
        if self.cache and response.status_code == 200:
            self.cache.store(
                url=url,
                status_code=response.status_code,
                headers=response.headers,
                body=response.body,
                etag=response.headers.get("etag", ""),
                last_modified=response.headers.get("last-modified", ""),
            )

        return response
