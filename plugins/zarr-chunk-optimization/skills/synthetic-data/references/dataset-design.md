# Dataset Design — Deep Reference

## Contents

| Section | Lines | Description |
|---------|-------|-------------|
| Choosing Dimensions and Shapes | 18–47 | Match production data characteristics for representative benchmarks |
| Data Type Selection | 48–82 | Impact of dtype on chunk size, and how the script fills each dtype |
| Compression Codec Impact | 83–130 | Codecs the script writes, measured ratios per pattern, why synthetic data misstates compression |
| Scaling Test Data | 131–184 | Sizing, `--sample-from` behavior and limits, opening the output with xarray |
| Reproducibility | 185–236 | Random seeds, metadata recording, and deterministic generation |
| Storage Backend Considerations | 237–282 | Local vs cloud latency, object store semantics, regional placement, script URL support |

---

Designing synthetic datasets for chunking benchmarks requires intentional choices about every parameter. A poorly designed test dataset can produce misleading benchmark results that do not translate to production performance. This reference covers the key design decisions in depth.

## Choosing Dimensions and Shapes

The number of dimensions and their relative sizes determine how chunking strategies interact with access patterns. A dataset shaped `(10, 10, 10)` will not reveal the trade-offs visible in a `(10000, 2048, 2048)` dataset.

### Match Production Aspect Ratios

If your production data has shape `(50000, 4096, 4096)`, keep the dimensions that chunks will span at their production size and shrink only the leading dimension (usually time), as `--sample-from` does:

- Good: `(1000, 4096, 4096)` — full spatial extent, fewer time steps
- Bad: `(100, 100, 100)` — spatial reads touch one or two chunks, so the trade-offs that drive chunking disappear

### Dimension Count

Common configurations by domain:

| Dimensions | Example Shape | Domain |
|-----------|---------------|--------|
| 2D | `(4096, 4096)` | Single images, spatial grids |
| 3D | `(1000, 2048, 2048)` | Time-series of spatial data, radio visibilities |
| 4D | `(365, 50, 180, 360)` | Atmospheric models (time, level, lat, lon) |
| 5D | `(100, 4, 50, 180, 360)` | Ensemble forecasts (member, time, level, lat, lon) |

### Minimum Sizes for Meaningful Benchmarks

Each dimension should be large enough that multiple chunks span it. A dimension of size 10 with chunk size 10 produces a single chunk along that axis, eliminating any chunking trade-off. Rules of thumb:

- At least **10 chunks** along the primary access dimension
- At least **4 chunks** along secondary dimensions
- Total dataset size of at least **1 GB** for local benchmarks, **5 GB** for cloud benchmarks

## Data Type Selection

The dtype determines the number of bytes per array element, which directly controls the in-memory and on-disk size of each chunk.

### Bytes Per Element

| dtype | Bytes | Typical Use |
|-------|-------|-------------|
| `int8` | 1 | Flags, masks, categorical |
| `int16` | 2 | Satellite radiance, elevation |
| `int32` | 4 | Counts, indices |
| `float16` | 2 | ML inference, reduced precision |
| `float32` | 4 | Most scientific data |
| `float64` | 8 | High-precision computation |
| `complex64` | 8 | Radio visibilities (real + imaginary float32) |
| `complex128` | 16 | High-precision complex data |

### Impact on Chunk Size

For a chunk shape of `(50, 256, 256)`:

- `float32`: 50 x 256 x 256 x 4 bytes = **12.5 MiB** per chunk
- `float64`: 50 x 256 x 256 x 8 bytes = **25.0 MiB** per chunk
- `int16`: 50 x 256 x 256 x 2 bytes = **6.25 MiB** per chunk

The `chunking-strategy` skill targets 1–100 MB per object after compression on cloud stores. Choosing the wrong dtype can push chunks outside that range.

### How the Script Fills Each dtype

`synthetic_data.py` always generates float32 values and casts them to `--dtype`. Integer dtypes therefore hold only a handful of small integers (truncated N(0, 1) values), which compress far better than real integer data. Complex dtypes get a zero imaginary part. If production data is integer or complex, benchmark a sample of it instead.

### Recommendation

Always use the same dtype as your production data. If you do not yet have production data, use `float32` as the default. It is the most common type in scientific computing and produces chunk sizes in the optimal range for most configurations.

## Compression Codec Impact

Compression affects benchmarks in two ways: it reduces the amount of data transferred from storage (faster I/O) but adds CPU cost for decompression (slower processing). The net effect depends on the data pattern, compression ratio, and storage bandwidth.

### Available Codecs

The `synthetic_data.py` script supports:

| Flag Value | Codec written to the store | Characteristics |
|-----------|----------------------------|-----------------|
| `zstd` (default) | `BloscCodec(cname="zstd", shuffle="bitshuffle")` | Best ratio-to-speed balance |
| `blosc` | `BloscCodec(cname="lz4", shuffle="bitshuffle")` | Fastest decompression; lower ratios |
| `gzip` | `GzipCodec` | Wide compatibility; slower than Blosc |
| `none` | `BytesCodec` only | No compression; measures raw I/O |

`--compression-level` (default 3) sets `clevel` for Blosc and `level` for gzip.

### Compression Ratios by Data Pattern

Every pattern is dominated by Gaussian noise, so none of them compresses like real data. Ratios measured with zarr 3.1.5 on a `(100, 256, 256)` float32 array with `(10, 64, 64)` chunks at level 3 (the full-size climate example in SKILL.md gives 1.27x for `temperature`):

| Pattern | `zstd` | `blosc` | `gzip` |
|---------|--------|---------|--------|
| `constant` | 2.0x | 2.0x | 1.8x |
| `temperature` | 1.26x | 1.25x | 1.12x |
| `radio` | 1.13x | 1.15x | 1.12x |
| `random` | 1.12x | 1.11x | 1.08x |

Real scientific data often compresses 2–10x (see `chunking-strategy`'s `references/cloud-storage-patterns.md`). A synthetic chunk is larger on disk than the same chunk of real data by the real ratio divided by the synthetic ratio: `temperature` with `zstd` (1.26x) is about 1.6x larger than real data that compresses 2x and about 8x larger than real data that compresses 10x, while `constant` (2.0x) matches 2x real data and is 5x larger than 10x real data. Across the table the gap runs from none to about 9x; where real data compresses better, synthetic data overstates bytes read and I/O time, especially on cloud storage.

### Benchmarking With and Without Compression

To isolate the effect of compression on benchmark results, generate identical datasets with and without compression:

```bash
# With compression
python scripts/synthetic_data.py -o /tmp/compressed.zarr \
    --shape 1000,1024,1024 --chunks 50,256,256 \
    --compression zstd --seed 42

# Without compression
python scripts/synthetic_data.py -o /tmp/uncompressed.zarr \
    --shape 1000,1024,1024 --chunks 50,256,256 \
    --compression none --seed 42
```

On synthetic data this pair measures codec CPU overhead only: the compressed store is barely smaller, so the I/O saving that makes compression worthwhile on real data never shows up. To decide whether compression is a net win for your storage backend, run the same comparison on a sample of the real dataset.

## Scaling Test Data

Benchmark datasets must be large enough to produce meaningful results but small enough to generate and store practically.

### Sizing Guidelines

| Purpose | Recommended Size | Rationale |
|---------|-----------------|-----------|
| Pipeline validation | 100 MB – 1 GB | Quick generation, fast iteration |
| Local benchmarks | 1 GB – 10 GB | Large enough to measure I/O patterns |
| Cloud benchmarks | 5 GB – 50 GB | Must amortize request overhead |
| Production simulation | 50 GB – 500 GB | Full-scale performance prediction |

### Reducing Along One Dimension

`--sample-from` (through `calculate_sample_shape`) reduces the first dimension (typically time) while preserving full resolution in other dimensions. This strategy maintains representative chunk access patterns:

- Full production shape: `(50000, 4096, 4096)` — 3.4 TB (3.1 TiB) at float32
- Benchmark sample: `(500, 4096, 4096)` — 33.6 GB (31.3 GiB) at float32
- Quick test: `(50, 4096, 4096)` — 3.4 GB (3.1 GiB) at float32

### Using --sample-from

If you have an existing large Zarr dataset, sample it rather than generating noise. Real values keep the real compression ratio, which synthetic patterns cannot reproduce:

```bash
python scripts/synthetic_data.py --sample-from /data/full.zarr/temperature \
    --output /tmp/sample.zarr --target-size 8
```

What the script does and does not handle (checked against zarr 3.1.5):

- `--target-size` is in GiB (2^30 bytes). The sample is the first N indices along dimension 0 at full extent elsewhere, so a time-leading sample covers only the start of the record and can miss seasonal or regime changes.
- The source must be a Zarr v3 **array**. An xarray store is a group and fails with `'Group' object has no attribute 'shape'`; pass the variable's path (`store.zarr/<var>`). Zarr v2 arrays fail with `Expected dict, got <class 'numcodecs...'>`.
- The sample keeps the source's chunk shape, codecs and attributes, but not its `dimension_names`, and it is written as a bare array (see "Opening the Output with xarray" below). `benchmark_runner.py` therefore labels its dimensions `dim_0`, `dim_1`, ...
- The whole sample is read into memory in one step, so `--target-size 8` needs more than 8 GiB of free RAM.
- `--overwrite` is ignored here: an existing output is replaced silently.

For an xarray dataset, `ds.isel(time=slice(0, n)).to_zarr(...)` (as in `chunking-strategy`'s `references/benchmarking-methodology.md`) keeps all variables, coordinates and dimension names.

### Opening the Output with xarray

The script writes a single array at the store root and records `--dims` both as Zarr v3 `dimension_names` and in `attrs["dimensions"]`. `chunking-strategy`'s `benchmark_runner.py` opens such a store directly. `xr.open_zarr` and `xr.open_dataset(..., engine="zarr")` accept only groups, so they raise `ContainsArrayError`. To use the output in your own xarray code, rewrite it as a Dataset (needs dask; the copy uses xarray's default codecs, not the source's):

```python
import dask.array as da
import xarray as xr
import zarr

z = zarr.open("/tmp/climate.zarr", mode="r")
data = da.from_array(z, chunks=z.chunks)
xr.DataArray(data, dims=z.attrs["dimensions"], name="data").to_dataset().to_zarr("/tmp/climate_ds.zarr")
```

## Reproducibility

Benchmarking requires exact reproducibility. Two runs with the same shape, dtype, pattern and seed produce bitwise-identical datasets.

### Random Seeds

The `--seed` flag controls all random number generation. Default is `42`. The script writes in batches of about 1 GiB along the first dimension and calls `numpy.random.seed(seed + batch_start)` for each batch. Batch length is derived from the shape and dtype, so changing either one changes the values: two datasets that differ in shape are not the same data cut differently. The `temperature` sine cycle also restarts at each batch boundary.

Key rules:

- Always specify `--seed` explicitly in benchmark scripts
- Use the same seed across all datasets in a comparison
- Document the seed in your benchmark report; the script does not store it in the array's attributes
- Different seeds produce statistically equivalent but numerically different data

### Metadata Recording

The script automatically stores metadata in Zarr attributes:

```python
z.attrs['dimensions']   # Dimension names
z.attrs['pattern_type'] # Data pattern used
z.attrs['created_by']   # 'synthetic_data.py'
```

For complete reproducibility, also record externally:

- Exact command line used
- Python and library versions (`zarr.__version__`, `numpy.__version__`)
- Date and machine identifier
- Any environment variables affecting storage (AWS region, credentials profile)

### Verifying Reproducibility

```python
import zarr
import numpy as np

z1 = zarr.open("/tmp/run1.zarr", mode="r")
z2 = zarr.open("/tmp/run2.zarr", mode="r")

# Check shapes match
assert z1.shape == z2.shape, f"Shape mismatch: {z1.shape} vs {z2.shape}"

# Check data is bitwise identical, one block along dim 0 at a time to bound memory
step = z1.chunks[0]
for i in range(0, z1.shape[0], step):
    assert np.array_equal(z1[i:i + step], z2[i:i + step]), f"Data differs at index {i}"

print("Datasets are identical")
```

## Storage Backend Considerations

Where you store synthetic data affects benchmark results. Local disk, S3, and GCS have fundamentally different performance characteristics.

### Local Filesystem

- **Latency:** Sub-millisecond for SSDs, single-digit milliseconds for HDDs
- **Throughput:** 500 MB/s – 3 GB/s for NVMe SSDs
- **Best for:** Pipeline development, quick iteration, compression comparisons
- **Caveat:** Results do not predict cloud performance; OS page cache can mask I/O costs

Always clear caches between benchmark runs on local storage:

```bash
# macOS
sudo purge

# Linux
sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
```

### Amazon S3

- **Latency:** 50–200 ms per GET request (same region)
- **Throughput:** 5–25 GB/s aggregate with parallel requests
- **Best for:** Production-representative benchmarks
- **Caveat:** Costs for PUT, GET, and storage; regional placement matters

Place synthetic data in the same region as your compute. Cross-region access adds 50–150 ms per request and incurs data transfer charges.

### Google Cloud Storage

- **Latency:** 40–150 ms per GET request (same region)
- **Throughput:** Similar to S3 with parallel requests
- **Best for:** GCP-native workflows
- **Caveat:** Requires `gcsfs` library; authentication via service account or application default credentials
- **Script support:** `synthetic_data.py` rejects `gcs://` URLs with `NotImplementedError` even when `gcsfs` is installed. A `gs://` URL goes straight to zarr's fsspec store, which should work with `gcsfs` installed but is untested. For any remote URL the script replaces existing data without `--overwrite`.

### Choosing a Backend for Benchmarks

| Benchmark Goal | Recommended Backend |
|---------------|-------------------|
| Develop and validate pipeline | Local |
| Compare chunk configurations | Local (faster iteration) |
| Predict production performance | Same backend as production |
| Compare storage backends | Run identical benchmarks on each |
