# go2web

HTTP client implemented over raw TCP sockets — no HTTP libraries used.

## Usage

```
go2web -u <URL>          # fetch URL and print human-readable content
go2web -s <search-term>  # search DuckDuckGo and print top 10 results
go2web -h                # show help
```

## Setup

```bash
pip install -r requirements.txt
chmod +x go2web
```

## Examples

```bash
# Fetch a webpage (HTML stripped, readable text output)
./go2web -u https://example.com

# Fetch a JSON API (pretty-printed)
./go2web -u https://httpbin.org/get

# Search and optionally open a result
./go2web -s "python socket programming"

# Redirects are followed automatically
./go2web -u http://github.com
```

## Features

| Feature | Details |
|---|---|
| HTTP + HTTPS | Raw `socket` + `ssl` modules, no HTTP libraries |
| Chunked transfer encoding | Decoded transparently |
| Redirect following | 301, 302, 303, 307, 308 — up to 10 hops |
| Human-readable output | HTML tags stripped via BeautifulSoup |
| DuckDuckGo search | Top 10 results from `html.duckduckgo.com` |
| Interactive selection | Pick a search result number to open it |
| HTTP cache | File-based cache in `~/.go2web_cache/` with 5-min TTL |
| Cache revalidation | ETag / If-None-Match and Last-Modified / If-Modified-Since |
| Content negotiation | `Accept` header; JSON responses are pretty-printed |

## Architecture

```
go2web                  # executable entry point
src/
  http_client.py        # raw TCP/SSL socket HTTP client + cache integration
  html_parser.py        # HTML → readable text (BeautifulSoup + stdlib fallback)
  search.py             # DuckDuckGo HTML scraping + interactive selection
  cache.py              # SHA-256 keyed JSON file cache with TTL
```

## Demo

![Lab 5 Demo](lab5-demo.gif)
