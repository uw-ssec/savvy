# HoloViews Patterns

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions.

## Overview

Patterns for composing HoloViews elements: overlays and layouts, axis and hover formatting, hover tooltips, DynamicMaps driven by widgets and streams, custom operations, linked selection, and quick plots with hvPlot. hvPlot returns HoloViews objects, so these patterns apply to `df.hvplot(...)` output too.

**Load when**: Creating complex visualizations with HoloViews

## Pattern 1: Overlay and Layout Composition

**When to use**: Several views of the same data, side by side (`+`) or on shared axes (`*`).

```python
import numpy as np
import pandas as pd
import holoviews as hv
from holoviews import opts

hv.extension("bokeh")

x = np.linspace(0, 4 * np.pi, 200)
df = pd.DataFrame({"x": x, "sin": np.sin(x), "cos": np.cos(x)})

curves = hv.Curve(df, "x", "sin", label="sin") * hv.Curve(df, "x", "cos", label="cos")
hist = hv.Histogram(np.histogram(df.sin, bins=20), kdims="sin")
scatter = hv.Scatter(df, "sin", "cos")

layout = (curves + hist + scatter).cols(2)

# Style by element type once, instead of per object.
layout.opts(
    opts.Curve(width=400, height=250, line_width=2),
    opts.Histogram(width=400, height=250, alpha=0.6),
    opts.Scatter(width=400, height=250, size=4),
    opts.Overlay(legend_position="top_left"),
)
```

- `*` builds an `Overlay` (shared axes); `+` builds a `Layout` (separate plots, axes linked when dimension labels and units match).
- Linked axes come from matching dimension labels (the label defaults to the name) and compatible units. Give unrelated axes different names or labels, or use `.opts(shared_axes=False)` on the layout.
- `hv.NdOverlay` and `hv.HoloMap` turn a dict of elements into a legend or a slider.

## Pattern 2: Dimension Labels, Units and Formatting

**When to use**: Axis labels and hover values must be readable without renaming DataFrame columns.

```python
import numpy as np
import pandas as pd
import holoviews as hv
from bokeh.models import NumeralTickFormatter

hv.extension("bokeh")

df = pd.DataFrame({
    "ts": pd.date_range("2024-01-01", periods=90, freq="D"),
    "rev": np.random.default_rng(1).normal(1e5, 2e4, 90).cumsum(),
})

time = hv.Dimension("ts", label="Date")
revenue = hv.Dimension("rev", label="Revenue", unit="USD")  # axis label: "Revenue (USD)"

curve = hv.Curve(df, time, revenue).opts(
    width=600, height=300,
    yformatter=NumeralTickFormatter(format="$0.0a"),  # axis ticks: $1.2m
    # Hover text is formatted in the browser with Bokeh's syntax, not by Python.
    hover_tooltips=[("Date", "@{ts}{%F}"), ("Revenue", "@{rev}{$0,0}")],
    hover_formatters={"@{ts}": "datetime"},
)
```

- `label` and `unit` set axis titles; `xformatter`/`yformatter` set tick labels and accept a format string such as `"%.1f"` or a Bokeh `TickFormatter`.
- Bokeh hover tooltips ignore a dimension's Python `value_format`. Format them with `hover_tooltips` and `hover_formatters` as above. `value_format` applies only to text HoloViews formats in Python, such as `dimension.pprint_value()`.

## Pattern 3: Hover Tooltips with Extra Columns

**When to use**: Points need context (a name, a category) that isn't on an axis.

```python
import numpy as np
import pandas as pd
import holoviews as hv

hv.extension("bokeh")

rng = np.random.default_rng(2)
df = pd.DataFrame({
    "gdp": rng.lognormal(10, 1, 50),
    "life": rng.normal(72, 6, 50),
    "country": [f"Country {i}" for i in range(50)],
    "pop": rng.integers(1, 300, 50),
})

points = hv.Points(df, kdims=["gdp", "life"], vdims=["country", "pop"]).opts(
    logx=True, size=8, width=500, height=350,
    hover_tooltips=[("Country", "@country"), ("Population (M)", "@pop"), ("GDP", "@gdp{0,0}")],
)
```

Columns become available to the tooltip by being listed as `vdims`. hvPlot does the same with `hover_cols=["country", "pop"]`.

## Pattern 4: DynamicMap with Key Dimensions

**When to use**: The plot depends on one or two parameters and you want sliders without writing a dashboard.

```python
import numpy as np
import holoviews as hv

hv.extension("bokeh")

x = np.linspace(0, 2 * np.pi, 300)


def wave(freq, phase):
    return hv.Curve((x, np.sin(freq * x + phase)), "x", "y").opts(width=500, ylim=(-1.1, 1.1))


dmap = hv.DynamicMap(wave, kdims=["freq", "phase"]).redim.range(freq=(0.5, 5.0), phase=(0.0, np.pi))
```

The callback runs only for the values the user picks, unlike a `HoloMap`, which precomputes every frame. In Panel, `pn.panel(dmap)` renders the same sliders; for custom widgets, pass a `pn.bind` function to `hv.DynamicMap` instead.

## Pattern 5: DynamicMap with Streams

**When to use**: The plot reacts to plot interaction (zoom, tap, selection) or to pushed data rather than to sliders.

```python
import numpy as np
import pandas as pd
import holoviews as hv

hv.extension("bokeh")

rng = np.random.default_rng(3)
df = pd.DataFrame({"x": rng.normal(size=5000), "y": rng.normal(size=5000)})
points = hv.Points(df).opts(width=400, height=400, tools=["box_select", "lasso_select"])

# Summarize whatever the user selects on the scatter plot.
selection = hv.streams.Selection1D(source=points)


def selected_hist(index):
    subset = df.iloc[index] if index else df
    return hv.Histogram(np.histogram(subset.x, bins=30), kdims="x").opts(
        width=400, height=400, title=f"{len(subset):,} points"
    )


hist = hv.DynamicMap(selected_hist, streams=[selection])

# Pipe: replace the data from Python code (a callback, a timer, a thread).
pipe = hv.streams.Pipe(data=df.head(100))
live = hv.DynamicMap(hv.Points, streams=[pipe]).opts(width=400, height=400)
pipe.send(df.sample(100, random_state=0))

layout = points + hist + live
```

Common streams: `RangeXY` (current zoom), `Tap`/`DoubleTap` (click position), `Selection1D` (selected indices), `BoundsXY` (box select bounds), `Pipe` (replace data), `Buffer` (append data). Data streams update in a live session (Jupyter or `panel serve`), not in exported static HTML.

## Pattern 6: Custom Operations

**When to use**: A reusable transformation that should work on elements, HoloMaps and DynamicMaps alike, and stay reactive when it wraps a DynamicMap.

```python
import numpy as np
import pandas as pd
import param
import holoviews as hv
from holoviews.operation import Operation

hv.extension("bokeh")


class rolling_mean(Operation):
    """Smooth the first value dimension with a centered rolling mean."""

    window = param.Integer(default=10, bounds=(1, None))

    def _process(self, element, key=None):
        xdim, ydim = element.kdims[0].name, element.vdims[0].name
        df = element.dframe()
        df[ydim] = df[ydim].rolling(self.p.window, center=True, min_periods=1).mean()
        return element.clone(df)


rng = np.random.default_rng(4)
noisy = hv.Curve(pd.DataFrame({"t": np.arange(500), "v": rng.normal(size=500).cumsum()}), "t", "v")

smoothed = noisy * rolling_mean(noisy, window=25).opts(color="red", line_width=2)
smoothed.opts(width=600, height=300)
```

- Read parameters through `self.p` so per-call overrides (`window=25`) take effect.
- For a one-off transformation, `element.apply(func, **kwargs)` is lighter. Pass widgets or parameters as kwargs and it becomes reactive.

## Pattern 7: Linked Selection Across Plots

**When to use**: Brushing in one plot should highlight the same rows in every other plot.

```python
import numpy as np
import pandas as pd
import holoviews as hv

hv.extension("bokeh")

rng = np.random.default_rng(5)
df = pd.DataFrame({
    "mpg": rng.normal(25, 5, 300),
    "hp": rng.normal(150, 40, 300),
    "weight": rng.normal(3000, 500, 300),
})

scatter = hv.Scatter(df, "hp", "mpg").opts(width=350, height=300)
hist = hv.operation.histogram(hv.Dataset(df), dimension="weight", bins=20).opts(width=350, height=300)

link = hv.link_selections.instance()
linked = link(scatter + hist)

# After the user selects, the filtered rows are available in Python:
selected_rows = link.filter(df)
```

`link_selections` works across element types built from the same columns, including hvPlot output and rasterized Datashader plots.

## Pattern 8: Basic hvPlot

**When to use**: A quick, interactive plot of a small to medium DataFrame (up to roughly 10K rows), without building elements by hand.

```python
import numpy as np
import pandas as pd
import hvplot.pandas  # noqa: F401  (registers the .hvplot accessor)

rng = np.random.default_rng(3)
df = pd.DataFrame({
    "day": np.tile(pd.date_range("2024-01-01", periods=60, freq="D"), 2),
    "city": np.repeat(["Seattle", "Portland"], 60),
    "temp_c": rng.normal(12, 4, 120),
    "rain_mm": rng.gamma(2, 3, 120),
})

lines = df.hvplot.line(x="day", y="temp_c", by="city", ylabel="Temperature (°C)", height=300, width=600)
points = df.hvplot.scatter(x="temp_c", y="rain_mm", by="city", hover_cols=["day"], height=300, width=600)

layout = (lines + points).cols(1)
```

- `by=` splits the data into one series per group, with a legend.
- `hover_cols=` adds columns to the tooltip, as in Pattern 3.
- The result is a HoloViews object, so `*`, `+` and `.opts()` from the patterns above work on it. Display it in a notebook, or put it in a Panel layout to serve it.

## Related

- [Datashader Patterns](./datashader-patterns.md): rasterizing large data in HoloViews
- [Integration Patterns](./integration-patterns.md): HoloViews inside Panel apps
- [HoloViews Best Practices](../best-practices/holoviews.md)
- [HoloViews Troubleshooting](../troubleshooting/holoviews-troubleshooting.md)
- [HoloViews user guide](https://holoviews.org/user_guide/index.html), including [Responding to Events](https://holoviews.org/user_guide/Responding_to_Events.html) and [Linked Brushing](https://holoviews.org/user_guide/Linked_Brushing.html)
