# Cloud Storage Backend Patterns

## Contents

| Section | Lines | Description |
|---------|-------|-------------|
| Pattern 1: S3 Backend with fsspec | 16–80 | Anonymous, requester-pays, profile and S3-compatible (MinIO) access |
| Pattern 2: GCS Backend with fsspec | 82–120 | Anonymous, service account and application default credentials |
| Pattern 3: Azure Blob Backend with fsspec | 122–157 | Environment credentials, managed identity, public containers |
| Pattern 4: High-Performance Cloud I/O with obstore | 159–216 | The Rust-based obstore library through `zarr.storage.ObjectStore` |
| Pattern 5: Icechunk Versioned Storage on S3 | 218–269 | Commits, branches, tags and time-travel reads |
| Pattern 6: Read-Through Caching for Remote Stores | 271–306 | What caches through zarr-python 3, and what does not |

---

## Pattern 1: S3 Backend with fsspec

**Description:** Access Zarr stores on Amazon S3 using the fsspec/s3fs backend. Supports anonymous access for public datasets, the standard AWS credential chain (environment variables, profiles, IAM roles), requester-pays buckets and S3-compatible endpoints.

**When to use:**
- Reading public datasets hosted on S3 (Pangeo CMIP6, NOAA, NASA)
- Writing research outputs to an S3 bucket
- Standard AWS credential chain (env vars, profiles, IAM roles)

**Code example:**

```python
import numpy as np
import zarr
from zarr.storage import FsspecStore

# ── Read a public Zarr store anonymously (Pangeo CMIP6, Zarr v2, us-west-2) ──
store = FsspecStore.from_url(
    "s3://cmip6-pds/CMIP6/CMIP/NOAA-GFDL/GFDL-ESM4/historical/r1i1p1f1/Omon/tos/gn/v20190726/",
    storage_options={"anon": True},
    read_only=True,
)
root = zarr.open_group(store=store, mode="r")
for name, arr in root.arrays():
    print(name, arr.shape, arr.chunks, arr.dtype)

# ── Write to a private bucket (credentials from the AWS credential chain) ──
store = FsspecStore.from_url("s3://my-research-bucket/experiment-001.zarr")
root = zarr.open_group(store=store, mode="w")
arr = root.create_array(
    "results",
    shape=(10000, 500),
    chunks=(1000, 500),  # 4 MB float64 chunks
    dtype="float64",
)
arr[:] = np.random.randn(10000, 500)
root.attrs["experiment"] = "turbulence-sim-001"
print(f"Wrote {arr.nbytes / 1e6:.1f} MB to S3")

# ── Read with a named AWS profile (~/.aws/config) ──
store = FsspecStore.from_url(
    "s3://shared-bucket/team-data.zarr",
    storage_options={"profile": "research-team"},
    read_only=True,
)

# ── Requester-pays bucket: you are billed for the requests; needs credentials ──
store = FsspecStore.from_url(
    "s3://requester-pays-bucket/data.zarr",
    storage_options={"requester_pays": True},
    read_only=True,
)

# ── S3-compatible endpoint (MinIO, Ceph, etc.) ──
# Keys come from AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY in the environment,
# never from source code.
store = FsspecStore.from_url(
    "s3://local-bucket/data.zarr",
    storage_options={"endpoint_url": "http://localhost:9000"},
)
```

`FsspecStore.from_url` defaults to `read_only=False`; pass `read_only=True` for stores you only read.

---

## Pattern 2: GCS Backend with fsspec

**Description:** Access Zarr stores on Google Cloud Storage using the fsspec/gcsfs backend. Supports anonymous access, service account keys, and application default credentials.

**When to use:**
- Reading public GCS-hosted datasets (Google Earth Engine exports, ARCO-ERA5)
- Writing outputs to a GCS bucket from a Compute Engine VM or Cloud Run job

**Code example:**

```python
import zarr
from zarr.storage import FsspecStore

# ── Anonymous access to public data (gcsfs uses token="anon"; it ignores anon=True) ──
store = FsspecStore.from_url(
    "gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3",
    storage_options={"token": "anon"},
    read_only=True,
)
root = zarr.open_group(store=store, mode="r")
print(sorted(root.array_keys())[:10])

# ── Service account JSON key (path to the file, not its contents) ──
store = FsspecStore.from_url(
    "gs://my-project-bucket/output.zarr",
    storage_options={"token": "/path/to/service-account.json"},
)

# ── Application default credentials (gcloud auth application-default login) ──
store = FsspecStore.from_url(
    "gs://my-project-bucket/output.zarr",
    storage_options={"token": "google_default"},
)
root = zarr.open_group(store=store, mode="w")
arr = root.create_array("data", shape=(5000, 5000), chunks=(500, 500), dtype="float32")
```

---

## Pattern 3: Azure Blob Backend with fsspec

**Description:** Access Zarr stores on Azure Blob Storage using the fsspec/adlfs backend. adlfs reads `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_STORAGE_ACCOUNT_NAME`, `AZURE_STORAGE_ACCOUNT_KEY` and `AZURE_STORAGE_SAS_TOKEN` from the environment. With none of those set, it falls back to `DefaultAzureCredential` (managed identity, `az login`, service principal env vars).

**When to use:**
- Reading or writing Zarr data in Azure Blob containers
- Running workloads on Azure VMs, AKS, or Azure Functions with managed identity

**Code example:**

```python
import zarr
from zarr.storage import FsspecStore

# ── Connection string, account key or SAS token from the environment ──
# export AZURE_STORAGE_CONNECTION_STRING=...   (or ACCOUNT_NAME + ACCOUNT_KEY / SAS_TOKEN)
store = FsspecStore.from_url("az://my-container/data.zarr", read_only=True)
root = zarr.open_group(store=store, mode="r")

# ── Managed identity or az login (DefaultAzureCredential) ──
store = FsspecStore.from_url(
    "az://my-container/data.zarr",
    storage_options={"account_name": "mystorageaccount", "anon": False},
)

# ── Public container ──
store = FsspecStore.from_url(
    "az://public-container/data.zarr",
    storage_options={"account_name": "publicaccount", "anon": True},
    read_only=True,
)
```

Passing `connection_string`, `account_key` or `sas_token` in `storage_options` also works, but load the value from a secret store or environment variable rather than writing it into code.

---

## Pattern 4: High-Performance Cloud I/O with obstore

**Description:** Use the Rust-based obstore library through `zarr.storage.ObjectStore`. obstore has its own HTTP stack and reads `AWS_*`, `GOOGLE_*` and `AZURE_*` environment variables in every constructor. Request parallelism is still capped by zarr's `async.concurrency` setting (default 10).

**When to use:**
- Large-scale analysis pipelines that are I/O bound
- Already using obstore in other parts of a pipeline (e.g., with GeoParquet)

**Code example:**

```python
import numpy as np
import zarr
from obstore.store import AzureStore, GCSStore, S3Store

# ── Public S3 data: skip request signing ──
obs = S3Store.from_url(
    "s3://cmip6-pds/CMIP6/CMIP/NOAA-GFDL/GFDL-ESM4/historical/r1i1p1f1/Omon/tos/gn/v20190726",
    region="us-west-2",
    skip_signature=True,
)
root = zarr.open_group(store=zarr.storage.ObjectStore(obs, read_only=True), mode="r")

# ── Private S3 (credentials from the environment) ──
obs_s3 = S3Store.from_url("s3://my-bucket/data.zarr", config={"AWS_REGION": "us-west-2"})
store = zarr.storage.ObjectStore(obs_s3, read_only=True)

# ── GCS with a service account key file ──
obs_gcs = GCSStore.from_url(
    "gs://my-bucket/data.zarr",
    config={"GOOGLE_SERVICE_ACCOUNT": "/path/to/key.json"},
)
store = zarr.storage.ObjectStore(obs_gcs, read_only=True)

# ── Azure (account key or SAS token from AZURE_STORAGE_* env vars) ──
obs_az = AzureStore.from_url(
    "az://my-container/data.zarr",
    config={"AZURE_STORAGE_ACCOUNT_NAME": "mystorageaccount"},
)
store = zarr.storage.ObjectStore(obs_az, read_only=True)

# ── Write with obstore ──
obs_w = S3Store.from_url("s3://my-bucket/output.zarr")
store = zarr.storage.ObjectStore(obs_w)
root = zarr.open_group(store=store, mode="w")
arr = root.create_array("field", shape=(5000, 5000), chunks=(500, 500), dtype="float32")
arr[:] = np.random.randn(5000, 5000).astype("float32")

# ── Client tuning ──
obs = S3Store.from_url(
    "s3://my-bucket/data.zarr",
    client_options={"timeout": "60s", "connect_timeout": "5s"},
)
```

Config keys are case-insensitive (`AWS_REGION` and `region` both work). A `GOOGLE_SERVICE_ACCOUNT` path is read when the store is constructed, so a wrong path fails immediately.

---

## Pattern 5: Icechunk Versioned Storage on S3

**Description:** Icechunk adds Git-like semantics (commits, branches, tags, time-travel reads) to Zarr on object storage. A `Repository` holds the history; each write happens in a `Session` whose `.store` you pass to zarr. Shown with the Icechunk 1.x/2.x API; the 0.1 names `StorageConfig` and `IcechunkStore.open_or_create` no longer exist.

**When to use:**
- Datasets that are updated incrementally and you need to track each revision
- Several writers that need atomic commits
- Reproducibility requirements (read data as it was at a specific snapshot)

**Code example:**

```python
import icechunk
import numpy as np
import zarr

# ── Open or create a repository on S3 (credentials from the environment) ──
storage = icechunk.s3_storage(
    bucket="my-bucket",
    prefix="versioned-climate",
    region="us-west-2",
    from_env=True,
)
repo = icechunk.Repository.open_or_create(storage)

# ── Write initial data on main and commit ──
session = repo.writable_session("main")
root = zarr.open_group(store=session.store, mode="w")
temp = root.create_array("temperature", shape=(365, 180, 360), chunks=(30, 180, 360), dtype="float32")
temp[:] = np.random.randn(365, 180, 360).astype("float32")
root.attrs["source"] = "CESM2 Model Output"
first_commit = session.commit("Initial temperature data for 2024")  # session is read-only afterwards

# ── Change data on a branch ──
repo.create_branch("bias-correction", snapshot_id=first_commit)
branch = repo.writable_session("bias-correction")
temp = zarr.open_array(store=branch.store, path="temperature", mode="r+")
temp[:] = temp[:] - 0.5
branch.commit("Apply -0.5 K bias correction")

# ── main is unchanged ──
main = repo.readonly_session(branch="main")
print(zarr.open_array(store=main.store, path="temperature", mode="r")[:10, 0, 0])

# ── Tag a release and read it back later ──
repo.create_tag("v1.0", snapshot_id=first_commit)
v1 = repo.readonly_session(tag="v1.0")
```

For local tests, `icechunk.local_filesystem_storage(path)` or `icechunk.in_memory_storage()` stand in for `s3_storage`. Skip `zarr.consolidate_metadata` on an Icechunk store: it raises `TypeError` because the store does not support consolidated metadata.

---

## Pattern 6: Read-Through Caching for Remote Stores

**Description:** zarr-python 3 has no `LRUStoreCache`. Caching comes from an fsspec caching protocol chained in front of the URL, or from a store wrapper. Only `simplecache::` reliably caches through `FsspecStore` on S3, GCS or Azure.

| Layer | Through `FsspecStore` on s3/gs/az (zarr 3.1, fsspec 2026.x) |
|---|---|
| `simplecache::` | Caches whole objects on first read. Needs `"asynchronous": True` in the target options. Sharded arrays fail (`OSError` on the shard-index read). Never re-checks the remote |
| `filecache::` | Writes cache files but re-downloads on every read |
| `blockcache::` | Passes reads straight through; nothing is cached |
| `zarr.experimental.cache_store.CacheStore` | Experimental. Works for unsharded arrays; on sharded arrays it caches byte ranges as whole objects and reads fail |

**When to use:**
- Repeatedly reading the same parts of an unsharded remote dataset that does not change
- Prototyping analysis on a remote dataset before scaling to cloud compute

**Code example:**

```python
import zarr
from zarr.storage import FsspecStore

store = FsspecStore.from_url(
    "simplecache::s3://cmip6-pds/CMIP6/CMIP/NOAA-GFDL/GFDL-ESM4/historical/r1i1p1f1/Omon/tos/gn/v20190726/",
    storage_options={
        "s3": {"anon": True, "asynchronous": True},  # asynchronous=True avoids an event-loop clash
        "simplecache": {"cache_storage": "/tmp/zarr-cache"},  # kept across runs; delete to refresh
    },
    read_only=True,
)
root = zarr.open_group(store=store, mode="r")
lat = root["lat"][:]  # first read downloads; later reads come from /tmp/zarr-cache
```

Without `"asynchronous": True`, the read fails with an `HTTPClientError` whenever the process already holds a synchronous s3fs instance with the same options (for example from an earlier `s3fs.S3FileSystem(anon=True).ls(...)`). For gcsfs use the `"gs"` key, for adlfs `"az"`.

The cache is keyed by path and never expires: after the remote store is rewritten, delete the cache directory or reads return old chunks and old metadata.
