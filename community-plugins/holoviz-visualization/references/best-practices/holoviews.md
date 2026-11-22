# HoloViews Best Practices

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions.

## Overview

HoloViews works best when elements describe the data (dimensions, labels, units) and options describe the look. These practices cover composition, customization and styling, and backend choice.

**Load when**: Building multi-plot figures, styling HoloViews or hvPlot output, or choosing a plotting backend.

## 1. Declare Dimensions Once, Properly

Give every element named key and value dimensions with labels and units. Axis labels, hover tooltips, linked axes and widgets all come from them.

```python
import holoviews as hv
import numpy as np
import pandas as pd

hv.extension('bokeh')

df = pd.DataFrame({
    'time': pd.date_range('2025-01-01', periods=100, freq='h'),
    'temp': 20 + np.random.randn(100).cumsum() * 0.2,
})

temp = hv.Dimension('temp', label='Temperature', unit='°C')

# ✅ Good: label and unit appear on the axis and in hover
curve = hv.Curve(df, 'time', temp).opts(tools=['hover'], width=600)

# ❌ Bad: anonymous columns give axes labelled 'x' and 'y'
# hv.Curve(df.values)
```

Elements whose dimensions share a **name** (and a compatible label and unit) link their axes automatically in a layout. Name dimensions consistently across a figure, and rename them (`.redim(old='new')`) when two columns mean different things.

## 2. Compose with `*`, `+` and Containers

| Operator / container | Result | Use for |
|----------------------|--------|---------|
| `a * b` | `Overlay` | Layers on shared axes |
| `a + b` | `Layout` | Side-by-side panels |
| `hv.HoloMap` / `hv.DynamicMap` | Animated or widget-driven | One element per parameter value |
| `hv.NdOverlay` / `hv.NdLayout` | Keyed collections | Many similar elements (one per group) |
| `.cols(n)` | Wrapped layout | Grids of panels |

```python
import holoviews as hv
import numpy as np

hv.extension('bokeh')

x = np.linspace(0, 10, 200)
curves = hv.NdOverlay({f: hv.Curve((x, np.sin(f * x)), 'x', 'y') for f in (1, 2, 3)}, kdims='frequency')
hist = hv.Histogram(np.histogram(np.random.randn(1000), bins=30))

layout = (curves + hist).cols(2).opts(shared_axes=False)
```

Prefer an `NdOverlay` keyed by a dimension over overlaying a hand-built list. It gets a legend and consistent colors for free. The hvPlot equivalent is `df.hvplot(by='group')`.

## 3. Separate Data From Options

Apply options with `.opts()` once you've built the element, or set defaults globally with `hv.opts.defaults`. Data-processing code should not set colors.

```python
import holoviews as hv
import numpy as np
from holoviews import opts

hv.extension('bokeh')

# Project-wide defaults, set once at startup
opts.defaults(
    opts.Curve(width=500, height=300, tools=['hover'], line_width=2),
    opts.Scatter(size=6, alpha=0.7),
)

points = hv.Scatter(np.random.randn(100, 2))
curve = hv.Curve(np.random.randn(50).cumsum())

# Per-object options for this figure only
overlay = (curve * points).opts(opts.Curve(color='black'), opts.Scatter(color='orange'))
```

- `.opts()` changes the element in place and returns it. To style one dataset two ways, use `.opts(..., clone=True)`; the clone shares the data rather than copying it.
- Options are validated against the loaded backend, and a misspelled option raises an error listing the closest valid names. Keep validation on. Don't silence it.
- Run `hv.help(hv.Curve)` to list the valid options for an element.

## 4. Style for Meaning

- Map color to a dimension (`color='category'` or `color=hv.dim('value')`) rather than hand-assigning colors per layer.
- Use perceptually uniform colormaps from Colorcet for continuous data (`cmap='cet_fire'`, `'cet_CET_L17'`). Use a diverging map centered on a meaningful midpoint (`clim` symmetric around zero, or `cnorm` plus `clim`) for signed data.
- Use `hv.dim` expressions for size and alpha so the mapping stays declarative.

```python
import holoviews as hv
import numpy as np
import pandas as pd

hv.extension('bokeh')

df = pd.DataFrame({
    'x': np.random.randn(200), 'y': np.random.randn(200),
    'change': np.random.randn(200), 'weight': np.random.rand(200),
})

scatter = hv.Scatter(df, 'x', ['y', 'change', 'weight']).opts(
    color='change', cmap='RdBu_r', clim=(-3, 3), colorbar=True,
    size=hv.dim('weight') * 10 + 3, width=500, tools=['hover'],
)
```

See the `colormaps-styling` skill for palette selection and the [Accessibility Best Practices](./accessibility.md) for colorblind-safe choices.

## 5. Use Dynamic Containers for Interactivity

- `hv.HoloMap` renders every frame up front. Use it for a small number of static frames you want to export.
- `hv.DynamicMap` computes frames on demand. Use it for anything driven by widgets, streams or large parameter spaces.
- Drive a `DynamicMap` from a Panel widget with `hv.DynamicMap(pn.bind(fn, widget))`, or from plot interaction with `streams=[hv.streams.RangeXY()]`.
- Use `hv.link_selections` for cross-filtering between plots. It is less code than wiring streams by hand.

```python
import holoviews as hv
import numpy as np
import pandas as pd

hv.extension('bokeh')

df = pd.DataFrame({'a': np.random.randn(500), 'b': np.random.randn(500), 'c': np.random.randn(500)})

# Box-select in either plot to filter both
linked = hv.link_selections(
    hv.Scatter(df, 'a', 'b') + hv.Scatter(df, 'b', 'c')
)
```

## 6. Choose the Backend for the Output

| Backend | Choose when |
|---------|-------------|
| `bokeh` (hvPlot's default; select with `hv.extension('bokeh')`) | Interactive web output, Panel apps, Datashader zooming |
| `matplotlib` | Static publication figures (PDF/SVG/PNG), LaTeX labels |
| `plotly` | 3D surfaces/scatter in a browser |

```python
import holoviews as hv
import numpy as np

hv.extension('bokeh', 'matplotlib')  # first listed is the active backend

curve = hv.Curve(np.random.randn(50).cumsum())
curve = curve.opts(width=500, backend='bokeh').opts(fig_size=150, backend='matplotlib')

hv.save(curve, 'figure.html')                        # bokeh
hv.save(curve, 'figure.png', backend='matplotlib')   # static image
```

Options are backend-specific (`width` in pixels for Bokeh, `fig_size` as a percentage for Matplotlib). Pass `backend=` to `.opts()` when a figure has to render in both.

## 7. Let hvPlot Do the Boilerplate

hvPlot returns ordinary HoloViews objects. Start with `df.hvplot(...)` and drop to HoloViews elements only when you need composition or options that hvPlot doesn't expose. Everything above (`.opts`, `*`, `+`) still applies.

## Anti-Patterns

| ❌ Avoid | ✅ Instead |
|---------|-----------|
| Building Bokeh figures and patching them via hooks first | `.opts()`; use `hooks`/`backend_opts` only for what options don't cover |
| `HoloMap` over hundreds of frames | `DynamicMap` |
| Unnamed dimensions (`x`, `y`) everywhere | Named, labelled `hv.Dimension` |
| A list of overlays built in a loop | `hv.NdOverlay` or `hvplot(by=...)` |
| `datashade()` when you want hover and a colorbar | `rasterize()` with `cmap` |

## Related

- [HoloViews Patterns](../patterns/holoviews-patterns.md)
- [HoloViews Troubleshooting](../troubleshooting/holoviews-troubleshooting.md)
- [Performance Best Practices](./performance.md)
- [HoloViews user guide](https://holoviews.org/user_guide/index.html)
- [Applying customizations](https://holoviews.org/user_guide/Applying_Customizations.html)
