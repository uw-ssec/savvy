# Rechunking Strategies — Deep Reference

## Contents

| Section | Lines | Description |
|---------|-------|-------------|
| In-Place vs Copy Rechunking | 17–61 | Trade-offs between overwriting source and writing to a new location |
| Chunk-at-a-Time Processing | 62–98 | The script's fallback copy, its memory profile and limits |
| Intermediate Storage Patterns | 99–149 | Temporary stores used by the rechunker library |
| Parallel Rechunking with rechunker | 150–198 | Running rechunker on a Dask cluster (zarr-python 2 only) |
| Rechunking Under zarr-python 3 | 199–256 | `zarr.from_array`, xarray `to_zarr`, dask `tasks` vs `p2p`, sharding, Kerchunk limits |
| Cost Estimation Formula | 257–303 | Time estimation based on Nguyen et al. (2023) findings |
| Monitoring Progress | 304–372 | Progress logs, ETA calculation, and memory tracking during rechunking |

---

## In-Place vs Copy Rechunking

### Copy Rechunking (Recommended)

Copy rechunking writes the rechunked data to a **new location**, leaving the original dataset untouched. This is the default and recommended approach.

**Advantages:**

- **Rollback safety.** If rechunking fails (OOM, network error, disk full), the original data is unaffected.
- **Validation before swap.** You can compare the rechunked output against the original before replacing it.
- **Cheap switch-over.** On one local filesystem a directory rename is instant. S3 and GCS have no rename: "moving" a prefix copies and deletes every object, so point readers at the new prefix instead.

**Disadvantages:**

- **Requires 2x storage.** You need enough space for both the original and the rechunked copy simultaneously.
- **Egress costs (cloud).** Reading the entire dataset from cloud storage incurs egress charges.

**Workflow:**

```bash
# 1. Rechunk to new location
python scripts/rechunk.py --input /data/original.zarr --output /data/rechunked.zarr --chunks "50,512,512"

# 2. Validate values, not just shape (see validation-safety.md, Post-Rechunk Validation)

# 3. Swap
mv /data/original.zarr /data/original_backup.zarr
mv /data/rechunked.zarr /data/original.zarr

# 4. Clean up after confirming production stability
rm -rf /data/original_backup.zarr
```

### In-Place Rechunking (Dangerous)

In-place rechunking overwrites the source data directly. This approach is almost never appropriate.

**Risks:**

- **Unrecoverable data loss.** An interrupted rechunk leaves the dataset in a partially-written, inconsistent state.
- **No rollback.** Once chunks are overwritten, the original data is gone.
- **Corruption on failure.** OOM kills, network timeouts, or disk errors during writing corrupt the dataset permanently.

**The only scenario where in-place rechunking might be acceptable** is when the dataset is easily reproducible (e.g., derived from a pipeline that can regenerate it) and storage constraints make a copy impossible. Even then, prefer deleting the original and rechunking from the upstream source.

## Chunk-at-a-Time Processing

When `rechunker` cannot be imported, `scripts/rechunk.py` falls back to a chunk-at-a-time copy. `rechunker` 0.5.4 (the latest release) requires `zarr<3`, so in a zarr-python 3 environment this fallback is the only path the script takes. It reads one target chunk's worth of data from the source and writes it to the output.

### How It Works

1. **Create output array.** Open a new Zarr store with the target chunk shape, copying dtype, compression and fill value from the source.
2. **Copy metadata.** Transfer all user-defined attributes from source to output.
3. **Iterate over target chunks.** Generate all chunk start indices from the target chunk grid. For each chunk, compute the slice boundaries and copy the data.
4. **Report progress.** Log completion percentage every 10% of chunks processed.

### Memory Profile

Peak memory during chunk-at-a-time processing is roughly:

```
peak_memory ≈ 2 × target_chunk_bytes + concurrency × decoded_source_chunk_bytes
```

The first term holds the assembled source slice and the encoded output chunk. The second term is the source chunks zarr decodes to fill that slice; zarr-python 3 fetches up to `async.concurrency` (default 10) of them at once. For a `(50, 512, 512)` `float32` target chunk:

```
2 × 50 × 512 × 512 × 4 bytes = 104,857,600 bytes ≈ 100 MiB
```

If the source chunks are `(1, 2048, 2048)` `float32` (16 MiB each), add up to 10 × 16 MiB = 160 MiB. The second term dominates when the source chunks are large along axes where the target chunks are small. `--max-mem` does not limit this path.

### When Chunk-at-a-Time Is Slower

Chunk-at-a-time processing can be significantly slower than the `rechunker` library because:

- **No parallelism.** Chunks are processed sequentially, one at a time.
- **No execution planning.** The rechunker library optimizes the read/write order to minimize redundant reads when source and target chunk grids are misaligned.
- **No intermediate buffering.** When chunk grids are misaligned, chunk-at-a-time may read the same source chunks multiple times for different target chunks.

**Recommendation:** The fallback is adequate for small datasets and testing. For production-sized rechunks under zarr-python 3, use the routes in [Rechunking Under zarr-python 3](#rechunking-under-zarr-python-3). Installing `rechunker` there fails to resolve or downgrades zarr to 2.x, because it pins `zarr<3` (upstream issue pangeo-data/rechunker#159).

## Intermediate Storage Patterns

The `rechunker` library (zarr-python 2 only) plans the copy so that no task exceeds `max_mem`. When a single pass cannot do that, it writes an intermediate store in a layout between the source and target grids, then copies from there to the output. This avoids reading the same source data many times.

### Local Intermediate Storage

`scripts/rechunk.py` always puts the intermediate store in a local temporary directory created with `tempfile.mkdtemp()`, whatever the input and output locations:

```python
import tempfile
temp_store = tempfile.mkdtemp(prefix='rechunker_')
```

The script deletes this directory only after a successful run. If the run fails, delete `rechunker_*` from the temp directory yourself. Ensure the filesystem hosting `/tmp` (or `TMPDIR`) has room: the intermediate store can be as large as the dataset.

### Cloud Intermediate Storage

For cloud-to-cloud rechunking, there are two options:

**Option 1: Local intermediate (what the script does).** The intermediate store is written to local disk. This is simpler but requires local storage equal to the dataset size and incurs egress charges for reading from cloud.

**Option 2: Cloud intermediate.** Call the `rechunker` API directly (zarr-python 2 environment) with a cloud path for the intermediate store:

```python
import rechunker
plan = rechunker.rechunk(
    source_array,
    target_chunks=(50, 512, 512),
    max_mem="4GB",
    target_store="s3://bucket/output.zarr",
    temp_store="s3://bucket/tmp/rechunk_intermediate"
)
plan.execute()
```

This avoids local disk requirements but doubles the cloud write operations. Clean up the intermediate store after rechunking:

```bash
aws s3 rm --recursive s3://bucket/tmp/rechunk_intermediate
```

### Storage Requirements Summary

| Scenario | Intermediate Location | Extra Storage Needed |
|----------|----------------------|---------------------|
| Local → Local | Local temp dir | 1x dataset size on local disk |
| Cloud → Local | Local temp dir | 1x dataset size on local disk |
| Local → Cloud | Local temp dir | 1x dataset size on local disk |
| Cloud → Cloud (local temp) | Local temp dir | 1x dataset size on local disk |
| Cloud → Cloud (cloud temp) | Cloud bucket | 1x dataset size in cloud storage |

## Parallel Rechunking with rechunker

The `rechunker` library (zarr-python 2 only) executes its plan with Dask by default, so a `distributed` client parallelizes it across workers.

### Setting Up Dask for Rechunking

```python
from dask.distributed import Client
import rechunker
import zarr

# Start a local Dask cluster
client = Client(n_workers=4, threads_per_worker=2, memory_limit="4GB")

# Open source data
source = zarr.open("s3://bucket/source.zarr", mode="r")

# Plan rechunking. max_mem is per task: 4 GB worker / 2 threads = 2 GB, halved for headroom.
plan = rechunker.rechunk(
    source,
    target_chunks=(50, 512, 512),
    max_mem="1GB",
    target_store="s3://bucket/output.zarr",
    temp_store="s3://bucket/tmp/rechunk_temp"  # must be reachable by every worker
)

# Execute with Dask
plan.execute()
```

### Worker Configuration Guidelines

Starting points only. Measure on a sample, because storage throughput usually caps the speedup.

| Dataset Size | Workers | Memory per Worker |
|-------------|---------|-------------------|
| < 10 GB | 1–2 | 2 GB |
| 10–100 GB | 4–8 | 4 GB |
| 100 GB–1 TB | 8–16 | 8 GB |
| > 1 TB | 16–32 | 8–16 GB |

### Caveats

- **Diminishing returns.** Beyond a certain worker count, the storage backend (disk IOPS or network bandwidth) becomes the bottleneck, not CPU.
- **Memory coordination.** `max_mem` is the memory one task may use, not a total for the plan. A worker runs one task per thread, so keep `max_mem × threads_per_worker` well under the worker's `memory_limit`.
- **Shared temp storage.** On a multi-machine cluster, a local `temp_store` path exists only on the machine that created it. Use object storage or a shared filesystem.
- **Cloud rate limits.** Many parallel workers writing small chunks can exceed S3 PUT rate limits (3,500 PUT/s per prefix). Monitor for throttling errors.
- **Task graph overhead.** Very small chunks produce very large task graphs, which can overwhelm the Dask scheduler. For datasets with millions of chunks, consider increasing the chunk size or using fewer workers.

## Rechunking Under zarr-python 3

`rechunker` cannot be installed alongside zarr-python 3. These routes can, and they read and write both Zarr v2 and v3.

### Single Array: `zarr.from_array`

```python
import zarr

src = zarr.open_array("/data/source.zarr", mode="r")
with zarr.config.set({"async.concurrency": 4}):  # caps regions copied at once
    dst = zarr.from_array(
        "/data/rechunked.zarr",
        data=src,
        chunks=(50, 512, 512),
        shards=None,  # or an outer shape such as (100, 1024, 1024) for a sharded v3 target
        fill_value=src.fill_value,  # not carried over by default (zarr-python 3.1)
        attributes=dict(src.attrs),  # not carried over by default (zarr-python 3.1)
    )
```

By default `from_array` keeps the source's Zarr format and codecs. In zarr-python 3.1 it drops the fill value and attributes despite its docstring, so pass both as above. It copies one output shard (or chunk, when unsharded) per task, so no two tasks write the same shard. Peak memory is about `async.concurrency × (output shard bytes + decoded source chunks that overlap it)`. Pass `shards` explicitly: the default `"keep"` reuses the source's shard shape, which may not fit the new chunks.

### Zarr Group or xarray Dataset: `.chunk()` + `to_zarr`

```python
import xarray as xr

ds = xr.open_zarr("/data/source.zarr")
ds = ds.chunk({"time": 100, "lat": 180, "lon": 360})
for var in ds.variables.values():
    for key in ("chunks", "shards", "preferred_chunks"):
        var.encoding.pop(key, None)  # stale source layout
ds.to_zarr("/data/rechunked.zarr", mode="w-")
```

Without the `encoding` cleanup, xarray reuses the source chunk shape or raises an error that the encoded chunks would overlap several dask chunks. To write a sharded v3 store, pass `encoding={"var": {"chunks": inner, "shards": outer}}` and make the dask chunks whole multiples of `outer`. xarray rejects dask chunks that straddle shards, because concurrent partial-shard writes corrupt data.

### Dask Rechunk Methods: `tasks` vs `p2p`

`ds.chunk(...)` and `dask.array.rechunk` build the new blocks with one of two methods:

- **`tasks`:** splits and concatenates blocks in the task graph, in memory. This is the only method without a `distributed` client. It is fine when source and target grids are close, but a full transpose such as `(1, Y, X)` to `(T, 1, 1)` makes a huge graph and high memory use.
- **`p2p`:** an all-to-all shuffle that spills to worker disk. It needs `distributed`. With a client running and `array.rechunk.method` unset, dask picks `p2p` automatically when the graph would be large.

Force a method with `dask.config.set({"array.rechunk.method": "p2p"})` or `x.rechunk(chunks, method="p2p")`.

### Zarr v3 Sharding Semantics

- The **inner chunk** (`chunks=`) is the unit a reader fetches and decodes. Size it for the access pattern.
- The **shard** (`shards=`) is the stored object. It holds many inner chunks and an index, and it cuts the object count.
- A write that covers part of a shard reads, modifies and rewrites the whole shard. Concurrent partial writes to the same shard race, and the last writer wins. Give every writer whole shards.
- `arr.chunks` reports the inner chunk shape. Use `arr.shards` to see the shard shape.

### What Cannot Rechunk

Kerchunk and VirtualiZarr build references to byte ranges of chunks that already exist. They can combine whole chunks from many files into one virtual array, but cannot split, merge or reorder the bytes inside a chunk, so the physical layout stays the same. A different chunk shape needs one of the rewrites above.

## Cost Estimation Formula

Nguyen et al. (2023) measured rechunking times for the OVRO-LWA dataset. They report the two ends of the range, not a curve between them.

### Observed Time Range

| Target Chunk Shape | Measured Rechunking Time |
|--------------------|------------------------|
| Large, e.g. `330 × 150 × 300` | ~6 minutes |
| Small, e.g. `10 × 10 × 10` | ~46 hours |

Measure your own sample for anything in between (see validation-safety.md, Sample-First Strategy).

### Factors in the Cost Model

The total rechunking time is influenced by:

1. **Number of target chunks.** More chunks means more individual read/write operations.

   ```
   num_chunks = product(ceil(shape[i] / target_chunks[i]) for i in range(ndim))
   ```

2. **Per-chunk overhead.** Each chunk incurs fixed overhead for opening, writing, and closing the chunk file/object. For cloud storage, this includes HTTP request latency (~50–200 ms per request).

3. **Data volume.** Total bytes that must be read and written:

   ```
   total_bytes = product(shape) × dtype.itemsize
   ```

4. **Chunk grid misalignment.** When source and target chunk grids do not align, some source chunks must be read multiple times. The rechunker library minimizes this through its intermediate storage strategy.

5. **Compression overhead.** Compressed data must be decompressed on read and recompressed on write. CPU-intensive codecs (e.g., zstd level 9) increase per-chunk processing time.

### Rough Estimate

A conservative estimate for local rechunking:

```
time_seconds ≈ num_target_chunks × time_per_chunk
```

Where `time_per_chunk` ranges from 0.01 seconds (local SSD, large chunks, no compression) to 0.5 seconds (cloud storage, small chunks, heavy compression).

**The `rechunk.py` script does not attempt a precise estimate.** Instead, it reports the Nguyen et al. range (6 minutes to 46 hours) because actual time depends heavily on storage backend, network conditions, and compression settings that cannot be measured before the operation begins.

## Monitoring Progress

### Built-in Progress Reporting

`scripts/rechunk.py` logs progress at 10% intervals during chunk-at-a-time processing. The `rechunker` path logs no progress; attach a dask progress bar or dashboard instead.

```
2024-03-08 14:23:01 - INFO - Progress: 100/1000 chunks (10%)
2024-03-08 14:25:47 - INFO - Progress: 200/1000 chunks (20%)
```

### ETA Calculation

To estimate remaining time from progress logs:

```python
import time

start_time = time.perf_counter()
chunks_processed = 0
total_chunks = 1000

for chunk in chunk_iterator:
    process_chunk(chunk)
    chunks_processed += 1

    elapsed = time.perf_counter() - start_time
    rate = chunks_processed / elapsed  # chunks per second
    remaining = (total_chunks - chunks_processed) / rate
    print(f"ETA: {remaining / 60:.1f} minutes remaining")
```

### Memory Tracking

Monitor memory usage during rechunking to detect leaks or excessive consumption:

```python
import tracemalloc

tracemalloc.start()

# ... rechunking operation ...

current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()

print(f"Current memory: {current / 1024**2:.1f} MB")
print(f"Peak memory: {peak / 1024**2:.1f} MB")
```

For continuous monitoring during long rechunking operations, use `psutil`:

```python
import psutil
import os

process = psutil.Process(os.getpid())
memory_mb = process.memory_info().rss / 1024**2
print(f"RSS: {memory_mb:.1f} MB")
```

### Verbose Mode

`--verbose` sets the log level to DEBUG and prints a full traceback on error. It does not add per-chunk timing or memory figures. For peak memory of a whole run, wrap it with `/usr/bin/time -v` (Linux) or `/usr/bin/time -l` (macOS):

```bash
/usr/bin/time -v python scripts/rechunk.py --input /data/source.zarr \
    --output /data/output.zarr --chunks "50,512,512" --verbose
```
