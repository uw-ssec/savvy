# Zarr + xarray Integration Patterns

Tested with zarr-python 3.1, xarray 2026.9, Dask 2026.8 and pandas 3.1. Each block runs on its own.

## Contents

| Section | Lines | Description |
|---------|-------|-------------|
| Pattern 1: Opening a Zarr Store | 18–64 | Chunk options, cloud stores, ERA5-style coordinate order |
| Pattern 2: Writing with Per-Variable Encoding | 68–124 | Chunks, dtype, codecs, fill values and time units |
| Pattern 3: Appending Along Time | 128–186 | Grow a store safely, with the checks xarray skips |
| Pattern 4: Region Writes for Parallel Output | 190–238 | Pre-allocate with a Dask template, then fill regions |
| Pattern 5: Aligning Dask Chunks with Zarr Chunks | 242–292 | Read and write alignment, stale encoding, shards |
| Pattern 6: Consolidated Metadata | 296–329 | What xarray writes, when it goes stale, v2 vs v3 |

---

## Pattern 1: Opening a Zarr Store

**Description:** Open a Zarr store as a lazy Dataset. The `chunks` argument decides whether Dask is used and how its chunks relate to the stored ones.

| `chunks=` | Result |
|-----------|--------|
| `{}` (default when Dask is installed) | Dask, one chunk per stored Zarr chunk |
| `"auto"` | Dask, larger chunks that are whole multiples of the stored ones |
| `{"time": 60}` | Dask with these sizes; a size that splits stored chunks warns `The specified chunks separate the stored chunks` |
| `None` | No Dask; lazy until accessed, then loaded as NumPy |

`xr.open_dataset(path, engine="zarr")` defaults to `chunks=None`. Other options: `consolidated` (`None` tries consolidated metadata and falls back), `zarr_format` (2 or 3; detected when omitted), `group`, `decode_cf`, `decode_times`, and `storage_options` for fsspec URLs.

**Code example:**

```python
import numpy as np
import pandas as pd
import xarray as xr

# A local stand-in for an ERA5-style store: latitude runs 90 → -90, longitude 0 → 359.
ds = xr.Dataset(
    {"t2m": (("time", "latitude", "longitude"), np.random.rand(48, 181, 360).astype("float32"))},
    coords={
        "time": pd.date_range("2024-01-01", periods=48, freq="h"),
        "latitude": np.linspace(90, -90, 181),
        "longitude": np.arange(0.0, 360.0),
    },
)
ds.to_zarr("era5_like.zarr", mode="w", encoding={"t2m": {"chunks": (24, 91, 180)}})

ds = xr.open_zarr("era5_like.zarr")  # chunks={} → Dask chunks == Zarr chunks
print(ds["t2m"].data.chunksize, ds["t2m"].encoding["chunks"])  # (24, 91, 180) (24, 91, 180)

# Latitude is descending: an ascending slice returns nothing, with no error.
print(ds.sel(latitude=slice(-30, 30)).sizes["latitude"])  # 0
tropics = ds.sel(latitude=slice(30, -30))
print(tropics.sizes["latitude"])  # 61

# Longitude is 0–360: a slice across Greenwich needs the 0–360 values or a roll.
west = ds.sel(longitude=slice(340, 359))
ds_180 = ds.assign_coords(longitude=((ds.longitude + 180) % 360) - 180).sortby("longitude")
print(ds_180.sel(longitude=slice(-20, 20)).sizes["longitude"])  # 41

# Cloud store: same call plus fsspec options (s3fs or gcsfs must be installed).
# ds = xr.open_zarr("s3://example-bucket/era5.zarr", storage_options={"anon": True})
```

---

## Pattern 2: Writing with Per-Variable Encoding

**Description:** Set the on-disk chunks, dtype, codecs, fill value and time units per variable. Encoding keys must match variable names (an unknown name raises `KeyError`), and unknown parameters raise `ValueError: unexpected encoding parameters for zarr backend`.

| Key | Notes |
|-----|-------|
| `chunks` | Tuple in the variable's dimension order. A dict raises `TypeError` |
| `shards` | Zarr v3 only: shard shape, a multiple of `chunks` |
| `dtype` | On-disk type; values are cast on write |
| `compressors`, `filters` | v3 takes `zarr.codecs` objects, v2 takes numcodecs. `compressor` (singular) is rejected |
| `_FillValue` | Value that marks missing data; needed for integer dtypes holding NaN |
| `scale_factor`, `add_offset` | CF packing into a smaller integer type |
| `units`, `calendar` | For time variables, e.g. `"seconds since 1970-01-01"` |

**Code example:**

```python
import numpy as np
import pandas as pd
import xarray as xr
import zarr

ds = xr.Dataset(
    {
        "temperature": (["time", "lat", "lon"], np.random.randn(365, 180, 360)),
        "precipitation": (["time", "lat", "lon"], np.random.rand(365, 180, 360)),
        "elevation": (["lat", "lon"], np.random.rand(180, 360)),
    },
    coords={
        "time": pd.date_range("2024-01-01", periods=365, freq="D"),
        "lat": np.linspace(-89.5, 89.5, 180),
        "lon": np.linspace(0.5, 359.5, 360),
    },
)
ds["temperature"][0, 0, 0] = np.nan

encoding = {
    "temperature": {
        "chunks": (30, 90, 180),                       # (time, lat, lon)
        "dtype": "float32",                            # half the bytes of float64
        "_FillValue": np.float32(-9999.0),
        "compressors": [zarr.codecs.ZstdCodec(level=3)],
    },
    "precipitation": {
        "chunks": (30, 90, 180),
        "dtype": "int16", "scale_factor": 0.001, "_FillValue": np.int16(-32768),  # CF packing
    },
    "elevation": {"chunks": (180, 360), "dtype": "float32"},
    "time": {"units": "seconds since 1970-01-01", "dtype": "int64"},
}
ds.to_zarr("encoded_dataset.zarr", mode="w", encoding=encoding)

check = xr.open_zarr("encoded_dataset.zarr")
print(check["temperature"].encoding["dtype"], check["temperature"].encoding["chunks"])  # float32 (30, 90, 180)
print(bool(np.isnan(check["temperature"][0, 0, 0])))  # True: -9999 decoded back to NaN
print(float(abs(check["precipitation"] - ds["precipitation"]).max()) <= 0.0005)  # True
```

---

## Pattern 3: Appending Along Time

**Description:** Grow a store with `append_dim`. xarray checks dimension sizes but not coordinate values, variable sets or time order, so check those first.

What happens without the checks:

- Different lat/lon values: the store's coordinates are overwritten (`mode="a"`), relabelling all earlier data.
- An extra or missing data variable: the append succeeds, then `open_zarr` raises `conflicting sizes for dimension 'time'`.
- Overlapping times: duplicate timestamps.
- Time units: the first write picks them (`days since ...` for daily data). Hourly data appended later is stored with a `UserWarning` and read back on the wrong dates. Set the units on the first write.
- Passing `encoding` on an append raises `variable '...' already exists, but encoding was provided`. The store's encoding is reused.

**Code example:**

```python
import numpy as np
import pandas as pd
import xarray as xr

lat = np.linspace(-89.5, 89.5, 180)
lon = np.linspace(0.5, 359.5, 360)


def month(start, days):
    return xr.Dataset(
        {"temperature": (["time", "lat", "lon"], np.random.randn(days, 180, 360).astype("float32"))},
        coords={"time": pd.date_range(start, periods=days, freq="D"), "lat": lat, "lon": lon},
    )


month("2024-01-01", 31).to_zarr(
    "growing_dataset.zarr",
    mode="w",
    encoding={
        "temperature": {"chunks": (31, 90, 180)},
        "time": {"units": "seconds since 1970-01-01", "dtype": "int64"},
    },
)


def safe_append(new, store, dim="time"):
    old = xr.open_zarr(store)
    for name in new.indexes:
        if name != dim and not old.indexes[name].equals(new.indexes[name]):
            raise ValueError(f"coordinate {name!r} differs from the store")
    if set(new.data_vars) != set(old.data_vars):
        raise ValueError(f"variables {set(new.data_vars)} != store {set(old.data_vars)}")
    if new[dim].values[0] <= old[dim].values[-1]:
        raise ValueError("new times overlap the store")
    new.to_zarr(store, append_dim=dim)


safe_append(month("2024-02-01", 29), "growing_dataset.zarr")
safe_append(month("2024-03-01", 31), "growing_dataset.zarr")

ds_all = xr.open_zarr("growing_dataset.zarr")
print(ds_all.sizes["time"])  # 91
print(ds_all.time.values[0], ds_all.time.values[-1])  # 2024-01-01 ... 2024-03-31
```

---

## Pattern 4: Region Writes for Parallel Output

**Description:** Pre-allocate the store once, then let independent workers fill non-overlapping regions. Safe concurrency needs every region to start and end on a Zarr chunk (or shard) boundary: xarray checks this for Dask-backed regions but not for NumPy-backed ones.

- Build the template from Dask arrays. `compute=False` defers only Dask data, so a NumPy template writes every chunk immediately.
- `region="auto"` finds the slice from the index coordinates and skips variables without the region dimension. An explicit `region={"time": slice(...)}` raises `ValueError` while variables such as `lat` and `lon` are still in the dataset; drop them first.
- `region` implies `mode="r+"`: values only, no new variables or shape changes.

**Code example:**

```python
import dask.array as da
import numpy as np
import pandas as pd
import xarray as xr

n_time, n_lat, n_lon = 365, 180, 360
times = pd.date_range("2024-01-01", periods=n_time, freq="D")
lat = np.linspace(-89.5, 89.5, n_lat)
lon = np.linspace(0.5, 359.5, n_lon)

# ── Step 1: metadata and coordinates only ──
template = xr.Dataset(
    {"temperature": (["time", "lat", "lon"],
                     da.zeros((n_time, n_lat, n_lon), chunks=(30, 90, 180), dtype="float32"))},
    coords={"time": times, "lat": lat, "lon": lon},
)
template.to_zarr("parallel_output.zarr", mode="w", compute=False,
                 encoding={"temperature": {"chunks": (30, 90, 180)}})


# ── Step 2: each worker writes its own region (edges on multiples of 30) ──
def process_and_write(start, stop):
    data = np.random.randn(stop - start, n_lat, n_lon).astype("float32")
    part = xr.Dataset(
        {"temperature": (["time", "lat", "lon"], data)},
        coords={"time": times[start:stop], "lat": lat, "lon": lon},
    )
    part.to_zarr("parallel_output.zarr", region="auto")
    # Explicit form: part.drop_vars(["lat", "lon"]).to_zarr(path, region={"time": slice(start, stop)})


for start, stop in [(0, 90), (90, 180), (180, 270), (270, 365)]:  # can run concurrently
    process_and_write(start, stop)

# ── Step 3: verify; unwritten regions read back as NaN ──
ds = xr.open_zarr("parallel_output.zarr")
print(int(ds["temperature"].isnull().sum()))  # 0
```

---

## Pattern 5: Aligning Dask Chunks with Zarr Chunks

**Description:** Each Dask chunk should cover whole Zarr chunks. On read, misalignment makes several tasks decode the same Zarr chunk. On write, `to_zarr` refuses it: `ValueError: Specified Zarr chunks encoding['chunks']=... would overlap multiple Dask chunks`. Dask chunks smaller than the Zarr chunk fail too. With `shards`, the Dask chunks must be multiples of the shard shape.

A dataset opened from Zarr keeps `encoding["chunks"]` and `encoding["preferred_chunks"]`. After `.chunk()`, `to_zarr` still uses them: it writes the old chunk shape when the new Dask chunks are multiples of it, and raises the overlap error otherwise. Remove them, or pass new `chunks` in `encoding`.

**Code example:**

```python
import numpy as np
import pandas as pd
import xarray as xr

xr.Dataset(
    {"t": (("time", "lat", "lon"), np.random.rand(120, 180, 360).astype("float32"))},
    coords={"time": pd.date_range("2024-01-01", periods=120)},
).to_zarr("data.zarr", mode="w", encoding={"t": {"chunks": (30, 90, 180)}})


def check_alignment(ds):
    for name, var in ds.data_vars.items():
        zarr_chunks = var.encoding.get("chunks")
        if zarr_chunks is None or var.chunks is None:
            continue
        for dim, dask_sizes, z in zip(var.dims, var.chunks, zarr_chunks):
            bad = [c for c in dask_sizes[:-1] if c % z]  # the last chunk may be partial
            print(f"{name}.{dim}: zarr {z}, dask {dask_sizes[0]}", "MISALIGNED" if bad else "ok")


ds = xr.open_zarr("data.zarr")                  # chunks={}: aligned
ds = xr.open_zarr("data.zarr", chunks={"time": 60, "lat": 180, "lon": 360})  # multiples: aligned
check_alignment(ds)

# Rechunk for a different output layout: drop the source layout first.
out = xr.open_zarr("data.zarr").chunk({"time": 120, "lat": 45, "lon": 90})
for var in out.variables.values():
    for key in ("chunks", "preferred_chunks", "shards"):
        var.encoding.pop(key, None)
out.to_zarr("rechunked.zarr", mode="w")
print(xr.open_zarr("rechunked.zarr")["t"].encoding["chunks"])  # (120, 45, 90)

# Sharded v3 output: Dask chunks must cover whole shards.
sharded = out.chunk({"time": 120, "lat": 90, "lon": 180})
sharded.to_zarr("sharded.zarr", mode="w",
                encoding={"t": {"chunks": (30, 45, 90), "shards": (120, 90, 180)}})

# Misaligned Dask chunks: let xarray realign them instead of raising.
xr.open_zarr("data.zarr").chunk({"time": 45}).to_zarr("aligned.zarr", mode="w", align_chunks=True)
```

`safe_chunks=False` also silences the error, but concurrent writes to a shared chunk can then lose data.

---

## Pattern 6: Consolidated Metadata

**Description:** Consolidated metadata stores every array's metadata in one object, so opening a remote store takes one request instead of one per array.

- `to_zarr` consolidates by default (`consolidated=None`), including after appends and new variables. There is nothing to redo after a normal xarray write.
- v2 stores keep it in `.zmetadata`. v3 stores keep it inside the root `zarr.json`, an extension outside the v3 spec, so zarr-python warns `ZarrUserWarning: Consolidated metadata is currently not part in the Zarr format 3 specification`. Pass `consolidated=False` if other v3 readers must open the store.
- It goes stale after writes with `consolidated=False` or through zarr-python directly. A v2 store then opens with the old shapes and no warning. A v3 store loses the consolidated block, so `consolidated=True` raises and `None` falls back with a `RuntimeWarning`.

**Code example:**

```python
import numpy as np
import pandas as pd
import xarray as xr
import zarr


def batch(start):
    return xr.Dataset({"v": ("time", np.arange(10.0))},
                      coords={"time": pd.date_range(start, periods=10)})


batch("2024-01-01").to_zarr("v2.zarr", mode="w", zarr_format=2)
batch("2024-01-11").to_zarr("v2.zarr", append_dim="time", consolidated=False)
print(xr.open_zarr("v2.zarr").sizes["time"])  # 10: stale .zmetadata

zarr.consolidate_metadata("v2.zarr")
print(xr.open_zarr("v2.zarr").sizes["time"])  # 20

group = zarr.open_group("v2.zarr", mode="r")
print(group.metadata.consolidated_metadata is not None)  # True; works for v2 and v3
```

For a remote store, open the store object with credentials and pass it: `zarr.consolidate_metadata(zarr.storage.FsspecStore.from_url(url, storage_options=..., read_only=False))`.
