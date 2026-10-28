# Offline mode

Set `UPSTREAM_MODE=offline` when international upstreams are unavailable or intentionally isolated. Cached PyPI metadata and artifacts remain local; uncached requests fail immediately with a clear 503 JSON response. No request path requires an external health check.
