# PyPI mirror MVP

Endpoints are `/pypi/simple/`, `/pypi/simple/<name>/`, and `/pypi/packages/<id>/`. The package endpoint consumes PyPI's JSON Simple API, persists trusted file metadata, and emits PEP 503-compatible anchors containing `#sha256=` fragments. Artifact URLs are internal IDs: a client cannot provide an arbitrary fetch URL.

On a miss the artifact is fetched only from `pypi.org` or `files.pythonhosted.org`, written to temp, SHA-256 verified against upstream metadata, moved atomically to blob storage, then served by Nginx. In `UPSTREAM_MODE=offline`, uncached metadata/files produce a quick 503 response.
