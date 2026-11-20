# Data Migration Patterns

## Contents

| Section | Lines | Description |
|---------|-------|-------------|
| Pattern 1: Single HDF5 File to Zarr via xarray | 17–76 | Convert one HDF5 file with new chunks and a deliberate dtype change |
| Pattern 2: Directory of NetCDF Files to Single Zarr Store | 77–131 | Combine many NetCDFs into one Zarr store |
| Pattern 3: Virtual References with VirtualiZarr or Kerchunk | 132–241 | Reference existing HDF5/NetCDF4 chunks without copying |
| Pattern 4: Group-by-Group Copy with h5py | 242–321 | Copy an HDF5 tree xarray can't model, chunk by chunk |
| Pattern 5: Incremental Migration with Checkpointing | 322–396 | Append file by file with a resumable checkpoint |
| Pattern 6: Post-Migration Validation Pipeline | 397–468 | Compare source and target chunk by chunk, with a report |
| Pattern 7: Zarr v2 Store to Zarr v3 | 469–508 | Rewrite a v2 store in the v3 format |

---

## Pattern 1: Single HDF5 File to Zarr via xarray

**Description:** Convert a single HDF5 file to Zarr using xarray as the intermediary. This handles CF metadata and coordinate variables, and sets a new chunk layout during conversion.

**When to use:**
- HDF5 files produced by scientific models or instruments
- Need to change chunk layout for cloud-optimized access
- The file has netCDF-4 style dimension scales. Without them h5netcdf names the dimensions `phony_dim_0`, `phony_dim_1`, ... Rename those with `ds.rename_dims(...)` before choosing chunks, or use Pattern 4.

**Code example:**

```python
import numpy as np
import xarray as xr

target = {"time": 30, "x": 100, "y": 100}

# ── Open lazily, with dask chunks equal to the target Zarr chunks ──
# A dimension left out of chunks= keeps the file's HDF5 chunk size.
ds = xr.open_dataset("simulation_output.h5", engine="h5netcdf", chunks=target)
print(f"Source: {dict(ds.sizes)}")
print(f"Variables: {list(ds.data_vars)}")

# ── Define encoding for Zarr ──
# encoding= replaces each listed variable's source encoding, so carry over
# the packing and fill values, then change only what you mean to change.
KEEP = ("dtype", "scale_factor", "add_offset", "_FillValue", "missing_value")


def cf_encoding(var):
    enc = {k: v for k, v in var.encoding.items() if k in KEEP}
    if var.encoding.get("_Unsigned") == "true":  # zarr rejects _Unsigned: store the unsigned dtype
        signed = np.dtype(enc["dtype"])
        enc["dtype"] = np.dtype(f"u{signed.itemsize}")
        for k in ("_FillValue", "missing_value"):
            if k in enc:
                enc[k] = np.asarray(enc[k], signed).astype(enc["dtype"])
    return enc


encoding = {}
for name, var in ds.data_vars.items():
    enc = cf_encoding(var)
    if var.dtype == "float64" and "scale_factor" not in enc:
        enc["dtype"] = "float32"  # deliberate narrowing
    enc["chunks"] = tuple(target.get(d, ds.sizes[d]) for d in var.dims)
    encoding[name] = enc

# ── Write to Zarr ──
ds.to_zarr("simulation_output.zarr", mode="w-", encoding=encoding)

# ── Verify ──
ds_zarr = xr.open_zarr("simulation_output.zarr")
print(f"Target: {dict(ds_zarr.sizes)}")
xr.testing.assert_allclose(ds, ds_zarr, rtol=1e-5)  # float32 keeps ~7 significant digits
print("Validation passed")
```

---

## Pattern 2: Directory of NetCDF Files to Single Zarr Store

**Description:** Combine an archive of NetCDF files (typically one file per time step or month) into a single Zarr store. This eliminates the many-small-files problem and enables efficient cloud storage.

**When to use:**
- Climate model output split into monthly or daily files
- Observational archives with one file per satellite pass or station
- Any collection of NetCDF files that should be a single dataset

**Code example:**

```python
import xarray as xr
from pathlib import Path

# ── Discover source files ──
source_dir = Path("netcdf_archive/")
files = sorted(source_dir.glob("*.nc"))
print(f"Found {len(files)} NetCDF files")

# ── Open all files lazily ──
ds = xr.open_mfdataset(
    files,
    combine="nested",
    concat_dim="time",
    parallel=True,  # use Dask for parallel file opening
)

# ── Rechunk the combined dataset ──
# open_mfdataset chunks each file separately (31, 28, 31, ... days), which
# overlaps 30-step Zarr chunks and makes to_zarr raise a ValueError.
target = {"time": 30, "lat": 90, "lon": 180}
ds = ds.chunk(target)
print(f"Combined: {dict(ds.sizes)}")

# ── Define encoding ──
encoding = {
    var: {"chunks": tuple(target[d] for d in ds[var].dims), "dtype": "float32"}
    for var in ds.data_vars
    if set(ds[var].dims) == {"time", "lat", "lon"}
}

# ── Write to Zarr ──
ds.to_zarr("combined_archive.zarr", mode="w-", encoding=encoding)
print("Migration complete")

# ── Verify total time steps ──
ds_zarr = xr.open_zarr("combined_archive.zarr")
print(f"Total time steps: {ds_zarr.sizes['time']}")
```

The `dtype` entry replaces each variable's source encoding. If the files hold packed integers (`scale_factor`, `add_offset`), carry those keys over as in Pattern 1.

---

## Pattern 3: Virtual References with VirtualiZarr or Kerchunk

**Description:** Create a virtual Zarr store that references chunks in existing HDF5/NetCDF4 files without copying any array data. Reads are served from the source files with byte-range requests.

**When to use:**
- Large archives where full copying is impractical or too expensive
- Source files are already on cloud storage (S3, GCS)
- Need a unified Zarr interface over many source files
- Want to try a layout before committing to a full copy

**Limits:** a virtual store keeps the source's chunk shape and codecs. VirtualiZarr and Kerchunk can join whole chunks from many files but cannot split or merge them, so a store full of tiny HDF5 chunks stays that way. A different layout needs a copy (Patterns 1 and 2). Zarr needs a regular chunk grid, so every file must have the same chunk shape and hold a whole number of chunks along the concatenation dimension. Contiguous monthly files of 28 to 31 days fail with `ValueError: Cannot concatenate arrays with inconsistent chunk shapes`, and files of uneven length with `Cannot concatenate arrays with partial chunks`. Such archives need a copy. `HDFParser` reads HDF5 and NetCDF4, not HDF4 (`.hdf`). Use `NetCDF3Parser` for NetCDF3 files.

**Code example (VirtualiZarr 2.x):**

```python
from pathlib import Path

import xarray as xr
from obspec_utils.registry import ObjectStoreRegistry
from obstore.store import LocalStore
from virtualizarr import open_virtual_mfdataset
from virtualizarr.parsers import HDFParser

# ── Scan each source file for chunk byte ranges ──
urls = [f"file://{p.resolve()}" for p in sorted(Path("archive/").glob("*.nc"))]
registry = ObjectStoreRegistry({"file://": LocalStore()})
vds = open_virtual_mfdataset(
    urls,
    registry=registry,
    parser=HDFParser(),
    concat_dim="time",
    combine="nested",
    coords="minimal",    # don't load and compare virtual variables
    compat="override",   # needed when non-index coordinates such as lat_bnds are virtual
)
print(f"Combined virtual dataset: {dict(vds.sizes)}")

# ── Write the references (metadata and byte offsets only) ──
vds.vz.to_kerchunk("virtual_archive.json", format="json")

# ── Read through the references ──
ds = xr.open_dataset("virtual_archive.json", engine="kerchunk")
print(f"Chunks are still the source's: {ds['temperature'].encoding['chunks']}")
subset = ds["temperature"].isel(time=slice(0, 10)).compute()
print(f"Subset shape: {subset.shape}")
```

For files on S3, register an `obstore.store.S3Store` for the bucket instead of `LocalStore`, for example `ObjectStoreRegistry({"s3://my-bucket": S3Store("my-bucket", region="us-west-2", skip_signature=True)})` for a public bucket, and pass `s3://my-bucket/...` URLs.

**Writing to Icechunk instead of JSON** (versioned, transactional). Icechunk only reads virtual chunks from containers you declare and authorize:

```python
import icechunk

source_dir = str(Path("archive/").resolve())
prefix = f"file://{source_dir}/"
config = icechunk.RepositoryConfig.default()
config.set_virtual_chunk_container(
    icechunk.VirtualChunkContainer(prefix, icechunk.local_filesystem_store(source_dir))
)
credentials = icechunk.containers_credentials(
    {prefix: icechunk.Credentials.LocalFileSystemAccess()}
)
repo = icechunk.Repository.create(
    icechunk.local_filesystem_storage("virtual_archive.icechunk"),
    config,
    authorize_virtual_chunk_access=credentials,
)
session = repo.writable_session("main")
vds.vz.to_icechunk(session.store)
session.commit("Add virtual references to archive/")

ds = xr.open_zarr(repo.readonly_session("main").store, consolidated=False)
```

**Kerchunk without VirtualiZarr** (older pipelines that already use it):

```python
import json
from pathlib import Path

import fsspec
import xarray as xr
from kerchunk.combine import MultiZarrToZarr
from kerchunk.hdf import SingleHdf5ToZarr

refs_list = []
for path in sorted(Path("archive/").glob("*.nc")):
    url = str(path.resolve())  # or "s3://bucket/file.nc" with fsspec.open(url, anon=True)
    with fsspec.open(url, mode="rb") as f:
        refs_list.append(SingleHdf5ToZarr(f, url).translate())

# coo_map decodes CF times. Without it, files whose time units differ
# ("days since 2024-01-01", "days since 2024-02-01", ...) have identical raw
# time values, and MultiZarrToZarr silently merges them into one file's length.
combined_refs = MultiZarrToZarr(
    refs_list, concat_dims=["time"], coo_map={"time": "cf:time"}
).translate()
with open("combined_refs.json", "w") as f:
    json.dump(combined_refs, f)

ds = xr.open_dataset(
    "combined_refs.json",
    engine="kerchunk",
    # For S3 sources add: storage_options={"remote_protocol": "s3", "remote_options": {"anon": True}}
)
```

---

## Pattern 4: Group-by-Group Copy with h5py

**Description:** Copy HDF5 group hierarchies directly to Zarr, preserving the tree, attributes and datasets. Use this when xarray cannot represent the HDF5 structure (deeply nested groups, datasets without dimension scales).

**When to use:**
- HDF5 files with complex group hierarchies that xarray flattens
- Need to preserve exact group/dataset structure
- Files with non-standard HDF5 features

**zarr-python 3 rules this code follows:**
- `create_array(name, data=..., dtype=...)` raises `ValueError`. `zarr.from_array(..., data=h5py_dataset)` reads and writes one output chunk at a time, so the dataset never sits in memory whole.
- `from_array` does not carry over the HDF5 `fillvalue` or attributes. Pass them.
- Attributes must be JSON: h5py returns `np.int64`, `np.ndarray` and sometimes `bytes`, which raise `TypeError: Object of type ... is not JSON serializable`.
- h5py follows soft links, so a plain walk copies the target twice, and a dangling external link raises `KeyError`. Copy hard links only and record the rest.

**Code example:**

```python
import h5py
import numpy as np
import zarr


def to_json(value):
    """Convert an h5py attribute value to a JSON-serializable one."""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    if isinstance(value, np.ndarray):
        return to_json(value.tolist())  # nested lists for 2-D and up
    if isinstance(value, (list, tuple)):
        return [to_json(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def migrate_hdf5_to_zarr(h5_path, zarr_path):
    """Recursively copy an HDF5 file to a Zarr store, one chunk at a time."""
    root = zarr.open_group(zarr_path, mode="w-")
    skipped = []

    def copy_node(h5_node, zarr_node):
        zarr_node.attrs.update({k: to_json(v) for k, v in h5_node.attrs.items()})
        for key in h5_node:
            if not isinstance(h5_node.get(key, getlink=True), h5py.HardLink):
                skipped.append(f"{h5_node.name}/{key} (link)")
                continue
            item = h5_node[key]
            if isinstance(item, h5py.Group):
                copy_node(item, zarr_node.create_group(key))
            elif item.ndim == 0:
                zarr_node.attrs[key] = to_json(item[()])  # scalar dataset
            elif item.dtype.kind in "OV":  # vlen strings, references, compound
                skipped.append(f"{item.name} (dtype {item.dtype})")
            else:
                zarr.from_array(
                    zarr_node.store,
                    name=f"{zarr_node.path}/{key}".lstrip("/"),
                    data=item,
                    chunks=item.chunks or "auto",  # HDF5 chunks may be tiny; see common-issues.md Issue 5
                    fill_value=item.fillvalue,
                    attributes={k: to_json(v) for k, v in item.attrs.items()},
                )

    with h5py.File(h5_path, "r") as h5f:
        copy_node(h5f, root)
    for s in skipped:
        print(f"  skipped {s}")
    print(f"Migrated {h5_path} → {zarr_path}")
    return zarr.open_group(zarr_path, mode="r")


# ── Usage ──
root = migrate_hdf5_to_zarr("instrument_data.h5", "instrument_data.zarr")
for path, node in root.members(max_depth=None):  # root.tree() needs the rich package
    print(path, getattr(node, "shape", ""))
```

---

## Pattern 5: Incremental Migration with Checkpointing

**Description:** Migrate a large archive of files with checkpoint tracking, so the migration can be resumed if interrupted. Each successfully migrated file is recorded, and completed files are skipped on restart.

**When to use:**
- Archives with thousands of files where migration takes hours or days
- Unreliable environments (spot instances, preemptible VMs)
- Need to track progress and stop cleanly on a bad file

**Two traps this code guards against:**
- **Time units.** Appends reuse the store's `time` units and dtype. With `days since ...` stored as int64, 6-hourly appends were written as the wrong dates (2000-01-03T06 became 2000-02-24), with only a `UserWarning`. Set units fine enough for every file on the first write, for every datetime variable: `time_bnds` keeps its own units from the file, and its 6-hourly bounds were appended as April dates. Update `encoding` in place so each variable keeps its calendar and fill value; `encoding={"time": {...}}` replaced a `standard` calendar with `proleptic_gregorian`.
- **Partial appends.** `to_zarr(append_dim=...)` resizes the arrays before writing data. A crash in between leaves extra fill-value steps, and blindly re-appending duplicates the file. Record the expected length and stop if the store disagrees.

**Code example:**

```python
import json
import logging
from pathlib import Path

import xarray as xr

logger = logging.getLogger(__name__)


def incremental_migrate(
    source_dir: str,
    zarr_path: str,
    checkpoint_file: str = "migration_checkpoint.json",
    pattern: str = "*.nc",
    time_units: str = "hours since 1970-01-01",  # fine enough for every file
):
    """Append files in order, resuming from a checkpoint. Stops on the first failure."""
    source_files = sorted(Path(source_dir).glob(pattern))
    checkpoint_path = Path(checkpoint_file)
    state = (json.loads(checkpoint_path.read_text()) if checkpoint_path.exists()
             else {"done": [], "time_len": 0})

    if state["done"]:
        # consolidated=False reads each array's own metadata, which a crashed write may have resized
        actual = xr.open_zarr(zarr_path, consolidated=False).sizes["time"]
        if actual != state["time_len"]:
            raise RuntimeError(
                f"{zarr_path} has {actual} time steps, checkpoint expects {state['time_len']}: "
                "an append was interrupted. Rebuild or trim the store before resuming."
            )

    remaining = [f for f in source_files if str(f) not in state["done"]]
    logger.info(f"Resuming: {len(state['done'])} done, {len(remaining)} remaining")

    for filepath in remaining:  # any exception stops the run; fix the file and rerun
        with xr.open_dataset(filepath) as ds:
            if not state["done"]:
                for var in ds.variables.values():
                    if " since " in str(var.encoding.get("units", "")):  # time, time_bnds, ...
                        var.encoding.update(units=time_units, dtype="int64")
                ds.to_zarr(zarr_path, mode="w-")
            else:
                ds.to_zarr(zarr_path, append_dim="time")
            state["time_len"] += ds.sizes["time"]
        state["done"].append(str(filepath))
        checkpoint_path.write_text(json.dumps(state))
        logger.info(f"Migrated {filepath.name}")

    logger.info(f"Migration complete: {len(state['done'])}/{len(source_files)} files")


# ── Usage ──
# incremental_migrate("netcdf_archive/", "migrated.zarr")
```

Skipping a failed file and carrying on would leave a gap in `time`, and appending it later would put it out of order.

---

## Pattern 6: Post-Migration Validation Pipeline

**Description:** Systematically validate that a migrated Zarr store matches the original source data in dimensions, variables, values and attributes.

**When to use:**
- After any format migration (HDF5/NetCDF → Zarr)
- Before decommissioning source files
- As part of an automated CI/CD migration pipeline

**Code example:**

```python
import numpy as np
import xarray as xr


def lost_or_changed(a, b):
    """Attribute names missing from b, or whose value differs."""
    return {k for k in a if k not in b or not np.array_equal(a[k], b[k])}


def validate_migration(source_path, zarr_path, rtol=1e-5, chunks="auto", **open_kwargs):
    """Compare a source file with its Zarr copy, chunk by chunk."""
    ds_src = xr.open_dataset(source_path, chunks=chunks, **open_kwargs)
    ds_dst = xr.open_zarr(zarr_path)
    report = {"passed": [], "failed": []}

    # ── 1. Dimensions and variables ──
    if dict(ds_src.sizes) == dict(ds_dst.sizes):
        report["passed"].append("Dimensions match")
    else:
        report["failed"].append(f"Dims: src={dict(ds_src.sizes)}, dst={dict(ds_dst.sizes)}")
    src_vars, dst_vars = set(ds_src.variables), set(ds_dst.variables)
    if src_vars - dst_vars:
        report["failed"].append(f"Missing variables: {src_vars - dst_vars}")
    if dst_vars - src_vars:
        report["failed"].append(f"Extra variables: {dst_vars - src_vars}")

    # ── 2. Values and attributes, every variable including time and bounds ──
    for name in sorted(src_vars & dst_vars):
        try:
            # NaN == NaN, works on datetimes, computes one dask chunk at a time
            xr.testing.assert_allclose(ds_src[name], ds_dst[name], rtol=rtol)
            report["passed"].append(f"{name}: values match (rtol={rtol})")
        except AssertionError as e:
            report["failed"].append(f"{name}: {str(e).splitlines()[0]}")
        bad_attrs = lost_or_changed(ds_src[name].attrs, ds_dst[name].attrs)
        if bad_attrs:
            report["failed"].append(f"{name}: missing or changed attrs {bad_attrs}")

    # ── 3. Global attributes ──
    bad_attrs = lost_or_changed(ds_src.attrs, ds_dst.attrs)
    if bad_attrs:
        report["failed"].append(f"Global attrs missing or changed: {bad_attrs}")

    # ── Print report ──
    print("\n=== Migration Validation Report ===")
    for item in report["passed"]:
        print(f"  PASS: {item}")
    for item in report["failed"]:
        print(f"  FAIL: {item}")
    print(f"\nResult: {len(report['passed'])} passed, {len(report['failed'])} failed")

    ds_src.close()
    ds_dst.close()
    return not report["failed"]
```

With no dtype narrowing, use `xr.testing.assert_equal` for an exact check.

---

## Pattern 7: Zarr v2 Store to Zarr v3

**Description:** Rewrite a Zarr v2 store in the v3 format, for sharding or for tools that only read v3. zarr-python 3 reads both formats.

**When to use:**
- A store written by zarr-python 2 or by xarray with `zarr_format=2`
- You want v3 features such as sharding, or a single format across an archive

**Code example:**

```python
import xarray as xr
import zarr

# Name the v3 codec instead of relying on a default. checksum=True makes a
# corrupted chunk fail to decode instead of reading back as wrong numbers.
compressor = zarr.codecs.ZstdCodec(level=3, checksum=True)

# ── xarray datasets ──
ds = xr.open_zarr("legacy_v2.zarr")
for var in ds.variables.values():
    var.encoding.pop("filters", None)  # v2 numcodecs objects are invalid in v3
    var.encoding["compressors"] = (compressor,)
ds.to_zarr("store_v3.zarr", zarr_format=3, mode="w-")
xr.testing.assert_identical(xr.open_zarr("legacy_v2.zarr"), xr.open_zarr("store_v3.zarr"))

# ── A single array without xarray metadata ──
src = zarr.open_array("legacy_array_v2.zarr", mode="r")
dst = zarr.from_array(
    "array_v3.zarr",
    data=src,
    zarr_format=3,
    compressors=compressor,
    fill_value=src.fill_value,     # dropped by default in zarr-python 3.1.5
    attributes=dict(src.attrs),    # dropped by default in zarr-python 3.1.5
)
print(dst.metadata.zarr_format, dst.chunks, dst.compressors)
```

Leaving the v2 `compressors` entry in `encoding` makes `to_zarr` raise `TypeError: Expected a BytesBytesCodec. Got <class 'numcodecs.blosc.Blosc'> instead.` The `compressor` (singular) key is rejected by both formats. v2 filters such as `Delta` have v3 equivalents under `zarr.codecs.numcodecs` (see `compression-codecs`). `from_array` keeps the chunk shape unless you pass `chunks=`. To change it, use `zarr-chunk-optimization:rechunking`.
