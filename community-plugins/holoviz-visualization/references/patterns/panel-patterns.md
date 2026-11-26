# Panel Patterns

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions.

## Overview

Complete patterns for Panel applications: reactive dashboards, multi-page apps, server-pushed updates, file uploads, and authentication. Every example runs as a script, so `panel serve app.py` serves it. The examples use the classic `pn.widgets`, `pn.pane` and `pn.template` API, which is fully supported in Panel 1.x. Panel 1.10 also exposes Material UI components under `panel.ui`.

**Load when**: Building Panel applications, dashboards, or interactive components

```bash
pixi add panel hvplot          # or: conda install -c conda-forge panel hvplot
pip install panel hvplot
```

## Pattern 1: Param-Based Dashboard

**When to use**: The app has state that several views share, or you want the logic testable without a browser.

Subclass `pn.viewable.Viewer`, declare state as parameters, and derive views with `@param.depends`. Panel renders `self.param` as widgets automatically.

```python
import numpy as np
import pandas as pd
import panel as pn
import param
import hvplot.pandas  # noqa: F401  registers df.hvplot

pn.extension()

rng = np.random.default_rng(0)
DATA = pd.DataFrame({
    "date": pd.date_range("2024-01-01", periods=365, freq="D"),
    "region": rng.choice(["North", "South", "East", "West"], 365),
    "sales": rng.gamma(2.0, 50.0, 365),
})


class SalesDashboard(pn.viewable.Viewer):
    region = param.Selector(objects=["All", "North", "South", "East", "West"], default="All")
    window = param.Integer(default=7, bounds=(1, 60), doc="Rolling window in days")

    @param.depends("region")
    def _filtered(self):
        if self.region == "All":
            return DATA
        return DATA[DATA.region == self.region]

    @param.depends("region", "window")
    def plot(self):
        # A "7D" window spans 7 calendar days even when filtering leaves gaps.
        df = self._filtered().set_index("date").sales.rolling(f"{self.window}D").mean()
        return df.hvplot.line(title=f"Sales ({self.region}, {self.window}-day mean)", height=350)

    @param.depends("region")
    def total(self):
        return pn.indicators.Number(label="Total sales", value=self._filtered().sales.sum(), format="{value:,.0f}")

    def __panel__(self):
        return pn.Row(
            pn.Column(self.param.region, self.param.window, self.total, width=250),
            self.plot,
        )


dashboard = SalesDashboard()
dashboard.servable()
```

✅ The class holds all state, so a test can set `dashboard.region = "North"` and check `dashboard._filtered()`.
❌ Don't create widgets and wire them with `.param.watch` callbacks that mutate other widgets; dependencies get hard to follow.

## Pattern 2: Function-Based App with `pn.bind`

**When to use**: Small apps with a few widgets and one or two outputs, where a class is overkill.

```python
import numpy as np
import pandas as pd
import panel as pn
import hvplot.pandas  # noqa: F401

pn.extension()

df = pd.DataFrame({"x": np.linspace(0, 10, 200)})

freq = pn.widgets.FloatSlider(label="Frequency", start=0.5, end=5, value=1)
kind = pn.widgets.RadioButtonGroup(label="Kind", options=["line", "scatter"], value="line")


def make_plot(freq, kind):
    data = df.assign(y=np.sin(freq * df.x))
    return data.hvplot(x="x", y="y", kind=kind, height=300)


app = pn.Column(freq, kind, pn.bind(make_plot, freq, kind))
app.servable()
```

Widgets passed to `pn.bind` are replaced by their current `value` when the function is called.

## Pattern 3: Multi-Page Application

**When to use**: Distinct pages that share little state.

Option A: serve several scripts. Each file is one page, and Panel builds an index page.

```bash
panel serve overview.py details.py admin.py
```

Option B: one script with in-app navigation, which suits pages that share state or data.

```python
import panel as pn

pn.extension()


def overview():
    return pn.pane.Markdown("## Overview\nKey metrics go here.")


def details():
    return pn.pane.Markdown("## Details\nDrill-down tables go here.")


PAGES = {"Overview": overview, "Details": details}

nav = pn.widgets.RadioBoxGroup(label="Page", options=list(PAGES), value="Overview")
page = pn.bind(lambda name: PAGES[name](), nav)

template = pn.template.FastListTemplate(
    title="Multi-page app",
    sidebar=[nav],
    main=[pn.panel(page)],
)
template.servable()
```

Option C: map URL paths to functions with `pn.serve({"/": overview, "/details": details})`. That call starts a server, so use it from a launcher script, not from inside an app served with `panel serve`.

## Pattern 4: Real-Time Streaming

**When to use**: Data arrives continuously (sensors, logs, prices) and the browser should update without reloads.

A served Panel app keeps a websocket open per session. The server pushes changes over it, and a periodic callback is the usual driver. Stream only the new rows: `hv.streams.Buffer` for plots and `Tabulator.stream` for tables.

```python
import numpy as np
import pandas as pd
import holoviews as hv
import panel as pn

hv.extension("bokeh")
pn.extension("tabulator")

empty = pd.DataFrame({"t": pd.Series(dtype="float64"), "value": pd.Series(dtype="float64")})
buffer = hv.streams.Buffer(empty, length=500, index=False)  # keeps the last 500 rows
plot = hv.DynamicMap(lambda data: hv.Curve(data, "t", "value"), streams=[buffer]).opts(
    height=300, responsive=True
)
table = pn.widgets.Tabulator(empty.copy(), height=200)

state = {"t": 0.0}


def tick():
    state["t"] += 1
    row = pd.DataFrame({"t": [state["t"]], "value": [np.random.randn()]})
    buffer.send(row)
    table.stream(row, rollover=50)  # keep at most 50 rows in the table


# Created per session; start=False until the user presses Start.
callback = pn.state.add_periodic_callback(tick, period=1000, start=False)
toggle = pn.widgets.Toggle(label="Start / stop", value=False)
toggle.param.watch(lambda event: setattr(callback, "running", event.new), "value")

app = pn.Column(toggle, plot, table)
app.servable()
```

- For data produced outside the session (a message queue or a background thread), update a shared object and have each session's periodic callback read from it. Don't touch a session's document from another thread.
- Use `hv.streams.Pipe` instead of `Buffer` when each update replaces the whole dataset.

## Pattern 5: File Upload Handling

**When to use**: Users supply their own CSV or Excel data.

`FileInput.value` holds the raw bytes. Parse them in a bound function and show a message until a file arrives.

```python
import html
import io

import pandas as pd
import panel as pn

pn.extension("tabulator")

upload = pn.widgets.FileInput(accept=".csv")


def preview(contents, filename):
    if not contents:
        return pn.pane.Markdown("Upload a CSV file to preview it.")
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except (ValueError, UnicodeDecodeError) as exc:
        # The filename comes from the user's machine: escape it before it reaches Markdown.
        return pn.pane.Alert(f"Could not parse {html.escape(filename)}: {html.escape(str(exc))}", alert_type="danger")
    return pn.Column(f"**{html.escape(filename)}**: {len(df):,} rows", pn.widgets.Tabulator(df, page_size=20))


app = pn.Column(upload, pn.bind(preview, upload.param.value, upload.param.filename))
app.servable()

# Simulate an upload, as a test would:
upload.param.update(value=b"a,b\n1,2\n3,4\n", filename="example.csv")
```

Uploads travel over the websocket, so large files can exceed the server's message limit. Raise it with `panel serve --websocket-max-message-size <bytes>`, or use `pn.widgets.FileDropper`, which uploads in chunks.

## Pattern 6: OAuth Authentication

**When to use**: The app must only be visible to signed-in users.

Panel ships OAuth providers (GitHub, Google, Azure, Okta, Auth0, GitLab and a generic provider) configured on the command line or by environment variables. No application code is needed to protect the app.

Pass the secrets as environment variables. Command-line flags such as `--oauth-secret` also work, but their values are visible to anyone who can list the server's processes.

```bash
export PANEL_OAUTH_PROVIDER=github
export PANEL_OAUTH_KEY="$GITHUB_CLIENT_ID"
export PANEL_OAUTH_SECRET="$GITHUB_CLIENT_SECRET"
export PANEL_COOKIE_SECRET=$(panel secret)
export PANEL_OAUTH_ENCRYPTION=$(panel oauth-secret)
panel serve app.py admin.py --setup auth_setup.py
```

Keep the client secret, cookie secret and encryption key out of source control.

Authentication proves who the user is; an `authorize_callback` decides what they may open. Set it in the `--setup` script so it applies to every app the server serves. Setting `pn.config.authorize_callback` inside `app.py` only applies to sessions of that app, so it can't guard `/admin`.

```python
# auth_setup.py, passed to panel serve with --setup
import panel as pn

ADMINS = {"alice", "bob"}


def authorize(user_info, request_path):
    """Return True to allow access to request_path; Panel calls it per request."""
    # user_info is the provider's raw profile: GitHub names the user "login",
    # Google and Auth0 use "email". pn.state.user holds the normalized name.
    return user_info.get("login") in ADMINS or not request_path.startswith("/admin")


pn.config.authorize_callback = authorize
```

Inside the app, read the signed-in user:

```python
import html

import panel as pn

pn.extension()

user = pn.state.user or "anonymous"  # None outside an authenticated server
app = pn.Column(f"Signed in as **{html.escape(user)}**", pn.pane.Markdown("Dashboard content"))
app.servable()
```

For a quick password gate instead of OAuth, use `panel serve app.py --basic-auth=credentials.json`, where the JSON file maps usernames to passwords, together with `PANEL_COOKIE_SECRET`. Leave `PANEL_OAUTH_PROVIDER` unset, or the OAuth provider replaces basic auth. `--basic-auth` also accepts the password itself, but then it shows up in the process list.

## Related

- [Param Patterns](./param-patterns.md): the parameter system Pattern 1 builds on
- [Performance Patterns](./performance-patterns.md): caching, deferred loading, async callbacks
- [Integration Patterns](./integration-patterns.md): Panel with HoloViews, FastAPI
- [Panel Best Practices](../best-practices/panel.md)
- [Panel Troubleshooting](../troubleshooting/panel-troubleshooting.md)
- [Panel how-to guides](https://panel.holoviz.org/how_to/index.html) and [authentication](https://panel.holoviz.org/how_to/authentication/index.html)
