---
name: zarr-xarray-integration
description: Use when reading or writing Zarr stores with xarray (open_zarr, to_zarr), setting to_zarr encoding, appending with append_dim, writing regions from parallel workers, or aligning Dask chunks with Zarr chunks or shards. Also use when to_zarr raises "would overlap multiple Dask chunks" or "must be an int or a tuple of ints", when appended times or coordinates come back wrong, or when a consolidated store opens stale.
metadata:
  references: references/patterns.md references/examples.md references/common-issues.md
---

# Zarr + xarray Integration

Reads, writes, appends to and region-writes Zarr stores through xarray and Dask without corrupting their layout, coordinates or timestamps.

**Core principle:** `to_zarr` writes what the encoding says and checks little else. On-disk chunks come from `encoding`, which data opened from Zarr keeps through `.chunk()`. Bad appends and region writes often succeed and leave a wrong store, so check inputs before writing.

## When to use

- Opening, writing, appending to or region-writing a Zarr store with xarray, locally or on S3/GCS
- Choosing `to_zarr` chunks, dtype, codecs or fill values
- After a write: wrong timestamps, replaced coordinates, duplicate times, or a store that won't open

## When NOT to use

- General xarray work (selection, groupby, NetCDF I/O): `xarray-for-multidimensional-data` (scientific-domain-applications plugin)
- zarr-python arrays and groups, v2 vs v3, sharding: `zarr-fundamentals`
- Codec choice: `compression-codecs`. Cloud credentials, fsspec, Icechunk: `cloud-storage-backends`
- HDF5/NetCDF conversion, VirtualiZarr, kerchunk: `data-migration`
- Choosing chunk shapes or rechunking a store: `chunking-strategy`, `rechunking` (zarr-chunk-optimization plugin)

## Quick reference

| Task | Call |
|------|------|
| Open lazily, one Dask chunk per Zarr chunk | `xr.open_zarr(path)` (default `chunks={}`) |
| Bigger Dask chunks, multiples of Zarr's | `chunks="auto"` or a dict of multiples |
| Open without Dask (NumPy on access) | `chunks=None`, or `xr.open_dataset(path, engine="zarr")` |
| Public S3 (needs `s3fs`) | `xr.open_zarr("s3://...", storage_options={"anon": True})` |
| Create (fails if present) / overwrite | `ds.to_zarr(path)` / `mode="w"` |
| Chunks, dtype, codecs | `encoding={"t2m": {"chunks": (24, 90, 180), "dtype": "float32", "compressors": [zarr.codecs.ZstdCodec()]}}` |
| Append | `new.to_zarr(path, append_dim="time")` |
| Pre-allocate, then fill regions | `template.to_zarr(path, mode="w", compute=False)` (Dask-backed), then `part.to_zarr(path, region="auto")` |
| Add variables / overwrite values only | `mode="a"` / `mode="r+"` (default with `region`) |
| Zarr v2 output | `zarr_format=2` (zarr-python 3 defaults to v3) |
| Consolidated metadata | Written by default. After writes with `consolidated=False` or plain zarr-python: `zarr.consolidate_metadata(path)` |

Code for each: [patterns.md](references/patterns.md). Workflows: [examples.md](references/examples.md). More symptoms: [common-issues.md](references/common-issues.md). Demo: `python assets/xarray-zarr-roundtrip.py`.

## Rechunk before writing: drop the stale encoding

```python
ds = xr.open_zarr("in.zarr").chunk({"time": 120, "lat": 90, "lon": 180})
for var in ds.variables.values():
    for key in ("chunks", "preferred_chunks", "shards"):
        var.encoding.pop(key, None)  # else to_zarr keeps the source chunks or raises
ds.to_zarr("out.zarr", mode="w")
```

## Common mistakes

| Mistake | What happens | Fix |
|---------|--------------|-----|
| `encoding` chunks as a dict | `TypeError: ... must be an int or a tuple of ints` | Tuple in dim order |
| `.chunk()` then `to_zarr` on data read from Zarr | Old chunks written silently, or the overlap error below | Pop the stale encoding (above) |
| Dask chunks not whole multiples of Zarr chunks or shards | `ValueError: ... would overlap multiple Dask chunks` | `.chunk()` to multiples, or `align_chunks=True` |
| First write sets time units (`days since` for daily data) | Later hourly appends land on wrong dates; only a `UserWarning` | First write: `encoding={"time": {"units": "seconds since 1970-01-01", "dtype": "int64"}}` |
| Appended batch has other lat/lon values | Store's coordinates replaced, no error | Compare `indexes` first |
| Appended batch adds or drops a variable | Reopening raises `conflicting sizes for dimension 'time'` | Append exactly the store's variables |
| Appended times overlap the store | Duplicate timestamps, no error | Start after the store's last time |
| Explicit `region` with coords lacking the region dim | `ValueError: ... at least one dimension in common with the region's dimensions` | `region="auto"`, or `drop_vars` them |
| Concurrent regions split a Zarr chunk or shard | Lost writes; NumPy-backed regions aren't checked | Region edges on chunk (shard) boundaries |
| `sel(lat=slice(-30, 30))` on descending latitude (ERA5) | Empty result, no error | `slice(30, -30)`; check 0–360 longitudes |
