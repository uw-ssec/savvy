#!/usr/bin/env python3
"""
HDF5 to Zarr Migration Demo
============================

Demonstrates the complete HDF5-to-Zarr migration workflow:
1. Create a sample HDF5 file with h5py, with dimension scales so xarray
   sees named dimensions (without them it reports phony_dim_0, phony_dim_1, ...)
2. Convert to Zarr via xarray
3. Validate the conversion (dimensions, variables, dtype, chunks, values, attributes)
4. Print a validation report and exit 1 if any check failed

Requirements (zarr-python 3):
    pip install "zarr>=3" xarray dask h5py h5netcdf numpy
    # or: pixi add zarr xarray dask h5py h5netcdf numpy

Usage:
    python assets/hdf5-to-zarr-migration.py
"""

import shutil
import sys
import tempfile
from pathlib import Path

import h5py
import numpy as np
import xarray as xr


def main():
    work_dir = Path(tempfile.mkdtemp(prefix="hdf5_zarr_migration_"))
    h5_path = work_dir / "source_data.h5"
    zarr_path = str(work_dir / "migrated_data.zarr")
    print(f"Working directory: {work_dir}\n")

    # ── 1. Create a sample HDF5 file ──
    print("=" * 60)
    print("1. Create sample HDF5 file")
    print("=" * 60)
    rng = np.random.default_rng(42)
    n_time, n_lat, n_lon = 90, 180, 360

    with h5py.File(h5_path, "w") as f:
        f.attrs["title"] = "Sample Climate Dataset"
        f.attrs["source"] = "Synthetic data for migration demo"

        # Coordinate arrays, registered as HDF5 dimension scales
        f.create_dataset("time", data=np.arange(n_time, dtype="float64"))
        f["time"].attrs["units"] = "days since 2024-01-01"
        f.create_dataset("lat", data=np.linspace(-89.5, 89.5, n_lat))
        f["lat"].attrs["units"] = "degrees_north"
        f.create_dataset("lon", data=np.linspace(0.5, 359.5, n_lon))
        f["lon"].attrs["units"] = "degrees_east"
        for dim in ("time", "lat", "lon"):
            f[dim].make_scale(dim)

        # Data variables
        temp = rng.normal(15.0, 10.0, (n_time, n_lat, n_lon)).astype("float32")
        f.create_dataset("temperature", data=temp, chunks=(30, 90, 180))
        f["temperature"].attrs["units"] = "Celsius"
        f["temperature"].attrs["long_name"] = "Air Temperature"

        precip = rng.exponential(2.0, (n_time, n_lat, n_lon)).astype("float32")
        f.create_dataset("precipitation", data=precip, chunks=(30, 90, 180))
        f["precipitation"].attrs["units"] = "mm/day"
        f["precipitation"].attrs["long_name"] = "Daily Precipitation"

        for var in ("temperature", "precipitation"):
            for axis, dim in enumerate(("time", "lat", "lon")):
                f[var].dims[axis].attach_scale(f[dim])

    print(f"  Created: {h5_path}")
    print(f"  Size: {h5_path.stat().st_size / 1e6:.1f} MB")
    print()

    # ── 2. Convert to Zarr via xarray ──
    print("=" * 60)
    print("2. Convert HDF5 to Zarr")
    print("=" * 60)
    ds = xr.open_dataset(h5_path, engine="h5netcdf", chunks={"time": 30})
    print(f"  Source dataset: {dict(ds.sizes)}")
    print(f"  Variables: {list(ds.data_vars)}")

    # encoding["chunks"] is a tuple in the variable's dimension order
    target_chunks = (30, 90, 180)
    encoding = {
        "temperature": {"chunks": target_chunks, "dtype": "float32"},
        "precipitation": {"chunks": target_chunks, "dtype": "float32"},
    }
    ds.to_zarr(zarr_path, mode="w", encoding=encoding)
    print(f"  Wrote Zarr store: {zarr_path}")
    print()

    # ── 3. Validate the conversion ──
    print("=" * 60)
    print("3. Validate migration")
    print("=" * 60)
    ds_zarr = xr.open_zarr(zarr_path)

    checks_passed = 0
    checks_failed = 0

    # Check dimensions
    if dict(ds.sizes) == dict(ds_zarr.sizes):
        print(f"  PASS: Dimensions match: {dict(ds.sizes)}")
        checks_passed += 1
    else:
        print(f"  FAIL: Dimensions differ: {dict(ds.sizes)} vs {dict(ds_zarr.sizes)}")
        checks_failed += 1

    # Check variables
    if set(ds.data_vars) == set(ds_zarr.data_vars):
        print(f"  PASS: Variables match: {list(ds.data_vars)}")
        checks_passed += 1
    else:
        print(f"  FAIL: Variables differ")
        checks_failed += 1

    # Check dtype and on-disk chunk shape
    for var in ds.data_vars:
        dtype, chunks = ds_zarr[var].dtype, ds_zarr[var].encoding.get("chunks")
        if dtype == ds[var].dtype and chunks == target_chunks:
            print(f"  PASS: {var} dtype={dtype}, chunks={chunks}")
            checks_passed += 1
        else:
            print(f"  FAIL: {var} dtype={dtype}, chunks={chunks}")
            checks_failed += 1

    # Check values
    for var in ds.data_vars:
        src_vals = ds[var].values
        dst_vals = ds_zarr[var].values
        if np.allclose(src_vals, dst_vals, equal_nan=True, rtol=1e-6):
            print(f"  PASS: {var} values match")
            checks_passed += 1
        else:
            max_diff = np.nanmax(np.abs(src_vals - dst_vals))
            print(f"  FAIL: {var} max difference = {max_diff}")
            checks_failed += 1

    # Check attributes
    for var in ds.data_vars:
        for attr in ["units", "long_name"]:
            if ds[var].attrs.get(attr) == ds_zarr[var].attrs.get(attr):
                print(f"  PASS: {var}.{attr} = '{ds[var].attrs[attr]}'")
                checks_passed += 1
            else:
                print(f"  FAIL: {var}.{attr} differs")
                checks_failed += 1

    print()
    print(f"Results: {checks_passed} passed, {checks_failed} failed")
    print()

    # ── Cleanup ──
    ds.close()
    ds_zarr.close()
    shutil.rmtree(work_dir)
    print(f"Cleaned up {work_dir}")
    print("Done.")
    return 1 if checks_failed else 0


if __name__ == "__main__":
    sys.exit(main())
