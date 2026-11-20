---
name: data-migration
description: Use when converting HDF5 (.h5) or NetCDF (.nc) files to Zarr, migrating scientific datasets or a Zarr v2 store to Zarr v3, or building a virtual Zarr store over existing files with VirtualiZarr or kerchunk. Also use when a converted store lost scale_factor, _FillValue or time units, kept the old chunk layout, shows phony_dim names, or fails validation against its source.
metadata:
  references: references/patterns.md references/examples.md references/common-issues.md
---

# Data Migration to Zarr

Copies HDF5 and NetCDF data into Zarr, upgrades Zarr v2 stores to v3, or builds virtual Zarr references over files that stay where they are.

**Core principle:** a migration is done when the target's decoded values, attributes and time coordinate match the source, not when `to_zarr` returns. Most silent damage comes from `encoding=`, which replaces the source variable's dtype, packing and fill value instead of adding to them.

## When to Use

- Converting `.h5` or `.nc` files into a Zarr store, or a Zarr v2 store into v3
- Serving an archive as Zarr without copying it (VirtualiZarr, kerchunk, Icechunk)
- A migrated store has `phony_dim_*` names, lost packing or fill values, wrong dates, the source's tiny chunks, or failed comparisons

**When NOT to use:**

- Rechunking a store that is already Zarr: use `zarr-chunk-optimization:rechunking`.
- Everyday xarray reads, appends and region writes: `zarr-xarray-integration`.
- Codecs: `compression-codecs`. Cloud stores and credentials: `cloud-storage-backends`.

## Quick Reference

| Source | Route | Code |
|--------|-------|------|
| One file with named dimensions | `xr.open_dataset(path, chunks=...)`, `to_zarr` | Below |
| Many NetCDF files | `xr.open_mfdataset`, `.chunk(...)` the result, `to_zarr` | [patterns.md](references/patterns.md) Pattern 2 |
| HDF5 groups xarray can't model | h5py walk, `zarr.from_array` per dataset | Pattern 4 |
| Zarr v2 store | Replace the v2 codec encoding, `to_zarr(zarr_format=3)` | Pattern 7 |
| Too large to copy | VirtualiZarr to kerchunk JSON or Icechunk | Pattern 3 |
| Thousands of files, restartable | Append per file with a checkpoint | Pattern 5 |

## Core Pattern

```python
import numpy as np
import xarray as xr

KEEP = ("dtype", "scale_factor", "add_offset", "_FillValue", "missing_value")


def cf_encoding(var):
    """The source packing and fill keys, which encoding= would otherwise drop."""
    enc = {k: v for k, v in var.encoding.items() if k in KEEP}
    if var.encoding.get("_Unsigned") == "true":  # zarr rejects _Unsigned: store the unsigned dtype
        signed = np.dtype(enc["dtype"])
        enc["dtype"] = np.dtype(f"u{signed.itemsize}")
        for k in ("_FillValue", "missing_value"):
            if k in enc:
                enc[k] = np.asarray(enc[k], signed).astype(enc["dtype"])
    return enc


target = {"time": 30, "lat": 90, "lon": 180}
ds = xr.open_dataset("climate_model_output.nc", chunks=target)  # name every dimension
encoding = {
    name: cf_encoding(var) | {"chunks": tuple(target[d] for d in var.dims)}
    for name, var in ds.data_vars.items() if set(var.dims) <= set(target)
}
ds.to_zarr("climate_output.zarr", mode="w-", encoding=encoding)
```

A dimension left out of `chunks=` keeps the file's HDF5 chunks, and `to_zarr` can then raise `would overlap multiple Dask chunks`. `encoding` chunks are a tuple in dimension order. Coordinates stay out of `encoding=`, so `time` keeps its units and calendar. Without `missing_value`, masked values came back as `0`; without the unsigned dtype, `200` came back as `-56`.

## Validate Before Deleting the Source

```python
def lost_or_changed(a, b):
    return {k for k in a if k not in b or not np.array_equal(a[k], b[k])}


src = xr.open_dataset("climate_model_output.nc", chunks=target)
dst = xr.open_zarr("climate_output.zarr")
xr.testing.assert_allclose(src, dst)  # names, sizes, coords, values; NaN == NaN; chunk by chunk
assert not (bad := lost_or_changed(src.attrs, dst.attrs)), f"global attributes {bad}"
for name in src.variables:  # assert_allclose ignores attributes
    assert not (bad := lost_or_changed(src[name].attrs, dst[name].attrs)), f"{name} attributes {bad}"
```

Use `xr.testing.assert_equal` when no dtype was narrowed. Per-file checks: [examples.md](references/examples.md) Example 4.

## Bundled Script

`python assets/hdf5-to-zarr-migration.py` builds a 47 MB HDF5 file with dimension scales in a temp directory, converts it, checks it, and exits 1 on any failed check.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| `encoding` chunks as a dict | `TypeError: ... must be an int or a tuple of ints`. Use a tuple. |
| `encoding={"v": {"chunks": ...}}` alone | Replaces the source encoding: packed int16 became float64. Merge the `KEEP` keys. All of `var.encoding` raises `unexpected encoding parameters`. |
| HDF5 without dimension scales | Dimensions are `phony_dim_N` and `chunks={"time": 30}` is ignored. Rename them or attach scales. |
| HDF5 `fillvalue` without `_FillValue` | Not masked, so sentinels stay numbers. Apply `.where(...)` first. |
| `open_mfdataset(..., chunks={"time": 30})` | Chunks are per file, so `to_zarr` raises `would overlap multiple Dask chunks`. `.chunk(...)` the combined dataset. |
| `.chunk(...)` on data read from Zarr | The source `encoding["chunks"]` wins silently. Pop `chunks`, `shards` and `preferred_chunks`. |
| `rechunker` | 0.5.4 pins `zarr<3,>=2.11`. See `zarr-chunk-optimization:rechunking`. |
| `zarr.from_array` defaults | zarr 3.1.5 drops `fill_value` and attributes. Pass both. |
| Appending finer time steps than the store's units | Dates come out wrong with only a `UserWarning`. Set units for `time` and `time_bnds` on the first write. |
| Kerchunk or VirtualiZarr to change chunks | They reference the existing chunks, and files must share one chunk shape (contiguous monthly files fail). Copy instead. |
| Kerchunk `MultiZarrToZarr` without `coo_map={"time": "cf:time"}` | Files with per-file time units merge silently: three 12-day files became 12 steps, the first file's dates over the last file's data. Pass `coo_map`. |
| VirtualiZarr 1.x code | 2.x needs `registry=` and `parser=`, and writes with `.vz.to_kerchunk` or `.vz.to_icechunk`. There is no `to_zarr`. |
| `.values` plus `np.allclose` | Loads whole arrays (3.2 GB RSS for 400 MB) and fails on datetimes. Use `xr.testing`. |
