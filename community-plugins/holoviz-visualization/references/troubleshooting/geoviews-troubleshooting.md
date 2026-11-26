# GeoViews Troubleshooting

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions.

## Overview

Most GeoViews problems are coordinate reference system (CRS) problems: the data is in one CRS, GeoViews assumes another, and the result is points in the wrong place or nothing on the map at all. This file also covers basemap tiles that do not load, projections that do not work with tiles, and installation or data-download problems with Cartopy.

**Load when**: Map data is misplaced or missing, a CRS or projection warning appears, a basemap is blank, or Cartopy fails to install or download data.

GeoViews has one rule that explains most of these problems. **`crs=` describes the coordinates your data is in, and `projection=` describes how the map is drawn.** Every GeoViews element assumes `crs=ccrs.PlateCarree()` (longitude/latitude in degrees) unless told otherwise. The Bokeh backend draws in Web Mercator by default.

## Points Cluster Near (0, 0) on a Tile Map

**Symptom**: Points that should spread across the world all appear in a tiny cluster off the coast of West Africa.

**Cause**: Plain `hv.Points` has no CRS. Over a tile layer, its lon/lat degrees are read as Web Mercator meters, so -122° becomes 122 m west of (0, 0).

**Fix**: Use a GeoViews element, which projects lon/lat for you. Or convert the coordinates yourself if you need a plain HoloViews element.

```python
import pandas as pd
import holoviews as hv
import geoviews as gv
import geoviews.tile_sources as gts

gv.extension('bokeh')

cities = pd.DataFrame({
    'lon': [-122.33, 2.35, 139.69],
    'lat': [47.61, 48.86, 35.69],
    'name': ['Seattle', 'Paris', 'Tokyo'],
})

geo_map = gts.CartoLight * gv.Points(cities, ['lon', 'lat'], ['name']).opts(size=10, tools=['hover'])

# Plain HoloViews alternative: convert to Web Mercator first
x, y = hv.util.transform.lon_lat_to_easting_northing(cities['lon'], cities['lat'])
hv_map = gts.CartoLight * hv.Points((x, y))
```

With hvPlot, `geo=True` does the same thing: `cities.hvplot.points('lon', 'lat', geo=True, tiles='CartoLight')`.

Also check the column order. Key dimensions are `[x, y]`, which means `['lon', 'lat']`. Passing `['lat', 'lon']` puts every point at a transposed location without raising an error.

## `While projecting ... none of the projected paths were contained within the bounds`

**Symptom**: The map is empty and the log shows:

```
WARNING:param.project_points: While projecting a Points element from a PlateCarree coordinate reference system (crs) to a Mercator projection none of the projected paths were contained within the bounds specified by the projection. Ensure you have specified the correct coordinate system for your data.
```

**Cause**: The data is already projected, for example in Web Mercator or UTM meters, but GeoViews assumed lon/lat degrees. Values like `-13618000` are far outside the -180..180 range.

**Fix**: Pass the data's actual CRS with `crs=`.

```python
import pandas as pd
import cartopy.crs as ccrs
import geoviews as gv
import geoviews.tile_sources as gts

gv.extension('bokeh')

mercator = pd.DataFrame({'x': [-13_618_000.0, 261_600.0], 'y': [6_041_000.0, 6_249_000.0]})
utm = pd.DataFrame({'easting': [550_000.0], 'northing': [5_272_000.0]})

web_mercator = gts.OSM * gv.Points(mercator, ['x', 'y'], crs=ccrs.GOOGLE_MERCATOR)
utm_zone_10 = gts.OSM * gv.Points(utm, ['easting', 'northing'], crs=ccrs.UTM(10))
```

`ccrs.epsg(code)` builds a CRS from an EPSG code, for example `ccrs.epsg(32610)` for UTM zone 10N.

## GeoDataFrame in a Projected CRS Is Misplaced

**Symptom**: A GeoPandas GeoDataFrame whose `.crs` is not EPSG:4326 lands in the wrong place or disappears. With hvPlot, `gdf.hvplot(geo=True)` can fail with the projection warning above, followed by `ValueError: cannot convert float NaN to integer`.

**Cause**: In these versions, neither `gv.Polygons(gdf)` nor `gdf.hvplot(geo=True)` reads `gdf.crs`. Both assume PlateCarree, as with any other data.

**Fix**: Reproject to EPSG:4326 first, or state the CRS explicitly.

```python
import geopandas as gpd
import cartopy.crs as ccrs
import geoviews as gv
import geoviews.tile_sources as gts
import hvplot.pandas  # noqa: F401
from shapely.geometry import box

gv.extension('bokeh')

gdf = gpd.GeoDataFrame(
    {'name': ['north', 'south']},
    geometry=[box(0, 42, 1, 43), box(0, 40, 1, 41)],
    crs='EPSG:4326',
).to_crs('EPSG:3857')                     # e.g. data delivered in Web Mercator

print(gdf.crs)                            # always check this first

reprojected = gts.CartoLight * gv.Polygons(gdf.to_crs('EPSG:4326'), vdims=['name'])
explicit = gts.CartoLight * gv.Polygons(gdf, vdims=['name'], crs=ccrs.epsg(3857))
via_hvplot = gdf.hvplot(geo=True, crs=ccrs.epsg(3857), tiles='CartoLight')
```

If `gdf.crs` is `None`, the file did not carry CRS metadata. Find out the real CRS from the data provider and assign it with `gdf.set_crs(...)` before reprojecting.

## Basemap Tiles Do Not Load

**Symptom**: Your data draws, but the background is blank or gray, or only some tiles appear.

**Cause**: Tiles are fetched by the **browser**, not by Python. Common reasons:
1. The browser has no network access to the tile server (offline, firewall, corporate proxy, or a strict Content Security Policy).
2. The provider requires an API key or a registered domain. The `gts.Stamen*` sources now point at Stadia Maps (`https://tiles.stadiamaps.com/tiles/stamen_toner/...`), and Stadia requires an account for use beyond local development.
3. The provider rate-limits or blocks heavy use. The OpenStreetMap tile servers are run by volunteers and have a usage policy.

**Fix**: Open the browser developer tools, look at the Network tab for failed tile requests, and switch to a provider you are allowed to use. For keyed providers, build a `WMTS` source with your own URL.

```python
import os
import geoviews as gv
import geoviews.tile_sources as gts

gv.extension('bokeh')

print(gts.StamenToner.data)              # shows which server a source uses
light = gts.CartoLight                    # no key needed for moderate use
imagery = gts.EsriImagery

key = os.environ.get('TILE_API_KEY', 'YOUR_KEY')
custom = gv.WMTS(f'https://tiles.example.com/{{Z}}/{{X}}/{{Y}}.png?api_key={key}', name='Custom')
```

hvPlot rejects tile names it does not recognize with `ValueError: StamenTonerX tiles not recognized. tiles must be either True, a xyzservices.TileProvider instance, a HoloViews or Geoviews basemap string (one of CartoDark, CartoEco, CartoLight, ...`. Use one of the listed names.

## Tiles with a Non-Mercator Projection

**Symptom**: With `projection=ccrs.Robinson()` (or any other projection besides Web Mercator), the tiles no longer line up with the data.

**Cause**: Web map tiles are pre-rendered in Web Mercator and cannot be reprojected. No error is raised.

**Fix**: Use tiles only with the default Web Mercator projection. For other projections, draw the context from vector features instead.

```python
import pandas as pd
import cartopy.crs as ccrs
import geoviews as gv

gv.extension('bokeh')

cities = pd.DataFrame({'lon': [-122.33, 2.35, 139.69], 'lat': [47.61, 48.86, 35.69]})

robinson = (gv.feature.coastline * gv.Points(cities, ['lon', 'lat']).opts(size=8)).opts(
    projection=ccrs.Robinson(), global_extent=True, width=700, height=350,
)
```

## Cartopy Downloads Fail (`DownloadWarning`) or Work Only Online

**Symptom**: The first plot that uses `gv.feature.*` prints `DownloadWarning: Downloading: https://naturalearth.s3.amazonaws.com/110m_physical/ne_110m_coastline.zip`. Offline, the same plot fails.

**Cause**: Cartopy fetches Natural Earth data on first use and caches it in `cartopy.config['data_dir']`.

**Fix**: Download the data ahead of time on a machine with network access (for example while building a Docker image), then reuse the cache directory.

```bash
cartopy_feature_download physical cultural --output /opt/cartopy-data
```

```python
import cartopy

print(cartopy.config['data_dir'])
# Point Cartopy at a pre-populated directory before any feature is drawn:
# cartopy.config['pre_existing_data_dir'] = '/opt/cartopy-data'
```

## Installation Problems

**Symptom**: Installing GeoViews or Cartopy fails while building `shapely`, `pyproj`, or Cartopy itself, or importing fails with errors about GEOS or PROJ libraries.

**Cause**: Cartopy, Shapely, and pyproj depend on compiled C libraries (GEOS and PROJ). Mixing package sources can leave mismatched copies of those libraries.

**Fix**: Install the geospatial stack from a single source. conda-forge provides consistent builds of every library involved:

```bash
pixi add geoviews geopandas           # or: conda install -c conda-forge geoviews geopandas
pip install geoviews geopandas        # works where binary wheels exist for your platform
```

If an environment is already mixed, recreate it rather than reinstalling single packages.

## Related

- [GeoViews Best Practices](../best-practices/geoviews.md)
- [GeoViews Patterns](../patterns/geoviews-patterns.md)
- [Datashader Troubleshooting](./datashader-troubleshooting.md) for large geographic datasets
- [GeoViews projections guide](https://geoviews.org/user_guide/Projections.html)
- [Cartopy CRS reference](https://cartopy.readthedocs.io/stable/reference/crs.html)
- [OpenStreetMap tile usage policy](https://operations.osmfoundation.org/policies/tiles/)
