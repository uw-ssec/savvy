# Performance Best Practices

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions.

## Overview

Most slow HoloViz apps have one of four causes. They send too much data to the browser, recompute work on every interaction, load everything when the page opens, or run blocking code on the server thread. This file covers the practice that fixes each one.

**Load when**: An app is slow to load or to respond, the browser struggles with a plot, or you are about to plot more than ~100K points.

## 1. Measure Before Optimizing

Find where the time goes before you change anything. Profile in the same environment the app runs in.

```python
import cProfile
import pstats

import numpy as np
import pandas as pd

def build_summary(n=200_000):
    df = pd.DataFrame({'g': np.random.randint(0, 50, n), 'v': np.random.randn(n)})
    return df.groupby('g')['v'].agg(['mean', 'std'])

profiler = cProfile.Profile()
profiler.enable()
build_summary()
profiler.disable()
pstats.Stats(profiler).sort_stats('cumulative').print_stats(5)
```

For a served app, the `--profiler` flag on `panel serve` (`pyinstrument`, `snakeviz` or `memray`, whichever is installed) profiles session creation. `--admin` adds a `/admin` page showing sessions, memory and CPU over time.

```bash
panel serve app.py --admin --profiler pyinstrument
```

## 2. Reduce Data Before It Reaches the Browser

Bokeh serializes every point it draws. Past a few hundred thousand points, rasterize on the server and send an image instead.

| Rows | Approach |
|------|----------|
| < 10K | Plot directly |
| 10K – 100K | Plot directly; prefer `Scatter`/`Points` over many glyph overlays |
| > 100K | `rasterize=True` (hvPlot) or `rasterize()` (HoloViews) |
| Out of memory | Dask or a Parquet subset, then rasterize |

```python
import holoviews as hv
import hvplot.pandas  # noqa: F401  registers .hvplot
import numpy as np
import pandas as pd

hv.extension('bokeh')

n = 1_000_000
df = pd.DataFrame({'x': np.random.randn(n), 'y': np.random.randn(n)})

# ✅ Good: server-side aggregation, re-rendered on zoom
plot = df.hvplot.points('x', 'y', rasterize=True, cnorm='eq_hist', cmap='viridis')

# ❌ Bad: one million glyphs serialized to the browser
# df.hvplot.points('x', 'y')
```

Prefer `rasterize` over `datashade`. `rasterize` sends aggregated values, so Bokeh applies the colormap. That gives you a colorbar, hover on the counts, and `clim`/`cnorm` control. `datashade` sends a pre-shaded RGB image and is only worth it when you need Datashader-specific shading (for example, categorical color mixing). See [Datashader Patterns](../patterns/datashader-patterns.md).

Also reduce columns and precision before plotting:

```python
import numpy as np
import pandas as pd

df = pd.DataFrame({
    'x': np.random.randn(100_000),
    'y': np.random.randn(100_000),
    'label': np.random.choice(['a', 'b', 'c'], 100_000),
    'unused': np.random.randn(100_000),
})

# ✅ Good: keep only what the plot needs, downcast, use categoricals
slim = df[['x', 'y', 'label']].astype({'x': 'float32', 'y': 'float32', 'label': 'category'})
print(df.memory_usage(deep=True).sum() // 1024, '->', slim.memory_usage(deep=True).sum() // 1024, 'KiB')
```

## 3. Cache Expensive Work

Cache data loading and heavy transforms so the work runs once per server process, not once per session or interaction.

```python
import numpy as np
import pandas as pd
import panel as pn

pn.extension()

@pn.cache(max_items=10, ttl=3600)
def load_data(region: str) -> pd.DataFrame:
    # Stand-in for a slow query or file read
    rng = np.random.default_rng(abs(hash(region)) % 2**32)
    return pd.DataFrame({'value': rng.normal(size=10_000)})

region = pn.widgets.Select(label='Region', options=['north', 'south'])
summary = pn.bind(lambda r: load_data(r).describe(), region)
app = pn.Column(region, pn.pane.DataFrame(summary))
```

- `pn.cache` memoizes by argument; `ttl`, `max_items`, `policy` and `to_disk=True` (requires `diskcache`) control eviction.
- `pn.state.as_cached(key, fn)` caches a single value under a key you choose.
- `pn.state.cache` is a plain dict shared across sessions for ad hoc use.
- Cached objects are shared between sessions, so never mutate them in place. Copy before you modify.
- `functools.lru_cache` also works, but it can't expire entries and won't clear when you call `pn.state.clear_caches()`.

## 4. Load Lazily

Render the shell of the page first, then fill in slow components.

```python
import time

import panel as pn

pn.extension(defer_load=True, loading_indicator=True)

def slow_report():
    time.sleep(0.1)  # stand-in for slow work
    return pn.pane.Markdown('## Report ready')

# The function runs after the page has loaded, with a spinner in its place
app = pn.Column('# Dashboard', slow_report)
```

- `pn.extension(defer_load=True)` defers every bound function. To defer just one, wrap it as `pn.panel(fn, defer_load=True)`.
- `pn.state.onload(callback)` runs a callback once the page is displayed. Use it to kick off data loading.
- Put rarely used views in `pn.Tabs(..., dynamic=True)`, so a tab renders only when it is opened.

## 5. Avoid Redundant Updates

Every parameter change can trigger a re-render. Batch changes, and update existing objects instead of replacing them.

```python
import holoviews as hv
import numpy as np
import panel as pn

pn.extension()
hv.extension('bokeh')

x = np.linspace(0, 10, 200)
freq = pn.widgets.FloatSlider(label='Frequency', start=0.5, end=5, value=1)

# ✅ Good: DynamicMap updates the existing Bokeh plot in place
def curve(freq):
    return hv.Curve((x, np.sin(freq * x))).opts(width=500)

dmap = hv.DynamicMap(pn.bind(curve, freq=freq))
app = pn.Column(freq, dmap)

# ✅ Good: apply several changes as one update
md = pn.pane.Markdown('a')
table = pn.pane.Markdown('b')
with pn.io.hold():
    md.object = 'updated'
    table.object = 'updated too'
```

- Use `value_throttled` (or `pn.config.throttled = True`) on sliders when the callback is expensive. It fires on release instead of on every drag step.
- Keep one `hv.DynamicMap` and drive it with widgets or streams, as above. A bound function that returns a new element (or a new `DynamicMap`) on every change makes Panel replace and re-render the whole plot.
- With `@param.depends`, list only the parameters the method actually uses.

## 6. Keep the Server Responsive

A blocking callback freezes every session handled by that thread.

```bash
# Multiple threads: callbacks run concurrently within one process
panel serve app.py --num-threads 4

# Multiple processes: isolates sessions (not available on Windows)
panel serve app.py --num-procs 2

# Import heavy modules / warm caches before the first user arrives
panel serve app.py --warm
```

Async callbacks (`async def`) let I/O-bound work yield to other sessions without needing threads. Push CPU-bound work into a thread or process pool, or precompute it.

## Performance Checklist

- [ ] Profiled before optimizing
- [ ] Data > 100K points is rasterized
- [ ] Only needed columns, downcast dtypes
- [ ] Data loading and heavy transforms wrapped in `pn.cache`
- [ ] Slow components deferred (`defer_load`, `onload`, dynamic tabs)
- [ ] Expensive sliders use `value_throttled`
- [ ] Server started with threads/processes sized to the workload

## Related

- [Performance Patterns](../patterns/performance-patterns.md) — caching, lazy loading and async code recipes
- [Datashader Patterns](../patterns/datashader-patterns.md)
- [Datashader Troubleshooting](../troubleshooting/datashader-troubleshooting.md)
- [Panel: Improve performance](https://panel.holoviz.org/how_to/performance/index.html)
- [Panel: Caching](https://panel.holoviz.org/how_to/caching/index.html)
- [HoloViews: Large data](https://holoviews.org/user_guide/Large_Data.html)
