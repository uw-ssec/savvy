# Benchmarking Methodology for Zarr Chunking — Deep Reference

## Contents

| Section | Lines | Description |
|---------|-------|-------------|
| Core Principles | 17–179 | Minimum runs, cache clearing, parameter isolation, environment control, sampling, timing, and warm-up |
| Common Pitfalls to Avoid | 180–267 | Six frequent mistakes and their fixes (caching, small data, lazy compute, network variance, rechunking, metadata) |
| Recommended Workflow | 268–285 | Step-by-step procedure for a complete benchmark session |
| Output Format | 286–304 | Structured markdown table format for reporting results |
| Script Output | 305–336 | JSON written by benchmark_runner.py and which fields to trust |

---

Best practices for running **reproducible, statistically valid** chunking benchmarks. Following this methodology ensures benchmark results are reliable and actionable.

## Core Principles

### 1. Minimum 5 Runs Per Configuration

**Never report single-run results.** I/O performance is inherently variable due to:

- Network jitter (for cloud storage)
- CPU scheduler behavior
- Background processes
- OS page cache state

**Minimum recommended:** 5 runs per configuration

**Better:** 10 runs

**Report:** Mean, standard deviation, min, and max across all runs

Example:
```
Spatial access (100, 512, 512): 8.3 s ± 0.7 s [min: 7.4 s, max: 9.6 s]
```

### 2. Clear Caching Between Runs

Caching can mask real I/O performance, leading to artificially fast subsequent runs.

#### OS Page Cache

**macOS:**
```bash
sudo purge
```

**Linux:**
```bash
sync
sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
```

**When to clear:** Between every benchmark run to ensure cold-cache performance.

#### fsspec Cache

`fsspec` (used by xarray and zarr for remote stores) only caches chunk bytes when you ask it to, by chaining a caching protocol in front of the URL (`simplecache::s3://...`, `filecache::s3://...`, `blockcache::s3://...`). A plain `s3://` or `gs://` URL fetches from storage on every read.

```python
import xarray as xr

# Benchmark: plain URL, no caching layer
ds = xr.open_zarr("s3://bucket/data.zarr", storage_options={"anon": True})

# NOT for benchmarking: caches every chunk on local disk after the first read
ds = xr.open_zarr("simplecache::s3://bucket/data.zarr",
                  storage_options={"s3": {"anon": True}})
```

`fsspec.config.conf` holds default keyword arguments per protocol (`conf["s3"] = {...}`); it has no global cache switch. `benchmark_runner.py`'s `clear_fsspec_cache()` only empties fsspec's cache of filesystem instances between runs; it does not touch the already-open dataset, the OS page cache, or a caching protocol in the dataset URL.

**Local stores and the script:** all timed runs happen in one process after a warm-up read of the same selection, so the OS page cache is warm for every timed run. Local results therefore measure decode and framework cost, not disk I/O. Clearing the page cache before the call does not change that. For cold reads, benchmark on the target object store or time reads yourself with a cache clear before each run.

**When to clear:** Never benchmark through a caching protocol. Clear the OS page cache (above) between runs for local stores.

### 3. Vary One Parameter at a Time

To understand the impact of each dimension, **vary only one chunk dimension per test**:

**Good experimental design:**
```
Base: (50, 256, 256)
Test time:   (10, 256, 256), (50, 256, 256), (100, 256, 256), (200, 256, 256)
Test freq:   (50, 64, 256), (50, 128, 256), (50, 256, 256), (50, 512, 256)
Test base:   (50, 256, 64), (50, 256, 128), (50, 256, 256), (50, 256, 512)
```

**Bad experimental design:**
```
(10, 64, 64), (50, 128, 128), (100, 256, 256), (200, 512, 512)
```
**Why bad?** Cannot isolate which dimension caused performance changes.

### 4. Controlled Environment

**Critical environmental factors:**

- **Network conditions:** For cloud storage (S3), use a consistent network connection. Avoid running benchmarks during known high-traffic periods.
- **CPU availability:** Disable background jobs. For HPC systems, request dedicated nodes.
- **I/O load:** Don't run benchmarks while other processes are heavily reading/writing.

**Record environmental context:**
```python
import platform
import psutil

env_info = {
    'python_version': platform.python_version(),
    'os': platform.system(),
    'os_version': platform.release(),
    'cpu_count': psutil.cpu_count(logical=False),
    'total_ram_gb': psutil.virtual_memory().total / 1024**3,
    'network_type': 'AWS us-east-1 to S3 (same region)',  # Example
    'instance_type': 't2.xlarge'  # If running on cloud
}
```

### 5. Representative Data Samples

**Problem:** Benchmarking the entire dataset may be too slow during testing.

**Solution:** Use representative samples, but ensure they're large enough to reflect real performance:

- **Too small:** Single chunk reads dominate, doesn't reflect multi-chunk access patterns
- **Too large:** Benchmarking takes too long, iteration is impractical

**Recommendation:** Sample size should require accessing **at least 10-20 chunks** for each access pattern.

**Example:**
```python
# If chunk shape is (50, 256, 256) and data shape is (10000, 2048, 2048)
# Sample: 500 time steps (10 chunks along time), full spatial extent.
# A map read at one time step then touches 8 x 8 = 64 chunks, and a time
# series at one pixel touches 10.
sample_ds = full_ds.isel(time=slice(0, 500))
```

### 6. Timing Methodology

**Use `time.perf_counter()`**, not `time.time()`:

```python
import time

start = time.perf_counter()
result = ds.isel(time=42).compute()
end = time.perf_counter()

wall_time = end - start
```

**Why not `time.time()`?** System clock can jump backward due to NTP adjustments.

**Include compute() call:** Ensure Dask actually executes. Without `.compute()`, xarray returns lazy objects.

### 7. Warm-Up Runs

**Problem:** First run may include Python import overhead, JIT compilation, etc.

**Solution:** Run 1-2 warm-up iterations before starting timed runs.

```python
# Warm-up (not timed)
_ = ds.isel(time=0).compute()
gc.collect()

# Timed runs
times = []
for i in range(5):
    clear_cache()  # OS and fsspec
    start = time.perf_counter()
    result = ds.isel(time=i).compute()
    end = time.perf_counter()
    times.append(end - start)
```

## Common Pitfalls to Avoid

### Pitfall 1: Not Clearing OS Cache

**Symptom:** First run is slow (10 s), subsequent runs are fast (0.5 s).

**Cause:** For a local store, the OS page cache is serving chunk files from RAM instead of disk. For S3/GCS the OS page cache is not involved: look for a caching protocol (`simplecache::`) in the URL, or first-run connection setup (warm-up handles that).

**Fix:** Clear the OS page cache between runs for local stores; never benchmark through a caching protocol (see section 2).

### Pitfall 2: Testing on Unrealistically Small Data

**Symptom:** All chunking strategies perform similarly in benchmarks, but differ greatly in production.

**Cause:** Test data is too small (e.g., single chunk). Performance differences only emerge with multi-chunk access.

**Fix:** Use samples large enough to access 10+ chunks per operation.

### Pitfall 3: Forgetting `.compute()`

**Symptom:** Operations complete in microseconds.

**Cause:** xarray returned a lazy Dask object without executing. Timing only measured graph construction, not actual I/O.

**Fix:** Always call `.compute()` inside the timed block.

### Pitfall 4: Network Variability on Shared Instances

**Symptom:** Huge variance in run times (e.g., 5 s, 12 s, 6 s, 15 s).

**Cause:** Cloud VM is sharing network bandwidth with other tenants.

**Fix:** Use dedicated instances, or increase run count to average out variability (e.g., 20 runs instead of 5).

### Pitfall 5: Mixing Rechunking with Access Benchmarks

**Symptom:** Benchmark times include rechunking overhead, masking access performance.

**Cause:** Rechunking the sample data **inside** the benchmark loop.

**Fix:** Rechunk **once** before benchmarking, then run access pattern benchmarks on the pre-rechunked data. This is also how `benchmark_runner.py` works: it reads the store's existing layout, and `--configs` is only a label, so each candidate needs its own store.

```python
# Correct approach: one store per candidate (not timed)
for config in chunk_configs:              # e.g. (1000, 32, 32)
    label = "x".join(map(str, config))
    target = dict(zip(sample_ds["t2m"].dims, config))
    rechunked = sample_ds.chunk(target)   # Dataset.chunk needs a dict, not a tuple
    for var in rechunked.variables.values():
        # Otherwise the source's on-disk chunks are written again
        var.encoding.pop("chunks", None)
        var.encoding.pop("preferred_chunks", None)
    rechunked.to_zarr(f"sample_c{label}.zarr", mode="w")
```

```bash
# Benchmark access patterns (timed), once per store
python scripts/benchmark_runner.py --dataset sample_c1000x32x32.zarr \
  --configs "1000,32,32" --slice-dims 0 --traverse-dims 0 --runs 5 \
  --output results_c1000x32x32.json
```

### Pitfall 6: Not Recording Configuration Details

**Symptom:** Cannot reproduce results later.

**Cause:** Missing metadata about Python versions, library versions, instance type, etc.

**Fix:** Record full environment at the start of each benchmark session:

```python
benchmark_metadata = {
    'date': '2024-03-08',
    'python': '3.11.7',
    'xarray': '2024.1.0',
    'zarr': '2.17.0',
    'dask': '2024.1.0',
    'fsspec': '2024.1.0',
    'instance_type': 't2.xlarge',
    'storage_backend': 'AWS S3 us-east-1',
    'data_shape': (10000, 2048, 2048),
    'data_dtype': 'float32',
    'compression': 'zstd level 3'
}
```

Save this metadata with the benchmark results.

## Recommended Workflow

1. **Define access patterns** matching real user workflows
2. **Generate candidate chunking configurations** (vary one dimension at a time)
3. **Prepare sample data** (large enough to access 10+ chunks per operation)
4. **Rechunk sample data** to each candidate configuration
5. **Run warm-up iterations** (1-2 runs, not timed)
6. **For each configuration:**
   - For each access pattern:
     - For each run (minimum 5):
       - Clear OS cache
       - Clear fsspec cache (if applicable)
       - Time the operation with `time.perf_counter()`
       - Measure peak memory with `tracemalloc` or `memory_profiler`
       - Record metrics
7. **Aggregate results:** Compute mean, std, min, max for each config × pattern
8. **Generate report** with all metrics and recommendations

## Output Format

Report results in structured markdown tables:

```markdown
## Spatial Access Pattern (load full frequency×baseline at single time)
Array: (10000, 2048, 2048) float32, so the result is 16 MiB.

| Chunk Shape | Chunk Size | Wall Time (mean ± std) | Min | Max | Peak Memory | Chunk GETs |
|-------------|------------|------------------------|-----|-----|-------------|------------|
| (10, 512, 512) | 10 MiB | 2.1 s ± 0.2 s | 1.8 s | 2.4 s | 0.3 GB | 16 |
| (50, 512, 512) | 50 MiB | 8.3 s ± 0.7 s | 7.4 s | 9.6 s | 1.4 GB | 16 |
| (100, 512, 512) | 100 MiB | 16.2 s ± 1.1 s | 14.9 s | 17.8 s | 2.8 GB | 16 |
```

Every row reads the same 4 × 4 = 16 chunks; what grows is the bytes fetched per chunk (160 MiB, 800 MiB, 1.6 GiB uncompressed). Larger time chunks never reduce the request count for a single-time-step read.

Include similar tables for each access pattern, followed by a **Recommendations** section explaining which configuration(s) to use based on the user's priorities.

## Script Output

`benchmark_runner.py` writes one JSON file per call:

```json
{
  "metadata": {"timestamp": "...", "dataset": "...", "num_runs": 5,
               "python_version": "...", "platform": "...", "processor": "...",
               "dimensions": ["time", "lat", "lon"], "num_dimensions": 3},
  "benchmarks": [
    {"dataset": "...", "chunk_config": [1000, 32, 32],
     "access_pattern": "traverse", "dim_index": 0, "dimension_name": "time",
     "num_runs": 5, "dimensions": ["time", "lat", "lon"], "shape": [8760, 721, 1440],
     "statistics": {
       "wall_time": {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "values": []},
       "peak_memory_mb": {"...": "same fields"},
       "throughput_mbps": {"...": "same fields"},
       "data_size_mb": {"...": "same fields"},
       "http_requests": {"...": "same fields"},
       "dask_tasks": {"...": "same fields"}}},
    {"chunk_config": [1000, 32, 32], "access_pattern": "slice", "dim_index": 0,
     "error": "..."}
  ]
}
```

- `chunk_config` is the `--configs` label, not a measured property of the store.
- One entry per config × pattern × dimension. Entries with `error` failed; the script still exits 0.
- `std` is the population standard deviation (`np.std`, ddof=0), slightly smaller than the sample standard deviation for 5–10 runs.
- `ttfb` and `chunk_utilization` are placeholders (`None`), not measurements.
- `http_requests` counts `GET`/`HEAD` lines in fsspec debug logs: approximate for S3/GCS, 0 for local stores.
- `peak_memory_mb` comes from `tracemalloc`, which sees NumPy buffers but may miss memory allocated inside compression libraries.
