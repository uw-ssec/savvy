# Testing Best Practices

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions; the test functions were also run with pytest.

## Overview

Almost everything in a HoloViz app can be tested without a browser. Transforms are plain functions, plots are inspectable objects, and components are `Parameterized` classes you can drive from Python. Save browser tests for the few behaviors that only exist in JavaScript. This file covers unit tests, integration tests, and how to approach visual regression.

**Load when**: Writing tests for a HoloViz project, or deciding what to test at which level.

## Test Pyramid for HoloViz Apps

| Level | What | Tooling | Speed |
|-------|------|---------|-------|
| Unit | Transforms, plot functions, `Parameterized` logic | pytest | ms |
| Integration | Component wiring, rendering to Bokeh models, serving | pytest, `hv.render`, `pn.serve` | seconds |
| UI (browser) | JS-only behavior: client-side interactions, layout | pytest + Playwright | slow |
| Visual | Pixel output of key figures | Image comparison (see below) | slow |

Most tests belong at the unit level.

```bash
pixi add pytest      # or: conda install -c conda-forge pytest / pip install pytest
pixi run pytest tests/
```

## 1. Unit-Test Transforms and Plot Functions

Test the data a plot receives and the dimensions it declares, not its pixels.

```python
import holoviews as hv
import numpy as np
import pandas as pd

def daily_totals(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby('day', as_index=False)['amount'].sum()

def totals_plot(df: pd.DataFrame) -> hv.Curve:
    return hv.Curve(daily_totals(df), 'day', 'amount')

def test_daily_totals_sums_per_day():
    df = pd.DataFrame({'day': [1, 1, 2], 'amount': [1.0, 2.0, 5.0]})
    assert daily_totals(df)['amount'].tolist() == [3.0, 5.0]

def test_totals_plot_declares_dimensions():
    df = pd.DataFrame({'day': [1, 2], 'amount': [1.0, 2.0]})
    plot = totals_plot(df)
    assert isinstance(plot, hv.Curve)
    assert [d.name for d in plot.kdims] == ['day']
    assert [d.name for d in plot.vdims] == ['amount']
    np.testing.assert_array_equal(plot.dimension_values('amount'), [1.0, 2.0])

def test_empty_input_gives_empty_plot():
    plot = totals_plot(pd.DataFrame({'day': [], 'amount': []}))
    assert len(plot) == 0
```

Always test the empty-data case. A filter that removes every row is the most common runtime failure in dashboards.

## 2. Test `Parameterized` Logic Directly

Set parameters and assert on the results. No widgets are needed.

```python
import param
import pytest

class Pricing(param.Parameterized):
    quantity = param.Integer(default=1, bounds=(1, 1000))
    unit_price = param.Number(default=10.0, bounds=(0, None))
    total = param.Number(default=10.0, constant=True)

    @param.depends('quantity', 'unit_price', watch=True)
    def _update_total(self):
        with param.edit_constant(self):
            self.total = self.quantity * self.unit_price

def test_total_updates_when_inputs_change():
    p = Pricing()
    p.param.update(quantity=3, unit_price=2.5)
    assert p.total == 7.5

def test_bounds_are_enforced():
    with pytest.raises(ValueError):
        Pricing(quantity=0)
```

## 3. Test Widget Wiring Without a Browser

Changing a widget's `value` in Python triggers the same callbacks as a user in the browser.

```python
import panel as pn

def build():
    n = pn.widgets.IntSlider(label='n', start=1, end=10, value=2)
    out = pn.panel(pn.bind(lambda n: f'n squared is {n ** 2}', n))
    return n, out

def test_slider_drives_output():
    n, out = build()
    n.value = 3
    assert 'n squared is 9' in out._pane.object  # ParamFunction holds the rendered pane
```

`out._pane` is an internal attribute. It's convenient, but it can change between releases. For a stable test, assert on the bound function's result directly: `pn.bind(fn, widget)()` returns the current value.

## 4. Integration: Render to Bokeh Models

Some options are only validated, and some errors only raised, when a plot is rendered. Render key figures in tests to catch them early.

```python
import holoviews as hv
import panel as pn
from bokeh.models import HoverTool

hv.extension('bokeh')

def make_plot():
    return hv.Scatter([(0, 1), (1, 2)]).opts(size=8, tools=['hover'])

def make_app():
    return pn.Column('# Report', make_plot())

def test_plot_renders_to_bokeh():
    fig = hv.render(make_plot())
    assert fig.select_one(HoverTool) is not None

def test_app_builds_a_document_root():
    root = make_app().get_root()
    assert root is not None
```

## 5. Integration: Serve the App

A smoke test that serves the app and opens a session catches import errors and failures that only happen inside a session. The HTTP status alone isn't enough: when the app raises during construction, Panel logs the traceback and serves a red error `Alert` in its place, still with status 200. Pull the session document and check for that alert.

```python
import socket
import time

import httpx
import panel as pn
from bokeh.client import pull_session

def create_app():
    return pn.Column('# Hello', pn.widgets.IntSlider(label='n'))

def free_port():
    with socket.socket() as s:
        s.bind(('localhost', 0))
        return s.getsockname()[1]

def test_app_serves():
    port = free_port()
    server = pn.serve(create_app, port=port, threaded=True, show=False)
    try:
        time.sleep(1)  # let the server thread start
        url = f'http://localhost:{port}/'
        assert httpx.get(url).status_code == 200
        # Opening a session runs create_app on the server.
        with pull_session(url=url) as session:
            roots = session.document.roots
        css = [c for root in roots for c in (getattr(root, 'css_classes', None) or [])]
        assert 'alert-danger' not in css, 'the app raised while building; see the traceback in the test output'
        assert any(type(root).__name__ == 'Column' for root in roots)
    finally:
        server.stop()
```

The test fails if `create_app` raises, because Panel's error page is a root with the `alert-danger` class. If your app itself shows a danger alert at the top level, assert on a root you expect instead. The test doesn't run any JavaScript; client-side rendering and interaction need a browser test.

## 6. Browser Tests With Playwright

Use Playwright (`pytest-playwright`, the tool Panel's own UI tests use) only for behavior that lives in JavaScript: client-side `jscallback`/`jslink` behavior, layout, and components whose state is set by the browser.

```python
# Requires: pytest-playwright and `playwright install chromium`
import panel as pn

def test_button_click_updates_text(page):  # `page` fixture from pytest-playwright
    clicked = pn.pane.Markdown('waiting')
    button = pn.widgets.Button(label='Go')
    button.on_click(lambda e: setattr(clicked, 'object', 'clicked'))
    server = pn.serve(pn.Column(button, clicked), port=5007, threaded=True, show=False)
    try:
        page.goto('http://localhost:5007')
        page.get_by_role('button', name='Go').click()
        page.get_by_text('clicked').wait_for()
    finally:
        server.stop()
```

## 7. Visual Regression

HoloViz has no built-in visual regression tool. Pick the cheapest approach that catches the regressions you care about:

1. **Compare data, not pixels**, wherever possible. Assert on `dimension_values`, aggregated arrays from `rasterize`, or Bokeh model properties. Such tests are robust across platforms and versions.
2. **Static figures**: render with the Matplotlib backend (`hv.save(obj, 'fig.png', backend='matplotlib')`) and compare against a stored baseline with a tolerance, for example with `pytest-mpl` or `matplotlib.testing.compare.compare_images`.
3. **Interactive pages**: take Playwright screenshots (`page.screenshot()` or `expect(page).to_have_screenshot()` in Playwright's test runner) and compare with a tolerance.

Pixel baselines break when fonts, browsers or library versions change, so pin those in CI and regenerate baselines deliberately.

```python
import holoviews as hv
import numpy as np
from holoviews.operation.datashader import rasterize

hv.extension('bokeh')

def test_rasterized_counts_are_stable():
    rng = np.random.default_rng(42)
    points = hv.Points(rng.normal(size=(10_000, 2)))
    img = rasterize(points, width=50, height=50, dynamic=False)
    counts = img.dimension_values(2)  # empty pixels are NaN, not 0
    assert np.nansum(counts) == 10_000  # every point lands in exactly one pixel
```

## Testing Checklist

- [ ] Transforms tested, including empty and single-row inputs
- [ ] Plot functions assert on dimensions and data
- [ ] `Parameterized` validation and watchers tested
- [ ] Widget → view wiring tested in Python
- [ ] Key figures rendered with `hv.render` in CI
- [ ] One serve smoke test
- [ ] Browser tests only for JS-side behavior

## Related

- [Code Organization Best Practices](./code-organization.md) — structure that makes code testable
- [Panel Troubleshooting](../troubleshooting/panel-troubleshooting.md)
- [Panel: Test and debug](https://panel.holoviz.org/how_to/test/index.html)
- [Playwright for Python](https://playwright.dev/python/)
