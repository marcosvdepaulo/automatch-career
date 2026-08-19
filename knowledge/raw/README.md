# Raw snapshots

`raw/<source>/<version>/` stores byte-for-byte copies of official source exports plus a
`manifest.json` with acquisition time, size and SHA-256 per file. Create snapshots only
through `python -m knowledge acquire`; an existing version is never overwritten.

Source datasets are intentionally not committed to Git.
