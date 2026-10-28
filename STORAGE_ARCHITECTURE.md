# Storage architecture

Default 500 GB allocation is configurable: PyPI 220 GB, npm 170 GB, temp 10 GB, while 25 GB is permanently reserved as emergency free space. These values are environment variables, never business-logic constants.

Before and during every PyPI download, `StorageManager` checks total quota, registry quota, and physical free space. Downloads land in `MIRROR_STORAGE_ROOT/temp`; only after SHA-256 verification are they atomically moved into `blobs/sha256/ab/cd/HASH`. Existing hashes reuse one blob.

The current MVP blocks admission when a limit would be crossed. Reservation rows, LRU-based eviction, and automatic cleanup must be implemented before enabling concurrent production fetches; without them, do not configure high download concurrency.
