# Real-World Examples

## Contents

| Section | Lines | Description |
|---------|-------|-------------|
| Example 1: Accessing a Public S3 Zarr Dataset | 14–54 | Read a CMIP6 subset from the Pangeo AWS S3 catalog and know what it downloads |
| Example 2: Writing a Large Dataset to GCS with obstore | 56–117 | Write a multi-band ~1 GB dataset to GCS with the Rust-based backend |
| Example 3: Setting Up Icechunk for Versioned Data on S3 | 119–189 | Daily commits, time-travel reads and tags |
| Example 4: Multi-Backend Data Pipeline | 191–248 | Read from S3, process, and write results to Azure Blob |

---

## Example 1: Accessing a Public S3 Zarr Dataset

**Dataset description:** CMIP6 climate model output hosted on AWS S3 (us-west-2) as part of the Pangeo CMIP6 collection: monthly sea surface temperature (`tos`, °C) from GFDL-ESM4 on its native ocean grid, stored as Zarr v2 with consolidated metadata.

**Problem:** You need a regional SST mean from a cloud-hosted store, and you want to know how much a read downloads before you run it. Here every chunk spans 120 months and the whole grid, so even a small box downloads full ~100 MB chunk objects.

**Code:**

```python
import numpy as np
import zarr
from zarr.storage import FsspecStore

# ── Open the store (anonymous, read-only) ──
url = "s3://cmip6-pds/CMIP6/CMIP/NOAA-GFDL/GFDL-ESM4/historical/r1i1p1f1/Omon/tos/gn/v20190726/"
store = FsspecStore.from_url(url, storage_options={"anon": True}, read_only=True)
root = zarr.open_group(store=store, mode="r")

# ── Check what a read will fetch: the chunk is the unit of transfer ──
tos = root["tos"]
chunk_mb = np.prod(tos.chunks) * tos.dtype.itemsize / 1e6
print(f"shape={tos.shape} chunks={tos.chunks} -> {tos.nchunks} chunks of {chunk_mb:.0f} MB uncompressed")
# shape=(1980, 576, 720) chunks=(120, 576, 720) -> 17 chunks of 199 MB uncompressed

# ── Native ocean grid: lat and lon are 2-D (y, x), and lon runs from -300 to 60 ──
lat = root["lat"][:]
lon = root["lon"][:] % 360
box = (lat >= 30) & (lat <= 60) & (lon >= 280) & (lon <= 350)  # North Atlantic, 80W-10W
rows, cols = np.nonzero(box)
y0, y1, x0, x1 = rows.min(), rows.max() + 1, cols.min(), cols.max() + 1

# ── Read the first year: touches 1 of the 17 chunks ──
sst = tos[0:12, y0:y1, x0:x1]
sst = np.where(sst == tos.fill_value, np.nan, sst)   # 1e20 marks land
sst = np.where(box[y0:y1, x0:x1], sst, np.nan)       # keep cells inside the box
print(f"1850 North Atlantic mean SST: {np.nanmean(sst):.2f} degC")
```

Reading all 165 years of this box would download all 17 chunks (~1.7 GB). For many small regional reads, the dataset needs a different chunk layout (see the `chunking-strategy` and `rechunking` skills), not a different backend.

---

## Example 2: Writing a Large Dataset to GCS with obstore

**Dataset description:** A synthetic remote sensing mosaic with 4 spectral bands of 10980 × 10980 uint16 pixels (~1 GB uncompressed), written to Google Cloud Storage using the obstore backend.

**Problem:** You need to write a large, multi-variable Zarr store to GCS with chunk objects big enough for cloud I/O, without holding a whole band in memory.

**Code:**

```python
import numpy as np
import zarr
from obstore.store import GCSStore

# ── Configure the GCS backend ──
obs = GCSStore.from_url(
    "gs://my-research-bucket/sentinel2-mosaic.zarr",
    config={"GOOGLE_SERVICE_ACCOUNT": "/path/to/key.json"},
)
store = zarr.storage.ObjectStore(obs)

# ── Create the root group with metadata ──
root = zarr.open_group(store=store, mode="w")
root.attrs.update({
    "title": "Sentinel-2 Regional Mosaic",
    "spatial_resolution": "10m",
    "crs": "EPSG:32610",
    "date_range": "2024-06-01/2024-08-31",
})

# ── Define array dimensions ──
n_bands = 4
n_y = 10980  # ~110 km at 10m
n_x = 10980
band_names = ["B02_Blue", "B03_Green", "B04_Red", "B08_NIR"]

# ── Chunk size: 2048 * 2048 * 2 bytes (uint16) = 8 MiB uncompressed per chunk ──
# (512 x 512 would be 512 KB, below the ~1 MB floor for object storage)
chunk_y, chunk_x = 2048, 2048

# ── Create band arrays ──
for i, name in enumerate(band_names):
    arr = root.create_array(
        name,
        shape=(n_y, n_x),
        chunks=(chunk_y, chunk_x),
        dtype="uint16",
        fill_value=0,
    )
    arr.attrs["long_name"] = name
    arr.attrs["units"] = "reflectance_scaled"

    # Write one row of chunks at a time (~45 MB), so no band is held in memory
    rng = np.random.default_rng(seed=i)
    for y_start in range(0, n_y, chunk_y):
        y_end = min(y_start + chunk_y, n_y)
        tile = rng.integers(0, 10000, size=(y_end - y_start, n_x), dtype="uint16")
        arr[y_start:y_end, :] = tile

print(f"Wrote {n_bands} bands, {n_y}x{n_x} pixels to GCS")
```

---

## Example 3: Setting Up Icechunk for Versioned Data on S3

**Dataset description:** A continuously updated air quality monitoring dataset that needs version history for regulatory compliance. Each daily update adds new observations and every past version must stay readable.

**Problem:** You need a Zarr-compatible store with atomic commits and the ability to read data as it existed at any past snapshot.

**Code:**

```python
import icechunk
import numpy as np
import zarr

# ── Repository on S3 (credentials from the environment) ──
storage = icechunk.s3_storage(
    bucket="air-quality-data",
    prefix="monitoring-v2",
    region="us-east-1",
    from_env=True,
)
repo = icechunk.Repository.open_or_create(storage)

# ── Day 1: create the structure and commit ──
session = repo.writable_session("main")
root = zarr.open_group(store=session.store, mode="w")
root.attrs["dataset"] = "Urban Air Quality Monitoring Network"
root.attrs["version_policy"] = "Daily commits, monthly tags"

# Station metadata (dtype=str: zarr 3.1 warns that "<U10" is not in the v3 spec)
n_stations = 50
stations = root.create_group("stations")
station_ids = stations.create_array("id", shape=(n_stations,), chunks=(n_stations,), dtype=str)
station_lat = stations.create_array("latitude", shape=(n_stations,), chunks=(n_stations,), dtype="float64")
station_lon = stations.create_array("longitude", shape=(n_stations,), chunks=(n_stations,), dtype="float64")

rng = np.random.default_rng(42)
station_ids[:] = [f"STN-{i:04d}" for i in range(n_stations)]
station_lat[:] = rng.uniform(40.0, 42.0, n_stations)
station_lon[:] = rng.uniform(-74.5, -73.5, n_stations)

# Measurement arrays (initially one day)
measurements = root.create_group("measurements")
pm25 = measurements.create_array(
    "pm25", shape=(24, n_stations), chunks=(24, n_stations), dtype="float32",
)
pm25[:] = rng.uniform(5.0, 35.0, (24, n_stations)).astype("float32")
pm25.attrs["units"] = "µg/m³"
pm25.attrs["long_name"] = "PM2.5 Concentration"

commit_1 = session.commit("Initial station setup with day-1 PM2.5 data")

# ── Day 2: a committed session is read-only, so open a new one ──
pm25_day2 = rng.uniform(5.0, 35.0, (24, n_stations)).astype("float32")
session = repo.writable_session("main")
pm25 = zarr.open_array(store=session.store, path="measurements/pm25", mode="r+")
pm25.resize((48, n_stations))
pm25[24:48, :] = pm25_day2
commit_2 = session.commit("Add day-2 PM2.5 observations")

# ── Read data as of the first commit (time travel) ──
day1 = repo.readonly_session(snapshot_id=commit_1)
root_v1 = zarr.open_group(store=day1.store, mode="r")
print(f"Day-1 snapshot shape: {root_v1['measurements/pm25'].shape}")  # (24, 50)

# ── Tag a monthly release and list history ──
repo.create_tag("2024-01", snapshot_id=commit_2)
for snapshot in repo.ancestry(branch="main"):
    print(snapshot.id[:8], snapshot.message)
```

---

## Example 4: Multi-Backend Data Pipeline

**Dataset description:** A processing pipeline that reads raw satellite data from an S3 archive, applies corrections, and writes results to Azure Blob Storage for downstream consumption by an Azure-based analytics platform.

**Problem:** You need to read from one cloud provider and write to another, using appropriate backends for each, while managing memory for a dataset that does not fit in RAM.

**Code:**

```python
import numpy as np
import zarr
from zarr.storage import FsspecStore

# ── Source: Read raw data from S3 ──
src_store = FsspecStore.from_url(
    "s3://satellite-archive/raw/2024-Q1.zarr",
    storage_options={"anon": True},
)
src = zarr.open_group(store=src_store, mode="r")
print(f"Source members: {list(src.keys())}")

# ── Destination: Azure Blob via managed identity / az login (DefaultAzureCredential) ──
dst_store = FsspecStore.from_url(
    "az://processed-data/corrected/2024-Q1.zarr",
    storage_options={"account_name": "analyticsstorage", "anon": False},
)
dst = zarr.open_group(store=dst_store, mode="w")
dst.attrs.update(dict(src.attrs))
dst.attrs["processing"] = "bias-corrected"

# ── Process each variable in chunk rows to manage memory ──
for var_name in ["radiance_band1", "radiance_band2", "radiance_band3"]:
    src_arr = src[var_name]
    dst_arr = dst.create_array(
        var_name,
        shape=src_arr.shape,
        chunks=src_arr.chunks,
        dtype="float32",
    )
    # Copy attributes
    dst_arr.attrs.update(dict(src_arr.attrs))

    # Process in row-chunks to limit memory
    chunk_rows = src_arr.chunks[0]
    for row_start in range(0, src_arr.shape[0], chunk_rows):
        row_end = min(row_start + chunk_rows, src_arr.shape[0])
        data = src_arr[row_start:row_end, :]

        # Apply bias correction (example: subtract per-row mean offset)
        correction = np.nanmean(data, axis=1, keepdims=True) * 0.02
        corrected = data - correction

        dst_arr[row_start:row_end, :] = corrected.astype("float32")

    print(f"Processed {var_name}: {src_arr.shape}")

print("Pipeline complete: S3 → process → Azure Blob")
```
