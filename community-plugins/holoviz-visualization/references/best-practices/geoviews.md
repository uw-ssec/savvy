# GeoViews Best Practices

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions.

## Overview

Most map bugs come from coordinates that are wrong without raising an error, not from code that crashes. These practices cover declaring coordinate reference systems (CRS), choosing tile providers, keeping maps fast, and keeping them accurate.

**Load when**: Building maps with GeoViews or `hvplot(geo=True)`, mixing data in different projections, or debugging misplaced or slow maps.

## 1. Always Declare the Data's CRS

GeoViews assumes data is longitude/latitude (`ccrs.PlateCarree()`) unless you say otherwise. Projected data such as UTM or national grids must declare its CRS, or it ends up in the wrong place.

```python
import cartopy.crs as ccrs
import geoviews as gv
import numpy as np
import pandas as pd

gv.extension('bokeh')

# Lon/lat data: x is longitude, y is latitude
cities = pd.DataFrame({'lon': [-122.3, -0.1, 139.7], 'lat': [47.6, 51.5, 35.7], 'name': ['Seattle', 'London', 'Tokyo']})
points = gv.Points(cities, ['lon', 'lat'], ['name'])  # crs defaults to PlateCarree

# Projected data: declare the source CRS explicitly
utm = pd.DataFrame({'easting': 550_000 + np.random.randn(50) * 1000,
                    'northing': 5_270_000 + np.random.randn(50) * 1000})
utm_points = gv.Points(utm, ['easting', 'northing'], crs=ccrs.UTM(zone=10))
```

- Key dimensions are `(x, y)` = `(longitude, latitude)`. Swapping them is the most common map bug.
- With GeoPandas, GeoViews does **not** pick up `gdf.crs`. A projected GeoDataFrame passed as-is is treated as lon/lat. Either reproject first (`gv.Polygons(gdf.to_crs(4326))`) or pass a cartopy CRS (`crs=ccrs.epsg(32610)`). Passing `crs=gdf.crs` fails, because that is a `pyproj.CRS`, not a cartopy one.
- With hvPlot, pass `geo=True` and, for projected data, `crs=` (an EPSG code or cartopy CRS).

## 2. Separate Data CRS From Display Projection

`crs=` says what the data **is**. The `projection` plot option says how to **draw** it. Bokeh tile basemaps are Web Mercator, so GeoViews projects everything to Web Mercator when you overlay tiles.

```python
import cartopy.crs as ccrs
import geoviews as gv
import geoviews.tile_sources as gts
import pandas as pd

gv.extension('bokeh')

df = pd.DataFrame({'lon': [-74.0, 2.35, 151.2], 'lat': [40.7, 48.86, -33.87]})
points = gv.Points(df, ['lon', 'lat']).opts(size=8, color='red', tools=['hover'])

# Web map: tiles force Web Mercator
web_map = (gts.CartoLight * points).opts(width=700, height=400)

# Static/global view without tiles: any cartopy projection
world = points.opts(projection=ccrs.Robinson(), global_extent=True, width=700, height=350, clone=True)
```

Use an equal-area projection (for example `ccrs.EqualEarth()` or `ccrs.AlbersEqualArea()`) for choropleths and density maps. Web Mercator inflates high-latitude areas.

## 3. Choose Tile Providers Carefully

`geoviews.tile_sources` defines ready-made providers. Constructing one doesn't fetch anything; the browser requests tiles when the map is displayed.

| Provider | Good for |
|----------|----------|
| `gts.OSM` | General street context |
| `gts.CartoLight` / `gts.CartoDark` | Neutral backgrounds under colored data |
| `gts.EsriImagery` | Satellite context |
| `gts.EsriTerrain`, `gts.OpenTopoMap` | Relief |

- Prefer muted basemaps (`CartoLight`) under data so the data, not the streets, carries the color.
- The `Stamen*` sources are still defined, but Stamen tiles are now served by Stadia Maps. Deployed apps need a Stadia account (an API key or a registered domain); only localhost development works without one. Without an account, they fail to load.
- Every provider has terms of use and attribution requirements. Tile sources show attribution automatically, so don't hide it. For heavy production traffic, use a provider plan or self-hosted tiles: `gv.WMTS('https://your-server/{Z}/{X}/{Y}.png')`.
- Deployed apps need outbound internet access from the **browser**, not the server, to load tiles.

## 4. Keep Maps Fast

```python
import cartopy.crs as ccrs
import geoviews as gv
import geoviews.tile_sources as gts
import numpy as np
import pandas as pd
from holoviews.operation.datashader import rasterize

gv.extension('bokeh')

n = 500_000
df = pd.DataFrame({'lon': np.random.uniform(-125, -65, n), 'lat': np.random.uniform(25, 50, n)})

# Project once up front instead of on every render
projected = gv.project(gv.Points(df, ['lon', 'lat']), projection=ccrs.GOOGLE_MERCATOR)

# Rasterize large point sets; aggregation re-runs on zoom
fast_map = gts.CartoLight * rasterize(projected).opts(cmap='fire', cnorm='eq_hist', alpha=0.8, width=700, height=400)
```

- Above ~100K points, rasterize (`rasterize(...)`, or `rasterize=True` in hvPlot).
- Project large datasets once with `gv.project` (or reproject in GeoPandas/pyproj ahead of time). Don't make every zoom pay for the projection.
- Simplify polygon geometries before plotting (`gdf.simplify(tolerance)`). Country-level choropleths rarely need survey-grade vertices.
- Load only the extent you display (spatial filters in the query, or `gdf.cx[xmin:xmax, ymin:ymax]`).

## 5. Keep Maps Accurate

- **Check extents after plotting.** If points land near (0, 0) off the coast of Africa, the CRS or lon/lat order is wrong.
- **Normalize longitudes** to one convention (−180..180 or 0..360) before combining datasets.
- **Don't compute distances or areas in degrees.** Reproject to an appropriate projected CRS (UTM zone, equal-area) in GeoPandas first.
- **Use the right projection for comparisons.** Equal-area projections are for area comparisons; conformal projections (Mercator) are for local shape and navigation.
- **State the CRS and data source** in the title or caption of published maps.

```python
import geopandas as gpd
from shapely.geometry import Point

# ✅ Good: buffer in meters in a projected CRS, then return to lon/lat
gdf = gpd.GeoDataFrame(geometry=[Point(-122.33, 47.61)], crs='EPSG:4326')
buffered = gdf.to_crs(epsg=32610).buffer(5_000).to_crs(epsg=4326)  # 5 km
print(buffered.total_bounds.round(3))
```

## Anti-Patterns

| ❌ Avoid | ✅ Instead |
|---------|-----------|
| `gv.Points(df, ['lat', 'lon'])` | `['lon', 'lat']` |
| Projected data without `crs=` | `crs=ccrs.UTM(...)` / `ccrs.epsg(code)`, or `gdf.to_crs(4326)` first |
| Choropleth in Web Mercator for area comparison | Equal-area `projection=` |
| 1M points as glyphs over tiles | `rasterize` |
| Stamen tiles without a Stadia account | Carto, OSM or Esri sources |

## Related

- [GeoViews Patterns](../patterns/geoviews-patterns.md)
- [GeoViews Troubleshooting](../troubleshooting/geoviews-troubleshooting.md)
- [Performance Best Practices](./performance.md)
- [GeoViews user guide](https://geoviews.org/user_guide/index.html)
- [Cartopy projections](https://cartopy.readthedocs.io/stable/reference/projections.html)
