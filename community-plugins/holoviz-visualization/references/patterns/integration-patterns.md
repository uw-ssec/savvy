# Integration Patterns

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions.

## Overview

Patterns for combining HoloViz libraries: HoloViews and hvPlot inside Panel, Datashader pipelines driven by widgets, GeoViews with Datashader, and Panel apps mounted in FastAPI. The libraries share Param underneath, so widgets, parameters and streams pass between them directly.

**Load when**: Using multiple HoloViz libraries together

## Pattern 1: Panel + HoloViews Dashboard

**When to use**: Widgets drive plots, and users should keep their zoom when a widget changes.

```python
import numpy as np
import pandas as pd
import holoviews as hv
import panel as pn
import hvplot.pandas  # noqa: F401

hv.extension("bokeh")
pn.extension()

rng = np.random.default_rng(0)
df = pd.DataFrame({
    "time": pd.date_range("2024-01-01", periods=2_000, freq="h"),
    "sensor": rng.choice(["s1", "s2", "s3"], 2_000),
    "value": rng.normal(size=2_000).cumsum(),
})

sensor = pn.widgets.Select(label="Sensor", options=["s1", "s2", "s3"])
smooth = pn.widgets.IntSlider(label="Smoothing (hours)", start=1, end=48, value=6)


def sensor_curve(sensor, smooth):
    data = df[df.sensor == sensor].set_index("time").value.rolling(f"{smooth}h").mean()
    return data.hvplot.line(height=300, responsive=True, title=sensor)


# Wrapping the bound function in a DynamicMap updates the plot in place,
# so the zoom survives. A bare pn.bind would replace the whole plot.
plot = hv.DynamicMap(pn.bind(sensor_curve, sensor, smooth))

# The same filter with a reactive expression: the table updates with the widgets.
dfx = pn.rx(df)
summary = dfx[dfx.sensor == sensor].describe()

app = pn.Row(pn.Column(sensor, smooth, width=250), pn.Column(plot, pn.pane.DataFrame(summary)))
app.servable()
```

✅ `hv.DynamicMap(pn.bind(...))` for plots; `pn.bind` or `pn.rx` for tables, text and indicators.
❌ Don't rebuild a whole layout in one bound function when only one plot depends on the widget.

## Pattern 2: Datashader + HoloViews Pipeline

**When to use**: Filtering a large dataset with widgets while every view stays rasterized.

```python
import numpy as np
import pandas as pd
import holoviews as hv
import panel as pn
from holoviews.operation.datashader import rasterize, dynspread

hv.extension("bokeh")
pn.extension()

n = 1_000_000
rng = np.random.default_rng(1)
trips = pd.DataFrame({
    "pickup_x": rng.normal(0, 1, n),
    "pickup_y": rng.normal(0, 1, n),
    "fare": rng.gamma(2, 8, n),
    "hour": rng.integers(0, 24, n),
})

hours = pn.widgets.IntRangeSlider(label="Hour of day", start=0, end=23, value=(0, 23))
min_fare = pn.widgets.FloatSlider(label="Minimum fare", start=0, end=60, value=0)


def filtered_points(hours, min_fare):
    lo, hi = hours
    sel = trips[(trips.hour >= lo) & (trips.hour <= hi) & (trips.fare >= min_fare)]
    return hv.Points(sel, ["pickup_x", "pickup_y"], vdims="fare")


points = hv.DynamicMap(pn.bind(filtered_points, hours, min_fare))
density = dynspread(rasterize(points)).opts(cmap="fire", cnorm="eq_hist", width=500, height=450, bgcolor="black")
mean_fare = rasterize(points, aggregator="mean").opts(cmap="viridis", colorbar=True, width=500, height=450)

app = pn.Column(pn.Row(hours, min_fare), pn.Row(density, mean_fare))
app.servable()
```

The filter runs in Python on each widget change, and rasterization reruns on each zoom. Both views share the `points` DynamicMap, so they always show the same subset. For data larger than memory, build `trips` as a Dask DataFrame; the operations accept it unchanged.

## Pattern 3: GeoViews + Datashader Maps

**When to use**: Millions of geographic points on a basemap with real projections.

```python
import numpy as np
import pandas as pd
import cartopy.crs as ccrs
import geoviews as gv
import geoviews.tile_sources as gts
import panel as pn
from holoviews.operation.datashader import rasterize, dynspread

gv.extension("bokeh")
pn.extension()

rng = np.random.default_rng(2)
n = 1_000_000
pings = pd.DataFrame({"lon": rng.normal(-73.98, 0.04, n), "lat": rng.normal(40.75, 0.03, n)})

# Project once to Web Mercator, so rasterize doesn't reproject on every zoom.
points = gv.project(gv.Points(pings, ["lon", "lat"]), projection=ccrs.GOOGLE_MERCATOR)
hotspots = dynspread(rasterize(points)).opts(cmap="fire", cnorm="eq_hist", alpha=0.85)

basemap = pn.widgets.Select(label="Basemap", options={"Light": gts.CartoLight, "Dark": gts.CartoDark})


def with_tiles(tiles):
    return (tiles() * hotspots).opts(width=700, height=500)


app = pn.Column(basemap, pn.bind(with_tiles, basemap))
app.servable()
```

hvPlot does both steps for you: `pings.hvplot.points("lon", "lat", geo=True, tiles="CartoLight", rasterize=True)`.

## Pattern 4: FastAPI + Panel

**When to use**: Panel dashboards belong in an existing FastAPI service, next to its REST endpoints.

`panel.io.fastapi` serves Panel apps from a FastAPI application, with no separate Panel server process. It needs FastAPI and an ASGI server:

```bash
pixi add panel fastapi uvicorn   # or: conda install -c conda-forge panel fastapi uvicorn
pip install "panel[fastapi]"     # pulls in fastapi[standard], which includes uvicorn
```

```python
import panel as pn
from fastapi import FastAPI
from panel.io.fastapi import add_application

app = FastAPI()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@add_application("/dashboard", app=app, title="Sales dashboard")
def create_dashboard():
    # Called once per browser session, like a script under `panel serve`.
    pn.extension()
    slider = pn.widgets.IntSlider(label="Units", start=0, end=100, value=10)
    return pn.Column(slider, pn.bind(lambda v: f"Revenue: ${v * 12.5:,.2f}", slider))


# Smoke test without starting a server:
from fastapi.testclient import TestClient

with TestClient(app) as client:
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/dashboard").status_code == 200
```

Run it with uvicorn (if the code is in `main.py`):

```bash
uvicorn main:app --port 8000
```

- `add_applications({"/a": app_a, "/b": "b.py"}, app=app)` mounts several apps; values can be Panel objects, functions or script paths.
- Each browser session still holds a websocket to the FastAPI process, so scale it the way you would scale `panel serve`.

## Pattern 5: Param Classes Shared Across Libraries

**When to use**: The same settings object should drive a HoloViews plot and Panel widgets, and stay usable from plain Python and tests.

```python
import numpy as np
import holoviews as hv
import panel as pn
import param

hv.extension("bokeh")
pn.extension()


class WaveSettings(param.Parameterized):
    frequency = param.Number(default=1.0, bounds=(0.1, 5))
    amplitude = param.Number(default=1.0, bounds=(0.1, 2))
    points = param.Integer(default=200, bounds=(50, 2000))


settings = WaveSettings()


def wave(frequency, amplitude, points):
    x = np.linspace(0, 4 * np.pi, points)
    return hv.Curve((x, amplitude * np.sin(frequency * x))).opts(ylim=(-2.1, 2.1), responsive=True, height=300)


# hv.streams.Params feeds parameter values into the DynamicMap callback.
plot = hv.DynamicMap(wave, streams=[hv.streams.Params(settings)])

app = pn.Row(pn.Param(settings, widgets={"points": pn.widgets.IntInput}), plot)
app.servable()

settings.param.update(frequency=2.5, amplitude=0.5)  # scripts and tests drive the same object
```

## Related

- [Panel Patterns](./panel-patterns.md), [HoloViews Patterns](./holoviews-patterns.md), [Datashader Patterns](./datashader-patterns.md), [GeoViews Patterns](./geoviews-patterns.md)
- [Performance Patterns](./performance-patterns.md)
- Lumen builds on these libraries for declarative and AI-assisted dashboards; see the [lumen-dashboards](../../skills/lumen-dashboards/SKILL.md) and [lumen-ai](../../skills/lumen-ai/SKILL.md) skills
- [HoloViz ecosystem overview](../holoviz-ecosystem.md)
- [Panel FastAPI integration](https://panel.holoviz.org/how_to/integrations/FastAPI.html)
