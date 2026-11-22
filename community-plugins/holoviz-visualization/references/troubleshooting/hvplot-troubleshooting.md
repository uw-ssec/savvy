# hvPlot Troubleshooting

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions.

## Overview

hvPlot returns ordinary HoloViews objects, so many rendering problems are really HoloViews problems (see [HoloViews Troubleshooting](./holoviews-troubleshooting.md)). This file covers the problems specific to hvPlot: the `.hvplot` accessor missing, plots that never appear outside a notebook, `groupby` widgets, and unrecognized plot kinds or options.

**Load when**: `.hvplot` is missing, a plot does not show, `groupby` misbehaves, or a `kind` or keyword is not accepted.

## `AttributeError: 'DataFrame' object has no attribute 'hvplot'`

**Symptom**: `df.hvplot.line(...)` fails with `AttributeError: 'DataFrame' object has no attribute 'hvplot'`.

**Cause**: `import hvplot` alone does not register the accessor. Each data library has its own module that patches `.hvplot` onto its objects.

**Fix**: Import the module for your data type before plotting.

```python
import numpy as np
import pandas as pd
import hvplot.pandas  # noqa: F401  registers df.hvplot (also GeoPandas GeoDataFrames)
import hvplot.xarray  # noqa: F401  registers ds.hvplot / da.hvplot

df = pd.DataFrame({'x': np.arange(10), 'y': np.random.rand(10)})
plot = df.hvplot.line('x', 'y')
```

| Data | Import |
|------|--------|
| pandas, GeoPandas | `import hvplot.pandas` |
| xarray | `import hvplot.xarray` |
| Dask | `import hvplot.dask` |
| Polars | `import hvplot.polars` |
| DuckDB | `import hvplot.duckdb` |

NetworkX graphs work differently: `import hvplot.networkx as hvnx` provides drawing functions such as `hvnx.draw(G)`, not a `G.hvplot` accessor.

If the data library is not installed, the import says so, for example `ImportError: Could not patch plotting API onto Polars. Polars could not be imported.` Install the library into the same environment.

`hvplot.intake` is deprecated in 0.13 and emits a `FutureWarning`. Read the data with pandas or xarray and plot that instead.

## Plot Does Not Appear

**Symptom**: The code runs without error, but no plot appears in a script, a terminal, or an IDE.

**Cause**: hvPlot returns an object. Notebooks display the last expression of a cell automatically; scripts do not.

**Fix**: Choose an output explicitly.

```python
import numpy as np
import pandas as pd
import hvplot
import hvplot.pandas  # noqa: F401
import panel as pn

df = pd.DataFrame({'x': np.arange(10), 'y': np.random.rand(10)})
plot = df.hvplot.line('x', 'y', title='Daily values')

hvplot.save(plot, 'plot.html')        # standalone HTML file
pn.panel(plot).servable()             # for `panel serve script.py`
# hvplot.show(plot)                   # starts a server and opens a browser tab
```

In a notebook, make sure the plot is the last expression in the cell, or wrap it in `display(plot)`. If the cell shows nothing at all, see [Panel Troubleshooting](./panel-troubleshooting.md#nothing-displays).

## `NotImplementedError: kind='bars' for data of type <class 'pandas.DataFrame'>`

**Symptom**: `df.hvplot(kind='bars')` raises `NotImplementedError`, or `df.hvplot.bars()` raises `AttributeError: 'hvPlotTabular' object has no attribute 'bars'`.

**Cause**: The kind name is misspelled or not supported for that data type.

**Fix**: Use one of the supported names. These are the kinds hvPlot 0.13 knows:

```python
from hvplot.converter import HoloViewsConverter

print(sorted(HoloViewsConverter._kind_mapping))
# ['area', 'bar', 'barh', 'bivariate', 'box', 'contour', 'contourf', 'dataset',
#  'density', 'errorbars', 'heatmap', 'hexbin', 'hist', 'image', 'kde', 'labels',
#  'line', 'ohlc', 'paths', 'points', 'polygons', 'quadmesh', 'rgb', 'scatter',
#  'step', 'table', 'trimesh', 'vectorfield', 'violin']
```

`_kind_mapping` is internal and may change. Use it to check names while debugging, not in application code. Gridded kinds (`image`, `quadmesh`, `contour`) expect xarray data.

## Misspelled Keyword Is Ignored

**Symptom**: A styling keyword has no effect, and the log shows a warning instead of an error:

```
WARNING:param.main: colour option not found for line plot with bokeh; similar options include: ['color', 'color', 'bgcolor']
```

**Cause**: hvPlot passes unknown keywords through as plot options. When none matches, it logs a warning and carries on.

**Fix**: Read the suggestion in the warning, or list the valid options for a kind with `hvplot.help`.

```python
import numpy as np
import pandas as pd
import hvplot
import hvplot.pandas  # noqa: F401

hvplot.help('line', docstring=False, generic=False, style=True)  # prints the style options

df = pd.DataFrame({'x': np.arange(10), 'y': np.random.rand(10)})
plot = df.hvplot.line('x', 'y', color='red', line_width=3)
```

## `DataError: Supplied data does not contain specified dimensions`

**Symptom**: `DataError: Supplied data does not contain specified dimensions, the following dimensions were not found: ['zz']`.

**Cause**: A column name passed as `x`, `y`, `by`, `c`, or `hover_cols` does not exist. Names are case-sensitive.

**Fix**: Check `df.columns`. If the column you want is the index, either call `reset_index()` or use `use_index=True` (the default when `x` is omitted).

```python
import numpy as np
import pandas as pd
import hvplot.pandas  # noqa: F401

df = pd.DataFrame({'Date': pd.date_range('2024-01-01', periods=10), 'Value': np.random.rand(10)})
print(list(df.columns))
plot = df.set_index('Date').hvplot.line(y='Value')  # x comes from the index
```

## `groupby` Failures

**Symptom**: One of these:
- `ValueError: The supplied groupby dimension(s) ['zz'] could not be found, expected one or more of: ['x', 'y', 'g', 'n']`
- The widget for `groupby` does not appear, and only one group is shown.
- A numeric column produces a slider when you wanted a dropdown.

**Cause**: `groupby` returns a `DynamicMap` whose widgets are created by Panel when the object is displayed. `hv.render()` or a static export only draws the first group. `by` is different: it overlays every group in a single plot and needs no widgets.

**Fix**: Display through Panel, choose the widget type explicitly, or use `dynamic=False` to precompute every group into a `HoloMap` that can be embedded in static HTML.

```python
import numpy as np
import pandas as pd
import hvplot.pandas  # noqa: F401
import panel as pn

df = pd.DataFrame({
    'x': np.tile(np.arange(10), 4),
    'y': np.random.rand(40),
    'station': np.repeat(['A', 'B', 'C', 'D'], 10),
    'level': np.repeat([1, 2, 3, 4], 10),
})

overlay = df.hvplot.line('x', 'y', by='station')                 # all groups in one plot
explorer = df.hvplot.line(
    'x', 'y', groupby='level',
    widgets={'level': pn.widgets.Select}, widget_location='top',  # dropdown, not slider
)
app = pn.panel(explorer)                                          # renders the widget
static = df.hvplot.line('x', 'y', groupby='station', dynamic=False)  # HoloMap
```

Keep `groupby` columns low-cardinality. Each unique value becomes a widget option, and with `dynamic=False` each one becomes a precomputed plot.

## Slow or Unresponsive Plot with Large Data

**Symptom**: The browser hangs or the notebook output is very large.

**Cause**: Every point is sent to the browser.

**Fix**: Pass `rasterize=True` so Datashader aggregates on the server. See [Datashader Troubleshooting](./datashader-troubleshooting.md).

```python
import numpy as np
import pandas as pd
import hvplot.pandas  # noqa: F401

df = pd.DataFrame({'x': np.random.randn(1_000_000), 'y': np.random.randn(1_000_000)})
plot = df.hvplot.points('x', 'y', rasterize=True, cnorm='eq_hist', cmap='fire')
```

## Related

- [HoloViews Troubleshooting](./holoviews-troubleshooting.md)
- [HoloViews Patterns](../patterns/holoviews-patterns.md)
- [hvPlot user guide](https://hvplot.holoviz.org/user_guide/index.html)
- [hvPlot API reference](https://hvplot.holoviz.org/ref/index.html)
