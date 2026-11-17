# Common Issues and Solutions

## Contents

| Issue | Description |
|-------|-------------|
| 1. v2 vs v3 API Confusion | Mixing format conventions |
| 2. Metadata Not Persisting | Attributes disappearing on reopen |
| 3. Memory Errors with Large Arrays | OOM on read/write |
| 4. Concurrent Write Corruption | Silent corruption from parallel writes |
| 5. `.info_complete()` Slow | Performance on large stores |
| 6. Chunk/Access Pattern Mismatch | Slow reads from wrong chunk layout |
| 7. Cloud Auth Failures | Connection errors on remote stores |

---

## Issue 1: Zarr v2 vs v3 API Confusion

**Symptoms:** `KeyError`/`FileNotFoundError` opening stores; metadata files not found; compression codec errors; old tutorial code failing.

**Cause:** zarr-python 3 defaults to v3 format, but most existing data is v2. The two use different metadata files (`.zarray` vs `zarr.json`) and different chunk key formats. In zarr-python 3.1.5 the default compressor depends on the call: v3 arrays get Zstd; v2 arrays get Zstd from `zarr.create_array` but Blosc (lz4) from `Group.create_array`, which is the path xarray uses. Set `compressors=` explicitly rather than relying on either default. Some zarr-python 2 APIs fail under zarr-python 3 whatever the format: `FSStore`, synchronizers, `len(z)`, and `compressor=` in `create_array` (use `compressors=`).

**Solution:**

```python
# Check format version
z = zarr.open_array("data.zarr", mode="r")
print(f"Format: v{z.metadata.zarr_format}")

# Explicit v2 for backward compatibility
z = zarr.create_array(store="legacy.zarr", shape=(1000,), dtype="float32", zarr_format=2)

# Explicit v3 for new data (default)
z = zarr.create_array(store="modern.zarr", shape=(1000,), dtype="float32", zarr_format=3)
```

---

## Issue 2: Metadata Not Persisting

**Symptoms:** Attributes set on arrays/groups are gone after reopening the store.

**Cause:** Typically caused by opening the store in `mode="w"` instead of `mode="r+"` or `mode="a"`, which overwrites the entire store. Can also occur if the process is killed before metadata is flushed.

**Solution:**

```python
# WRONG: mode="w" overwrites everything
z = zarr.open_array("data.zarr", mode="w", shape=(100,), dtype="float32")  # wipes existing data

# RIGHT: mode="r+" to modify existing store
z = zarr.open_array("data.zarr", mode="r+")
z.attrs["new_attr"] = "preserved"

# RIGHT: mode="a" to open or create
z = zarr.open_array("data.zarr", mode="a", shape=(100,), dtype="float32")
```

---

## Issue 3: Memory Errors with Large Arrays

**Symptoms:** `MemoryError` or OOM kill when reading/writing arrays larger than RAM.

**Cause:** Attempting to read the entire array with `z[:]` or writing a full NumPy array at once.

**Solution:**

```python
# WRONG: loads entire array into memory
data = z[:]

# RIGHT: read in chunks
for i in range(0, z.shape[0], 1000):
    chunk = z[i:i+1000]
    process(chunk)

# RIGHT: use xarray + Dask for lazy access
import xarray as xr
ds = xr.open_zarr("data.zarr", chunks={"time": 30})  # lazy — no data loaded
result = ds["temperature"].mean(dim="time").compute()  # processes chunk-by-chunk
```

---

## Issue 4: Concurrent Write Corruption

**Symptoms:** After a parallel write, parts of the array hold the fill value or stale data; results differ between runs; checksums don't match.

**Cause:** Two writers touched the same chunk (or, in a sharded array, the same shard), even through slices that don't overlap. Each one reads the whole chunk or shard, changes its part and writes the whole object back, so the later write erases the other's values. zarr-python 3 has no locks to prevent this: `zarr.ThreadSynchronizer` and `zarr.ProcessSynchronizer` are gone (`AttributeError`), and `synchronizer=` is accepted but ignored with a `ZarrRuntimeWarning`.

**Solution:**

```python
z = zarr.open_array("data.zarr", mode="r")
block = z.shards or z.chunks   # the unit each writer must own
print(f"Give each writer whole blocks of {block}")

# Safe with chunks=(1000,): process 1 writes z[0:1000], process 2 writes z[1000:2000]
# Unsafe: process 1 writes z[0:500], process 2 writes z[500:1000] (same chunk)
```

If writers can't be aligned, route every write to a shared chunk through one process. Blosc thread settings under multiprocessing are covered by the **compression-codecs** skill.

---

## Issue 5: `.info_complete()` Slow on Large Arrays

**Symptoms:** `z.info_complete()` takes minutes; hangs on cloud-stored arrays.

**Cause:** `info_complete()` lists every stored chunk (or shard) object and sums their sizes to report initialized chunks and bytes stored. For arrays with millions of chunks (especially on cloud storage), this generates millions of requests.

**Solution:**

```python
# Use .info for quick checks (does NOT scan all chunks)
print(z.info)

# Only use .info_complete() on small arrays or locally
# For cloud stores, sample a subset instead:
sample = z[0:100, 0:100]
print(f"Sample dtype: {sample.dtype}, nbytes: {sample.nbytes}")
```

---

## Issue 6: Chunk Size Mismatch with Access Pattern

**Symptoms:** Reads are much slower than expected; high memory usage for small subsets; poor compression ratio.

**Cause:** Chunks are aligned for one access pattern but the actual reads follow a different pattern. Example: chunks of `(365, 30, 30)` (time-optimized) when maps at one time step, `z[t, :, :]`, are common: each map read decodes 72 chunks, 365 time steps each.

**Solution:**

```python
# Diagnose: check chunk layout
z = zarr.open_array("data.zarr", mode="r")
print(f"Shape: {z.shape}, Chunks: {z.chunks}")

# Sizes below are float32 for a (365, 180, 360) array.
# If primary access is spatial slices (fixed time, varying lat/lon):
# Use chunks=(8, 180, 360)   # ~2.1 MB

# If primary access is time series (fixed location, all times):
# Use chunks=(365, 30, 30)   # ~1.3 MB

# Balanced (mixed access): chunks=(30, 90, 180)   # ~1.9 MB
# Rule of thumb: at least 1 MB uncompressed per chunk, aligned with the dominant access pattern
```

→ See the **zarr-chunk-optimization** plugin for benchmarking tools.

---

## Issue 7: Cloud Store Authentication Failures

**Symptoms:** `403 Forbidden`, `NoCredentialsError`, `ExpiredTokenException`; works locally but fails on VM.

**Cause:** Missing credentials, expired tokens, or misconfigured IAM role.

**Solution:**

```python
from zarr.storage import FsspecStore

# Public data — use anonymous access
store = FsspecStore.from_url("s3://public-bucket/data.zarr", storage_options={"anon": True})

# Private — set env vars: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
# Or use a named profile:
store = FsspecStore.from_url("s3://bucket/data.zarr", storage_options={"profile": "research"})

# EC2/ECS — attach an IAM role, no config needed (auto-detected by s3fs)
```

→ See **cloud-storage-backends** skill for full auth reference across S3, GCS, and Azure.
