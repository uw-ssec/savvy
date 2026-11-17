# Real-World Examples

## Contents

| Section | Lines | Description |
|---------|-------|-------------|
| Example 1: Migrating a Climate Model Archive | 14–87 | Convert a directory of monthly NetCDF files to a single Zarr store |
| Example 2: Virtual Zarr References for Granules on S3 | 88–142 | Create virtual references for cloud-hosted HDF5/NetCDF4 files |
| Example 3: HDF5 Instrument Data to Cloud Zarr with Rechunking | 143–232 | Migrate and rechunk instrument data for cloud-optimized access |
| Example 4: Validating a Large Migration | 233–316 | Per-file source-vs-target validation |

---

## Example 1: Migrating a Climate Model Archive

**Dataset description:** A 10-year climate model simulation stored as 120 monthly NetCDF files, each containing daily temperature and precipitation on a 180×360 grid (about 1.9 GB in total).

**Problem:** The many-small-files format is slow to open and expensive on cloud storage. You need to combine everything into a single consolidated Zarr store with cloud-optimized chunks.

**Code:**

```python
import xarray as xr
import numpy as np
from pathlib import Path

# ── Create synthetic monthly NetCDF files (simulating the archive) ──
archive_dir = Path("climate_archive")
archive_dir.mkdir(exist_ok=True)

rng = np.random.default_rng(42)
years = range(2010, 2020)
days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

for year in years:
    for month in range(1, 13):
        n_days = days_in_month[month - 1]
        ds = xr.Dataset(
            {
                "temperature": (["time", "lat", "lon"],
                    rng.normal(15.0, 10.0, (n_days, 180, 360)).astype("float32")),
                "precipitation": (["time", "lat", "lon"],
                    rng.exponential(2.0, (n_days, 180, 360)).astype("float32")),
            },
            coords={
                "time": xr.date_range(f"{year}-{month:02d}-01", periods=n_days, freq="D",
                                      calendar="noleap", use_cftime=True),
                "lat": np.linspace(-89.5, 89.5, 180),
                "lon": np.linspace(0.5, 359.5, 360),
            },
        )
        ds.to_netcdf(archive_dir / f"{year}-{month:02d}.nc")

print(f"Created {len(list(archive_dir.glob('*.nc')))} NetCDF files")

# ── Combine and migrate to Zarr ──
files = sorted(archive_dir.glob("*.nc"))
ds_combined = xr.open_mfdataset(files, combine="nested", concat_dim="time", parallel=True)

# One dask chunk per file (31, 28, 31, ... days) would overlap the 30-day
# Zarr chunks, and to_zarr would raise. Rechunk the combined dataset first.
ds_combined = ds_combined.chunk({"time": 30, "lat": 90, "lon": 180})
print(f"Combined: {dict(ds_combined.sizes)}")
print(f"Total size: {ds_combined.nbytes / 1e9:.1f} GB")

# ── Write with optimized encoding (chunks are a tuple in dimension order) ──
encoding = {
    "temperature": {"chunks": (30, 90, 180), "dtype": "float32"},
    "precipitation": {"chunks": (30, 90, 180), "dtype": "float32"},
}
ds_combined.to_zarr(
    "climate_10yr.zarr",
    mode="w",
    encoding=encoding,
    consolidated=True,
)

# ── Verify ──
ds_zarr = xr.open_zarr("climate_10yr.zarr", consolidated=True)
print(f"Zarr store: {ds_zarr.sizes['time']} time steps")
print(f"Time range: {ds_zarr.time.values[0]} to {ds_zarr.time.values[-1]}")
print(f"Calendar: {ds_zarr.time.encoding['calendar']}")  # noleap, carried from the files
print(f"Variables: {list(ds_zarr.data_vars)}")
```

---

## Example 2: Virtual Zarr References for Granules on S3

**Dataset description:** Thousands of HDF5/NetCDF4 swath granules (~100 MB each) in an S3 bucket, all with the same variables, cross-track size and chunk shape. Every granule must hold a whole number of chunks along `scanline`, or the concatenation raises `ValueError: Cannot concatenate arrays with partial chunks`.

**Problem:** Copying all granules to Zarr would require terabytes of storage and days of transfer time. Instead, create virtual Zarr references that point to the original files, enabling Zarr-compatible reads without any data copying. The references keep each granule's own chunks.

**Code:**

```python
import xarray as xr
from obspec_utils.registry import ObjectStoreRegistry
from obstore.store import S3Store
from virtualizarr import open_virtual_mfdataset
from virtualizarr.parsers import HDFParser

# ── List source files ──
# In practice, find granules with a catalog search (CMR, STAC, earthaccess).
bucket = "example-public-bucket"
source_files = [f"s3://{bucket}/L2/2024/001/granule_{i:03d}.h5" for i in range(1, 4)]

# ── Tell VirtualiZarr how to read the bucket ──
# Public bucket: unsigned requests. For NASA Earthdata protected buckets, use
# S3Store(..., credential_provider=obstore.auth.earthdata.NasaEarthdataCredentialProvider(url))
# from inside AWS us-west-2.
registry = ObjectStoreRegistry(
    {f"s3://{bucket}": S3Store(bucket, region="us-west-2", skip_signature=True)}
)

# ── Scan granules and combine along the along-track dimension ──
combined = open_virtual_mfdataset(
    source_files,
    registry=registry,
    parser=HDFParser(),
    concat_dim="scanline",
    combine="nested",
    coords="minimal",
    compat="override",
)
print(f"Virtual dataset: {dict(combined.sizes)}")

# ── Write the references (no data copied) ──
combined.vz.to_kerchunk("granules_virtual.json", format="json")

# ── Use it like a normal Zarr store; reads go to the original files on S3 ──
ds = xr.open_dataset(
    "granules_virtual.json",
    engine="kerchunk",
    storage_options={"remote_protocol": "s3", "remote_options": {"anon": True}},
)
subset = ds["radiance"].isel(scanline=slice(0, 100)).compute()
print(f"Loaded subset: {subset.shape}")
```

---

## Example 3: HDF5 Instrument Data to Cloud Zarr with Rechunking

**Dataset description:** A 50 GB HDF5 file from a high-energy physics detector with nested groups and time-series data chunked for sequential write during data acquisition.

**Problem:** The original HDF5 chunking (optimized for writing during acquisition) is terrible for analytical reads. You need to rechunk for time-slice access and upload to S3 for shared analysis.

**Code:**

```python
import math

import h5py
import numpy as np
import zarr


def to_json(value):
    """h5py returns NumPy scalars, arrays and bytes; Zarr attributes must be JSON."""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    if isinstance(value, np.ndarray):
        return [to_json(v) for v in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    return value


# ── Inspect the source HDF5 structure ──
with h5py.File("detector_run_2024.h5", "r") as f:
    def print_tree(group, indent=0):
        for key in group:
            item = group[key]
            prefix = "  " * indent
            if isinstance(item, h5py.Dataset):
                print(f"{prefix}{key}: shape={item.shape}, chunks={item.chunks}, dtype={item.dtype}")
            elif isinstance(item, h5py.Group):
                print(f"{prefix}{key}/")
                print_tree(item, indent + 1)
    print_tree(f)

# ── Migrate with rechunking ──
# Original chunks: (100000, 1), optimized for appending one channel at a time
# Target chunks: ~5 MB of whole rows, e.g. (5120, 256) for 256 float32 channels
with h5py.File("detector_run_2024.h5", "r") as h5f:
    store = zarr.storage.FsspecStore.from_url("s3://physics-data/detector_2024.zarr")  # needs s3fs
    root = zarr.open_group(store=store, mode="w-")
    root.attrs.update({k: to_json(v) for k, v in h5f.attrs.items()})

    for group_name in ["detectors", "triggers", "calibration"]:
        if group_name not in h5f:
            continue

        zg = root.create_group(group_name)
        zg.attrs.update({k: to_json(v) for k, v in h5f[group_name].attrs.items()})

        for ds_name, h5_ds in h5f[group_name].items():
            if not isinstance(h5_ds, h5py.Dataset) or h5_ds.ndim == 0:
                continue

            # Cloud-optimized chunks (~5 MB): whole rows, as many as fit
            row_bytes = h5_ds.dtype.itemsize * math.prod(h5_ds.shape[1:])
            rows = max(1, min(h5_ds.shape[0], 5 * 1024 * 1024 // row_bytes))
            new_chunks = (rows, *h5_ds.shape[1:])

            arr = zg.create_array(
                ds_name,
                shape=h5_ds.shape,
                chunks=new_chunks,
                dtype=h5_ds.dtype,
                fill_value=h5_ds.fillvalue,
                attributes={k: to_json(v) for k, v in h5_ds.attrs.items()},
            )

            # Copy in blocks of whole target chunks, about one source chunk tall,
            # so each source chunk is decompressed once and memory stays bounded
            # even when the source is contiguous.
            src_rows = h5_ds.chunks[0] if h5_ds.chunks else rows
            step = max(rows, src_rows // rows * rows)
            for start in range(0, h5_ds.shape[0], step):
                arr[start:start + step] = h5_ds[start:start + step]

            print(f"  {group_name}/{ds_name}: {h5_ds.chunks} → {new_chunks}")

print("Migration with rechunking complete")
```

Peak memory is one block of `step` rows, about 100 MB for `(100000, 1)` source chunks with 256 float32 channels. To rechunk a store that is already Zarr, use `zarr-chunk-optimization:rechunking`.

---

## Example 4: Validating a Large Migration

**Dataset description:** A multi-terabyte climate dataset that was migrated from 500 NetCDF files to a single Zarr store. The migration took 8 hours and you need to verify data integrity before deleting the source files.

**Problem:** You cannot load the entire dataset into memory for comparison. Validation must work file by file, reporting any discrepancies with their exact location.

**Code:**

```python
import xarray as xr
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_chunked(source_files, zarr_path, concat_dim="time", rtol=1e-5):
    """Validate a large migration by comparing one source file at a time."""
    ds_zarr = xr.open_zarr(zarr_path, chunks={})
    errors = []
    total_checks = 0

    # Compare each source file against the corresponding slice in Zarr
    time_offset = 0
    for filepath in sorted(source_files):
        ds_src = xr.open_dataset(filepath)
        n_time = ds_src.sizes[concat_dim]

        for var in ds_src.data_vars:  # includes datetime variables such as time_bnds
            if var not in ds_zarr:
                errors.append(f"Missing variable {var} in Zarr store")
                continue

            # Extract the corresponding slice from Zarr
            src = ds_src[var].load()
            dst = ds_zarr[var].isel(
                {concat_dim: slice(time_offset, time_offset + n_time)}
            ).compute()

            try:
                # NaN == NaN, works for datetimes, also checks the time coordinate
                xr.testing.assert_allclose(src, dst, rtol=rtol)
            except AssertionError:
                msg = f"{filepath.name}/{var}: values differ"
                if src.dtype.kind in "fiu":
                    diff = np.abs(src.values.astype("float64") - dst.values.astype("float64"))
                    if not np.all(np.isnan(diff)):
                        loc = np.unravel_index(np.nanargmax(diff), diff.shape)
                        msg += f", max_diff={np.nanmax(diff):.2e} at {loc}"
                errors.append(msg)
            total_checks += 1

        time_offset += n_time
        ds_src.close()
        logger.info(f"Validated {filepath.name} (offset={time_offset})")

    # Check total size matches
    expected_time = time_offset
    actual_time = ds_zarr.sizes[concat_dim]
    if expected_time != actual_time:
        errors.append(f"Time dimension: expected {expected_time}, got {actual_time}")

    ds_zarr.close()

    # Report
    print(f"\n{'='*50}")
    print(f"Validation complete: {total_checks} checks")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("ALL CHECKS PASSED")
    print(f"{'='*50}")

    return len(errors) == 0


# ── Usage ──
# source_files = sorted(Path("netcdf_archive/").glob("*.nc"))
# validate_chunked(source_files, "migrated.zarr")
```
