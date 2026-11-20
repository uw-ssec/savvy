---
name: chunking-strategy
description: Use when choosing or tuning Zarr chunk shapes for a multi-dimensional scientific array on S3, GCS or local disk, when map reads or time-series reads from a Zarr store are slow or run out of memory, or when comparing candidate chunk configurations by wall-clock time, peak memory or performance bias (Nguyen et al. 2023) before rechunking.
metadata:
  references: references/access-patterns.md references/memory-constraints.md references/nguyen-2023.md references/benchmarking-methodology.md references/cloud-storage-patterns.md references/performance-interpretation.md
  scripts: scripts/benchmark_runner.py
  assets: assets/benchmark-config-example.json assets/report-template.md
---

# Chunking Strategy Benchmarking

Benchmarks candidate Zarr chunk shapes against the reads a dataset actually serves, measuring wall-clock time and peak memory before any rechunk.

**Core principle:** a read fetches and decompresses every chunk it touches, whole. Map reads want chunks short in time and wide in space, time-series reads the opposite, so measure candidates instead of guessing. Method: Nguyen et al. (2023), [DOI: 10.1002/essoar.10511054.2](https://doi.org/10.1002/essoar.10511054.2).

## When to Use

- Picking chunks for a new store, or a target layout before rechunking.
- Maps load fast but time series crawl (or the reverse), small selections run out of memory, or reads issue thousands of tiny GETs.

**When NOT to use:**
- Read patterns are still unknown or unweighted: use **access-pattern-analysis** first.
- The shape is decided and the data must be rewritten: use **rechunking**.
- No representative data to benchmark: use **synthetic-data** to generate stores.
- Results exist and need a stakeholder report: use **performance-reporting**.

## Quick Reference

| Read pattern (dims `time, lat, lon`) | xarray (positional) | Script flag | Shape that favors it (float32) |
|---|---|---|---|
| Map at one time step | `da.isel(time=t)` | `--slice-dims 0` | `(1, 721, 1440)`, 4.2 MB |
| Time series at one point | `da.isel(lat=i, lon=j)` | `--traverse-dims 0` | `(1000, 32, 32)`, 4.1 MB |
| Spectrum (dims `time, freq, baseline`) | `da.isel(time=t, baseline=b)` | `--traverse-dims 1` | `(8, 2048, 64)`, 4.2 MB |

- **Size:** aim for compressed chunk objects of 1–100 MB on object storage. KB-sized chunks are latency-bound (each GET pays ~20–100 ms).
- **Memory per read:** up to uncompressed chunk bytes × chunks the selection touches, plus 1.5–2× overhead.
- **PB** (Nguyen et al.) = max / min of mean wall time across patterns for one config. Plugin heuristic bands: < 1.5 balanced, 1.5–3 moderate, 3–10 biased, > 10 extreme.
- **Weighted score** = Σ wᵢ × Tᵢ over patterns (weights from access-pattern-analysis); rank by it. Keep PB unweighted.
- `mean ± std` is run spread (ddof=0), not a confidence interval.

## Running the Benchmark

`scripts/benchmark_runner.py` times reads of the store's **existing** layout. `--configs` is only a label copied into the output; it does not rechunk. Each candidate needs its own store (a sample rechunked with **rechunking**, or generated with **synthetic-data**) and its own run:

```bash
python scripts/benchmark_runner.py \
  --dataset /scratch/era5_sample_c1000x32x32.zarr \
  --configs "1000,32,32" \
  --slice-dims 0 --traverse-dims 0 \
  --runs 5 --output results_c1000x32x32.json
```

- `slice` (`--slice-dims d`): fix the middle index along dim *d*, read the whole hyperplane.
- `traverse` (`--traverse-dims d`): fix every other dim at its middle, read the 1-D line along *d*.
- Both default to every dim. `--runs` must be at least 5. Only the first data variable is read.
- `--warmup` is parsed but not applied: one warm-up run always happens.
- A failed benchmark is an entry with only an `error` field and the script still exits 0; check before trusting the JSON ([output format](references/benchmarking-methodology.md#script-output)).
- On a local store every timed run follows a warm-up read of the same selection, so the OS page cache is warm: results show decode cost, not disk I/O. Benchmark on the production object store when I/O is the question.

## Workflow

1. Map each weighted read pattern to `slice` or `traverse` plus a dim index.
2. Pick 3–5 candidates (current layout, one per dominant pattern, one balanced), varying one dim at a time. Drop any over the memory budget.
3. Build one store per candidate on a sample where every pattern touches 10+ chunks.
4. Benchmark each store. If std/mean > 0.3, rerun with `--runs 10` or more before comparing.
5. Compute PB and weighted score; fill `assets/report-template.md` or hand off to **performance-reporting**.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Passing several `--configs` against one store and reading the differences as chunk effects | Every run reads the same layout. One store per candidate |
| `--traverse-dims 1 2` on `(time, lat, lon)` to get time series | That reads lines along lat and lon. A time series is `--traverse-dims 0` |
| `ds.sel(time=42)` for "time step 42" | `sel` matches labels: `KeyError` on datetime coords. Use `isel(time=42)` |
| `sel(lat=slice(30, 60), lon=slice(-120, -60))` on ERA5-style grids | Latitude descends and longitude is 0–360, so both return empty. Use `lat=slice(60, 30), lon=slice(240, 300)` |
| `ds.chunk({...}).to_zarr(...)` to build a candidate store | The source's `encoding["chunks"]` wins and the old layout is written. Delete `encoding["chunks"]` and `encoding["preferred_chunks"]` per variable first |
| Treating a Zarr v3 shard as the read unit | The inner chunk is the read unit; the shard is the storage object. Size and benchmark inner chunks for reads |
| Expecting Kerchunk or VirtualiZarr to provide a second layout | They reference existing chunks only. A new layout needs a rechunk |

## References

| Reference | Load when |
|---|---|
| [access-patterns.md](references/access-patterns.md) | Mapping workflows to spatial, time-series and spectral reads |
| [memory-constraints.md](references/memory-constraints.md) | Memory budgets, OOM, all-or-nothing chunk reads |
| [benchmarking-methodology.md](references/benchmarking-methodology.md) | Run counts, cache clearing, building candidate stores, pitfalls |
| [cloud-storage-patterns.md](references/cloud-storage-patterns.md) | S3/GCS latency, request cost, sharding, caching |
| [performance-interpretation.md](references/performance-interpretation.md) | Reading results, PB, weighted scores, recommendations |
| [nguyen-2023.md](references/nguyen-2023.md) | Research basis for the method |

## Limitations

Read performance only (no write, rechunk or codec benchmarking), one variable per store.
