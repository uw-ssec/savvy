---
name: cloud-storage-backends
description: Use when reading or writing Zarr data on Amazon S3, Google Cloud Storage, Azure Blob or an S3-compatible endpoint such as MinIO, when setting up FsspecStore, ObjectStore (obstore), s3fs, gcsfs, adlfs or Icechunk storage and credentials, or when remote Zarr access fails or is slow, with symptoms like 403 Forbidden, NoCredentialsError, requester-pays buckets, slow store opens, timeouts, high GET-request bills, CORS errors, or an fsspec simplecache or filecache that errors or never hits.
metadata:
  references: references/patterns.md references/examples.md references/common-issues.md
---

# Cloud Storage Backends for Zarr

Connects zarr-python 3 to S3, GCS and Azure Blob through fsspec, obstore or Icechunk, covering credentials, caching and request tuning.

**Core principle:** on object storage every metadata or chunk read is an HTTP request with ~20–100 ms to first byte, so request count sets cost and speed. Consolidate metadata, keep chunk objects at 1 MB or more, raise concurrency, and let the provider's credential chain supply secrets.

## When to Use

Opening or writing a store at an `s3://`, `gs://`, `az://` or S3-compatible URL; choosing FsspecStore, ObjectStore or Icechunk; or a remote store that errors, crawls or costs too much.

**When NOT to use:**
- Choosing chunk or shard shapes: `chunking-strategy`. Rewriting to a new layout: `rechunking` (both in zarr-chunk-optimization).
- Zarr basics, v2 vs v3, the sharding API: `zarr-fundamentals`.
- `xr.open_zarr` / `to_zarr` options, Dask alignment: `zarr-xarray-integration`.
- NetCDF/HDF5 to Zarr, VirtualiZarr or Kerchunk: `data-migration`.

## Quick Reference

Install the filesystem you need (`s3fs`, `gcsfs`, `adlfs`, `obstore`, `icechunk`). `zarr[remote]` adds only fsspec and obstore.

| Need | zarr-python 3 |
|---|---|
| Public S3 | `FsspecStore.from_url("s3://b/x.zarr", storage_options={"anon": True}, read_only=True)` |
| Public GCS / Azure | `{"token": "anon"}` (gcsfs ignores `anon`) / `{"account_name": "acct", "anon": True}` |
| Requester-pays S3 | `{"requester_pays": True}`, with credentials |
| Private bucket | Env vars, `{"profile": "name"}`, IAM role, `{"token": "google_default"}`, Azure `{"account_name": "acct"}` (DefaultAzureCredential) |
| MinIO / Ceph | `{"endpoint_url": "http://host:9000"}`, keys in `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` |
| obstore | `zarr.storage.ObjectStore(S3Store.from_url(url, region="us-west-2"), read_only=True)` |
| Versions, atomic commits | Icechunk: `repo.writable_session("main")`, write to `session.store`, `session.commit(msg)` |
| Local cache | `"simplecache::s3://b/x.zarr"` with `{"s3": {"anon": True, "asynchronous": True}, "simplecache": {"cache_storage": "/tmp/zarr-cache"}}` |
| More parallel GETs | `zarr.config.set({"async.concurrency": 64})` (default 10); s3fs also needs `{"config_kwargs": {"max_pool_connections": 64}}` |
| Faster opens | `zarr.consolidate_metadata(store)` after writes (v2: `.zmetadata`; v3: inside the root `zarr.json`) |

Code per provider: [patterns.md](references/patterns.md). End-to-end runs: [examples.md](references/examples.md). Fixes by symptom: [common-issues.md](references/common-issues.md). Credential-free demo: `python assets/cloud-storage-demo.py`.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Keys, SAS tokens or connection strings in code | Environment variables, profiles, instance roles, managed identity |
| zarr-2 `FSStore` / `LRUStoreCache`; Icechunk `StorageConfig` / `IcechunkStore.open_or_create` | Removed. Use `FsspecStore`; `icechunk.Repository` + `Session` |
| `simplecache::` with only `{"s3": {"anon": True}}` | Add `"asynchronous": True`, or reads fail with an event-loop `HTTPClientError` whenever the process already used a sync s3fs with the same options |
| `simplecache::` on sharded arrays or changing data | Unsharded, unchanging data only: shard reads raise `OSError` and cached objects never refresh |
| `filecache::` / `blockcache::` for Zarr on S3, GCS or Azure | Use `simplecache::`; through `FsspecStore` these re-download on every read |
| Sharding to cut GET requests | Bigger inner chunks cut GETs. A partial-shard read is an index GET plus one ranged GET per inner chunk; sharding cuts object and PUT counts |
| Parallel workers writing parts of one shard | Each partial write rewrites the whole shard; align write blocks to shards |
