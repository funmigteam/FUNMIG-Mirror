# Database schema

PostgreSQL is the metadata source of truth; package bytes are never stored in it.

- `Package` identifies a normalized package by registry and supports package-level pinning.
- `PackageVersion` models each retained version and version pin.
- `RemoteFile` is cached PyPI Simple API metadata; it is safe to retain when the binary is absent.
- `Artifact` maps a package file to a verified `Blob`, and holds cache priority and access counters.
- `Blob` is content-addressable (`sha256`, size, relative path, reference count), allowing byte-level deduplication.

Indexes and uniqueness constraints cover registry/name, version, hash, priority, and last access. Analytics, bundles, npm, and jobs are intentionally not represented as complete: they are later phases, not fake models.
