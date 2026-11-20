---
name: synthetic-data
description: Use when a Zarr chunking benchmark needs input data and the production dataset is unavailable, restricted, or too large to copy; when the user asks for a synthetic, random, or test Zarr dataset or array with a given shape, chunks, dtype, or compression; or when a smaller benchmark sample must be cut from an existing Zarr store, on local disk or S3.
metadata:
  references: references/dataset-design.md
  scripts: scripts/synthetic_data.py
  assets: assets/synthetic-config-example.json
---

# Synthetic Data Generation for Chunking Benchmarks

Generates reproducible synthetic Zarr arrays, or cuts a leading-dimension sample from an existing Zarr array, as input for chunking benchmarks.

**Core principle:** synthetic data fixes shape, chunks and dtype, not content. Every pattern is noise-dominated and compresses about 1.1–2x; real scientific data often compresses 2–10x. Compare chunk shapes and access patterns with it, not codecs or absolute read times.

## When to Use

- No access to production data, or it is too large or restricted to copy.
- Validating a benchmark pipeline before running it on real data.
- Comparing chunk shapes for a known array shape and dtype.

**When NOT to use:**
- Choosing a codec or predicting real I/O cost: benchmark a sample of the real data (`--sample-from`, or `ds.isel(...)` as in `chunking-strategy`).
- Defining which reads to benchmark: `access-pattern-analysis`.
- Running the benchmark: `chunking-strategy`. Rewriting real data: `rechunking`. Writing up results: `performance-reporting`.

## Quick Reference

Run from this skill's directory; `python scripts/synthetic_data.py --help` lists every flag.

```bash
# Climate-like, 0.88 GiB float32 (chunks 22.6 MiB)
python scripts/synthetic_data.py --output /tmp/climate.zarr \
    --shape 3650,180,360 --chunks 365,90,180 \
    --dims time,lat,lon --pattern temperature --seed 42

# Radio-like, 15.6 GiB float32 (chunks 12.5 MiB); --compression none isolates raw I/O
python scripts/synthetic_data.py --output /tmp/radio.zarr \
    --shape 1000,2048,2048 --chunks 50,256,256 \
    --dims time,frequency,baseline --pattern radio --compression none --seed 42

# To S3 (s3fs + AWS credentials), 1.95 GiB
python scripts/synthetic_data.py --output s3://bucket/synthetic.zarr \
    --shape 500,1024,1024 --chunks 50,256,256 --seed 42

# First ~8 GiB along dim 0 of an existing Zarr v3 array (loads the whole sample into RAM)
python scripts/synthetic_data.py --sample-from /data/full.zarr/temperature \
    --output /tmp/sample.zarr --target-size 8
```

| `--pattern` | Content | zstd ratio |
|-------------|---------|-----------|
| `random` (default) | N(0, 1) noise | ~1.1x |
| `temperature` | lat+lon gradient × sine over dim 0, plus noise | ~1.25x |
| `radio` | real amplitudes \|N + iN\|, not complex values | ~1.1x |
| `constant` | 100 + 0.01·N(0, 1) | ~2x |

Ratios measured on a 100×256×256 float32 array. [references/dataset-design.md](references/dataset-design.md) covers what `--help` omits: codec mapping, dtype casting, sampling, cloud URLs, seeding. [assets/synthetic-config-example.json](assets/synthetic-config-example.json) records a run; the script has no `--config` flag.

## Validate Before Benchmarking

```python
import numpy as np, zarr

z = zarr.open("/tmp/climate.zarr", mode="r")
assert (z.shape, z.chunks, z.dtype) == ((3650, 180, 360), (365, 90, 180), np.float32)
print(dict(z.attrs))  # dimensions, pattern_type, created_by (the seed is not stored)
sample = z[0:5]
assert np.isfinite(sample).all() and sample.std() > 0
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Opening the output with `xr.open_zarr` | It raises `ContainsArrayError`: the store is a bare array, not a group. `chunking-strategy`'s `benchmark_runner.py` opens it as is; for your own xarray code, wrap it as a Dataset (see the reference). |
| Picking a codec from synthetic results | Noise barely compresses: you measure codec CPU cost without the I/O saving. |
| `--dtype int16` or `complex64` | Values are generated as float32 and cast: int16 holds a handful of small integers, complex has a zero imaginary part. |
| `--sample-from store.zarr` on an xarray store | It is a group (`'Group' object has no attribute 'shape'`); point at the variable, `store.zarr/<var>`. |
| Different shape or dtype, same seed | Data is identical only for identical shape, dtype, pattern and seed. Record the full command. |
| Chunks that do not divide the shape | Use even divisors of the shape to avoid partial edge chunks. |
