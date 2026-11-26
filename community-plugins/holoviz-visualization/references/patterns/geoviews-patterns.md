# GeoViews Patterns

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions.

## Overview

Patterns for maps with GeoViews: basemaps, point/line/polygon overlays, choropleths, coordinate reference systems, and spatial operations done in GeoPandas before display. GeoViews elements are HoloViews elements with a `crs`, so composition, `opts` and streams work as usual.

**Load when**: Creating maps or spatial visualizations

```bash
pixi add geoviews geopandas   # or: conda install -c conda-forge geoviews geopandas
pip install geoviews geopandas
```

Install from conda-forge when you can: Cartopy, PROJ and GEOS ship as binaries there.

## Pattern 1: Basic Map

**When to use**: Points with longitude/latitude on a web basemap.

```python
import numpy as np
import pandas as pd
import geoviews as gv
import geoviews.tile_sources as gts

gv.extension("bokeh")

rng = np.random.default_rng(0)
stations = pd.DataFrame({
    "lon": rng.uniform(-125, -67, 200),
    "lat": rng.uniform(25, 49, 200),
    "name": [f"Station {i}" for i in range(200)],
    "temp": rng.normal(15, 8, 200),
})

points = gv.Points(stations, kdims=["lon", "lat"], vdims=["name", "temp"]).opts(
    color="temp", cmap="coolwarm", size=7, colorbar=True, tools=["hover"],
)
map_plot = (gts.CartoLight() * points).opts(width=750, height=450)
```

- Plain longitude/latitude data needs no `crs` argument: GeoViews assumes `ccrs.PlateCarree()` and projects to Web Mercator for the tiles.
- hvPlot shortcut: `stations.hvplot.points("lon", "lat", geo=True, tiles="CartoLight", c="temp")`.

## Pattern 2: Tile Providers and Basemaps

**When to use**: Choosing or customizing the background map.

```python
import geoviews as gv
import geoviews.tile_sources as gts
import xyzservices.providers as xyz
from xyzservices import TileProvider

gv.extension("bokeh")

print(sorted(gts.tile_sources))  # every built-in provider

street = gts.OSM()
imagery = gts.EsriImagery()
dark = gts.CartoDark()

# Any provider from xyzservices (installed with Bokeh) carries its own attribution.
topo = gv.WMTS(xyz.OpenTopoMap)

# A custom XYZ service: wrap the URL in a TileProvider so the attribution is shown.
custom = gv.WMTS(TileProvider(
    name="My tiles",
    url="https://tiles.example.com/{z}/{x}/{y}.png",
    attribution="© Example contributors",
))

# Labels on top of imagery: overlay a reference layer.
labelled = (imagery * gts.EsriReference().opts(alpha=0.8)).opts(width=600, height=400)
```

- Tiles load in the browser, so an offline or firewalled viewer sees a blank background while the data still draws.
- The Stamen sources still in `gts` now need a Stadia Maps API key. Prefer Carto, Esri or OSM.
- Check each provider's usage policy before you deploy a public app on it.

## Pattern 3: Point, Line and Polygon Overlays

**When to use**: Combining several vector layers, for example routes, regions and sites.

```python
import geopandas as gpd
import geoviews as gv
import geoviews.tile_sources as gts
from shapely.geometry import LineString, Point, box

gv.extension("bokeh")

regions = gpd.GeoDataFrame(
    {"region": ["West", "East"]},
    geometry=[box(-10, 40, 0, 50), box(0, 40, 10, 50)],
    crs="EPSG:4326",
)
route = gpd.GeoDataFrame(
    {"route": ["A"]}, geometry=[LineString([(-8, 42), (-2, 46), (6, 44)])], crs="EPSG:4326"
)
sites = gpd.GeoDataFrame(
    {"site": ["P", "Q", "R"]},
    geometry=[Point(-5, 45), Point(2, 47), Point(7, 42)],
    crs="EPSG:4326",
)

layers = (
    gts.CartoLight()
    * gv.Polygons(regions, vdims=["region"]).opts(fill_alpha=0.2, line_color="black", tools=["hover"])
    * gv.Path(route).opts(color="red", line_width=3)
    * gv.Points(sites, vdims=["site"]).opts(size=10, color="navy", tools=["hover"])
).opts(width=700, height=450)
```

GeoViews reads geometries straight from a GeoDataFrame, but not its `.crs`. It assumes longitude/latitude unless you pass `crs=`, so convert with `gdf.to_crs(epsg=4326)` first or declare the CRS (Pattern 5). Overlay order is draw order: tiles first, polygons, then lines and points on top.

## Pattern 4: Choropleth Maps

**When to use**: Coloring regions by a value.

```python
import numpy as np
import geopandas as gpd
import geoviews as gv
from shapely.geometry import box

gv.extension("bokeh")

# A 6 x 4 grid of cells stands in for counties or districts.
cells = [box(x, y, x + 1, y + 1) for x in range(-6, 0) for y in range(40, 44)]
rng = np.random.default_rng(1)
gdf = gpd.GeoDataFrame(
    {"district": [f"D{i:02d}" for i in range(len(cells))], "rate": rng.uniform(0, 30, len(cells))},
    geometry=cells,
    crs="EPSG:4326",
)

choropleth = gv.Polygons(gdf, vdims=["district", "rate"]).opts(
    color="rate", cmap="viridis", colorbar=True, clabel="Rate per 1,000",
    line_color="white", tools=["hover"], width=600, height=400,
)
```

- `color` must name one of the `vdims`; list every column you want in the hover there too.
- Normalize by population or area before plotting counts, or larger regions will dominate.
- Use a sequential colormap for rates and a diverging one only when there is a meaningful midpoint.

## Pattern 5: Coordinate Reference Systems

**When to use**: Data comes in a projected CRS (UTM, a national grid), or the output map needs a specific projection.

```python
import numpy as np
import pandas as pd
import cartopy.crs as ccrs
import geoviews as gv
import geoviews.tile_sources as gts

gv.extension("bokeh")

# Points recorded in UTM zone 10N (metres), around Seattle.
rng = np.random.default_rng(2)
utm = pd.DataFrame({"x": rng.normal(550_000, 2_000, 100), "y": rng.normal(5_272_000, 2_000, 100)})

# Declare the CRS the coordinates are in; GeoViews projects for display.
points = gv.Points(utm, ["x", "y"], crs=ccrs.UTM(zone=10)).opts(size=6, color="crimson")
on_tiles = gts.OSM() * points

# Project once up front when the same data is redrawn often.
projected = gv.project(points, projection=ccrs.GOOGLE_MERCATOR)

# Without tiles, the map can use any Cartopy projection.
world = gv.Points(
    pd.DataFrame({"lon": [-120, 0, 120], "lat": [45, 0, -30]}), ["lon", "lat"]
).opts(projection=ccrs.Robinson(), global_extent=True, size=10, width=600, height=320)
```

| Situation | Do this |
|-----------|---------|
| Longitude/latitude columns | Nothing: PlateCarree is the default |
| Projected metres (UTM, EPSG:3857, national grid) | Pass `crs=` to the element (`ccrs.epsg(code)` works too) |
| GeoDataFrame | GeoViews ignores `.crs`: use `gdf.to_crs(epsg=4326)`, or pass `crs=ccrs.epsg(gdf.crs.to_epsg())` |
| Web tiles in the overlay | Keep the default Web Mercator display projection; tiles can't be reprojected |

Mixing up the data CRS and the display projection is the most common GeoViews mistake. `crs` describes the data; `projection` describes the plot.

## Pattern 6: Spatial Joins and Buffers

**When to use**: You need to count points per region, or find features within a distance, before you plot.

GeoViews displays geometry; it doesn't do spatial analysis. Do the analysis in GeoPandas and hand GeoViews the result.

```python
import numpy as np
import geopandas as gpd
import geoviews as gv
import geoviews.tile_sources as gts
from shapely.geometry import box

gv.extension("bokeh")

rng = np.random.default_rng(3)
zones = gpd.GeoDataFrame(
    {"zone": ["A", "B", "C", "D"]},
    geometry=[box(-1, 51, 0, 52), box(0, 51, 1, 52), box(-1, 52, 0, 53), box(0, 52, 1, 53)],
    crs="EPSG:4326",
)
events = gpd.GeoDataFrame(
    geometry=gpd.points_from_xy(rng.uniform(-1, 1, 500), rng.uniform(51, 53, 500)), crs="EPSG:4326"
)

# Spatial join: which zone is each event in? Then count per zone.
joined = gpd.sjoin(events, zones, how="inner", predicate="within")
counts = zones.merge(joined.groupby("zone").size().rename("events").reset_index(), on="zone")

# Buffer in metres: project to a metric CRS first, then back for display.
sites = gpd.GeoDataFrame(geometry=gpd.points_from_xy([-0.5, 0.5], [51.5, 52.5]), crs="EPSG:4326")
buffers = sites.to_crs(epsg=27700).buffer(10_000).to_crs(epsg=4326)  # 10 km, British National Grid
near = events[events.within(buffers.union_all())]

overlay = (
    gts.CartoLight()
    * gv.Polygons(counts, vdims=["zone", "events"]).opts(color="events", cmap="Blues", alpha=0.6, tools=["hover"])
    * gv.Polygons(gpd.GeoDataFrame(geometry=buffers)).opts(fill_alpha=0, line_color="red", line_width=2)
    * gv.Points(near).opts(color="red", size=4)
).opts(width=650, height=500)
```

❌ Don't buffer in EPSG:4326: the distance is in degrees, and a degree of longitude shrinks toward the poles.

For millions of points, rasterize them instead of drawing each one: `rasterize(gv.Points(df, ["lon", "lat"]))` works as in [Datashader Patterns](./datashader-patterns.md#pattern-4-geographic-aggregation).

## Related

- [Datashader Patterns](./datashader-patterns.md): large point sets on maps
- [Integration Patterns](./integration-patterns.md): GeoViews + Datashader + Panel
- [GeoViews Best Practices](../best-practices/geoviews.md)
- [GeoViews Troubleshooting](../troubleshooting/geoviews-troubleshooting.md)
- [GeoViews user guide](https://geoviews.org/user_guide/index.html) and [GeoPandas docs](https://geopandas.org/)
