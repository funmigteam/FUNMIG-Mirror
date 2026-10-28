# Security

Upstream URLs are discovered only from the configured PyPI Simple API and binary fetches are allow-listed to PyPI public hosts over HTTPS. User input never becomes a filesystem path or outbound URL. Hash verification is mandatory before publishing a blob. Configure TLS, secure Django secret, trusted proxy headers, and rate limiting at Nginx before public launch.
