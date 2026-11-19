# Common Issues and Solutions

## Contents

| Section | Lines | Description |
|---------|-------|-------------|
| Issue 1: HDF5 Features Not Supported in Zarr | 17–78 | Links, object references, variable-length strings and plugin filters |
| Issue 2: Metadata Loss During Conversion | 79–136 | `encoding=` replacing the source's packing and fill value |
| Issue 3: Memory Errors on Large File Conversion | 137–195 | Whole variables loaded into memory during migration |
| Issue 4: Virtual References Become Invalid | 196–247 | Source files moved or renamed after creating references |
| Issue 5: Chunk Size Not Optimal After Migration | 248–290 | Inheriting the HDF5 chunk layout |
| Issue 6: Fill Value Mismatch Between HDF5 and Zarr | 291–333 | HDF5 fill values that xarray does not mask |
| Issue 7: Encoding/Dtype Differences Between Source and Target | 334–381 | Unexpected type or time changes during migration |

---

## Issue 1: HDF5 Features Not Supported in Zarr

**Symptoms:**
- `TypeError` or `ValueError` during migration
- The same data appearing twice in the Zarr output (a soft link was followed), or `KeyError: "Unable to synchronously open object (can't open file)"` (a dangling external link)
- Object references (`h5py.Reference`) or variable-length strings causing errors
- Data compressed with an HDF5 plugin filter (e.g., bitshuffle, LZF, Blosc) failing to read without `hdf5plugin`, or VirtualiZarr/Kerchunk lacking a matching codec

**Cause:** Zarr has no links, object references or named data types. h5py resolves soft and external links when you index a group, so a naive walk copies link targets again or fails on a missing external file. Plugin filters are an HDF5 feature: h5py needs the plugin to decode them, and virtual references need an equivalent Zarr codec.

**Solution:**

```python
import h5py
import zarr

BUILTIN_FILTERS = {1: "deflate", 2: "shuffle", 3: "fletcher32", 4: "szip", 5: "nbit", 6: "scaleoffset"}

# ── Diagnose: Identify features Zarr can't hold ──
with h5py.File("complex.h5", "r") as f:
    def check_features(group, path=""):
        for key in group:
            full_path = f"{path}/{key}"
            link = group.get(key, getlink=True)
            if isinstance(link, h5py.SoftLink):
                print(f"  SOFT LINK: {full_path} → {link.path}")
                continue
            if isinstance(link, h5py.ExternalLink):
                print(f"  EXTERNAL LINK: {full_path} → {link.filename}:{link.path}")
                continue

            item = group[key]
            if isinstance(item, h5py.Dataset):
                if h5py.check_dtype(ref=item.dtype):
                    print(f"  OBJECT REF: {full_path}")
                elif h5py.check_string_dtype(item.dtype):
                    print(f"  STRING: {full_path} ({item.dtype})")
                plist = item.id.get_create_plist()
                for i in range(plist.get_nfilters()):
                    code, _, _, name = plist.get_filter(i)
                    if code not in BUILTIN_FILTERS:
                        print(f"  PLUGIN FILTER: {full_path} uses {code} ({name.decode()})")
            elif isinstance(item, h5py.Group):
                check_features(item, full_path)

    check_features(f)

# ── Fix: copy hard-linked numeric datasets only, chunk by chunk ──
with h5py.File("complex.h5", "r") as f:
    root = zarr.open_group("resolved.zarr", mode="w-")
    for key in f:
        if not isinstance(f.get(key, getlink=True), h5py.HardLink):
            continue  # recreate links as attributes or copies on purpose
        target = f[key]
        if isinstance(target, h5py.Dataset) and target.ndim and target.dtype.kind not in "OV":
            zarr.from_array(root.store, name=key, data=target, fill_value=target.fillvalue)
```

For a full recursive copy with attributes, see [patterns.md](patterns.md) Pattern 4.

---

## Issue 2: Metadata Loss During Conversion

**Symptoms:**
- `_FillValue`, `scale_factor` or `add_offset` missing from the Zarr store
- Packed `int16` data stored as `float64` or `float32`, making the store several times larger
- CF encoding attributes moved from `attrs` to `encoding` or vice versa

**Cause:** xarray moves `_FillValue`, `missing_value`, `scale_factor`, `add_offset`, `_Unsigned`, `dtype`, `units` and `calendar` (for times) from `attrs` into each variable's `encoding` when it decodes. A plain `ds.to_zarr()` writes them back. Passing `encoding={var: {...}}` **replaces** that variable's encoding, so anything not in your dict is gone. Passing the whole source encoding back fails too: `ValueError: unexpected encoding parameters for zarr backend: ['zlib', 'szip', ...]`.

**Solution:**

```python
import xarray as xr

# ── Diagnose: Compare attributes before and after ──
ds_src = xr.open_dataset("source.nc", decode_cf=False)  # raw attributes
ds_decoded = xr.open_dataset("source.nc")  # CF-decoded

for var in ds_src.data_vars:
    raw_attrs = set(ds_src[var].attrs.keys())
    decoded_attrs = set(ds_decoded[var].attrs.keys())
    moved = raw_attrs - decoded_attrs
    if moved:
        print(f"{var}: attrs moved to encoding: {moved}")

# ── Fix 1: Skip CF decoding; raw values and attributes are written unchanged ──
ds = xr.open_dataset("source.nc", decode_cf=False)
ds.to_zarr("output.zarr", mode="w")

# ── Fix 2: Keep the CF keys when you pass encoding ──
import numpy as np

KEEP = ("dtype", "scale_factor", "add_offset", "_FillValue", "missing_value")


def cf_encoding(var):
    """The source packing and fill keys, which encoding= would otherwise drop."""
    enc = {k: v for k, v in var.encoding.items() if k in KEEP}
    if var.encoding.get("_Unsigned") == "true":  # zarr rejects _Unsigned: store the unsigned dtype
        signed = np.dtype(enc["dtype"])
        enc["dtype"] = np.dtype(f"u{signed.itemsize}")
        for k in ("_FillValue", "missing_value"):
            if k in enc:
                enc[k] = np.asarray(enc[k], signed).view(enc["dtype"])
    return enc


ds = xr.open_dataset("source.nc")
encoding = {name: cf_encoding(var) for name, var in ds.data_vars.items()}
ds.to_zarr("output.zarr", mode="w", encoding=encoding)
```

Without `missing_value`, values masked by it are written as `0`. Without the unsigned dtype, an `_Unsigned` byte of `200` reads back as `-56`: xarray keeps the signed storage dtype, and the zarr backend rejects `_Unsigned` in `encoding=`.

Don't copy the raw attributes back onto decoded data with `ds[var].attrs.update(...)`: `to_zarr` then raises `ValueError: Key 'add_offset' already exists in attrs`, and if it didn't, readers would apply the scale twice.

---

## Issue 3: Memory Errors on Large File Conversion

**Symptoms:**
- System OOM kill during `ds.to_zarr()`
- Swap space fills up during conversion
- `MemoryError` while copying a dataset with h5py

**Cause:** `xr.open_dataset()` is lazy, but without `chunks=` its variables are not dask arrays, so `to_zarr` reads each whole variable into memory before writing it. With h5py, `dataset[:]` does the same.

**Solution:**

```python
import xarray as xr

# ── Fix 1: Open with Dask chunks (lazy loading), naming every dimension ──
ds = xr.open_dataset(
    "huge_file.nc",
    chunks={"time": 30, "lat": 90, "lon": 180},  # lazy
)
ds.to_zarr("output.zarr", mode="w")  # Dask writes chunk-by-chunk

# ── Fix 2: Process variables one at a time ──
import zarr

ds_info = xr.open_dataset("huge_file.nc", chunks={})
for var in ds_info.data_vars:
    ds_var = xr.open_dataset("huge_file.nc", chunks={"time": 30})[var]
    ds_var.to_dataset().to_zarr(
        "output.zarr",
        mode="a" if var != list(ds_info.data_vars)[0] else "w",
    )
    print(f"Wrote {var}")

# ── Fix 3: For h5py, copy in slices ──
import h5py
import numpy as np

with h5py.File("huge_file.h5", "r") as f:
    src = f["data"]
    root = zarr.open_group("output.zarr", mode="w")
    dst = root.create_array(
        "data",
        shape=src.shape,
        chunks=(1000, 1000),
        dtype=src.dtype,
    )

    # Copy in chunks
    chunk_size = 1000
    for start in range(0, src.shape[0], chunk_size):
        end = min(start + chunk_size, src.shape[0])
        dst[start:end] = src[start:end]
        print(f"Copied rows {start}-{end}")
```

Fix 3 holds one band of 1000 full rows at a time, which suits a 2-D dataset. For any shape, `zarr.from_array(root.store, name="data", data=src, chunks=..., fill_value=src.fillvalue)` reads and writes one output chunk at a time.

---

## Issue 4: Virtual References Become Invalid

**Symptoms:**
- `ReferenceNotReachable: Reference "temperature/1.0" failed to fetch target ...` when reading through a Kerchunk JSON store
- Data was accessible but now returns errors
- Virtual store metadata loads but data reads fail

**Cause:** VirtualiZarr and Kerchunk store the URL, byte offset and length of every source chunk. If source files are moved, renamed, deleted, or modified, the references become stale.

**Solution:**

```python
# ── Prevention: keep the sources immutable and online ──
# - S3 Object Lock or bucket versioning, read-only permissions on source directories
# - Archive tiers such as S3 Glacier Flexible Retrieval need a restore before any read,
#   so virtual reads fail there

import json
from pathlib import Path

import xarray as xr
from obspec_utils.registry import ObjectStoreRegistry
from obstore.store import LocalStore
from virtualizarr import open_virtual_mfdataset
from virtualizarr.parsers import HDFParser

# ── Fix 1: Files moved, contents unchanged: rewrite the paths ──
old_prefix, new_prefix = "/data/old_location", "/data/new_location"
refs = json.loads(Path("virtual_store.json").read_text())
for key, ref in refs["refs"].items():
    if isinstance(ref, list) and ref and isinstance(ref[0], str):  # [url, offset, length]
        ref[0] = ref[0].replace(old_prefix, new_prefix, 1)
Path("virtual_store_moved.json").write_text(json.dumps(refs))

# ── Fix 2: Files changed: rescan them ──
urls = [f"file://{p.resolve()}" for p in sorted(Path("new_location/").glob("*.nc"))]
vds = open_virtual_mfdataset(
    urls,
    registry=ObjectStoreRegistry({"file://": LocalStore()}),
    parser=HDFParser(),
    concat_dim="time",
    combine="nested",
    coords="minimal",
    compat="override",
)
vds.vz.to_kerchunk("virtual_store.json", format="json")  # overwrite references
```

**Fix 3: Version the references in Icechunk.** Write with `vds.vz.to_icechunk(session.store)` and `session.commit(...)` as in [patterns.md](patterns.md) Pattern 3. Each regeneration is a new snapshot, and older snapshots still point to the old locations, which helps auditing.

---

## Issue 5: Chunk Size Not Optimal After Migration

**Symptoms:**
- Cloud reads are slow despite successful migration
- Thousands of tiny objects in the Zarr store
- Each chunk is only a few KB instead of MB

**Cause:** The migration inherited the HDF5 chunk layout, which was optimized for local disk access rather than cloud storage (large chunks to minimize request count). This happens when the source is opened with `chunks={}`, when a dimension is left out of `chunks=` (it takes the file's chunk size), when an h5py copy reuses `dataset.chunks`, and always with VirtualiZarr or Kerchunk, which reference the existing chunks.

**Solution:**

```python
import xarray as xr

# ── Diagnose: Check chunk sizes ──
ds = xr.open_zarr("migrated.zarr")
for var in ds.data_vars:
    chunks = ds[var].encoding.get("chunks")
    if chunks:
        size_bytes = ds[var].dtype.itemsize
        for c in chunks:
            size_bytes *= c
        print(f"{var}: chunks={chunks}, size={size_bytes/1e6:.2f} MB")

# ── Fix: Rechunk during migration ──
# Target: at least 1 MB uncompressed per chunk; 1-100 MB chunk objects suit object storage
# (zarr-chunk-optimization:chunking-strategy sizes them from the access pattern)
target = {"time": 30, "lat": 90, "lon": 180}
ds_src = xr.open_dataset("source.h5", engine="h5netcdf", chunks=target)
encoding = {
    name: cf_encoding(var) | {"chunks": tuple(target[d] for d in var.dims)}  # cf_encoding: Issue 2
    for name, var in ds_src.data_vars.items()
    if set(var.dims) == {"time", "lat", "lon"}
}
ds_src.to_zarr("rechunked_output.zarr", mode="w", encoding=encoding)
```

Chunks alone would replace the source encoding and write packed integers as floats (Issue 2).

**For a store that is already Zarr**, don't install `rechunker`: 0.5.4, its latest release, requires `zarr<3,>=2.11`. Under zarr-python 3, use `zarr.from_array` for single arrays or `ds.chunk(...).to_zarr(...)` after popping `chunks`, `shards` and `preferred_chunks` from every variable's `encoding`. Without that cleanup xarray silently keeps the old chunks. The `zarr-chunk-optimization:rechunking` skill covers both routes, memory planning and validation.

---

## Issue 6: Fill Value Mismatch Between HDF5 and Zarr

**Symptoms:**
- Missing values in the source appear as specific numbers in Zarr (e.g., -9999, -999, 9.96921e+36)
- Valid data values appear as NaN in the Zarr store
- Statistical computations give different results after migration

**Cause:** xarray masks only values named by a CF `_FillValue` or `missing_value` attribute. The HDF5 dataset fill value (h5py `fillvalue`) is a different thing, and a plain HDF5 file without a `_FillValue` attribute is read unmasked: a dataset with `fillvalue=-999` came back as `[1., -999., -999.]`. Passing `encoding=` with only some keys can also drop the source `_FillValue` (Issue 2).

**Solution:**

```python
import xarray as xr
import numpy as np

# ── Diagnose: Check fill values in source ──
ds_raw = xr.open_dataset("source.nc", decode_cf=False)
for var in ds_raw.data_vars:
    fv = ds_raw[var].attrs.get("_FillValue", "not set")
    mv = ds_raw[var].attrs.get("missing_value", "not set")
    print(f"{var}: _FillValue={fv}, missing_value={mv}")

# ── Fix 1: Preserve fill values (and the packing they belong to) in encoding ──
ds = xr.open_dataset("source.nc")
encoding = {name: cf_encoding(var) for name, var in ds.data_vars.items()}  # cf_encoding: Issue 2
ds.to_zarr("output.zarr", mode="w", encoding=encoding)

# ── Fix 2: Use NaN as fill value (simplest for float data) ──
encoding = {var: {"_FillValue": np.nan} for var in ds.data_vars
            if ds[var].dtype.kind == "f"}  # NaN can't fill datetimes such as time_bnds
ds.to_zarr("output.zarr", mode="w", encoding=encoding)

# ── Fix 3: Explicitly handle missing data before writing ──
for var in ds.data_vars:
    # Replace any remaining sentinel values with NaN
    ds[var] = ds[var].where(ds[var] != -9999.0)
ds.to_zarr("output.zarr", mode="w")
```

Fix 2 replaces each variable's encoding, so packed integers are written as floats.

---

## Issue 7: Encoding/Dtype Differences Between Source and Target

**Symptoms:**
- Values differ slightly between source and migrated store
- Integer data becomes float after migration
- Time coordinates decoded differently
- Large precision differences in specific value ranges

**Cause:** xarray's CF decoding applies `scale_factor` and `add_offset` transformations, converting packed integer data to float. If the Zarr write doesn't re-encode with the same packing parameters, the on-disk representation changes. Times are decoded to `datetime64` or, for calendars such as `noleap` and `360_day`, to cftime objects, and re-encoded with the `units` and `calendar` kept in `encoding`.

**Solution:**

```python
import xarray as xr
import numpy as np

# ── Diagnose: Compare dtypes ──
ds_raw = xr.open_dataset("source.nc", decode_cf=False)
ds_decoded = xr.open_dataset("source.nc")
ds_zarr = xr.open_zarr("output.zarr")

for var in ds_raw.data_vars:
    print(f"{var}:")
    print(f"  Source (raw):     dtype={ds_raw[var].dtype}")
    print(f"  Source (decoded): dtype={ds_decoded[var].dtype}")
    print(f"  Zarr:             dtype={ds_zarr[var].dtype}")
print(f"time: source {ds_decoded.time.encoding.get('units')} / {ds_decoded.time.encoding.get('calendar')}, "
      f"zarr {ds_zarr.time.encoding.get('units')} / {ds_zarr.time.encoding.get('calendar')}")

# ── Fix 1: Preserve original packing ──
ds = xr.open_dataset("source.nc")
encoding = {name: cf_encoding(var) for name, var in ds.data_vars.items()}  # cf_encoding: Issue 2
ds.to_zarr("output.zarr", mode="w", encoding=encoding)

# ── Fix 2: Skip CF decoding entirely ──
ds = xr.open_dataset("source.nc", decode_cf=False)
ds.to_zarr("output.zarr", mode="w")  # raw stored values and attributes, nothing decoded

# ── Fix 3: Accept the type change and set target dtype explicitly ──
ds = xr.open_dataset("source.nc")
encoding = {
    "temperature": {"dtype": "float32"},  # accept decoded float
    "precipitation": {"dtype": "float32"},
}
ds.to_zarr("output.zarr", mode="w", encoding=encoding)
```

Leave `time` out of `encoding=` unless you mean to change it, so its units and calendar carry over. When appending files to a store, the store's time units win: see [patterns.md](patterns.md) Pattern 5.
