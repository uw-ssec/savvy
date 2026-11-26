# Performance Patterns

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions.

## Overview

Patterns for keeping HoloViz apps responsive: caching, lazy loading, sending less data to the browser, batching updates, and moving slow work off the main event loop. Measure first: most slow apps load data in every session or send too many rows to the browser.

**Load when**: Optimizing slow applications or handling large data

## Pattern 1: Data Caching

**When to use**: The same expensive load or computation runs for every session or every widget change.

```python
import time

import numpy as np
import pandas as pd
import panel as pn

pn.extension()


@pn.cache(max_items=16, ttl=600)  # LRU, entries expire after 10 minutes
def load_region(region: str) -> pd.DataFrame:
    time.sleep(0.5)  # stands in for a slow query
    rng = np.random.default_rng(len(region))
    return pd.DataFrame({"day": np.arange(365), "sales": rng.gamma(2, 50, 365)})


start = time.perf_counter()
load_region("north")              # slow: computed
load_region("north")              # fast: from the cache, shared by all sessions
print(f"{time.perf_counter() - start:.2f}s for two calls")

# One shared object for the whole server process, created on first use.
lookup = pn.state.as_cached("lookup-table", lambda: {i: f"id-{i}" for i in range(10_000)})

region = pn.widgets.Select(label="Region", options=["north", "south"])
app = pn.Column(region, pn.bind(lambda r: pn.pane.DataFrame(load_region(r).describe()), region))
app.servable()
```

- `pn.cache(to_disk=True)` persists across restarts (needs `diskcache`); `per_session=True` keeps separate entries for each browser session (each tab or visit), not per signed-in user.
- Arguments are hashed, so DataFrames and arrays work as keys. Clear with `load_region.clear()` or `pn.state.clear_caches()`.
- Return values are shared, so don't mutate a cached DataFrame in place.

## Pattern 2: Lazy Loading

**When to use**: The page should appear immediately, and some content isn't visible at first.

```python
import time

import numpy as np
import pandas as pd
import panel as pn
import hvplot.pandas  # noqa: F401

pn.extension()


def slow_plot():
    time.sleep(0.5)
    df = pd.DataFrame(np.random.default_rng(0).normal(size=(1_000, 2)), columns=["a", "b"])
    return df.hvplot.scatter("a", "b", height=300)


# Render the layout first, then fill this in once the page has loaded.
deferred = pn.panel(slow_plot, defer_load=True)

# dynamic=True renders only the active tab. Wrap the function as lazy as well,
# or it is still called up front even though its tab isn't shown.
tabs = pn.Tabs(
    ("Summary", "Quick text"),
    ("Details", pn.param.ParamFunction(slow_plot, lazy=True)),
    dynamic=True,
)

# Run setup code after the page is shown, e.g. to fetch data for a placeholder.
status = pn.pane.Markdown("Loading data...")


def on_load():
    status.object = f"Loaded {len(pd.DataFrame({'x': range(10_000)})):,} rows"


pn.state.onload(on_load)

app = pn.Column(status, deferred, tabs)
app.servable()
```

Set `pn.config.defer_load = True` (or `pn.extension(defer_load=True)`) to defer every bound function in the app.

## Pattern 3: Send Less Data to the Browser

**When to use**: Tables or plots have more rows than a user can see.

```python
import numpy as np
import pandas as pd
import holoviews as hv
import panel as pn
from holoviews.operation import decimate
from holoviews.operation.datashader import rasterize

hv.extension("bokeh")
pn.extension("tabulator")

rng = np.random.default_rng(1)
big = pd.DataFrame({"x": rng.normal(size=500_000), "y": rng.normal(size=500_000)})

# Tables: page on the server. Only the visible page goes to the browser.
table = pn.widgets.Tabulator(big, pagination="remote", page_size=50, height=400)

# Plots: aggregate (Datashader) or subsample (decimate) instead of sending every point.
image = rasterize(hv.Points(big)).opts(cmap="blues", width=400, height=400)
sample = decimate(hv.Points(big), max_samples=5_000).opts(width=400, height=400, tools=["hover"])

app = pn.Column(pn.Row(image, sample), table)
app.servable()
```

| Rows in view | Approach |
|--------------|----------|
| < 10K | Plot directly |
| 10K – 100K | `decimate`, or Bokeh's WebGL backend: `.opts(backend_opts={"plot.output_backend": "webgl"})` |
| > 100K | `rasterize` / `datashade`; see [Datashader Patterns](./datashader-patterns.md) |
| Larger than memory | Dask DataFrame + Datashader, or query a database per view |

## Pattern 4: Batching and Throttling Updates

**When to use**: One user action changes several components, or a slider fires too many expensive callbacks.

```python
import numpy as np
import pandas as pd
import panel as pn

pn.extension()

indicators = [pn.indicators.Number(label=f"KPI {i}", value=0) for i in range(5)]
table = pn.pane.DataFrame(pd.DataFrame())


def refresh(event=None):
    values = np.random.default_rng().integers(0, 100, len(indicators))
    with pn.io.hold():  # send all changes to the browser as one message
        for ind, v in zip(indicators, values):
            ind.value = int(v)
        table.object = pd.DataFrame({"kpi": range(len(values)), "value": values})


button = pn.widgets.Button(label="Refresh", color="primary")
button.on_click(refresh)

# Bind to value_throttled so the callback runs on release, not on every drag step.
slider = pn.widgets.IntSlider(label="Window", start=1, end=100, value=10)
expensive = pn.bind(lambda w: f"Recomputed with window={w}", slider.param.value_throttled)

app = pn.Column(button, pn.Row(*indicators), table, slider, expensive)
app.servable()
refresh()
```

`pn.config.throttled = True` makes all sliders report only on release.

## Pattern 5: Async Callbacks

**When to use**: Callbacks wait on I/O (HTTP, databases, files) and other users shouldn't wait with them.

```python
import asyncio
import html

import panel as pn

pn.extension()

query = pn.widgets.TextInput(label="Search", value="holoviz")


async def search(term):
    # Stands in for an awaitable I/O call, e.g. `await httpx.AsyncClient().get(url)`.
    await asyncio.sleep(0.5)
    # The search term is user input: escape it before it reaches Markdown.
    return pn.pane.Markdown(f"Results for **{html.escape(term)}**")


async def progress(term):
    # Async generators stream intermediate output.
    for pct in (25, 50, 75):
        yield pn.indicators.Progress(value=pct, width=200)
        await asyncio.sleep(0.1)
    yield pn.pane.Markdown(f"Finished processing **{html.escape(term)}**")


app = pn.Column(query, pn.bind(search, query), pn.bind(progress, query))
app.servable()
```

Async helps only when the code awaits. A CPU-bound function marked `async` still blocks the event loop; use Pattern 6 for that.

## Pattern 6: Threads and Web Worker Offloading

**When to use**: CPU-heavy or blocking work (model fits, large aggregations) would freeze the app.

Server side, give Panel a thread pool so callbacks from different sessions run concurrently:

```bash
panel serve app.py --num-threads 4        # or pn.config.nthreads = 4 in code
panel serve app.py --num-procs 4          # separate processes, for CPU-bound work
```

Threads help when the work releases the GIL (NumPy, pandas, Datashader/Numba, I/O). For pure-Python CPU work, use `--num-procs` or a process pool.

Browser side, `panel convert` compiles an app to run in Pyodide. The `pyodide-worker` target runs Python in a Web Worker, so the page stays responsive while Python works:

```bash
panel convert app.py --to pyodide-worker --out dist/
```

The converted app needs no server, but it runs only packages available for Pyodide, and every visitor's browser downloads Python and the libraries on first load.

Within one session, mark the slow part with a loading indicator so users can see it's working:

```python
import time

import panel as pn

pn.extension(loading_indicator=True)  # bound functions show a spinner while they run

n = pn.widgets.IntSlider(label="Size", start=1, end=5, value=2)


def heavy(n):
    time.sleep(0.2 * n)  # blocking work
    return f"Done with size {n}"


app = pn.Column(n, pn.panel(pn.bind(heavy, n)))
app.servable()
```

## Related

- [Datashader Patterns](./datashader-patterns.md): rendering large data
- [Panel Patterns](./panel-patterns.md): streaming updates
- [Performance Best Practices](../best-practices/performance.md)
- [Panel performance how-to](https://panel.holoviz.org/how_to/performance/index.html), [caching](https://panel.holoviz.org/how_to/caching/index.html) and [concurrency](https://panel.holoviz.org/how_to/concurrency/index.html)
