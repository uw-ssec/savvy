#!/usr/bin/env python3
"""
xarray + Zarr Roundtrip Demo
=============================

Demonstrates the core xarray-Zarr workflow:
1. Create a synthetic xarray Dataset
2. Write to Zarr with encoding
3. Read back and verify
4. Append new time steps
5. Inspect Dask/Zarr chunk alignment

Requirements:
    pip install xarray zarr numpy pandas dask
    # or: pixi add xarray zarr numpy pandas dask

Usage:
    python xarray-zarr-roundtrip.py
"""

import shutil
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


def main():
    work_dir = Path(tempfile.mkdtemp(prefix="xarray_zarr_demo_"))
    store_path = str(work_dir / "demo_dataset.zarr")
    print(f"Working directory: {work_dir}\n")

    # ── 1. Create a synthetic Dataset ──
    print("=" * 60)
    print("1. Create synthetic xarray Dataset")
    print("=" * 60)
    rng = np.random.default_rng(42)
    ds = xr.Dataset(
        {
            "temperature": (["time", "lat", "lon"], rng.normal(15.0, 10.0, (90, 180, 360)).astype("float64")),
            "precipitation": (["time", "lat", "lon"], rng.exponential(2.0, (90, 180, 360)).astype("float64")),
        },
        coords={
            "time": pd.date_range("2024-01-01", periods=90, freq="D"),
            "lat": np.linspace(-89.5, 89.5, 180),
            "lon": np.linspace(0.5, 359.5, 360),
        },
        attrs={"title": "Demo Climate Dataset", "source": "Synthetic"},
    )
    print(f"  Dataset: {dict(ds.sizes)}")
    print(f"  Variables: {list(ds.data_vars)}")
    print(f"  temperature dtype: {ds['temperature'].dtype}")
    print()

    # ── 2. Write to Zarr with encoding ──
    print("=" * 60)
    print("2. Write to Zarr with per-variable encoding")
    print("=" * 60)
    # encoding["chunks"] must be a tuple in the variable's dimension order;
    # a dict raises TypeError.
    encoding = {
        "temperature": {"chunks": (30, 90, 180), "dtype": "float32"},
        "precipitation": {"chunks": (30, 90, 180), "dtype": "float32"},
    }
    ds.to_zarr(store_path, mode="w", encoding=encoding)
    print(f"  Wrote to: {store_path}")
    print("  Encoding: dtype=float32, chunks=(30, 90, 180)")
    print()

    # ── 3. Read back and verify ──
    print("=" * 60)
    print("3. Read back and verify roundtrip")
    print("=" * 60)
    ds_read = xr.open_zarr(store_path, chunks={})
    print(f"  Dims: {dict(ds_read.sizes)}")
    print(f"  temperature dtype on disk: {ds_read['temperature'].encoding.get('dtype')}")
    print(f"  Zarr chunks: {ds_read['temperature'].encoding.get('chunks')}")

    # Verify values (accounting for float64 → float32 precision loss)
    orig = ds["temperature"].values.astype("float32")
    read = ds_read["temperature"].values
    max_diff = np.max(np.abs(orig - read))
    print(f"  Max value difference (float64→float32): {max_diff:.2e}")
    assert max_diff < 1e-6, "Roundtrip verification failed!"
    print("  Roundtrip verification: PASSED")
    print()

    # ── 4. Append new time steps ──
    print("=" * 60)
    print("4. Append new time steps")
    print("=" * 60)
    ds_new = xr.Dataset(
        {
            "temperature": (["time", "lat", "lon"], rng.normal(20.0, 8.0, (30, 180, 360)).astype("float32")),
            "precipitation": (["time", "lat", "lon"], rng.exponential(3.0, (30, 180, 360)).astype("float32")),
        },
        coords={
            "time": pd.date_range("2024-03-31", periods=30, freq="D"),
            "lat": np.linspace(-89.5, 89.5, 180),
            "lon": np.linspace(0.5, 359.5, 360),
        },
    )
    # xarray does not check these before appending: different lat/lon values
    # silently replace the store's coordinates, and overlapping times duplicate.
    assert ds_read.indexes["lat"].equals(ds_new.indexes["lat"])
    assert ds_read.indexes["lon"].equals(ds_new.indexes["lon"])
    assert set(ds_new.data_vars) == set(ds_read.data_vars)
    assert ds_new.time.values[0] > ds_read.time.values[-1]
    ds_new.to_zarr(store_path, append_dim="time")

    ds_appended = xr.open_zarr(store_path)
    print("  Time steps before: 90")
    print(f"  Time steps after:  {ds_appended.sizes['time']}")
    print(f"  Time range: {ds_appended.time.values[0]} to {ds_appended.time.values[-1]}")
    assert ds_appended.sizes["time"] == 120
    assert ds_appended.indexes["time"].is_monotonic_increasing
    print()

    # ── 5. Inspect chunk alignment ──
    print("=" * 60)
    print("5. Inspect Dask/Zarr chunk alignment")
    print("=" * 60)
    ds_chunked = xr.open_zarr(store_path, chunks={})
    for var in ds_chunked.data_vars:
        zarr_chunks = ds_chunked[var].encoding.get("chunks", "N/A")
        dask_chunks = ds_chunked[var].data.chunksize
        print(f"  {var}:")
        print(f"    Zarr chunks: {zarr_chunks}")
        print(f"    Dask chunks: {dask_chunks}")
        # Aligned means every Dask chunk is a whole multiple of the Zarr chunk.
        # Smaller Dask chunks are not aligned: they re-read a Zarr chunk per task,
        # and to_zarr refuses to write them in parallel.
        if zarr_chunks != "N/A":
            aligned = all(d % z == 0 for d, z in zip(dask_chunks, zarr_chunks))
            print(f"    Aligned: {'YES' if aligned else 'NO — consider rechunking'}")
    print()

    # ── Cleanup ──
    shutil.rmtree(work_dir)
    print(f"Cleaned up {work_dir}")
    print("Done.")


if __name__ == "__main__":
    main()
