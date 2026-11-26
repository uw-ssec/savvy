# Panel Best Practices

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions.

## Overview

Guidelines for building Panel apps that stay readable as they grow. They cover choosing a reactive API, layout and sizing, per-session state, and getting an app ready to serve.

**Load when**: Building or reviewing a Panel dashboard or web application.

## 1. Pick One Reactive Style per Component

Panel has three reactive APIs. All are current. Mixing them inside one component makes the data flow hard to follow.

| API | Use for |
|-----|---------|
| `pn.bind(fn, widget)` | Function-based apps; a few widgets driving a view |
| `pn.rx(value)` | Expression pipelines (`dfx[dfx.x > slider]`) |
| `param.Parameterized` + `@param.depends` | Reusable components with state, testable without a UI |

```python
import numpy as np
import pandas as pd
import panel as pn

pn.extension()

df = pd.DataFrame({'x': np.arange(100), 'y': np.random.randn(100).cumsum()})

# pn.bind: the function gets plain values, not widgets
window = pn.widgets.IntSlider(label='Window', start=1, end=20, value=5)

def smoothed(window):
    return df.assign(y=df.y.rolling(window).mean()).tail(5)

bind_app = pn.Column(window, pn.pane.DataFrame(pn.bind(smoothed, window)))

# pn.rx: build an expression; it re-evaluates when the widget changes
threshold = pn.widgets.FloatSlider(label='Threshold', start=-5, end=5, value=0)
dfx = pn.rx(df)
count = dfx[dfx.y > threshold].shape[0]  # widgets resolve to their current value
rx_app = pn.Column(threshold, pn.pane.Markdown(pn.rx('Rows above threshold: {}').format(count)))
```

For the class-based style, see [Param Best Practices](./param.md).

## 2. Keep Callbacks Pure, Side Effects Explicit

A bound function should **return** a view. Side effects (writing files, mutating other components) go in `.param.watch` callbacks or `on_click` handlers. Never hide them in a view function that Panel may call many times.

```python
import panel as pn

pn.extension()

log = pn.pane.Markdown('')
button = pn.widgets.Button(label='Save', color='primary')

# ✅ Good: side effect in an event handler
def save(event):
    log.object = f'Saved ({button.clicks} clicks)'

button.on_click(save)
app = pn.Row(button, log)
```

## 3. Update in Place Instead of Rebuilding

Create components once, then change their `.object`, `.value` or `.options`. Replacing whole layouts causes flicker and resets widget state.

```python
import pandas as pd
import panel as pn

pn.extension('tabulator')

table = pn.widgets.Tabulator(pd.DataFrame({'a': [1, 2, 3]}), pagination='remote', page_size=20)
status = pn.pane.Markdown('Ready')

def refresh(event=None):
    with pn.io.hold():  # one update to the browser instead of two
        table.value = pd.DataFrame({'a': [4, 5, 6]})
        status.object = 'Refreshed'

refresh()
app = pn.Column(status, table)
```

## 4. Layout and Sizing

- Use `sizing_mode='stretch_width'` for most content and give plots a fixed or minimum height. A plot whose height and width both stretch inside a container of unknown height collapses.
- Build page structure from `pn.Row`, `pn.Column`, `pn.Tabs`, `pn.GridSpec`/`pn.GridStack` and `pn.FlexBox`. Don't fight it with CSS.
- Put controls in a template sidebar and content in the main area.
- Use a `pn.Card` for optional detail the user can collapse.

```python
import holoviews as hv
import numpy as np
import panel as pn

pn.extension()
hv.extension('bokeh')

plot = hv.Curve(np.random.randn(100).cumsum()).opts(responsive=True, min_height=300)
controls = pn.Column(pn.widgets.Select(label='Series', options=['A', 'B']))

template = pn.template.FastListTemplate(
    title='Sales Dashboard',
    sidebar=[controls],
    main=[pn.Card(plot, title='Trend', sizing_mode='stretch_width')],
)
template.servable()
```

## 5. Manage State per Session

Module-level objects in a script served with `panel serve` are re-created for each session. Objects in an **imported** module are shared by all sessions.

- Keep per-user state (selected filters, uploaded data) in objects created inside the served script, or in a `Parameterized` instance per session.
- Keep shared read-only resources (reference data, models) in imported modules or `pn.cache`.
- Use `pn.state.cache` for deliberate cross-session sharing. Treat cached objects as read-only.
- `pn.state.user` and `pn.state.user_info` expose the logged-in user when OAuth or basic auth is enabled.
- Release resources with `pn.state.on_session_destroyed(callback)`.

```python
import panel as pn

pn.extension()

def on_destroy(session_context):
    # Close connections, delete temp files, etc.
    pass

pn.state.on_session_destroyed(on_destroy)
```

## 6. Declare the Extensions You Use

Panel 1.10 loads a component's JS on demand (`pn.config.lazy_resources`, on by default). Still, list the extensions an app uses in `pn.extension`, so the resources load up front with the page. Also set `lazy_resources=False` for air-gapped deployments: undeclared components then fail loudly instead of trying to fetch from a CDN.

```python
import panel as pn

pn.extension('tabulator', 'plotly', notifications=True, design='material')
```

## 7. Report Errors to the User

Long callbacks should show progress, and failures should reach the user rather than only the server log.

```python
import panel as pn

pn.extension(notifications=True)

def run(event):
    with button.param.update(loading=True):
        try:
            result = 1 / 1  # real work here
            pn.state.notifications.success(f'Done: {result}')
        except Exception as e:
            pn.state.notifications.error(f'Failed: {e}', duration=0)

button = pn.widgets.Button(label='Run')
button.on_click(run)
app = pn.Column(button)
```

## 8. Know Where the API Is Heading

Panel 1.10 ships a `panel.ui` namespace that re-exports the Material UI components (from `panel-material-ui`) alongside the classic components. Panel 2.0 moves the implementation there. The classic `pn.widgets`/`pn.pane` API used in this file still works in 1.x.

- Fix `PendingDeprecationWarning`s (such as `name=` → `label=` and `button_type=` → `color=`) as they appear. They mark what 2.0 removes.
- `panel migrate path/ --diff` previews a rewrite of classic code to the `panel.ui` namespace, and `--fix` applies it. Review the diff before committing.

## 9. Prepare for Serving

- End the app with `.servable()` and serve it with `panel serve app.py`. Use `--dev` while developing.
- Don't call `pn.serve` or `.show()` inside a script you serve with `panel serve`.
- Read configuration (paths, credentials) from environment variables, not literals.
- See [Deployment Best Practices](./deployment.md) for auth, scaling and monitoring.

## Anti-Patterns

| ❌ Avoid | ✅ Instead |
|---------|-----------|
| Re-creating widgets inside a bound function | Create once, bind the view |
| `widget.param.watch` for a plain view | `pn.bind` or `@param.depends` |
| Heavy I/O at import time with no cache | `pn.cache` or `pn.state.onload` |
| Global mutable state in an imported module | Per-session objects or explicit `pn.state.cache` |
| `name=` for widget labels, `button_type=` | `label=` and `color=` (the old names raise `PendingDeprecationWarning` in Panel 1.10) |

## Related

- [Panel Patterns](../patterns/panel-patterns.md)
- [Panel Troubleshooting](../troubleshooting/panel-troubleshooting.md)
- [Performance Best Practices](./performance.md)
- [Panel how-to guides](https://panel.holoviz.org/how_to/index.html)
- [Panel: Reactive APIs](https://panel.holoviz.org/explanation/api/index.html)
