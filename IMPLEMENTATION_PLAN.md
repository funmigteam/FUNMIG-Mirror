# Implementation plan

1. Complete PyPI correctness: metadata/version parsing, Redis request coalescing, durable reservations, tests, health tasks.
2. Add cleanup/eviction and package statistics.
3. Implement npm with equivalent verification and offline tests.
4. Build prefetch, dependency graph, platform profiles, pins, and offline bundles.
5. Add local documentation/search/dashboard and production observability.
6. Deploy with DNS, TLS, backups, and national-network isolation tests.
