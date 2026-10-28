# npm mirror specification

npm is not implemented yet. It will expose `/npm/`, cache registry metadata and tarballs, verify `integrity`/`shasum`, use the same storage manager/blob layout, and correctly preserve scoped names. It must not be advertised as available until its integration tests pass.
