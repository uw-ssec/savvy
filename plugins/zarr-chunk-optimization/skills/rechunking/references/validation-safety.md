# Validation & Safety — Deep Reference

## Contents

| Section | Lines | Description |
|---------|-------|-------------|
| Pre-Rechunk Validation | 16–113 | Checks to perform before starting a rechunking operation |
| Post-Rechunk Validation | 114–195 | Verifying that the rechunked output matches the source |
| Sample-First Strategy | 196–277 | Rechunking a subset before committing to the full dataset |
| Rollback Patterns | 278–353 | Path swap, backup strategies, and recovery procedures |
| Data Integrity Checks | 354–408 | Checksum comparison, sampled validation, NaN handling |
| Common Failure Modes | 409–491 | OOM during rechunk, interrupted writes, and corrupted chunks |

---

## Pre-Rechunk Validation

Before starting any rechunking operation, validate the following conditions. `scripts/rechunk.py` checks steps 1 and 3, and step 6 for local paths only. Do the rest yourself.

### 1. Source Integrity

Confirm the source Zarr store is readable and contains valid data:

```python
import zarr

source = zarr.open("/data/source.zarr", mode="r")
assert isinstance(source, zarr.Array), "Source is not a Zarr array"
print(f"Zarr format: {source.metadata.zarr_format}")
print(f"Shape: {source.shape}")
print(f"Chunks: {source.chunks}  Shards: {source.shards}")
print(f"Dtype: {source.dtype}")
print(f"Compressors: {source.compressors}")
```

`Array.compressor` raises on Zarr v3 arrays under zarr-python 3; use `compressors`. If the source is a Zarr group, `scripts/rechunk.py` rejects it: verify each array independently and use the xarray or array-by-array route in rechunking-strategies.md.

### 2. Disk Space

Estimate the output size and confirm sufficient free space:

```python
import numpy as np
import shutil

source = zarr.open("/data/source.zarr", mode="r")
uncompressed_bytes = np.prod(source.shape) * source.dtype.itemsize
estimated_gb = uncompressed_bytes / (1024**3)

# Check available space at output location
free_gb = shutil.disk_usage("/data").free / (1024**3)

print(f"Estimated output size: {estimated_gb:.1f} GB (uncompressed)")
print(f"Available disk space: {free_gb:.1f} GB")

# Need space for output + intermediate store
assert free_gb > estimated_gb * 2.5, "Insufficient disk space (need 2.5x dataset size)"
```

The 2.5x multiplier accounts for the output (1x) plus intermediate storage (1x) plus headroom (0.5x).

### 3. Chunk Compatibility

Verify that target chunk dimensions match the array dimensions:

```python
target_chunks = (50, 512, 512)
assert len(target_chunks) == len(source.shape), \
    f"Dimension mismatch: target has {len(target_chunks)} dims, source has {len(source.shape)}"

for i, (chunk, extent) in enumerate(zip(target_chunks, source.shape)):
    assert chunk > 0, f"Chunk size must be positive (dim {i}: {chunk})"
    if chunk > extent:
        print(f"Warning: chunk size {chunk} exceeds extent {extent} for dim {i}")
```

### 4. Compression Compatibility

`scripts/rechunk.py` keeps the source codecs and has no option to change them. If you change codecs through `zarr.from_array(compressors=...)` or xarray `encoding`, round-trip a small array with them first:

```python
import zarr
from zarr.codecs import BloscCodec

test = zarr.create_array(zarr.storage.MemoryStore(), shape=(100,), dtype=source.dtype,
                         compressors=BloscCodec(cname="zstd", clevel=3))
test[:] = np.arange(100).astype(source.dtype)
assert np.array_equal(test[:], np.arange(100).astype(source.dtype))
```

### 5. Cloud Credentials

For S3/GCS sources or outputs, verify credentials before starting:

```python
import zarr

# Opening the array checks credentials and finds the metadata for either format
# (zarr.json for v3, .zarray for v2).
source = zarr.open_array("s3://bucket/source.zarr", mode="r")
```

For the output, list the target prefix too: the script checks for an existing output on local paths only.

### 6. Output Path Safety

Confirm the output path does not contain valuable data that would be overwritten:

```bash
# Check if output path exists
ls -la /data/output.zarr 2>/dev/null && echo "WARNING: Output path exists" || echo "Output path is clear"
```

## Post-Rechunk Validation

After rechunking completes, validate the output thoroughly before swapping it into production.

### Automatic Validation (Built into rechunk.py)

The `rechunk.py` script automatically checks:

1. **Shape match:** `output.shape == source.shape`
2. **Chunk match:** `output.chunks == target_chunks`
3. **Element count:** `output.size == source.size`

These checks catch gross errors (wrong dimensions, truncated data) but do not verify individual values.

### Manual Validation (Recommended)

#### Dtype Verification

```python
source = zarr.open("/data/source.zarr", mode="r")
output = zarr.open("/data/output.zarr", mode="r")

assert source.dtype == output.dtype, \
    f"Dtype mismatch: source={source.dtype}, output={output.dtype}"
```

#### Metadata Preservation

```python
# Check all user-defined attributes were preserved
for key in source.attrs:
    assert key in output.attrs, f"Missing attribute: {key}"
    assert source.attrs[key] == output.attrs[key], \
        f"Attribute mismatch for '{key}': {source.attrs[key]} != {output.attrs[key]}"
```

#### Value Comparison

Rechunking must be bit-exact, so compare values exactly. Iterate over the **output's** chunk grid: each block then reads one output chunk (or shard) once. Looping over single indices instead (`source[i]`) re-reads every output chunk once per index it spans.

```python
import itertools
import numpy as np

def values_equal(a, b):
    """Exact comparison where NaN == NaN for float and complex data."""
    if np.iscomplexobj(a) or np.iscomplexobj(b):
        # equal_nan=True on complex data ignores the other component of a NaN
        return values_equal(a.real, b.real) and values_equal(a.imag, b.imag)
    return np.array_equal(a, b, equal_nan=np.issubdtype(a.dtype, np.inexact))


def iter_blocks(arr):
    """Yield slices covering arr one stored object (shard, else chunk) at a time."""
    block = arr.shards or arr.chunks
    starts = [range(0, n, b) for n, b in zip(arr.shape, block)]
    for start in itertools.product(*starts):
        yield tuple(slice(s, s + b) for s, b in zip(start, block))


def random_blocks(arr, k, seed=0):
    """Yield k random block slices from arr's stored-object grid."""
    rng = np.random.default_rng(seed)
    block = arr.shards or arr.chunks
    for _ in range(k):
        yield tuple(slice(i * b, (i + 1) * b)
                    for n, b in zip(arr.shape, block)
                    for i in [int(rng.integers(-(-n // b)))])


# Full check: every output block
for sl in iter_blocks(output):
    assert values_equal(source[sl], output[sl]), f"Mismatch in {sl}"

# Very large stores: a sample of whole blocks checks far more values per read
# than single random elements
for sl in random_blocks(output, k=50):
    assert values_equal(source[sl], output[sl]), f"Mismatch in {sl}"
```

Without `equal_nan=True`, `np.array_equal` reports identical float data with NaN fill values as a mismatch. Keep it off for integer and string data; `equal_nan=True` raises on strings. On complex data it treats `nan+1j` and `nan+999j` as equal, so `values_equal` compares the real and imaginary parts separately.

## Sample-First Strategy

Always rechunk a small sample before processing the full dataset. This catches configuration errors, estimates actual rechunking speed, and validates the output format — all within minutes instead of hours.

### Creating a Sample

Extract a block that spans two **target** chunks along every axis. A thin slab along the first axis cannot exercise a target chunk that is long on that axis, such as a time-series layout.

```python
import zarr
import numpy as np

target = (50, 512, 512)  # the --chunks you will use on the full dataset
source = zarr.open_array("/data/full_dataset.zarr", mode="r")

region = tuple(slice(0, min(n, 2 * c)) for n, c in zip(source.shape, target))
data = source[region]  # loads 2**ndim target chunks into memory

sample = zarr.create_array(
    "/tmp/rechunk_sample.zarr",
    shape=data.shape,
    chunks=source.chunks,
    dtype=source.dtype,
    zarr_format=source.metadata.zarr_format,
    compressors=source.compressors,
    overwrite=True,
)
sample[:] = data
sample.attrs.update(source.attrs)
```

### Rechunking the Sample

```bash
python scripts/rechunk.py \
    --input /tmp/rechunk_sample.zarr \
    --output /tmp/rechunk_sample_output.zarr \
    --chunks "50,512,512" \
    --summary /tmp/rechunk_sample_summary.json
```

### Validating the Sample

```python
source_sample = zarr.open("/tmp/rechunk_sample.zarr", mode="r")
output_sample = zarr.open("/tmp/rechunk_sample_output.zarr", mode="r")

# Full comparison is feasible for small samples
assert source_sample.shape == output_sample.shape
assert source_sample.dtype == output_sample.dtype
assert values_equal(source_sample[:], output_sample[:])  # from Value Comparison above
print("Sample validation passed")
```

### Estimating Full Rechunk Time

Use the sample timing to estimate the full dataset rechunking time:

```python
import json

with open("/tmp/rechunk_sample_summary.json") as f:  # the --summary path; open() does not expand globs
    summary = json.load(f)

sample_time = summary["actual_time_seconds"]
sample_elements = np.prod(summary["array_shape"])
full_elements = np.prod(source.shape)

estimated_full_time = sample_time * (full_elements / sample_elements)
print(f"Estimated full rechunk time: {estimated_full_time / 3600:.1f} hours")
```

This is a rough linear extrapolation: the sample time includes fixed start-up cost, and a cloud store adds per-request latency that a local sample does not show.

### Decision Criteria

After validating the sample:

- **Proceed** if: shape/dtype/values match, estimated time is acceptable, memory usage is within budget.
- **Abort** if: values differ, memory usage exceeds budget, estimated time is unacceptable.
- **Adjust** if: rechunking works but is too slow. Under zarr-python 3 the script copies sequentially and `--max-mem` has no effect; switch to `zarr.from_array` with higher `async.concurrency`, or to dask (see rechunking-strategies.md).

## Rollback Patterns

### Pattern 1: Swap Paths (Recommended)

Write to a new location, verify, then swap paths:

```bash
# Step 1: Rechunk to new path
python scripts/rechunk.py --input /data/dataset.zarr \
                  --output /data/dataset_new.zarr \
                  --chunks "50,512,512"

# Step 2: Verify with the Post-Rechunk Validation code above (there is no bundled validate script)

# Step 3: Swap
mv /data/dataset.zarr /data/dataset_old.zarr
mv /data/dataset_new.zarr /data/dataset.zarr

# Step 4: Keep backup until production is confirmed stable
# (days or weeks later)
rm -rf /data/dataset_old.zarr
```

Each `mv` within one filesystem is an atomic rename, but the swap takes two, so readers briefly see no `/data/dataset.zarr`. Stop readers during the swap, or use the symlink pattern below, where one rename switches readers. A move across filesystems copies the data and is not atomic. Object stores (S3, GCS) have no rename at all: point readers at the new prefix rather than moving objects.

### Pattern 2: Versioned Backups

For datasets that are rechunked periodically, use versioned paths:

```bash
/data/dataset_v1.zarr          # Original
/data/dataset_v2.zarr          # First rechunk
/data/dataset_v3.zarr          # Second rechunk
/data/dataset_current.zarr -> dataset_v3.zarr  # Symlink to current version
```

Update the symlink atomically: create a temporary link in the same directory, then rename it over the old one.

```python
import os

os.symlink("/data/dataset_v3.zarr", "/data/.dataset_current.zarr.tmp")
os.replace("/data/.dataset_current.zarr.tmp", "/data/dataset_current.zarr")
```

Don't use `ln -sfn`: BSD `ln`, as on macOS, deletes the old link before creating the new one, so readers can find no path.

Readers should open the resolved path, `zarr.open(os.path.realpath("/data/dataset_current.zarr"))`. An array opened through the symlink resolves it again for every chunk, so a swap during a long read mixes chunks from two versions.

### Pattern 3: Cloud Versioning

For S3-hosted datasets, enable bucket versioning to provide automatic rollback:

```bash
aws s3api put-bucket-versioning \
    --bucket my-bucket \
    --versioning-configuration Status=Enabled
```

With versioning enabled, overwritten objects can be restored to previous versions. This provides a safety net but should not replace the write-verify-swap pattern.

### Pattern 4: Copy-on-Write Filesystems

On ZFS or Btrfs, use filesystem snapshots before rechunking:

```bash
# ZFS
zfs snapshot tank/data@before-rechunk

# Rechunk
python scripts/rechunk.py --input /data/dataset.zarr --output /data/dataset_new.zarr --chunks "50,512,512"

# If something goes wrong
zfs rollback tank/data@before-rechunk
```

## Data Integrity Checks

### Checksum Comparison

A checksum reads as much data as the direct comparison above. It earns its cost when source and output are not readable at the same time, for example when the hash is recorded before the source moves:

```python
import hashlib
import itertools
import zarr
import numpy as np

def compute_array_checksum(path: str, block: tuple) -> str:
    """SHA-256 of a Zarr array's values, read block by block in a fixed order."""
    arr = zarr.open_array(path, mode="r")
    hasher = hashlib.sha256()
    starts = [range(0, n, b) for n, b in zip(arr.shape, block)]
    for start in itertools.product(*starts):
        sl = tuple(slice(s, s + b) for s, b in zip(start, block))
        hasher.update(np.ascontiguousarray(arr[sl]).tobytes())
    return hasher.hexdigest()

# Hash both arrays over the SAME block grid (here the output's chunks),
# or the byte order differs and identical data hashes differently.
block = zarr.open_array("/data/output.zarr", mode="r").chunks
source_hash = compute_array_checksum("/data/source.zarr", block)
output_hash = compute_array_checksum("/data/output.zarr", block)

assert source_hash == output_hash, "Checksum mismatch — data corruption detected"
print(f"Checksum match: {source_hash}")
```

### Sampled Validation for Very Large Stores

Summary statistics (mean, std, min, max) are not a cheaper substitute: they read every value, the same as an exact comparison, and `np.mean` returns NaN when a slice holds NaN. To save time, read less data instead: compare a random sample of whole output blocks exactly with `random_blocks` from Value Comparison above.

### NaN and Special Value Handling

Rechunking should preserve NaN, Inf, and other special floating-point values:

```python
src_data = source[0]
dst_data = output[0]

# Check NaN positions match
assert np.array_equal(np.isnan(src_data), np.isnan(dst_data)), "NaN positions differ"

# Check Inf positions match
assert np.array_equal(np.isinf(src_data), np.isinf(dst_data)), "Inf positions differ"

# Check finite values match
finite_mask = np.isfinite(src_data)
assert np.array_equal(src_data[finite_mask], dst_data[finite_mask]), "Finite values differ"
```

## Common Failure Modes

### 1. Out-of-Memory (OOM) During Rechunking

**Symptoms:** Process killed by OS (exit code 137 on Linux), `MemoryError` exception, system becomes unresponsive.

**Causes:**
- `--max-mem` set too high for available system memory.
- Target chunk size is very large, causing individual chunks to exceed available RAM.
- Memory leak in compression codec (rare but possible with certain Blosc configurations).

**Prevention:**
- On the `rechunker` path, `--max-mem` is per task: keep `max_mem × concurrent tasks` well under RAM.
- On the fallback path (zarr-python 3), memory follows the target chunk and the source chunks it overlaps, not `--max-mem`. See rechunking-strategies.md, Memory Profile.
- Verify that individual target chunks fit in memory: `chunk_elements × bytes_per_element < available_RAM / 4`.
- Measure peak memory of the sample rechunk with `/usr/bin/time -v` (Linux) or `/usr/bin/time -l` (macOS). `--verbose` does not report memory.

**Recovery:** The output is likely incomplete or corrupted. Delete it and restart with a lower `--max-mem`, or with smaller target chunks on the fallback path.

### 2. Interrupted Writes

**Symptoms:** Rechunking process terminated (Ctrl+C, network disconnect, system crash) before completion.

**Causes:**
- User interruption during a long rechunking operation.
- Network timeout during cloud storage write.
- System shutdown or crash.

**Prevention:**
- Use the write-to-new-location pattern so the source is never affected.
- For cloud storage, use a reliable network connection and consider running on a cloud instance in the same region as the storage.

**Recovery:** Delete the incomplete output and restart. The source data is safe (assuming you wrote to a new location).

### 3. Corrupted Chunks

**Symptoms:** `zarr.open()` succeeds but reading specific chunks raises exceptions (`ValueError`, `RuntimeError` from the compressor).

**Causes:**
- Partial write to a chunk file (interrupted during compression or flush).
- Disk full during write (chunk file created but truncated).
- Cloud storage eventual consistency issues (mostly historical — modern S3 is strongly consistent).

**Detection:**

```python
import zarr

arr = zarr.open_array("/data/output.zarr", mode="r")
errors = []

for sl in iter_blocks(arr):  # from Value Comparison above
    try:
        _ = arr[sl]
    except Exception as e:
        errors.append((sl, str(e)))

if errors:
    print(f"Found {len(errors)} unreadable blocks:")
    for sl, msg in errors[:10]:
        print(f"  {sl}: {msg}")
```

**Recovery:** Delete the corrupted output and rechunk again. If corruption is in the source, restore from backup or upstream pipeline.

### 4. Metadata Loss

**Symptoms:** Rechunked dataset is missing user-defined attributes (units, coordinate labels, provenance).

**Causes:**
- Fallback chunk-by-chunk copy correctly transfers attributes via `output_array.attrs.update(source_array.attrs)`, but custom scripts may omit this step.
- Zarr group-level attributes may not be copied when rechunking individual arrays within a group.
- `zarr.from_array` in zarr-python 3.1 copies neither attributes nor the fill value unless you pass `attributes=` and `fill_value=`.

**Prevention:** Always verify metadata preservation as part of post-rechunk validation (see Post-Rechunk Validation section above).

**Recovery:** Copy attributes from the source to the output manually:

```python
source = zarr.open("/data/source.zarr", mode="r")
output = zarr.open("/data/output.zarr", mode="r+")
output.attrs.update(source.attrs)
```
