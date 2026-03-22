"""HTTP client over raw TCP sockets."""

import socket
import ssl
from dataclasses import dataclass, field
from urllib.parse import urlparse


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


def _read_all(sock) -> bytes:
    """Read all bytes from socket until EOF."""
    buf = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf += chunk
    return buf


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


class HTTPClient:
    def __init__(self, cache=None):
        self.cache = cache

    def request(self, url: str, extra_headers: dict = None) -> HTTPResponse:
        """Make a GET request, returning an HTTPResponse."""
        scheme, host, port, path = _parse_url(url)

        # Build raw request
        headers_lines = [
            f"GET {path} HTTP/1.1",
            f"Host: {host}",
            "User-Agent: go2web/1.0",
            "Accept: text/html,application/json;q=0.9,*/*;q=0.8",
            "Accept-Encoding: identity",
            "Connection: close",
        ]
        if extra_headers:
            for k, v in extra_headers.items():
                headers_lines.append(f"{k}: {v}")
        request_str = "\r\n".join(headers_lines) + "\r\n\r\n"

        # Connect
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.settimeout(15)
        try:
            raw_sock.connect((host, port))
            if scheme == "https":
                context = ssl.create_default_context()
                sock = context.wrap_socket(raw_sock, server_hostname=host)
            else:
                sock = raw_sock

            sock.sendall(request_str.encode("latin-1"))
            raw = _read_all(sock)
        finally:
            raw_sock.close()

        # Split headers / body
        if b"\r\n\r\n" in raw:
            header_part, body_bytes = raw.split(b"\r\n\r\n", 1)
        else:
            header_part = raw
            body_bytes = b""

        status_code, reason = _parse_status_line(header_part)
        headers = _parse_headers(header_part)
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
