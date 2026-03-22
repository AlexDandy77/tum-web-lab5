# go2web

HTTP client implemented over raw TCP sockets (no HTTP libraries).

## Usage

```
go2web -u <URL>         # fetch URL and print human-readable content
go2web -s <search-term> # search DuckDuckGo and print top 10 results
go2web -h               # show help
```

## Setup

```bash
pip install -r requirements.txt
chmod +x go2web
```

## Features

- HTTP and HTTPS over raw TCP sockets
- Chunked transfer encoding support
- HTTP redirect following (301, 302, 303, 307, 308)
- Human-readable output (HTML tags stripped)
- DuckDuckGo search with interactive result selection
- File-based HTTP cache with TTL and ETag/304 revalidation
- Content negotiation (JSON and HTML)
