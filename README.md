# Funmig Mirror

Selective, offline-first package mirror foundation for `mirror.funmig.com`.

## Quick start

```sh
cp .env.example .env
# Set MIRROR_DATA_DIR to the host disk/path that must hold cached package data.
export MIRROR_DATA_DIR=/srv/funmig-mirror-data
docker compose up -d --build
docker compose exec web python manage.py migrate
```

For commands shown in the UI, keep the public host configured as `MIRROR_DOMAIN=mirror.funmig.com`. Do not set it to `localhost` unless you intentionally want the local development address shown.

The PyPI client URL is `https://mirror.funmig.com/pypi/simple/` once DNS/TLS are configured.

## Storage location

On a host deployment, set `MIRROR_DATA_DIR` to the desired absolute host path; Compose mounts it at `/data/mirror`. For non-Docker development, set `MIRROR_STORAGE_ROOT` directly. Data is organized as `blobs/`, `temp/`, `metadata/`, and `exports/` under that root. Do not place it inside the repository or container filesystem.

## Domain activation

Create an `A`/`AAAA` record for `mirror.funmig.com` pointing to the server, configure TLS (for example via your reverse-proxy certificate workflow), then set `MIRROR_DOMAIN` and `DJANGO_ALLOWED_HOSTS` accordingly. The included Nginx config already routes that hostname, but TLS certificates are deliberately not bundled in the repository.

## Current scope

PyPI metadata/cache-on-demand is the MVP. See `IMPLEMENTATION_PLAN.md` for incomplete features; npm and the dashboard are not yet production-ready.
