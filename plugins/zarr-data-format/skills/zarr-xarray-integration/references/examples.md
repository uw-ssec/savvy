# Real-World Examples

Each example builds its own input locally so it runs offline. Tested with zarr-python 3.1, xarray 2026.9, Dask 2026.8 and pandas 3.1. Example 4 also needs `netCDF4` (or `h5netcdf`).

## Contents

| Section | Lines | Description |
|---------|-------|-------------|
| Example 1: Regional Means from an ERA5-Style Store | 16–63 | Lazy reads, area weights, descending latitude, monthly means |
| Example 2: Building a Time Series with Incremental Appends | 67–130 | Daily ingestion that grows one Zarr store |
| Example 3: Climatology and Anomalies with Dask | 134–182 | Out-of-core groupby, rechunked before writing |
| Example 4: Converting NetCDF Files to a Single Zarr Store | 186–246 | Combine monthly NetCDF files into one store |

---

## Example 1: Regional Means from an ERA5-Style Store

**Dataset description:** Daily 2 m temperature on a 1° grid laid out like ERA5: latitude runs from 90 to -90 and longitude from 0 to 359. Here a local store stands in for the cloud copy.

**Problem:** Compute the global, area-weighted monthly mean and a tropical-band mean without loading the whole dataset, then save the result.

**Code:**

```python
import numpy as np
import pandas as pd
import xarray as xr

# ── Stand-in for the remote store ──
times = pd.date_range("2023-01-01", periods=365, freq="D")
lat = np.linspace(90, -90, 181)
lon = np.arange(0.0, 360.0)
t2m = 288 - 30 * np.abs(np.sin(np.deg2rad(lat)))[None, :, None] + np.random.randn(365, 181, 360)
xr.Dataset(
    {"t2m": (("time", "latitude", "longitude"), t2m.astype("float32"))},
    coords={"time": times, "latitude": lat, "longitude": lon},
).to_zarr("era5_t2m.zarr", mode="w", encoding={"t2m": {"chunks": (31, 181, 360)}})

# ── Open lazily ──
# Remote: xr.open_zarr("s3://<bucket>/era5_t2m.zarr", storage_options={"anon": True})  # needs s3fs
ds = xr.open_zarr("era5_t2m.zarr")
t2m = ds["t2m"]
print(f"Dask chunks: {t2m.data.chunksize}, size: {t2m.nbytes / 1e6:.0f} MB")

# ── Area-weighted global mean ──
weights = np.cos(np.deg2rad(ds.latitude))
global_mean = t2m.weighted(weights).mean(dim=["latitude", "longitude"])

# ── Tropical band: latitude is descending, so slice from north to south ──
assert t2m.sel(latitude=slice(-23.5, 23.5)).size == 0  # wrong order: empty, no error
tropics = t2m.sel(latitude=slice(23.5, -23.5))
tropical_mean = tropics.weighted(weights.sel(latitude=tropics.latitude)).mean(dim=["latitude", "longitude"])

# ── Monthly means ("MS" or "ME"; pandas 3 rejects "1M") ──
monthly = xr.Dataset({
    "global_t2m": global_mean.resample(time="MS").mean(),
    "tropical_t2m": tropical_mean.resample(time="MS").mean(),
}).compute()
print(monthly.sizes["time"])  # 12
print(bool((monthly.tropical_t2m > monthly.global_t2m).all()))  # True

monthly.to_zarr("era5_monthly_means.zarr", mode="w")
```

---

## Example 2: Building a Time Series with Incremental Appends

**Dataset description:** A synthetic weather station network producing hourly temperature and humidity readings. Each day's batch is appended to one Zarr store.

**Problem:** Append daily batches with one code path, without the silent failures xarray allows: shifted time units, changed station lists, or overlapping days.

**Code:**

```python
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

store_path = "station_timeseries.zarr"
n_stations = 100
hours_per_day = 24
rng = np.random.default_rng(42)
# An object array writes variable-length strings. A plain list becomes fixed-width "<U8",
# which Zarr v3 writes with an UnstableSpecificationWarning.
stations = np.array([f"STN-{i:04d}" for i in range(n_stations)], dtype=object)


def generate_daily_data(date_str):
    shape = (hours_per_day, n_stations)
    return xr.Dataset(
        {
            "temperature": (["time", "station"], rng.normal(20.0, 5.0, shape).astype("float32")),
            "humidity": (["time", "station"], rng.uniform(30.0, 95.0, shape).astype("float32")),
        },
        coords={
            "time": pd.date_range(date_str, periods=hours_per_day, freq="h"),
            "station": stations,
        },
        attrs={"source": "Weather Station Network", "frequency": "hourly"},
    )


# Set on the first write; appends reuse the store's encoding.
encoding = {
    "temperature": {"chunks": (24, 100), "dtype": "float32"},
    "humidity": {"chunks": (24, 100), "dtype": "float32"},
    "time": {"units": "seconds since 1970-01-01", "dtype": "int64"},
}

for date in ["2024-06-01", "2024-06-02", "2024-06-03", "2024-06-04", "2024-06-05"]:
    ds_day = generate_daily_data(date)
    if not Path(store_path).exists():
        ds_day.to_zarr(store_path, mode="w", encoding=encoding)
        print(f"Created store with {date}")
        continue
    existing = xr.open_zarr(store_path)
    assert existing.indexes["station"].equals(ds_day.indexes["station"]), "station list changed"
    assert ds_day.time.values[0] > existing.time.values[-1], f"{date} already ingested"
    ds_day.to_zarr(store_path, append_dim="time")
    print(f"Appended {date}")

ds_all = xr.open_zarr(store_path)
print(f"Time steps: {ds_all.sizes['time']} (expected {5 * 24})")
print(f"Time range: {ds_all.time.values[0]} to {ds_all.time.values[-1]}")
print(f"Mean temperature: {float(ds_all['temperature'].mean()):.1f}°C")
assert ds_all.indexes["time"].is_monotonic_increasing and ds_all.indexes["time"].is_unique
```

---

## Example 3: Climatology and Anomalies with Dask

**Dataset description:** A global ocean temperature dataset (365 days × 720 lat × 1440 lon, about 1.5 GB as float32) stored in Zarr.

**Problem:** Compute a monthly climatology and daily anomalies lazily with Dask and write both back to Zarr. The groupby subtraction returns Dask chunks one time step long, so rechunk before writing or `to_zarr` raises the overlap error.

**Code:**

```python
import dask.array as da
import numpy as np
import pandas as pd
import xarray as xr

# ── Create a synthetic source store ──
n_time, n_lat, n_lon = 365, 720, 1440
ds = xr.Dataset(
    {"sst": (["time", "lat", "lon"],
             da.random.random((n_time, n_lat, n_lon), chunks=(30, 180, 360)).astype("float32"))},
    coords={
        "time": pd.date_range("2024-01-01", periods=n_time, freq="D"),
        "lat": np.linspace(-89.875, 89.875, n_lat),
        "lon": np.linspace(0.125, 359.875, n_lon),
    },
)
ds.to_zarr("ocean_sst_source.zarr", mode="w", encoding={"sst": {"chunks": (30, 180, 360)}})

# ── Open with Dask chunks equal to the Zarr chunks ──
ds = xr.open_zarr("ocean_sst_source.zarr")

# ── Climatology and anomalies (lazy) ──
climatology = ds["sst"].groupby("time.month").mean(dim="time")
anomalies = ds["sst"].groupby("time.month") - climatology
print(f"Climatology shape: {climatology.shape}")  # (12, 720, 1440)
print(f"Anomaly Dask chunks along time: {anomalies.chunks[0][:3]}...")  # (1, 1, 1)...

# ── Write climatology (small) ──
climatology.to_dataset(name="sst_climatology").to_zarr("ocean_sst_climatology.zarr", mode="w")

# ── Write anomalies: rechunk to the target layout first ──
anom_ds = anomalies.to_dataset(name="sst_anomaly").chunk({"time": 30, "lat": 180, "lon": 360})
anom_ds.to_zarr("ocean_sst_anomalies.zarr", mode="w",
                encoding={"sst_anomaly": {"chunks": (30, 180, 360)}})

# ── Verify ──
ds_anom = xr.open_zarr("ocean_sst_anomalies.zarr")
print(f"Zarr chunks: {ds_anom['sst_anomaly'].encoding['chunks']}")  # (30, 180, 360)
print(f"Anomaly mean (should be ~0): {float(ds_anom['sst_anomaly'].mean()):.6f}")
```

---

## Example 4: Converting NetCDF Files to a Single Zarr Store

**Dataset description:** Twelve monthly NetCDF4 files of daily temperature and precipitation from a climate model.

**Problem:** Combine them into one Zarr store with uniform 30-day chunks. `open_mfdataset` makes one Dask chunk per file (31, 29, 31, ... days), which does not line up with 30-day Zarr chunks, so rechunk before writing. For large archives or virtual references, see the `data-migration` skill.

**Code:**

```python
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

# ── Create synthetic monthly NetCDF files ──
output_dir = Path("monthly_netcdf")
output_dir.mkdir(exist_ok=True)

days_per_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
rng = np.random.default_rng(42)

for month, n_days in enumerate(days_per_month, start=1):
    ds = xr.Dataset(
        {
            "temperature": (["time", "lat", "lon"], rng.normal(15.0, 10.0, (n_days, 180, 360)).astype("float32")),
            "precipitation": (["time", "lat", "lon"], rng.exponential(2.0, (n_days, 180, 360)).astype("float32")),
        },
        coords={
            "time": pd.date_range(f"2024-{month:02d}-01", periods=n_days, freq="D"),
            "lat": np.linspace(-89.5, 89.5, 180),
            "lon": np.linspace(0.5, 359.5, 360),
        },
        attrs={"source": "Synthetic Climate Model", "month": month},
    )
    ds.to_netcdf(output_dir / f"2024-{month:02d}.nc")
print(f"Created {len(days_per_month)} NetCDF files")

# ── Combine lazily: one Dask chunk per file along time ──
ds_combined = xr.open_mfdataset(
    sorted(output_dir.glob("*.nc")),
    combine="nested",
    concat_dim="time",
    chunks={"time": 31, "lat": 90, "lon": 180},
)
print(f"Dask chunks along time: {ds_combined['temperature'].chunks[0][:3]}...")  # (31, 29, 31)...

# ── Rechunk to the Zarr layout, then write ──
ds_combined = ds_combined.chunk({"time": 30, "lat": 90, "lon": 180})
encoding = {
    "temperature": {"chunks": (30, 90, 180), "dtype": "float32"},
    "precipitation": {"chunks": (30, 90, 180), "dtype": "float32"},
}
ds_combined.to_zarr("annual_combined.zarr", mode="w", encoding=encoding, consolidated=True)

# ── Verify ──
ds_zarr = xr.open_zarr("annual_combined.zarr", consolidated=True)
print(f"Zarr store: {ds_zarr.sizes['time']} time steps")  # 366
print(f"Zarr chunks: {ds_zarr['temperature'].encoding['chunks']}")  # (30, 90, 180)
print(f"Variables: {list(ds_zarr.data_vars)}")
```
