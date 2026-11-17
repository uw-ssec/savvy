# Common Issues and Solutions

## Contents

| Section | Lines | Description |
|---------|-------|-------------|
| Issue 1: Authentication Failures on S3 | 17–68 | Wrong credentials, expired tokens, requester-pays buckets |
| Issue 2: Slow Reads from Cloud Storage | 70–121 | Small chunks, low concurrency, missing caching |
| Issue 3: fsspec vs obstore — When to Use Which | 123–161 | Choosing the right backend library for your workload |
| Issue 4: Icechunk Version Conflicts | 163–201 | Concurrent commits to the same branch |
| Issue 5: CORS Errors When Accessing from Browser | 203–245 | Cross-origin errors when using browser-based Zarr clients |
| Issue 6: Slow Opens and Connection Timeouts | 247–279 | Many metadata requests without consolidated metadata |
| Issue 7: Cost Optimization for Cloud Zarr | 281–333 | Reducing cloud storage and request costs |

---

## Issue 1: Authentication Failures on S3

**Symptoms:**
- `ClientError: An error occurred (403) when calling the HeadObject operation: Forbidden`
- `NoCredentialsError: Unable to locate credentials`
- `ExpiredTokenException` after running for a while
- Works locally but fails on EC2 or in a container

**Cause:** The S3 credential chain is not finding valid credentials. Common reasons: environment variables not set, AWS profile not configured, IAM role not attached to the instance, temporary credentials have expired, or the bucket is requester-pays (anonymous and un-flagged requests get 403).

**Solution:**

```python
from zarr.storage import FsspecStore

# ── Check which credentials the AWS chain finds (s3fs uses the same chain) ──
import botocore.session
creds = botocore.session.get_session().get_credentials()
print(creds.method if creds else "no credentials found")  # e.g. "env", "shared-credentials-file", "iam-role"

# ── Fix 1: Set environment variables ──
# export AWS_ACCESS_KEY_ID=AKIA...
# export AWS_SECRET_ACCESS_KEY=...
# export AWS_DEFAULT_REGION=us-west-2

# ── Fix 2: Use a named profile from ~/.aws/config instead of keys in code ──
store = FsspecStore.from_url(
    "s3://my-bucket/data.zarr",
    storage_options={"profile": "research-team"},
)

# ── Fix 3: For public data, use anonymous access ──
store = FsspecStore.from_url(
    "s3://public-bucket/data.zarr",
    storage_options={"anon": True},
)

# ── Fix 4: For EC2/ECS, attach an IAM role and just use defaults ──
store = FsspecStore.from_url("s3://my-bucket/data.zarr")
# s3fs automatically uses instance metadata credentials

# ── Fix 5: Requester-pays bucket (needs credentials; you pay for requests and egress) ──
store = FsspecStore.from_url(
    "s3://requester-pays-bucket/data.zarr",
    storage_options={"requester_pays": True},
)

# ── Fix 6: Refresh expired session tokens ──
# Use `aws sts get-session-token` or configure credential_process in ~/.aws/config
```

---

## Issue 2: Slow Reads from Cloud Storage

**Symptoms:**
- Reading a small subset takes much longer than expected
- Network I/O dominates wall-clock time
- Cloud egress costs are unexpectedly high
- CPU utilization is low while reading

**Cause:** The most common causes are: (1) chunk sizes too small, generating thousands of HTTP requests for small objects; (2) too few requests in flight (zarr-python 3 defaults to 10); (3) no caching, so repeated reads re-download the same chunks.

**Solution:**

```python
import zarr
from zarr.storage import FsspecStore

# ── Diagnose: Check chunk sizes ──
root = zarr.open_group("s3://my-bucket/data.zarr", mode="r")
arr = root["temperature"]
chunk_bytes = arr.dtype.itemsize
for c in arr.chunks:  # for a sharded array this is the inner chunk, the read unit
    chunk_bytes *= c
print(f"Chunk size: {chunk_bytes / 1e6:.2f} MB uncompressed")
# Target: compressed chunk objects of 1 MB or more (1–100 MB) on object storage

# ── Fix 1: Re-chunk to larger chunks (one-time rewrite to a new path) ──
# Use the `rechunking` skill (zarr-chunk-optimization plugin); pick the shape
# with `chunking-strategy` first.

# ── Fix 2: Raise concurrency (zarr's limit and the s3fs connection pool) ──
zarr.config.set({"async.concurrency": 64})
store = FsspecStore.from_url(
    "s3://my-bucket/data.zarr",
    storage_options={"config_kwargs": {"max_pool_connections": 64}},
)

# ── Fix 3: Cache repeated reads (unsharded arrays; see patterns.md Pattern 6) ──
store = FsspecStore.from_url(
    "simplecache::s3://my-bucket/data.zarr",
    storage_options={
        "s3": {"anon": True, "asynchronous": True},
        "simplecache": {"cache_storage": "/tmp/zarr-cache"},
    },
)

# ── Fix 4: Use obstore for higher throughput ──
from obstore.store import S3Store
obs = S3Store.from_url("s3://my-bucket/data.zarr")
store = zarr.storage.ObjectStore(obs, read_only=True)
```

---

## Issue 3: fsspec vs obstore — When to Use Which

**Symptoms:**
- Uncertainty about which backend library to choose
- Performance differences between the two
- Feature gaps when switching backends

**Cause:** Both fsspec and obstore provide cloud storage access for Zarr, but they have different strengths and trade-offs.

**Solution:**

| Factor | fsspec (s3fs/gcsfs/adlfs) | obstore |
|--------|---------------------------|---------|
| **Language** | Pure Python | Rust (Python bindings) |
| **Throughput** | Good | Better (native async) |
| **Caching** | `simplecache::` only (see patterns.md Pattern 6) | No built-in caching |
| **Ecosystem** | Broad (pandas, Dask, xarray) | Growing |
| **Auth flexibility** | Many options (profiles, tokens, etc.) | Env vars, config dict |
| **S3-compatible** | Yes (endpoint_url) | Yes |
| **Maturity** | Very mature | Newer, rapidly improving |

```python
# Use fsspec when:
# - You need caching
# - You need broad auth options (profiles, SAS tokens)
# - You're already using fsspec elsewhere (Dask, xarray)

# Use obstore when:
# - Maximum throughput is critical
# - You're building a high-performance pipeline
# - You want lower per-request latency

# Use Icechunk when:
# - You need versioning, branching, or time-travel
# - Multiple writers need atomic commits
# - Regulatory requirements demand audit trails
```

---

## Issue 4: Icechunk Version Conflicts

**Symptoms:**
- `icechunk.ConflictError` from `session.commit()`
- `icechunk.RebaseFailedError` after rebasing
- `ReadOnlyError`, or `ValueError: Store is read-only but mode is 'r+'`, when writing through a session that was already committed

**Cause:** Icechunk uses optimistic concurrency. A commit fails with `ConflictError` if another writer moved the branch since the session was opened. A rebase replays the session's changes on the new tip, and fails with `RebaseFailedError` when both writers changed the same chunks or metadata. A committed session is read-only; open a new writable session for the next commit.

**Solution:**

```python
import icechunk

storage = icechunk.s3_storage(bucket="my-bucket", prefix="data", from_env=True)
repo = icechunk.Repository.open(storage)

# ── Fix 1: Rebase and retry when writers touched different chunks ──
def commit_with_rebase(session, message, max_tries=3):
    for attempt in range(max_tries):
        try:
            return session.commit(message)
        except icechunk.ConflictError:
            if attempt == max_tries - 1:
                raise
            # Raises RebaseFailedError if both writers changed the same chunks
            session.rebase(icechunk.ConflictDetector())

# ── Fix 2: Give each parallel writer its own branch ──
tip = repo.lookup_branch("main")
repo.create_branch("writer-1", snapshot_id=tip)
repo.create_branch("writer-2", snapshot_id=tip)
writer_1 = repo.writable_session("writer-1")
# ... write data to writer_1.store ...
writer_1.commit("Writer 1 batch")
# Merge branches later (application-level merge)
```

---

## Issue 5: CORS Errors When Accessing from Browser

**Symptoms:**
- `Access to fetch at '...' has been blocked by CORS policy` (or `Access to XMLHttpRequest ...`)
- JavaScript Zarr clients (zarrita.js, zarr.js) cannot read the store
- Works from Python but fails from a web application

**Cause:** The cloud storage bucket does not have CORS configured to allow requests from the web application's origin.

**Solution:**

S3: save this as `cors.json` (plain JSON, no comments) and apply it with `aws s3api put-bucket-cors --bucket my-bucket --cors-configuration file://cors.json`.

```json
{
    "CORSRules": [
        {
            "AllowedHeaders": ["*"],
            "AllowedMethods": ["GET", "HEAD"],
            "AllowedOrigins": ["https://my-app.example.com"],
            "ExposeHeaders": ["ETag", "Content-Length", "Content-Range"],
            "MaxAgeSeconds": 3600
        }
    ]
}
```

GCS uses a different format. Save this as `cors-gcs.json` and apply it with `gcloud storage buckets update gs://my-bucket --cors-file=cors-gcs.json`.

```json
[
    {
        "origin": ["https://my-app.example.com"],
        "method": ["GET", "HEAD"],
        "responseHeader": ["Content-Type", "Content-Length", "Content-Range", "ETag"],
        "maxAgeSeconds": 3600
    }
]
```

Azure Blob: set CORS rules under Storage Account > Resource sharing (CORS) > Blob service.

---

## Issue 6: Slow Opens and Connection Timeouts

**Symptoms:**
- Opening a group, or `xr.open_zarr`, takes seconds to minutes before any data is read
- `TimeoutError`, `ConnectTimeoutError` or `ReadTimeoutError` while opening

**Cause:** Without consolidated metadata, zarr-python 3 lists each group and reads one metadata object per array and group (more for v2), one request each. A store with hundreds of variables or nested groups pays hundreds of 20–100 ms round trips. The chunk count does not matter: zarr never lists chunks when opening, so sharding does not speed up opens.

**Solution:**

```python
import zarr

# ── Fix 1: Consolidate metadata ──
# Run once after creating or updating the store, and again after adding arrays
# or changing shapes. v2 writes .zmetadata; v3 embeds it in the root zarr.json
# (a zarr-python extension that other implementations may ignore).
zarr.consolidate_metadata("s3://my-bucket/data.zarr")

# Readers pick it up automatically; open_consolidated fails if it is missing
root = zarr.open_consolidated("s3://my-bucket/data.zarr", mode="r")

# ── Fix 2: Increase s3fs timeouts ──
from zarr.storage import FsspecStore
store = FsspecStore.from_url(
    "s3://my-bucket/data.zarr",
    storage_options={
        "config_kwargs": {"connect_timeout": 60, "read_timeout": 120},
    },
)
```

---

## Issue 7: Cost Optimization for Cloud Zarr

**Symptoms:**
- Unexpectedly high cloud storage bills
- S3 GET request costs dominate (not storage costs)
- Egress charges from reading data across regions

**Cause:** Cloud storage costs come from three sources: (1) storage volume, (2) number of requests (GET/PUT), and (3) data transfer (egress). Small Zarr chunks generate many requests; cross-region reads incur egress charges.

**Solution:**

```python
import zarr

# ── Strategy 1: Increase chunk size to reduce request count ──
# 100x100 float32 chunks = 40 KB each = too many requests
# 1000x1000 float32 chunks = 4 MB each = better
arr = zarr.create_array(
    store="s3://my-bucket/cost-optimized.zarr",
    shape=(50000, 50000),
    chunks=(1000, 1000),  # ~4 MB per chunk
    dtype="float32",
)

# ── Strategy 2: Use sharding to reduce object and PUT counts ──
# The inner chunk (chunks=) is the read unit; the shard (shards=) is the stored
# object. Reading part of a shard costs one GET for its index plus one ranged GET
# per inner chunk, so GETs only drop for whole-shard reads. Size inner chunks for
# the reads (see `chunking-strategy`), and write whole shards.
arr = zarr.create_array(
    store="s3://my-bucket/sharded.zarr",
    shape=(50000, 50000),
    chunks=(500, 500),    # 1 MB inner chunks
    shards=(5000, 5000),  # 100 MB shards: 100 objects instead of 10,000
    dtype="float32",
)

# ── Strategy 3: Use S3 Intelligent-Tiering for infrequently accessed data ──
# Configure via S3 bucket lifecycle policy (not Zarr-specific)

# ── Strategy 4: Co-locate compute and storage ──
# Run analysis in the same region as the data to avoid egress
# e.g., use us-west-2 EC2 for data stored in us-west-2 S3

# ── Strategy 5: Use compression to reduce storage and transfer ──
arr = zarr.create_array(
    store="s3://my-bucket/compressed.zarr",
    shape=(50000, 50000),
    chunks=(1000, 1000),
    dtype="float32",
    compressors=zarr.codecs.ZstdCodec(level=5),  # good ratio
)
```
