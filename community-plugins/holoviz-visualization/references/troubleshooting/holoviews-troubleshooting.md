# HoloViews Troubleshooting

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions.

## Overview

These are the HoloViews problems that come up most often: elements that print as text instead of rendering, options rejected by the backend, dimension names that do not match the data, and `DynamicMap` or composition errors. hvPlot output is a HoloViews object, so everything here applies to hvPlot too.

**Load when**: A HoloViews plot does not render, an `.opts()` call fails, a `DynamicMap` shows nothing, or an overlay or layout behaves unexpectedly.

## Plot Prints as Text (`:Curve [x] (y)`)

**Symptom**: Instead of a plot, the notebook or console shows a text summary like `:Curve   [x]   (y)`.

**Cause**: No plotting extension is loaded, or the code runs in a plain script where nothing displays objects.

**Fix**: Call `hv.extension('bokeh')` once, before creating plots. In a script, save the object or serve it with Panel.

```python
import holoviews as hv
import panel as pn

hv.extension('bokeh')

curve = hv.Curve([(0, 1), (1, 3), (2, 2)], 'x', 'y')
hv.save(curve, 'curve.html')     # standalone HTML
pn.panel(curve).servable()       # for `panel serve script.py`
```

Saving to PNG needs a headless browser. Without one, `hv.save(curve, 'curve.png')` raises `RuntimeError: Neither firefox and geckodriver nor a variant of chromium browser and chromedriver are available on system PATH...`. Install `selenium` plus `firefox` and `geckodriver` (both on conda-forge), or switch to the matplotlib backend for static images.

## `ValueError: Unexpected option 'colour' for Curve type across all extensions`

**Symptom**: `.opts()` raises `ValueError: Unexpected option 'colour' for Curve type across all extensions. Similar options for current extension ('bokeh') are: ['bgcolor', 'color', 'line_color'].`

**Cause**: The option name does not exist for that element. A common case is using matplotlib names with Bokeh: `linewidth` fails with a suggestion of `['line_width', ...]`.

**Fix**: Use the name from the suggestion list, or list the valid options with `hv.help`.

```python
import holoviews as hv

hv.extension('bokeh')

curve = hv.Curve([(0, 1), (1, 3)]).opts(color='red', line_width=3, tools=['hover'])
hv.help(hv.Curve, pattern='line_')   # filter the option listing
```

## Options on an Overlay Are Rejected

**Symptom**: `(curve * scatter).opts(color='red')` raises `ValueError: Unexpected option 'color' for Overlay type across all extensions. Similar options for current extension ('bokeh') are: ['bgcolor', 'text_color'].`

**Cause**: Options passed directly to `.opts()` on a container apply to the container itself. An `Overlay` has no `color`.

**Fix**: Target the elements with `hv.opts.<Element>(...)` specs. Those specs travel down into overlays and layouts.

```python
import holoviews as hv
from holoviews import opts

hv.extension('bokeh')

curve = hv.Curve([(0, 1), (1, 2), (2, 1.5)])
scatter = hv.Scatter([(0, 1), (1, 2), (2, 1.5)])

plot = (curve * scatter).opts(
    opts.Curve(color='red'),
    opts.Scatter(size=8, color='black'),
    opts.Overlay(title='Targeted options'),
)
```

## Backend-Specific Options

**Symptom**: One of these:
- `Error: Backend 'matplotlib' does not exist` from `hv.output(backend='matplotlib')`.
- `WARNING:param.main: Option 'linewidth' for Curve type not valid for selected backend ('bokeh'). Option only applies to following backends: ['matplotlib']`.

**Cause**: Each backend has its own option names. A backend has to be loaded with `hv.extension` before you can switch to it, and an option for an inactive backend is ignored with a warning.

**Fix**: Load every backend you need, then tag options with `backend=`.

```python
import holoviews as hv

hv.extension('bokeh', 'matplotlib')   # first one listed is the active backend

curve = hv.Curve([(0, 1), (1, 3)]).opts(line_width=3)               # bokeh
curve = curve.opts(linewidth=3, backend='matplotlib')                # matplotlib
hv.output(backend='matplotlib')                                      # switch for display
hv.output(backend='bokeh')
```

## `DataError: Supplied data does not contain specified dimensions`

**Symptom**: `DataError: Supplied data does not contain specified dimensions, the following dimensions were not found: ['X']`.

**Cause**: The key dimensions (`kdims`) or value dimensions (`vdims`) you named are not columns in the data. Names are case-sensitive.

**Fix**: Use the exact column names. Give a dimension a display label with `hv.Dimension` instead of renaming the data.

```python
import numpy as np
import pandas as pd
import holoviews as hv

hv.extension('bokeh')

df = pd.DataFrame({'t': np.arange(5), 'temp_c': [20.1, 20.5, 21.0, 20.8, 20.2]})
print(list(df.columns))

curve = hv.Curve(df, kdims=[hv.Dimension('t', label='Time (s)')],
                 vdims=[hv.Dimension('temp_c', label='Temperature', unit='°C')])
```

## Axes Linked (or Mislabeled) Across Plots

**Symptom**: Zooming one plot in a layout zooms another plot that shows unrelated data. Or an overlay shows only the first element's axis labels.

**Cause**: HoloViews links axes whose dimensions have the same label and unit. The label defaults to the dimension name, so two plots with a dimension called `x` share one range, even if the data have nothing in common. An overlay labels its axes from its first element.

**Fix**: Give unrelated data distinct dimension names or labels, or turn off linking for the layout.

```python
import pandas as pd
import holoviews as hv

hv.extension('bokeh')

small = hv.Curve(pd.DataFrame({'x': [0, 1], 'y': [0, 1]}), 'x', 'y')
large = hv.Curve(pd.DataFrame({'x': [0, 100], 'y': [0, 1000]}), 'x', 'y')

unlinked = (small + large).opts(shared_axes=False)
renamed = small + large.redim(x='distance', y='load')   # distinct names, no linking
```

## `DynamicMap cannot be displayed without explicit indexing`

**Symptom**: `SkipRendering: DynamicMap cannot be displayed without explicit indexing as 'f' dimension(s) are unbounded. Set dimensions bounds with the DynamicMap redim.range or redim.values methods.`

**Cause**: A `DynamicMap` with key dimensions needs to know which values are valid, so it can create widgets and choose an initial frame.

**Fix**: Declare the range or values on the dimension, or use `redim`.

```python
import numpy as np
import holoviews as hv

hv.extension('bokeh')

def wave(freq):
    x = np.linspace(0, 10, 200)
    return hv.Curve((x, np.sin(freq * x)), 'x', 'y')

dmap = hv.DynamicMap(wave, kdims=hv.Dimension('freq', range=(0.5, 5.0), default=1.0))
dmap_values = hv.DynamicMap(wave, kdims='freq').redim.values(freq=[1, 2, 4])
```

Wrap the `DynamicMap` in `pn.panel(dmap)` to get the slider or dropdown in a served app.

## `DynamicMap` Callback Errors

**Symptom**: One of these:
- `TypeError: DynamicMap does not accept NoneType type, data elements have to be a ('ViewableElement', 'NdMapping', 'Layout').`
- `AssertionError: DynamicMap must only contain one type of object, not both Scatter and Curve.`
- A log line such as `WARNING:param.<lambda>: Callable raised "ZeroDivisionError('division by zero')".` followed by the original exception.

**Cause**: The callback returned nothing, returned different element types for different keys, or raised. The warning line shows the arguments the callback was invoked with, which is usually enough to reproduce the problem.

**Fix**: Return the same element type on every path, using an empty element when there is no data. Call the callback directly with the logged arguments to debug it.

```python
import numpy as np
import pandas as pd
import holoviews as hv

hv.extension('bokeh')

df = pd.DataFrame({'site': ['a', 'a', 'b'], 'x': [0, 1, 0], 'y': [1, 2, 3]})

def by_site(site):
    subset = df[df.site == site]
    if subset.empty:
        return hv.Scatter([], 'x', 'y')        # same type, no data
    return hv.Scatter(subset, 'x', 'y')

print(by_site('c'))                            # call directly while debugging
dmap = hv.DynamicMap(by_site, kdims=hv.Dimension('site', values=['a', 'b', 'c']))
```

## Composition Errors

**Symptom**: `TypeError: unsupported operand type(s) for *: 'Curve' and 'int'`, or a layout's grid is wider or narrower than you wanted.

**Cause**: `*` (overlay) and `+` (layout) only combine HoloViews objects. A layout wraps after four columns by default.

**Fix**: Convert values to elements first, for example `hv.HLine(3)` instead of `3`, and set the number of columns with `.cols()`.

```python
import holoviews as hv

hv.extension('bokeh')

curve = hv.Curve([(0, 1), (1, 4), (2, 2)])
with_threshold = curve * hv.HLine(3).opts(color='gray', line_dash='dashed')
grid = (curve + with_threshold + curve.relabel('copy')).cols(2)
```

## Related

- [HoloViews Best Practices](../best-practices/holoviews.md)
- [HoloViews Patterns](../patterns/holoviews-patterns.md)
- [hvPlot Troubleshooting](./hvplot-troubleshooting.md)
- [Customizing Plots](https://holoviews.org/user_guide/Customizing_Plots.html)
- [Applying Customizations](https://holoviews.org/user_guide/Applying_Customizations.html)
- [Live Data (DynamicMap)](https://holoviews.org/user_guide/Live_Data.html)
