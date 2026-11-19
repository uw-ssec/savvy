---
name: rechunking
description: Use when an existing Zarr (.zarr) array or dataset must be rechunked to a new layout, such as changing chunk sizes or shard shape, optimizing Zarr storage layout, or applying a chunk configuration identified by benchmarking, on local disk, S3, or GCS. Also use when rechunker, dask rechunk, or xarray to_zarr runs out of memory or raises chunk alignment errors during a rechunk.
metadata:
  references: references/rechunking-strategies.md references/validation-safety.md
  scripts: scripts/rechunk.py
  assets: assets/rechunk-config-example.json
---

# Rechunking Zarr Datasets

Rewrites an existing Zarr array or dataset into a new chunk or shard layout without putting the source at risk.

**Core principle:** rechunking rewrites every byte, which took from 6 minutes to 46 hours in Nguyen et al. (2023). Choose the target layout first, write to a new path, and prove the values match before anything replaces the source.

## When to Use

Use it when a chosen chunk or shard shape must be applied to a real store, or when a rechunk runs out of memory or fails with chunk alignment errors.

**When NOT to use:**

- Target chunks not chosen yet: use `chunking-strategy`, after `access-pattern-analysis`.
- Comparing benchmark results: use `performance-reporting`. Need test data: use `synthetic-data`.
- One computation needs different blocks: `ds.chunk(...)` regroups dask blocks in memory and rewrites nothing.

## Quick Reference: Pick the Tool

| Situation | Tool |
|-----------|------|
| Single Zarr array | `python scripts/rechunk.py` or `zarr.from_array(new_path, data=src, chunks=...)` |
| Sharded Zarr v3 target | `zarr.from_array(..., chunks=inner, shards=outer)` or xarray encoding `{"chunks", "shards"}`. The script cannot set shards. |
| Zarr group or xarray Dataset | `ds.chunk(...).to_zarr(new_path, zarr_format=<source format>)` with stale encoding removed. Group whose arrays lack dimension names: `zarr.from_array` per array. The script rejects groups. |
| Larger-than-memory transpose, e.g. `(1, Y, X)` to `(T, 1, 1)` | dask on a `distributed` cluster (`method="p2p"`), or `rechunker` under zarr-python 2 |

Code for each route, sharding rules and memory planning: [rechunking-strategies.md](references/rechunking-strategies.md).

## Bundled Script

```bash
python scripts/rechunk.py --input /data/source.zarr --output /data/rechunked.zarr \
  --chunks "50,512,512" --max-mem 1GB --summary results/rechunk_report.json
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--input`, `-i` / `--output`, `-o` | required | Source and new store (local, `s3://`, `gs://`). Paths must differ. |
| `--chunks`, `-c` | required | Target chunk shape, comma-separated |
| `--max-mem` | `2GB` | Per-task memory, used only by `rechunker` |
| `--overwrite` | off | Allow an existing local output |
| `--summary` | `rechunk_summary_<timestamp>.json` | JSON summary path |
| `--verbose`, `-v` | off | Debug logging and tracebacks |

The script uses `rechunker` when it imports, but `rechunker` 0.5.4 requires `zarr<3`. Under zarr-python 3 it copies one target chunk at a time and ignores `--max-mem`. Afterwards it checks shape, chunk shape and element count, not values. Example values for each flag: [assets/rechunk-config-example.json](assets/rechunk-config-example.json).

## Safety Protocol

1. **Sample first:** rechunk a block spanning two target chunks per axis with the real `--chunks`.
2. **Validate the sample** with an exact value comparison.
3. **Rechunk the full dataset to a new path.** Never in place.
4. **Verify, then switch readers.** Keep the original until the new store has worked in production.

Code for every step: [validation-safety.md](references/validation-safety.md).

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Same path for `--input` and `--output` | Unchecked. With `--overwrite` or a cloud path, the fallback opens the output with `mode='w'` and erases the source. |
| Trusting the existence check on S3/GCS | It runs for local paths only. Check the prefix yourself. |
| `--max-mem` at 25% of RAM | It is per task, and dask runs one task per thread. Keep `max_mem × threads` well under RAM. |
| `pip install rechunker` under zarr-python 3 | It pins `zarr<3`. Use `zarr.from_array`, xarray or dask. |
| Reusing the source `encoding` in `to_zarr` | Drop `chunks`, `shards` and `preferred_chunks`, or xarray keeps the old layout or raises. |
| `to_zarr` without `zarr_format` on a v2 source | The output defaults to v3, which rejects the v2 compressor. Pass the source's format. |
| Parallel writers sharing a shard | A partial shard write rewrites the whole shard, and concurrent ones lose data. Align blocks to shards. |
| Trusting `zarr.from_array` defaults | In zarr-python 3.1 it drops the fill value and attributes. Pass `fill_value=` and `attributes=`. |
| `np.array_equal` on float data with NaN | Pass `equal_nan=True`. |
| Kerchunk or VirtualiZarr to change layout | They reference existing chunks only. A new layout needs a rewrite. |
