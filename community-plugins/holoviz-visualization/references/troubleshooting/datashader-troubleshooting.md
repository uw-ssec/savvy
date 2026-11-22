# Datashader Troubleshooting

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions.

## Overview

Datashader problems fall into four groups: aggregation fails because a column has the wrong dtype, the image is blank, the colors hide the structure in the data, or the pipeline is slow or runs out of memory. The examples call Datashader directly (`ds.Canvas`) and through HoloViews (`rasterize`), because many fixes differ between the two.

**Load when**: A Datashader aggregation raises an error, a rasterized plot is blank or washed out, or large-data rendering is slow or memory-bound.

## `TypeError: Cannot interpret '<StringDtype(na_value=nan)>' as a data type`

**Symptom**: `cvs.points(...)` or `ds.by('cat')` raises this `TypeError`.

**Cause**: Datashader aggregates numeric arrays with Numba. pandas 3 reads text columns as the `str` dtype by default, and Datashader cannot use those columns as coordinates, as values to aggregate, or as categories.

**Fix**: Make coordinates and aggregated values numeric, and make category columns `category` dtype.

```python
import numpy as np
import pandas as pd
import datashader as ds

n = 10_000
df = pd.DataFrame({
    'x': np.random.randn(n).astype(str),               # numbers read as text
    'y': np.random.randn(n),
    'kind': np.random.choice(['car', 'bus', 'bike'], n),
})

df['x'] = pd.to_numeric(df['x'])
df['kind'] = df['kind'].astype('category')

cvs = ds.Canvas(plot_width=300, plot_height=300)
agg = cvs.points(df, 'x', 'y', agg=ds.by('kind', ds.count()))
print(agg.dims, list(agg.coords['kind'].values))
```

With Dask, a column that is not categorical raises `ValueError: input must be categorical`. Convert it with `ddf['kind'].astype('category')` or `ddf.categorize(columns=['kind'])` before aggregating.

## `ValueError: x must be real`

**Symptom**: `cvs.points(df, 'time', 'value')` or `cvs.line(...)` raises `ValueError: x must be real` (or `x columns must be real`) on a datetime column.

**Cause**: `ds.Canvas` only accepts real-valued coordinates, and `datetime64` columns are rejected.

**Fix**: Convert the timestamps to integers for direct Datashader use, or go through HoloViews, which converts datetimes for you and keeps date-formatted axes.

```python
import numpy as np
import pandas as pd
import datashader as ds
import holoviews as hv
from holoviews.operation.datashader import rasterize

hv.extension('bokeh')

ts = pd.DataFrame({
    'time': pd.date_range('2024-01-01', periods=100_000, freq='s'),
    'value': np.random.randn(100_000).cumsum(),
})

# Direct Datashader: integer nanoseconds since the epoch
numeric = ts.assign(time=ts['time'].astype('datetime64[ns]').astype('int64'))
agg = ds.Canvas(plot_width=400, plot_height=200).line(numeric, 'time', 'value')

# HoloViews: datetime axis handled for you
plot = rasterize(hv.Curve(ts, 'time', 'value'))
```

## `KeyError: "['value'] not in index"`

**Symptom**: An aggregator such as `ds.mean('value')` raises `KeyError: "['value'] not in index"`.

**Cause**: The column named in the aggregator does not exist in the DataFrame.

**Fix**: Check `df.columns`. With HoloViews, also declare the column as a value dimension, so it is kept in the element's data: `hv.Points(df, ['x', 'y'], ['value'])`.

## Blank or Empty Image

**Symptom**: The output is fully transparent, or a rasterized HoloViews plot shows nothing.

**Cause**: Usually one of these:
1. `x_range`/`y_range` do not overlap the data, for example ranges in lon/lat for data in Web Mercator meters.
2. A `mean`, `max`, or other reduction returns `NaN` in every empty pixel, and `NaN` shades as transparent. With very sparse data, almost every pixel is empty.
3. Points are so sparse that single pixels are invisible at screen size.

**Fix**: Inspect the aggregate before shading, then spread sparse points.

```python
import numpy as np
import pandas as pd
import datashader as ds
import datashader.transfer_functions as tf

df = pd.DataFrame({'x': np.random.randn(2_000), 'y': np.random.randn(2_000)})

wrong = ds.Canvas(plot_width=200, plot_height=200, x_range=(100, 200), y_range=(100, 200))
print(int(wrong.points(df, 'x', 'y').sum()))     # 0: range misses the data

cvs = ds.Canvas(plot_width=200, plot_height=200)  # ranges computed from the data
agg = cvs.points(df, 'x', 'y')
print(int(agg.sum()), int((agg > 0).sum()))      # points counted, pixels hit

img = tf.dynspread(tf.shade(agg), threshold=0.5, max_px=3)
```

In HoloViews, use `dynspread(rasterize(points))`, or pass `dynspread=True` to hvPlot.

## `ValueError: Unexpected option 'cmap' for RGB type`

**Symptom**: `datashade(points).opts(cmap='fire')` fails with `Unexpected option 'cmap' for RGB type across all extensions. No similar options found.`

**Cause**: `datashade` shades in Python and returns an `hv.RGB` image. The colors are already fixed, so the plot has no colormap to change and no colorbar. It has no per-pixel aggregate values to hover over either, unless you add a `selector` (see the HoloViews guide to interactive hover for big data).

**Fix**: Prefer `rasterize`, which returns an `hv.Image` of aggregate values that Bokeh colormaps in the browser. If you need `datashade`, pass `cmap` to the operation itself.

```python
import numpy as np
import pandas as pd
import holoviews as hv
from holoviews.operation.datashader import datashade, rasterize

hv.extension('bokeh')

df = pd.DataFrame({'x': np.random.randn(500_000), 'y': np.random.randn(500_000)})
points = hv.Points(df, ['x', 'y'])

image = rasterize(points).opts(cmap='fire', cnorm='eq_hist', colorbar=True, tools=['hover'])
rgb = datashade(points, cmap=['lightblue', 'darkblue'])
```

## Colors Hide the Structure

**Symptom**: The plot is a single bright blob with everything else in the darkest color, or it looks uniformly flat.

**Cause**: Counts in large data are heavily skewed. A linear color scale spends the whole colormap on a few dense pixels.

**Fix**: Change the normalization. The keyword differs by API: HoloViews and hvPlot use `cnorm` (`'linear'`, `'log'`, `'eq_hist'`), while `tf.shade` uses `how`. Passing `cnorm` to `tf.shade` raises `TypeError: shade() got an unexpected keyword argument 'cnorm'`.

```python
import numpy as np
import pandas as pd
import colorcet as cc
import datashader as ds
import datashader.transfer_functions as tf

df = pd.DataFrame({'x': np.random.standard_cauchy(200_000), 'y': np.random.randn(200_000)})
cvs = ds.Canvas(plot_width=300, plot_height=300, x_range=(-10, 10), y_range=(-4, 4))
agg = cvs.points(df, 'x', 'y')

linear = tf.shade(agg, cmap=cc.fire, how='linear')   # dominated by the core
equalized = tf.shade(agg, cmap=cc.fire, how='eq_hist')
logged = tf.shade(agg, cmap=cc.fire, how='log')
```

Two related errors from `tf.shade`:
- `ValueError: Unknown color: 'notacmap'`. A string `cmap` is read as a single color name. Pass a list of colors or a palette such as `colorcet.fire`.
- `ValueError: Insufficient colors provided (1) for the categorical fields available (2)`. A categorical aggregate needs a `color_key` entry for every category.

## Slow First Render, Then Fast

**Symptom**: The first aggregation takes noticeably longer than later ones (in testing, about 0.3 s against 1 ms for the same 10K points).

**Cause**: Datashader compiles its aggregation kernels with Numba on first use for each combination of glyph, reduction, and dtype.

**Fix**: This is expected. In a served app, warm the kernels at startup with a tiny aggregate that uses the same glyph, reduction, and dtypes, so the first user does not pay the compile cost.

## Slow Interaction or Memory Errors

**Symptom**: Each zoom takes seconds, the process uses far more memory than expected, or it is killed with `MemoryError`.

**Cause**: The whole dataset is re-aggregated on every zoom or pan, so its size and dtype dominate the cost. Categorical aggregates (`ds.by`) allocate one layer per category (height × width × categories).

**Fix**:
- Load only the columns you plot, and downcast to `float32` where precision allows.
- Store data as Parquet and load with Dask when it does not fit in memory; call `.persist()` once if it does fit, so partitions are not re-read on every zoom.
- Keep categorical aggregates to a modest number of categories; group rare ones into an "other" category.
- Reduce `width`/`height` of the plot, or set `pixel_ratio=1` on `rasterize` for high-DPI screens.

```python
import numpy as np
import pandas as pd
import dask.dataframe as dd
import holoviews as hv
from holoviews.operation.datashader import rasterize

hv.extension('bokeh')

pdf = pd.DataFrame({
    'x': np.random.randn(1_000_000).astype('float32'),
    'y': np.random.randn(1_000_000).astype('float32'),
})
ddf = dd.from_pandas(pdf, npartitions=8).persist()   # in practice: dd.read_parquet(path, columns=['x', 'y'])

plot = rasterize(hv.Points(ddf, ['x', 'y']), pixel_ratio=1).opts(width=600, height=400)
```

See [Performance Patterns](../patterns/performance-patterns.md) for caching and loading strategies.

## Related

- [Datashader Patterns](../patterns/datashader-patterns.md)
- [Performance Best Practices](../best-practices/performance.md)
- [Large Data in HoloViews](https://holoviews.org/user_guide/Large_Data.html)
- [Interactive hover for big data](https://holoviews.org/user_guide/Interactive_Hover_for_Big_Data.html)
- [Datashader getting started](https://datashader.org/getting_started/index.html)
- [Datashader performance guide](https://datashader.org/user_guide/Performance.html)
