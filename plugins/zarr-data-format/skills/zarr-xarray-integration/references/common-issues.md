# Common Issues and Solutions

Error messages are from zarr-python 3.1 and xarray 2026.9.

## Contents

| Section | Lines | Description |
|---------|-------|-------------|
| Issue 1: Dask and Zarr Chunks Don't Line Up | 21–53 | Read warnings, write errors, stale encoding |
| Issue 2: Append Fails or Damages the Store | 57–97 | Size errors, replaced coordinates, unreadable stores |
| Issue 3: Wrong Timestamps After Appending | 101–124 | Time units fixed by the first write |
| Issue 4: Encoding Rejected or Not Applied | 128–160 | Dict chunks, wrong names, codec keys |
| Issue 5: Region Write Errors | 164–192 | Variables outside the region, partial chunks, new variables |
| Issue 6: Memory Blow-Up on to_zarr | 196–225 | NumPy-backed data, oversized chunks |
| Issue 7: Consolidated Metadata Stale | 229–251 | Old shapes after writes that skipped consolidation |
| Issue 8: dtype, Fill Values and Strings | 255–284 | NaN as 0, precision, Zarr v3 string types |
| Issue 9: Empty Selection on ERA5-Style Grids | 288–307 | Descending latitude, 0–360 longitude |

---

## Issue 1: Dask and Zarr Chunks Don't Line Up

**Symptoms:**
- On open: `UserWarning: The specified chunks separate the stored chunks along dimension "time" starting at index 45. This could degrade performance.`
- On write: `ValueError: Specified Zarr chunks encoding['chunks']=(30, 90, 180) for variable named 't' would overlap multiple Dask chunks.`
- `ds.chunk({...}).to_zarr(...)` succeeds but the store keeps the source's chunk shape

**Cause:** Each Dask chunk must cover whole Zarr chunks (or whole shards, for sharded v3 arrays). Dask chunks smaller than the Zarr chunk fail too. Data opened from Zarr also keeps `encoding["chunks"]` and `encoding["preferred_chunks"]`, and `to_zarr` uses them after `.chunk()`.

**Solution:**

```python
import numpy as np
import xarray as xr

xr.Dataset({"t": (("time", "lat", "lon"), np.random.rand(90, 180, 360))}).to_zarr(
    "data.zarr", mode="w", encoding={"t": {"chunks": (30, 90, 180)}})

ds = xr.open_zarr("data.zarr", chunks={})                     # Dask chunks == Zarr chunks
ds = xr.open_zarr("data.zarr", chunks={"time": 60, "lat": 180})  # whole multiples

# Writing a new layout: remove the stale encoding first.
out = xr.open_zarr("data.zarr").chunk({"time": 90, "lat": 45, "lon": 90})
for var in out.variables.values():
    for key in ("chunks", "preferred_chunks", "shards"):
        var.encoding.pop(key, None)
out.to_zarr("relayout.zarr", mode="w")

# Keeping the target layout but fixing misaligned Dask chunks:
xr.open_zarr("data.zarr").chunk({"time": 45}).to_zarr("aligned.zarr", mode="w", align_chunks=True)
```

`ds.chunk((30, 90, 180))` on a Dataset is a different error (`ValueError: Chunks do not add up to shape`, after a `FutureWarning`); pass a dict. `safe_chunks=False` silences the overlap error, but concurrent writes to a shared chunk can lose data.

---

## Issue 2: Append Fails or Damages the Store

**Symptoms:**
- `ValueError: variable 't' already exists with different dimension sizes: {'lat': 18, 'lon': 36} != {'lat': 9, 'lon': 36}. to_zarr() only supports changing dimension sizes when explicitly appending`
- `ValueError: variable 't' already exists, but encoding was provided`
- The append succeeds, then `open_zarr` raises `conflicting sizes for dimension 'time': length 120 on 't' and length 60 on {'time': 'q', 'lat': 'q', 'lon': 'q'}`
- The store's lat/lon values changed, or the time index has duplicates

**Cause:** xarray checks the sizes of non-append dimensions but not their values. With the default `mode="a"` it rewrites every variable without `append_dim`, including `lat` and `lon`, so new values relabel the existing data. A batch with an extra variable creates that variable at the batch's length, and a batch missing one leaves it short. Overlapping times are appended as duplicates. On append the store's encoding is reused, so passing `encoding` is an error.

**Solution:** check the batch before appending (the full helper is Pattern 3 in [patterns.md](patterns.md)):

```python
import numpy as np
import pandas as pd
import xarray as xr


def batch(start, lat=np.linspace(-85, 85, 18)):
    return xr.Dataset(
        {"t": (("time", "lat", "lon"), np.ones((30, 18, 36), "float32"))},
        coords={"time": pd.date_range(start, periods=30), "lat": lat, "lon": np.linspace(5, 355, 36)},
    )


batch("2024-01-01").to_zarr("timeseries.zarr", mode="w")
new = batch("2024-01-31")

existing = xr.open_zarr("timeseries.zarr")
assert existing.indexes["lat"].equals(new.indexes["lat"])
assert existing.indexes["lon"].equals(new.indexes["lon"])
assert set(new.data_vars) == set(existing.data_vars)
assert new.time.values[0] > existing.time.values[-1]
new.to_zarr("timeseries.zarr", append_dim="time")

# mode="a-" appends only variables that have append_dim, leaving lat/lon untouched.
batch("2024-03-01").to_zarr("timeseries.zarr", append_dim="time", mode="a-")
print(xr.open_zarr("timeseries.zarr").sizes["time"])  # 90
```

To recover a store that no longer opens because of a stray variable, open with `xr.open_zarr(path, drop_variables=["q"])`, or delete it with `del zarr.open_group(path, mode="a")["q"]` and then run `zarr.consolidate_metadata(path)`.

---

## Issue 3: Wrong Timestamps After Appending

**Symptoms:**
- `UserWarning: Times can't be serialized faithfully to int64 with requested units 'days since 2024-06-01'. Serializing with units 'hours since 2024-06-01' instead.`
- Hourly steps appended to the store read back one day apart

**Cause:** The first write picks the time units from its own data. One daily step, or a daily series, gets `days since ...`. Appends must use the store's units, so finer times are written in other units under the old label.

**Solution:** set units fine enough for every future append on the first write:

```python
import pandas as pd
import xarray as xr

first = xr.Dataset({"v": ("time", [1.0])}, coords={"time": pd.DatetimeIndex(["2024-06-01 00:00"])})
first.to_zarr("obs.zarr", mode="w",
              encoding={"time": {"units": "seconds since 1970-01-01", "dtype": "int64"}})
for hour in (1, 2, 3):
    step = xr.Dataset({"v": ("time", [1.0])}, coords={"time": pd.DatetimeIndex([f"2024-06-01 {hour:02d}:00"])})
    step.to_zarr("obs.zarr", append_dim="time")
print(xr.open_zarr("obs.zarr").time.values[-1])  # 2024-06-01T03:00
```

Check an existing store's units with `xr.open_zarr(path).time.encoding["units"]`. Non-standard calendars (`noleap`, `360_day`) decode to `cftime` objects; to force that for standard calendars, pass `decode_times=xr.coders.CFDatetimeCoder(use_cftime=True)`, which replaces the deprecated `use_cftime=True`.

---

## Issue 4: Encoding Rejected or Not Applied

**Symptoms:**
- ``TypeError: zarr chunk sizes specified in `encoding['chunks']` must be an int or a tuple of ints. Instead found encoding['chunks']=('time', 'lat', 'lon')``
- `KeyError: 'temp'`
- `ValueError: unexpected encoding parameters for zarr backend` naming `['compressor']`
- `TypeError: Expected a BytesBytesCodec. Got <class 'numcodecs.blosc.Blosc'> instead.`
- Chunks on disk differ from what you asked for

**Cause:** `encoding["chunks"]` takes a tuple in the variable's dimension order, and a dict is read as its keys. Every encoding key must name a variable in the dataset. With zarr-python 3 the codec key is `compressors` (plural) for both formats; v3 arrays take `zarr.codecs` objects and v2 arrays take numcodecs. Chunks that differ from the request usually come from the stale encoding in Issue 1.

**Solution:**

```python
import numpy as np
import xarray as xr
import zarr

ds = xr.Dataset({"temperature": (("time", "lat", "lon"), np.random.rand(60, 90, 180))})
print(list(ds.data_vars))  # encoding keys must come from this list

encoding = {
    "temperature": {
        "chunks": (30, 90, 180),
        "dtype": "float32",
        "compressors": [zarr.codecs.BloscCodec(cname="zstd", clevel=5, shuffle="bitshuffle")],
    },
}
ds.to_zarr("output.zarr", mode="w", encoding=encoding)

applied = xr.open_zarr("output.zarr")["temperature"].encoding
print(applied["chunks"], applied["dtype"], applied["compressors"])
```

---

## Issue 5: Region Write Errors

**Symptoms:**
- ``ValueError: when setting `region` explicitly in to_zarr(), all variables in the dataset to write must have at least one dimension in common with the region's dimensions ['time']``
- `ValueError: ... would overlap multiple Dask chunks`, naming a region slice such as `slice(np.int64(60), np.int64(75), None)`
- `ValueError: dataset contains non-pre-existing variables ['u'], which is not allowed in` ... `with mode='r+'`
- Concurrent workers lose each other's data, with no error

**Cause:** An explicit `region` needs every variable in the dataset to share a region dimension. Dask-backed regions must start and end on Zarr chunk boundaries in the default `mode="r+"`, which also can't create variables. NumPy-backed regions are not checked at all, so concurrent workers whose regions share a chunk overwrite each other.

**Solution:**

```python
import dask.array as da
import numpy as np
import pandas as pd
import xarray as xr

times = pd.date_range("2024-01-01", periods=120)
coords = {"time": times, "lat": np.linspace(-85, 85, 18), "lon": np.linspace(5, 355, 36)}
template = xr.Dataset({"t": (("time", "lat", "lon"), da.zeros((120, 18, 36), chunks=(30, 18, 36)))}, coords=coords)
template.to_zarr("regions.zarr", mode="w", compute=False)

part = xr.Dataset({"t": (("time", "lat", "lon"), np.ones((30, 18, 36)))}, coords={**coords, "time": times[30:60]})
part.to_zarr("regions.zarr", region="auto")                                       # infers time=slice(30, 60)
part.drop_vars(["lat", "lon"]).to_zarr("regions.zarr", region={"time": slice(30, 60)})  # explicit form
```

Keep region edges on multiples of the chunk (or shard) size. Writing a partial chunk is allowed with `mode="a"`, but only safe when no other writer touches that chunk.

---

## Issue 6: Memory Blow-Up on to_zarr

**Symptoms:**
- `MemoryError` or an OOM kill during `ds.to_zarr()`
- Memory grows to the full dataset size before anything is written

**Cause:** The data isn't Dask-backed (it was loaded, built from NumPy, or opened with `chunks=None`), so the whole array is in memory. Or the Dask chunks are so large that a few concurrent tasks exceed RAM.

**Solution:**

```python
import numpy as np
import pandas as pd
import xarray as xr

ds = xr.Dataset({"t": (("time", "lat", "lon"), np.random.rand(120, 180, 360))},
                coords={"time": pd.date_range("2024-01-01", periods=120)})

# Fix 1: make it Dask-backed with moderate chunks (tens to hundreds of MB), aligned with the encoding.
print(ds.chunks)  # empty mapping → NumPy-backed
ds = ds.chunk({"time": 30, "lat": 90, "lon": 180})
ds.to_zarr("output.zarr", mode="w", encoding={"t": {"chunks": (30, 90, 180)}})

# Fix 2: write in stages, one time block per call.
ds.to_zarr("staged.zarr", mode="w", compute=False, encoding={"t": {"chunks": (30, 90, 180)}})
for start in range(0, ds.sizes["time"], 30):
    ds.isel(time=slice(start, start + 30)).to_zarr("staged.zarr", region="auto")
```

On a cluster, `dask.distributed.Client(memory_limit="4GB")` caps each worker's memory and spills to disk instead of being killed.

---

## Issue 7: Consolidated Metadata Stale

**Symptoms:**
- After an append, a v2 store opens with the old shape and no warning
- A v3 store warns `RuntimeWarning: Failed to open Zarr store with consolidated metadata, but successfully read with non-consolidated metadata`, or raises `Consolidated metadata requested with 'use_consolidated=True' but not found` with `consolidated=True`

**Cause:** `to_zarr` re-consolidates after every write by default, so this only happens after a write with `consolidated=False` or a change made with zarr-python directly. v2 then serves the old `.zmetadata`; v3 drops the consolidated block from `zarr.json`.

**Solution:**

```python
import numpy as np
import xarray as xr
import zarr

xr.Dataset({"v": ("time", np.arange(10.0))}).to_zarr("data.zarr", mode="w", zarr_format=2)
xr.Dataset({"v": ("time", np.arange(10.0))}).to_zarr("data.zarr", append_dim="time", consolidated=False)
print(xr.open_zarr("data.zarr").sizes["time"])  # 10 (stale)

zarr.consolidate_metadata("data.zarr")
print(xr.open_zarr("data.zarr").sizes["time"])  # 20
print(xr.open_zarr("data.zarr", consolidated=False).sizes["time"])  # 20: bypasses consolidated metadata
```

---

## Issue 8: dtype, Fill Values and Strings

**Symptoms:**
- `SerializationWarning: saving variable ... with floating point data as an integer dtype without any _FillValue to use for NaNs`, then NaNs read back as 0
- Values differ slightly after a roundtrip (float64 written as float32)
- A float64 batch appended to a float32 store comes back float32
- `UnstableSpecificationWarning: The data type (FixedLengthUTF32(length=8, ...)) does not have a Zarr V3 specification`
- Missing (`None`) strings read back as `""`

**Cause:** The encoding `dtype`, or the store's dtype on append, wins. Integer types need a `_FillValue` to hold NaN. String coordinates built from a Python list become fixed-width NumPy `<U` strings, a type without a Zarr v3 spec; object arrays are written as variable-length strings, which can't hold `None`.

**Solution:**

```python
import numpy as np
import xarray as xr

ds = xr.Dataset(
    {"count": ("station", np.array([1.0, np.nan, 3.0]))},
    coords={"station": np.array(["STN-0000", "STN-0001", "STN-0002"], dtype=object)},  # variable-length
)
encoding = {"count": {"dtype": "int16", "_FillValue": np.int16(-1)}}
ds.to_zarr("output.zarr", mode="w", encoding=encoding)

back = xr.open_zarr("output.zarr")
print(back["count"].values)                                       # [ 1. nan  3.]
print(xr.open_zarr("output.zarr", decode_cf=False)["count"].values)  # [ 1 -1  3]: raw on-disk values
```

`zarr_format=2` writes fixed-width strings without the warning if older readers need the store.

---

## Issue 9: Empty Selection on ERA5-Style Grids

**Symptoms:**
- `ds.sel(latitude=slice(-30, 30))` returns zero latitudes, with no error
- A box across the Greenwich meridian, such as `slice(-20, 20)`, returns only its eastern half

**Cause:** ERA5 and many reanalysis grids store latitude from 90 to -90 and longitude from 0 to 359.75. Label slices follow the stored order.

**Solution:**

```python
import numpy as np
import xarray as xr

ds = xr.Dataset(coords={"latitude": np.linspace(90, -90, 721), "longitude": np.arange(0, 360, 0.25)})
print(ds.sel(latitude=slice(30, -30)).sizes["latitude"])  # 241: slice in stored (descending) order
ds = ds.sortby("latitude")                                 # or sort once, then slice ascending
ds = ds.assign_coords(longitude=((ds.longitude + 180) % 360) - 180).sortby("longitude")
print(ds.sel(longitude=slice(-20, 20)).sizes["longitude"])  # 161
```
