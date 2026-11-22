# Download Patterns Reference

Complete code templates for each access pattern and full pipeline examples for common data sources.

---

## Pattern 1: Direct HTTP Download

Used by: PRISM, Stage IV, DEM

```python
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def download_file(url, dest_dir, retries=3, backoff=2):
    """Download a single file with retry logic."""
    dest = Path(dest_dir) / Path(url).name
    if dest.exists():
        print(f"  Skipping {dest.name} (already exists)")
        return dest

    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            dest.write_bytes(response.content)
            return dest
        except requests.RequestException as e:
            if attempt < retries - 1:
                wait = backoff ** attempt
                print(f"  Retry {attempt + 1}/{retries} for {dest.name} in {wait}s: {e}")
                time.sleep(wait)
            else:
                print(f"  FAILED: {dest.name}: {e}")
                return None

def download_batch(urls, dest_dir, max_workers=8):
    """Download multiple files in parallel."""
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_file, url, dest_dir): url for url in urls}
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            print(f"Downloaded {i}/{len(urls)}")
            results.append(result)

    failed = [r for r in results if r is None]
    if failed:
        print(f"WARNING: {len(failed)} downloads failed")
    return results
```

---

## Pattern 2: REST API Query

Used by: USGS, Synoptic

```python
import requests
import pandas as pd
import io
import re
import time

def parse_rdb(text):
    """Parse an NWIS RDB response into one DataFrame.

    A multi-site response holds one table per site: each has its own
    `agency_cd ...` header and data-type row (5s 15s 20d ...), and the value
    columns carry a per-site time-series ID (e.g. 151445_00060).
    """
    blocks, skip_type_row = [], False
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        if line.startswith("agency_cd"):
            blocks.append([line])           # header of a new site table
            skip_type_row = True
        elif skip_type_row:
            skip_type_row = False           # data-type row under each header
        elif blocks:
            blocks[-1].append(line)
    frames = []
    for block in blocks:
        df = pd.read_csv(io.StringIO("\n".join(block)), sep="\t", dtype={"site_no": str})
        # Drop the time-series ID prefix: 151445_00060 -> 00060, 151445_00060_cd -> 00060_cd,
        # unless a site has two series for one parameter (then keep the IDs)
        names = [re.sub(r"^\d+_(\d{5})", r"\1", c) for c in df.columns]
        if len(set(names)) == len(names):
            df.columns = names
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def query_usgs_api(sites, start_date, end_date, parameter_codes, format="rdb"):
    """Query USGS instantaneous values API."""
    params = {
        "sites": ",".join(sites) if isinstance(sites, list) else sites,
        "startDT": start_date,
        "endDT": end_date,
        "parameterCd": ",".join(parameter_codes) if isinstance(parameter_codes, list) else parameter_codes,
        "format": format,
    }

    response = requests.get(
        "https://nwis.waterservices.usgs.gov/nwis/iv/",
        params=params,
        timeout=120,
    )
    response.raise_for_status()

    # RDB: one table (header + data-type row) per site
    return parse_rdb(response.text)

def query_usgs_bulk(site_list, start_date, end_date, parameter_codes, batch_size=10, delay=1.0):
    """Query USGS API in batches to avoid rate limiting."""
    all_data = []
    batches = [site_list[i:i + batch_size] for i in range(0, len(site_list), batch_size)]

    for i, batch in enumerate(batches, 1):
        print(f"Querying batch {i}/{len(batches)} ({len(batch)} sites)...")
        df = query_usgs_api(batch, start_date, end_date, parameter_codes)
        all_data.append(df)
        if i < len(batches):
            time.sleep(delay)

    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()
```

---

## Pattern 3: Cloud Object Storage / S3

Used by: CONUS404, HRRR, WRF-CMIP6

### CONUS404 (Zarr on S3)

```python
import xarray as xr
import s3fs

def open_conus404(dataset_kind="daily", variables=None):
    """Open CONUS404 dataset from OSN Pod S3 Zarr store."""
    zarr_urls = {
        "daily": "s3://hytest/conus404/conus404_daily.zarr",
        "hourly": "s3://hytest/conus404/conus404_hourly.zarr",
    }

    fs = s3fs.S3FileSystem(
        anon=True,
        client_kwargs={"endpoint_url": "https://usgs.osn.mghpcc.org"},
    )

    ds = xr.open_zarr(
        fs.get_mapper(zarr_urls[dataset_kind]),
        consolidated=True,
    )

    if variables:
        ds = ds[variables]

    return ds
```

### WRF-CMIP6 (NetCDF files on S3)

```python
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

def download_wrf_files(bucket, prefix, dest_dir, max_workers=8):
    """Download WRF-CMIP6 files from S3."""
    s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
    Path(dest_dir).mkdir(parents=True, exist_ok=True)

    # List files
    paginator = s3.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        keys.extend([obj["Key"] for obj in page.get("Contents", [])])

    print(f"Found {len(keys)} files to download")

    def download_one(key):
        local_path = Path(dest_dir) / Path(key).name
        if not local_path.exists():
            s3.download_file(bucket, key, str(local_path))
        return local_path

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        paths = list(executor.map(download_one, keys))

    print(f"Downloaded {len(paths)} files to {dest_dir}")
    return paths
```

---

## Pattern 4: Specialized Library Wrappers

Used by: Herbie (HRRR), pyPRISMClimate, obspy (IRIS)

### HRRR via Herbie

```python
import shutil
assert shutil.which("wgrib2"), "wgrib2 not found in PATH. Install: conda install -c conda-forge wgrib2"

from herbie import Herbie
import pandas as pd
import xarray as xr
from concurrent.futures import ThreadPoolExecutor

def download_hrrr_range(date_range, model="hrrr", product="sfc", fxx=0, search_pattern=":TMP:2 m", max_workers=8):
    """Download HRRR data for a date range using Herbie."""
    dates = pd.date_range(date_range[0], date_range[1], freq="1D")

    def download_day(date):
        try:
            H = Herbie(date, model=model, product=product, fxx=fxx)
            ds = H.xarray(search_pattern)
            # Fields on different levels (2 m, 10 m) come back as a list of Datasets;
            # drop their conflicting scalar level coordinate before merging
            if isinstance(ds, list):
                ds = xr.merge([d.drop_vars("heightAboveGround", errors="ignore") for d in ds])
            return ds
        except Exception as e:
            print(f"  Failed for {date}: {e}")
            return None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        datasets = list(executor.map(download_day, dates))

    # Filter out failures
    datasets = [ds for ds in datasets if ds is not None]
    if not datasets:
        raise RuntimeError("All downloads failed")

    print(f"Successfully downloaded {len(datasets)}/{len(dates)} days")
    return xr.concat(datasets, dim="time")
```

---

## Full Pipeline Example: HRRR

Complete end-to-end pipeline for downloading, subsetting, and saving HRRR data.

```python
# Generated by GAIA Data Downloader Agent
# Source: HRRR (High-Resolution Rapid Refresh)
# AOI: Skagit River Watershed
# Date Range: 2024-01-01 to 2024-01-31

import shutil
import xarray as xr
import geopandas as gpd
import numpy as np
import pandas as pd
import regionmask
from herbie import Herbie
from concurrent.futures import ThreadPoolExecutor

# ============================================================
# Configuration — modify these parameters before running
# ============================================================
CONFIG = {
    "source": "HRRR",
    "model": "hrrr",
    "product": "sfc",
    "date_range": ("2024-01-01", "2024-01-31"),
    "frequency": "1D",
    "forecast_hour": 0,
    "parameters": {
        "TMP:2 m": "temperature_2m",
        "UGRD:10 m": "u_wind_10m",
        "VGRD:10 m": "v_wind_10m",
    },
    "aoi_path": "../data/GIS/SkagitBoundary.json",
    "output_path": "../data/weather_data/hrrr_skagit_202401.zarr",
    "output_format": "zarr",
    "max_workers": 8,
}
# ============================================================
# Download logic — generally no need to modify below this line
# ============================================================

def main():
    # Dependency check
    assert shutil.which("wgrib2"), (
        "wgrib2 not found in PATH. Install via: conda install -c conda-forge wgrib2"
    )

    # Build search pattern from parameters, keeping the level ("TMP:2 m"):
    # the bare name (":TMP:") also matches every pressure level
    search_pattern = ":(?:" + "|".join(CONFIG["parameters"]) + ")"

    # Load AOI
    aoi = gpd.read_file(CONFIG["aoi_path"])
    dates = pd.date_range(
        CONFIG["date_range"][0], CONFIG["date_range"][1], freq=CONFIG["frequency"]
    )
    print(f"Downloading {len(dates)} days of HRRR data...")

    # Download
    def download_day(date):
        H = Herbie(
            date,
            model=CONFIG["model"],
            product=CONFIG["product"],
            fxx=CONFIG["forecast_hour"],
        )
        ds = H.xarray(search_pattern)
        # Fields on different levels (2 m, 10 m) come back as a list of Datasets;
        # drop their conflicting scalar level coordinate before merging
        if isinstance(ds, list):
            ds = xr.merge([d.drop_vars("heightAboveGround", errors="ignore") for d in ds])
        return ds

    with ThreadPoolExecutor(max_workers=CONFIG["max_workers"]) as executor:
        datasets = []
        for i, ds in enumerate(executor.map(download_day, dates), 1):
            datasets.append(ds)
            print(f"  Downloaded {i}/{len(dates)}: {dates[i-1]:%Y-%m-%d}")

    # Combine
    ds = xr.concat(datasets, dim="time")
    print(f"Combined dataset: {dict(ds.sizes)}")

    # cfgrib names these fields t2m/u10/v10; rename the ones present to the
    # CONFIG names (other fields keep their cfgrib names)
    cfgrib_names = {"TMP:2 m": "t2m", "UGRD:10 m": "u10", "VGRD:10 m": "v10"}
    ds = ds.rename({cfgrib_names[k]: v for k, v in CONFIG["parameters"].items()
                    if cfgrib_names.get(k) in ds})

    # Spatial subset: HRRR is curvilinear (2-D latitude/longitude, no x/y
    # coordinate values), so mask with regionmask instead of rio.clip
    mask = regionmask.from_geopandas(aoi.to_crs("EPSG:4326").dissolve()).mask(
        ds.longitude, ds.latitude, wrap_lon=180
    )
    ds_clipped = ds.where(mask.notnull(), drop=True)
    print(f"Clipped to AOI: {dict(ds_clipped.sizes)}")

    # Derive wind speed
    if "u_wind_10m" in ds_clipped and "v_wind_10m" in ds_clipped:
        ds_clipped["windspeed_10m"] = np.sqrt(
            ds_clipped["u_wind_10m"] ** 2 + ds_clipped["v_wind_10m"] ** 2
        )
        print("Derived: windspeed_10m")

    # Save
    ds_clipped.to_zarr(CONFIG["output_path"], mode="w")
    print(f"Saved to {CONFIG['output_path']}")
    print(f"Dataset size: {ds_clipped.nbytes / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
```

---

## Full Pipeline Example: CONUS404

```python
# Generated by GAIA Data Downloader Agent
# Source: CONUS404 (USGS High-Resolution Weather Reanalysis)
# AOI: Study area boundary
# Date Range: 2020-01-01 to 2020-12-31

import xarray as xr
import s3fs
import geopandas as gpd
import rioxarray  # registers the .rio accessor

# ============================================================
# Configuration — modify these parameters before running
# ============================================================
CONFIG = {
    "source": "CONUS404",
    "dataset_kind": "daily",
    "date_range": ("2020-01-01", "2020-12-31"),
    "variables": ["T2", "PREC_ACC_NC"],
    "aoi_path": "../data/GIS/StudyArea.json",
    "output_path": "../data/weather_data/conus404_study_2020.zarr",
    "output_format": "zarr",
}
# ============================================================
# Download logic — generally no need to modify below this line
# ============================================================

ZARR_URLS = {
    "daily": "s3://hytest/conus404/conus404_daily.zarr",
    "hourly": "s3://hytest/conus404/conus404_hourly.zarr",
}


def main():
    # Connect to S3
    fs = s3fs.S3FileSystem(
        anon=True,
        client_kwargs={"endpoint_url": "https://usgs.osn.mghpcc.org"},
    )
    print(f"Opening CONUS404 {CONFIG['dataset_kind']} dataset...")

    ds = xr.open_zarr(
        fs.get_mapper(ZARR_URLS[CONFIG["dataset_kind"]]),
        consolidated=True,
    )

    # Select variables and time range; make "crs" a coordinate so it survives
    # the selection and ds.rio.crs can read the Lambert Conformal projection
    ds = ds.set_coords("crs")[CONFIG["variables"]].sel(
        time=slice(CONFIG["date_range"][0], CONFIG["date_range"][1])
    )
    print(f"Selected {len(CONFIG['variables'])} variables, {len(ds.time)} timesteps")

    # Spatial subset
    aoi = gpd.read_file(CONFIG["aoi_path"])
    aoi_reproj = aoi.to_crs(ds.rio.crs)
    ds_clipped = ds.rio.clip(aoi_reproj.geometry)
    print(f"Clipped to AOI: {dict(ds_clipped.sizes)}")

    # Save
    print(f"Writing to {CONFIG['output_path']}...")
    # Drop the source store's Zarr v2 codecs, which Zarr v3 cannot reuse, then
    # re-attach the CRS: the clipped variables no longer point at the "crs"
    # grid mapping (reopen with decode_coords="all" to get it back)
    out = ds_clipped.drop_encoding().rio.write_crs(ds.rio.crs, grid_mapping_name="crs")
    out.to_zarr(CONFIG["output_path"], mode="w")
    print(f"Saved. Dataset size: {ds_clipped.nbytes / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
```

---

## Full Pipeline Example: USGS Streamflow

```python
# Generated by GAIA Data Downloader Agent
# Source: USGS Instantaneous Values
# Sites: Skagit basin stations
# Date Range: 2020-01-01 to 2023-12-31

import requests
import pandas as pd
import io
import re
from pathlib import Path
import time

# ============================================================
# Configuration — modify these parameters before running
# ============================================================
CONFIG = {
    "source": "USGS",
    "sites": ["12200500", "12194000", "12189500"],
    "date_range": ("2020-01-01", "2023-12-31"),
    "parameters": {
        "00060": "discharge_cfs",
        "00065": "gage_height_ft",
    },
    "output_path": "../data/usgs/skagit_streamflow.csv",
    "batch_size": 5,
    "request_delay": 1.0,
}
# ============================================================
# Download logic — generally no need to modify below this line
# ============================================================

API_URL = "https://nwis.waterservices.usgs.gov/nwis/iv/"


def parse_rdb(text):
    """Parse an NWIS RDB response into one DataFrame.

    A multi-site response holds one table per site: each has its own
    `agency_cd ...` header and data-type row (5s 15s 20d ...), and the value
    columns carry a per-site time-series ID (e.g. 151445_00060).
    """
    blocks, skip_type_row = [], False
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        if line.startswith("agency_cd"):
            blocks.append([line])           # header of a new site table
            skip_type_row = True
        elif skip_type_row:
            skip_type_row = False           # data-type row under each header
        elif blocks:
            blocks[-1].append(line)
    frames = []
    for block in blocks:
        df = pd.read_csv(io.StringIO("\n".join(block)), sep="\t", dtype={"site_no": str})
        # Drop the time-series ID prefix: 151445_00060 -> 00060, 151445_00060_cd -> 00060_cd,
        # unless a site has two series for one parameter (then keep the IDs)
        names = [re.sub(r"^\d+_(\d{5})", r"\1", c) for c in df.columns]
        if len(set(names)) == len(names):
            df.columns = names
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def query_batch(sites, start, end, param_codes):
    """Query USGS API for a batch of sites."""
    params = {
        "sites": ",".join(sites),
        "startDT": start,
        "endDT": end,
        "parameterCd": ",".join(param_codes),
        "format": "rdb",
    }
    response = requests.get(API_URL, params=params, timeout=120)
    response.raise_for_status()
    return parse_rdb(response.text)


def main():
    sites = CONFIG["sites"]
    param_codes = list(CONFIG["parameters"].keys())
    batches = [
        sites[i : i + CONFIG["batch_size"]]
        for i in range(0, len(sites), CONFIG["batch_size"])
    ]

    all_data = []
    for i, batch in enumerate(batches, 1):
        print(f"Querying batch {i}/{len(batches)} ({len(batch)} sites)...")
        df = query_batch(batch, CONFIG["date_range"][0], CONFIG["date_range"][1], param_codes)
        all_data.append(df)
        if i < len(batches):
            time.sleep(CONFIG["request_delay"])

    result = pd.concat(all_data, ignore_index=True)
    print(f"Retrieved {len(result)} records from {len(sites)} sites")

    # Save
    Path(CONFIG["output_path"]).parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(CONFIG["output_path"], index=False)
    print(f"Saved to {CONFIG['output_path']}")


if __name__ == "__main__":
    main()
```

---

## Error Handling and Retry Pattern

Reusable retry wrapper for any download function:

```python
import time
import functools

def with_retry(max_retries=3, backoff_factor=2, exceptions=(Exception,)):
    """Decorator for retry with exponential backoff."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries - 1:
                        raise
                    wait = backoff_factor ** attempt
                    print(f"  Attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
                    time.sleep(wait)
        return wrapper
    return decorator

# Usage:
@with_retry(max_retries=3, exceptions=(requests.RequestException,))
def download_file(url, dest):
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    Path(dest).write_bytes(response.content)
```
