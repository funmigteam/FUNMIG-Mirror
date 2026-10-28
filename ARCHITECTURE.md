# Architecture

Funmig Mirror is a selective, cache-on-demand registry service. Django resolves package metadata and cache policy, workers perform slow upstream work, PostgreSQL stores metadata, Redis will provide distributed locks/counters, and Nginx serves verified bytes through `X-Accel-Redirect`.

Only the PyPI MVP is implemented. npm, documentation hub, offline bundles, dashboard, Celery scheduling, and production TLS automation remain planned work.

`MIRROR_DOMAIN` is the canonical public host. `MIRROR_STORAGE_ROOT` is the sole root for mirror bytes and may point to any mounted disk.
