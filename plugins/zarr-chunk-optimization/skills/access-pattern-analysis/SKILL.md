---
name: access-pattern-analysis
description: Use when choosing or benchmarking Zarr chunk shapes and the read workload is not yet written down; when a user describes their work informally ("I make maps", "I pull time series at stations", "I look at spectra"); when several teams or workflows share one dataset and need relative weights; or when reads are slow and the chunk layout may not match how the data is read.
metadata:
  references: references/pattern-identification.md references/workflow-mapping.md
  assets: assets/pattern-definitions-template.json assets/workflow-questionnaire.md
---

# Access Pattern Analysis

Access pattern analysis turns how people actually read a multi-dimensional Zarr dataset into weighted, executable pattern definitions that the chunking benchmark can test. Chunk for how data is read, not how it was written.

**Not for:** running benchmarks (`chunking-strategy`), interpreting results (`performance-reporting`), or converting data to a chosen layout (`rechunking`).

| Resource | Use for |
|----------|---------|
| `assets/workflow-questionnaire.md` | Interviewing users |
| `assets/pattern-definitions-template.json` | The output file scaffold |
| `references/pattern-identification.md` | Pattern details and domain examples; resolving conflicts between patterns |
| `references/workflow-mapping.md` | Mapping descriptions and xarray code to patterns; weighting methods; counting chunks touched |

## Workflow

1. **Interview** users with the questionnaire.
2. **Inspect the store:** dimension order, shape, dtype, chunks and coordinate conventions (see Coordinate Check).
3. **Map** each workflow to patterns using the tables below.
4. **Fill in the template.** Each pattern gets an xarray operation, a weight, the evidence for that weight, and its benchmark arguments.
5. **Validate:**
   - Weights sum to 1.0.
   - Every operation returns a non-empty result against the store or a sample of it.
   - Every weight's `evidence` names a source. Unsourced weights start with `ASSUMPTION:` and need the user's confirmation before benchmarking.
6. **Hand off.** Give the patterns' `benchmark_args` to `chunking-strategy` (`python scripts/benchmark_runner.py --slice-dims … --traverse-dims …`) and the weights to `performance-reporting`. The benchmark script does not read the JSON file.

## Quick Reference

Shapes are for `(time, lat, lon)`, or `(time, x, freq)` for spectral data. Chunk sizes are about 1 MB of float32, within the 1–100 MB that `chunking-strategy` recommends.

| Pattern | xarray operation | Suitable chunks | Benchmark args |
|---------|------------------|-----------------|----------------|
| Spatial | `ds.sel(time="2020-01-01")` | `(1, 512, 512)` | `--slice-dims 0` |
| Temporal | `ds.sel(lat=45.0, lon=270.0, method="nearest")` | `(1000, 16, 16)` | `--traverse-dims 0` |
| Spectral | `ds.isel(time=0, x=0)` | `(1, 64, 4096)` | `--traverse-dims 2` |
| Diagonal | `sel` with slices on 2+ dims | balanced | none; `benchmark_args: null` |

`--slice-dims N` fixes one index on dimension N and reads the rest. `--traverse-dims N` fixes every other dimension and reads all of N. Never use `(…, 1, 1)` chunks for point reads: they make KB-sized objects, millions of them.

| User says | Pattern |
|-----------|---------|
| "maps", "fields", "snapshots" | Spatial |
| "trends", "time series at stations" | Temporal |
| "spectra", "bands", "channels" | Spectral |
| "regional averages over time" | Diagonal |
| "anomalies", "climatology" | Mixed; ask which output they look at |

## Coordinate Check

ERA5-style grids store latitude descending and longitude as 0–360. Check before writing any `sel()`:

```python
ds.lat[0] > ds.lat[-1]     # True → write slice(60, 30), not slice(30, 60)
float(ds.lon.min()) >= 0   # True → 90°W is lon=270, not -90
```

A reversed slice returns an empty array, and `method="nearest"` snaps an out-of-range longitude to the grid edge. Neither raises an error, so a benchmark would time a read of nothing, or of the wrong place.

## Example

ERA5 daily 2 m temperature, 0.25° grid, float32. Bytes = selected elements × 4.

```json
{
  "dataset": {"name": "era5-daily-2m-temp", "dimensions": ["time", "lat", "lon"],
              "shape": [14600, 721, 1440], "dtype": "float32",
              "current_chunks": [1, 721, 1440], "storage_backend": "s3"},
  "patterns": [
    {"name": "spatial_single_timestep",
     "xarray_operation": "ds['t2m'].sel(time='2020-06-15')",
     "weight": 0.60, "evidence": "Access logs 2024-02: ~200 map renders/day, 15 users",
     "benchmark_args": "--slice-dims 0", "expected_bytes_per_read": 4152960},
    {"name": "temporal_single_point",
     "xarray_operation": "ds['t2m'].sel(lat=45.0, lon=270.0, method='nearest')",
     "weight": 0.25, "evidence": "Validation team interview: ~80 station pulls/day",
     "benchmark_args": "--traverse-dims 0", "expected_bytes_per_read": 58400},
    {"name": "diagonal_regional_mean",
     "xarray_operation": "ds['t2m'].sel(lat=slice(60, 30), lon=slice(240, 300), time=slice('2000', '2020')).mean(dim=['lat', 'lon'])",
     "weight": 0.15, "evidence": "ASSUMPTION: climate-index team not yet interviewed",
     "benchmark_args": null, "expected_bytes_per_read": 894776124}
  ]
}
```

The diagonal read (121 × 241 × 7,671 days × 4 B, about 895 MB) has the lowest weight but is by far the largest read. Point that out to the user.

## When Patterns Conflict

If one pattern is more than 3× as frequent as the rest, optimize for it. If the patterns are roughly even, use a compromise shape such as `(100, 64, 64)`, adding Zarr v3 sharding so the small chunks don't flood the store. Otherwise, keep two differently chunked copies. In a sharded array the inner chunk is the read unit, so sharding does not settle a conflict by itself. Kerchunk and VirtualiZarr can't change the chunk layout at all. Details: `references/pattern-identification.md`, Pattern Conflict Resolution.

## Common Mistakes

- Benchmarking before identifying patterns, or assuming there is only one.
- Weighting by operation count when one rare pattern reads 100× more bytes.
- Writing `sel()` without the Coordinate Check. The resulting empty reads raise no error.
- Expecting `benchmark_runner.py` to read the pattern JSON. It takes `--slice-dims` and `--traverse-dims` only.
