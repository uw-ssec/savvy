# Datashader Patterns

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions.

## Overview

Patterns for rendering data too large to send to the browser point by point. Datashader aggregates rows into a fixed-size grid on the server, and only the image travels to the browser. Through HoloViews the grid is recomputed on every zoom or pan.

**Load when**: Working with datasets > 100K points

```bash
pixi add datashader holoviews hvplot   # or: conda install -c conda-forge datashader holoviews hvplot
pip install datashader holoviews hvplot
```

### `rasterize` or `datashade`?

| Operation | Returns | Colormapping | Hover | Colorbar | Use when |
|-----------|---------|--------------|-------|----------|----------|
| `rasterize` | `hv.Image` of aggregate values | In the browser (Bokeh) | Aggregate value per pixel | Yes | Default choice |
| `datashade` | `hv.RGB` image | On the server (Datashader) | Only with `selector=` (a sample row per pixel) | No | Categorical color mixing, or exact Datashader shading |

Both live in `holoviews.operation.datashader`. hvPlot exposes them as `rasterize=True` and `datashade=True`.

## Pattern 1: Basic Datashading

**When to use**: A scatter plot with 100K+ points.

```python
import numpy as np
import pandas as pd
import holoviews as hv
from holoviews.operation.datashader import rasterize, dynspread

hv.extension("bokeh")

n = 1_000_000
rng = np.random.default_rng(0)
df = pd.DataFrame({
    "x": np.concatenate([rng.normal(0, 1, n // 2), rng.normal(3, 0.5, n // 2)]),
    "y": np.concatenate([rng.normal(0, 1, n // 2), rng.normal(2, 0.5, n // 2)]),
})

points = hv.Points(df, ["x", "y"])
shaded = dynspread(rasterize(points).opts(cmap="fire", cnorm="eq_hist", colorbar=True))
shaded.opts(width=600, height=450, bgcolor="black", tools=["hover"])
```

The hvPlot equivalent is a single call:

```python
import numpy as np
import pandas as pd
import hvplot.pandas  # noqa: F401

df = pd.DataFrame(np.random.default_rng(0).normal(size=(1_000_000, 2)), columns=["x", "y"])
plot = df.hvplot.points("x", "y", rasterize=True, dynspread=True, cmap="fire", cnorm="eq_hist", width=600)
```

`dynspread` enlarges isolated pixels so sparse regions stay visible when zoomed in.

## Pattern 2: Categorical Scatter

**When to use**: Points belong to a few groups and the mix of groups at each pixel matters.

```python
import numpy as np
import pandas as pd
import datashader as ds
import holoviews as hv
from holoviews.operation.datashader import datashade, dynspread

hv.extension("bokeh")

rng = np.random.default_rng(1)
centers = {"a": (0, 0), "b": (2, 1), "c": (1, 3)}
frames = [
    pd.DataFrame({"x": rng.normal(cx, 0.8, 300_000), "y": rng.normal(cy, 0.8, 300_000), "group": g})
    for g, (cx, cy) in centers.items()
]
df = pd.concat(frames, ignore_index=True)
df["group"] = df["group"].astype("category")  # ds.by needs a categorical column

color_key = {"a": "#1f77b4", "b": "#ff7f0e", "c": "#2ca02c"}
shaded = dynspread(
    datashade(hv.Points(df, ["x", "y"], vdims="group"), aggregator=ds.by("group"), color_key=color_key)
).opts(width=600, height=450)

# Server-side shading draws no legend; add one with empty points.
legend = hv.NdOverlay({g: hv.Points([(np.nan, np.nan)]).opts(color=c) for g, c in color_key.items()})
plot = shaded * legend
```

`ds.by("group")` is the current form of the older `ds.count_cat("group")`, and it also accepts a reduction (`ds.by("group", ds.mean("value"))`). With `rasterize`, the same aggregator returns an `ImageStack` that Bokeh colors in the browser.

## Pattern 3: Time Series Rasterization

**When to use**: Long series (millions of samples) or many overlapping series.

```python
import numpy as np
import pandas as pd
import holoviews as hv
from holoviews.operation.datashader import rasterize

hv.extension("bokeh")

n = 2_000_000
rng = np.random.default_rng(2)
series = pd.DataFrame({
    "time": pd.date_range("2020-01-01", periods=n, freq="s"),
    "value": rng.normal(size=n).cumsum(),
})

one_long = rasterize(hv.Curve(series, "time", "value"), line_width=1).opts(
    width=700, height=300, cmap="blues", cnorm="log"
)

# 200 series of 2,000 samples: stack them in one frame with an id column.
t = np.arange(2_000)
many = pd.DataFrame({
    "t": np.tile(t, 200),
    "v": (rng.normal(size=(200, 2_000)).cumsum(axis=1)).ravel(),
    "series": np.repeat(np.arange(200), 2_000),
})
overlay = hv.NdOverlay({i: hv.Curve(g, "t", "v") for i, g in many.groupby("series")}, kdims="series")
density = rasterize(overlay).opts(width=700, height=300, cmap="viridis", cnorm="eq_hist")

layout = (one_long + density).cols(1)
```

Each pixel counts how many lines cross it, so the density view shows where most series sit and which ones are outliers.

## Pattern 4: Geographic Aggregation

**When to use**: Millions of GPS points, events or sensor readings on a map.

```python
import numpy as np
import pandas as pd
import holoviews as hv
from holoviews.element.tiles import CartoLight
from holoviews.operation.datashader import rasterize, dynspread
from holoviews.util.transform import lon_lat_to_easting_northing

hv.extension("bokeh")

rng = np.random.default_rng(3)
lon = rng.normal(-122.33, 0.05, 500_000)
lat = rng.normal(47.61, 0.03, 500_000)
easting, northing = lon_lat_to_easting_northing(lon, lat)  # tiles use Web Mercator
df = pd.DataFrame({"easting": easting, "northing": northing})

points = hv.Points(df, ["easting", "northing"])
hotspots = dynspread(rasterize(points).opts(cmap="fire", cnorm="eq_hist", alpha=0.8))
map_plot = (CartoLight() * hotspots).opts(width=700, height=500)
```

With GeoViews, keep longitude and latitude and let it project for you; see [GeoViews Patterns](./geoviews-patterns.md).

## Pattern 5: Custom Aggregations

**When to use**: The color should encode something other than point counts, such as a mean, maximum or spread of a value column.

```python
import numpy as np
import pandas as pd
import datashader as ds
import datashader.transfer_functions as tf
import holoviews as hv
from holoviews.operation.datashader import rasterize

hv.extension("bokeh")

rng = np.random.default_rng(4)
n = 500_000
df = pd.DataFrame({"x": rng.uniform(0, 10, n), "y": rng.uniform(0, 10, n)})
df["temp"] = np.sin(df.x) + np.cos(df.y) + rng.normal(0, 0.2, n)

points = hv.Points(df, ["x", "y"], vdims="temp")
mean_temp = rasterize(points, aggregator=ds.mean("temp")).opts(cmap="coolwarm", colorbar=True, title="Mean")
max_temp = rasterize(points, aggregator=ds.max("temp")).opts(cmap="inferno", colorbar=True, title="Max")
spread = rasterize(points, aggregator=ds.std("temp")).opts(cmap="viridis", colorbar=True, title="Std")
layout = (mean_temp + max_temp + spread).opts(hv.opts.Image(width=300, height=280))

# Standalone Datashader (no HoloViews): useful for batch image export.
canvas = ds.Canvas(plot_width=400, plot_height=400, x_range=(0, 10), y_range=(0, 10))
agg = canvas.points(df, "x", "y", agg=ds.mean("temp"))  # an xarray.DataArray
img = tf.shade(agg, cmap=["blue", "white", "red"], how="linear")
hot_cells = int((agg > 1.5).sum())  # aggregates are arrays: compute on them directly
```

Other reductions: `ds.count()`, `ds.sum(col)`, `ds.min(col)`, `ds.var(col)`, `ds.any()`, `ds.first(col)`, `ds.last(col)`, and `ds.summary(...)` for several at once.

## Pattern 6: Dynamic Colormapping

**When to use**: Users need to switch colormaps, normalization or color limits without recomputing the aggregate.

With `rasterize`, colormapping happens in the browser, so changing it is cheap.

```python
import numpy as np
import pandas as pd
import holoviews as hv
import panel as pn
from holoviews.operation.datashader import rasterize

hv.extension("bokeh")
pn.extension()

rng = np.random.default_rng(5)
df = pd.DataFrame({"x": rng.standard_cauchy(500_000), "y": rng.standard_cauchy(500_000)})
df = df[(df.x.abs() < 20) & (df.y.abs() < 20)]

cmap = pn.widgets.Select(label="Colormap", options=["fire", "viridis", "kbc", "gray"], value="fire")
cnorm = pn.widgets.RadioButtonGroup(label="Normalization", options=["linear", "log", "eq_hist"], value="eq_hist")

image = rasterize(hv.Points(df, ["x", "y"]))


def styled(norm):
    # cnorm picks the Bokeh color mapper type, so build a new plot when it changes...
    plot = image.opts(cnorm=norm, colorbar=True, width=550, height=450, clone=True)
    # ...while cmap can be updated in place on the existing plot.
    return plot.apply.opts(cmap=cmap)


app = pn.Row(pn.Column(cmap, cnorm), pn.bind(styled, cnorm))
app.servable()
```

- `cnorm="eq_hist"` reveals structure in heavy-tailed data; `"log"` and `"linear"` keep values comparable across views.
- Set `clim=(low, high)` to fix the color range across frames or plots.
- `.apply.opts(...)` accepts widgets and parameters, and updates the options in place when they change. Don't pass `cnorm` that way: in HoloViews 1.23 switching an existing plot from `linear` to `eq_hist` fails, which is why the example rebuilds the plot for that one option.

## Pattern 7: Out-of-Core Data with Dask

**When to use**: 10M+ rows, or more data than fits comfortably in memory.

Datashader aggregates Dask DataFrames partition by partition, in parallel. Read straight into Dask (for example `dd.read_parquet(path, columns=["x", "y"])`) and persist the result if it fits in cluster memory.

```python
import numpy as np
import pandas as pd
import dask.dataframe as dd
import holoviews as hv
from holoviews.operation.datashader import rasterize

hv.extension("bokeh")

rng = np.random.default_rng(6)
pdf = pd.DataFrame({"x": rng.normal(size=2_000_000), "y": rng.normal(size=2_000_000)})
ddf = dd.from_pandas(pdf, npartitions=8).persist()  # with real data: dd.read_parquet(...)

plot = rasterize(hv.Points(ddf, ["x", "y"])).opts(cmap="fire", cnorm="eq_hist", width=500, height=450)
```

- Read only the columns you plot, and store floats as `float32` to halve memory.
- Every zoom rescans all partitions, so `persist()` keeps those scans in memory instead of rereading files.

## Related

- [Performance Patterns](./performance-patterns.md): caching, lazy loading, data reduction
- [GeoViews Patterns](./geoviews-patterns.md): projected maps with Datashader
- [Integration Patterns](./integration-patterns.md): Datashader + HoloViews + Panel pipelines
- [Datashader Troubleshooting](../troubleshooting/datashader-troubleshooting.md)
- [Datashader docs](https://datashader.org/) and [HoloViews large-data guide](https://holoviews.org/user_guide/Large_Data.html)
