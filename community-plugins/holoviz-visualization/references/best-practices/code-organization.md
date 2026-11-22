# Code Organization Best Practices

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions.

## Overview

A HoloViz app stays maintainable when data access, transformation and presentation live in separate modules, and each UI piece is a small component you can test. This file covers project structure, modularity and naming.

**Load when**: Starting a new HoloViz project, or splitting a single-file notebook or app that has grown too large.

## 1. Project Structure

Start with a package, not a folder of scripts. Keep the served entry point thin.

```text
my-dashboard/
├── pixi.toml / pyproject.toml   # dependencies, pinned
├── src/my_dashboard/
│   ├── __init__.py
│   ├── data.py          # loading and caching (no Panel imports)
│   ├── transforms.py    # pure functions: DataFrame in, DataFrame out
│   ├── plots.py         # functions returning HoloViews/hvPlot objects
│   ├── components/      # pn.viewable.Viewer subclasses
│   │   ├── filters.py
│   │   └── summary.py
│   └── app.py           # assembles components into a template
├── apps/
│   └── main.py          # `from my_dashboard.app import create_app; create_app().servable()`
├── tests/
└── notebooks/           # exploration only; nothing imports from here
```

Layer rules:

| Layer | May import | Must not import |
|-------|-----------|-----------------|
| `data`, `transforms` | pandas, numpy, xarray | panel, holoviews |
| `plots` | holoviews, hvplot, transforms | panel widgets |
| `components` | panel, param, plots, data | — |
| `app` | components | — |

With these rules, transforms and plots can be tested and reused in notebooks without a server.

## 2. Build Components as `Viewer` Classes

`pn.viewable.Viewer` gives a `Parameterized` class a `__panel__` method, so it can go into any layout like a built-in component. Parameters are the component's public API.

```python
import holoviews as hv
import numpy as np
import pandas as pd
import panel as pn
import param
from panel.viewable import Viewer

pn.extension()
hv.extension('bokeh')

def load_sales() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    return pd.DataFrame({
        'day': pd.date_range('2025-01-01', periods=90),
        'region': rng.choice(['north', 'south'], 90),
        'revenue': rng.gamma(2, 100, 90),
    })

def revenue_plot(df: pd.DataFrame) -> hv.Curve:
    return hv.Curve(df, 'day', 'revenue').opts(responsive=True, min_height=250)

class RegionFilter(Viewer):
    region = param.Selector(objects=['north', 'south'])

    def __panel__(self):
        return pn.widgets.RadioButtonGroup.from_param(self.param.region)

class RevenueView(Viewer):
    data = param.DataFrame()
    region = param.String(default='north', allow_refs=True)  # accepts another parameter as its value

    @param.depends('data', 'region')
    def _plot(self):
        return revenue_plot(self.data[self.data.region == self.region])

    def __panel__(self):
        return pn.panel(self._plot)

def create_app():
    data = load_sales()
    filt = RegionFilter()
    view = RevenueView(data=data, region=filt.param.region)  # live reference, stays in sync
    return pn.template.FastListTemplate(title='Sales', sidebar=[filt], main=[view])

app = create_app()

# The reference keeps the two components in sync
filt = RegionFilter()
view = RevenueView(data=load_sales(), region=filt.param.region)
filt.region = 'south'
assert view.region == 'south'
```

- Pass dependencies in through parameters (`data=`). Don't load them inside the component.
- Link components by passing one component's parameter as another's value (`region=filt.param.region`). The receiving parameter needs `allow_refs=True` (Param 2.1+). The value then tracks the source, so you don't need a manual watcher.
- A `create_app()` factory builds a fresh app per session and is easy to call from tests.

## 3. Keep Functions Small and Pure

```python
import pandas as pd

# ✅ Good: pure transform, trivially testable
def top_n(df: pd.DataFrame, column: str, n: int = 5) -> pd.DataFrame:
    return df.nlargest(n, column)

# ❌ Bad: reads a widget, mutates global state, returns nothing
# def update():
#     global df
#     df = df.nlargest(slider.value, 'revenue')
#     plot_pane.object = df.hvplot()
```

## 4. Naming Conventions

| Thing | Convention | Example |
|-------|-----------|---------|
| Modules | `snake_case`, by responsibility | `transforms.py`, not `utils2.py` |
| `Parameterized` / `Viewer` classes | `PascalCase` noun | `RevenueView`, `RegionFilter` |
| Parameters | `snake_case`, user-facing meaning | `date_range`, not `dr` |
| View methods | noun or `view_*` | `plot`, `view_table` |
| Side-effect watchers | leading underscore, verb | `_update_total` |
| Plot functions | `*_plot` returning an element | `revenue_plot(df)` |
| Constants | `UPPER_SNAKE` with a comment for magic values | `MAX_POINTS = 100_000  # rasterize above` |

Set `label=` on parameters when the UI caption should differ from the Python name. Don't rename the parameter to make the UI read better.

## 5. Configuration

- Keep environment-specific values (paths, URLs, credentials) in environment variables or a config file read in `data.py`. Never hard-code secrets.
- Put shared HoloViews option defaults in one place (`plots.py`, via `hv.opts.defaults(...)`) and call `pn.extension(...)` once, in the entry point.

```python
import os

DATA_URL = os.environ.get('SALES_DATA_URL', 'sales.parquet')  # default for local dev
```

## 6. Notebooks vs. Modules

- Explore in notebooks. Once code is reused, move it into `src/`, and import it back into the notebook.
- A Panel app in a notebook can be served unchanged with `panel serve notebook.ipynb`, but production apps should be `.py` files: easier to review, diff and test.

## Related

- [Panel Best Practices](./panel.md)
- [Testing Best Practices](./testing.md)
- [Documentation Best Practices](./documentation.md)
- [Panel: Build components with Viewer](https://panel.holoviz.org/how_to/custom_components/custom_viewer.html)
