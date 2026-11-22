# Panel Troubleshooting

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions.

## Overview

This file covers Panel problems in roughly the order you meet them: nothing displays, the server will not start or the browser cannot connect, widgets do not update the output, components do not render, the app freezes or leaks state between users, and authentication fails to start.

**Load when**: A Panel app shows nothing, `panel serve` fails, widgets stop driving the output, or a deployed app behaves differently from the local one.

## Nothing Displays

**Symptom**: A notebook cell or a served app shows no output, or `panel serve app.py` serves an empty page.

**Cause**: Usually one of these:
1. **Notebook without the extension.** The log shows `Displaying Panel objects in the notebook requires the panel extension to be loaded. Ensure you run pn.extension() before displaying objects in the notebook.`
2. **Script without `.servable()`.** `panel serve` only shows objects marked servable. A bare expression at the end of a script is not displayed.
3. **Plain `python app.py`.** Running the script with Python builds the objects and exits. Nothing is served.

**Fix**: Load the extension once at the top, mark the root object servable, and start the app with `panel serve`.

```python
import numpy as np
import holoviews as hv
import panel as pn

pn.extension()                        # in a notebook, run this before displaying anything
hv.extension('bokeh')

curve = hv.Curve(np.random.rand(20).cumsum())
app = pn.Column('# Sensor overview', curve)
app.servable()                        # picked up by `panel serve app.py`
```

```bash
panel serve app.py --show --dev       # --dev reloads the app when the file changes
```

If the page loads but stays blank, open the browser developer tools. A JavaScript error in the console, or a failed `/ws` request in the Network tab, points to the sections below.

## `OSError: [Errno 48] Address already in use`

**Symptom**: `panel serve` (or `pn.serve`) fails at startup with `OSError: [Errno 48] Address already in use`. On Linux the error number is 98.

**Cause**: Another process, often an earlier `panel serve` that is still running, holds the port (default 5006).

**Fix**: Stop the old process, or choose another port.

```bash
lsof -i :5006                     # find the process holding the port (macOS/Linux)
panel serve app.py --port 5007
```

## Blank Page When Served Remotely: `Refusing websocket connection from Origin`

**Symptom**: The app works on `localhost` but is blank when opened through a hostname, a Docker port mapping, or a reverse proxy. The server log shows `Refusing websocket connection from Origin 'http://myhost:5006'; use --allow-websocket-origin=myhost:5006 or set BOKEH_ALLOW_WS_ORIGIN=myhost:5006 to permit this; currently we allow origins {'localhost:5006'}`.

**Cause**: Panel's server only accepts websocket connections from origins on its allow list, which contains just `localhost` by default.

**Fix**: Allow the public origin, listen on all interfaces inside a container, and tell Panel about any URL prefix added by the proxy.

```bash
panel serve app.py \
  --address 0.0.0.0 --port 5006 \
  --allow-websocket-origin=dashboard.example.org \
  --prefix /dashboard \
  --use-xheaders                  # trust X-Forwarded-* headers from the proxy
```

The reverse proxy must forward websocket upgrades (`Upgrade` and `Connection` headers). With `--num-procs` greater than 1, or with several replicas, the load balancer needs sticky sessions so that each browser keeps talking to the same process.

## Widget Changes Do Not Update the Output

**Symptom**: Moving a widget does nothing, or the output updates once and then stops.

**Cause**: The function is bound to a *value* instead of the widget. `pn.bind(fn, slider.value)` passes the number once, so nothing is watching the widget. The same happens when a `@param.depends` decorator is missing or names the wrong parameter.

**Fix**: Pass the widget (or `widget.param.value`) to `pn.bind`.

```python
import panel as pn

pn.extension()

slider = pn.widgets.IntSlider(label='Window', value=3, start=1, end=10)

def describe(window):
    return f'Rolling window: {window}'

stale = pn.bind(describe, slider.value)   # wrong: bound to the number 3
live = pn.bind(describe, slider)          # right: re-runs when the slider moves

slider.value = 5
print(stale(), '|', live())               # Rolling window: 3 | Rolling window: 5

app = pn.Column(slider, live)
```

Two related causes:
- **In-place mutation.** Changing `pane.object` in place, for example `df.loc[...] = ...` on the DataFrame a pane shows, does not notify Panel. Assign a new object (`pane.object = new_df`) or call `pane.param.trigger('object')`.
- **Callback errors.** An exception in a callback leaves the old output on screen. Run `panel serve` with `--log-level debug` and check the server log. In a notebook, check the browser console.

See [Param Troubleshooting](./param-troubleshooting.md) for watchers that do not fire.

## Component Does Not Render: `pn.extension('tabulator')`

**Symptom**: A `Tabulator`, `Plotly`, `Vega`, `ECharts`, or similar component is missing, and the log shows a warning such as `pn.extension was initialized but 'tabulator' extension was not loaded...` or `Tabulator was not imported on instantiation and may not render in the served application.`

**Cause**: These components need extra JavaScript. Panel 1.10 normally loads it on demand (`pn.config.lazy_resources = True`). On-demand loading is unavailable when `lazy_resources` is turned off, or when a served app or saved file uses inline resources (notebooks are exempt). In those cases a component whose extension was not declared may not render.

**Fix**: Declare every extension you use in the first `pn.extension` call. This also avoids an extra round trip when the component first renders.

```python
import pandas as pd
import panel as pn

pn.extension('tabulator', 'plotly')

table = pn.widgets.Tabulator(pd.DataFrame({'site': ['A', 'B'], 'value': [1.5, 2.5]}))
```

## App Freezes During a Slow Callback

**Symptom**: While one callback runs (a query, a model fit), the app stops responding, and other users of the same server wait too.

**Cause**: By default, Panel runs callbacks on the server's single event loop, so a blocking call blocks everything.

**Fix**: Make I/O-bound callbacks `async`, or enable a thread pool for blocking code. Show a loading indicator either way.

```python
import asyncio
import panel as pn

pn.extension(nthreads=4)              # same as `panel serve app.py --num-threads 4`

button = pn.widgets.Button(label='Run query')

async def run_query(clicks):
    if not clicks:
        return 'Press the button.'
    await asyncio.sleep(0.1)          # stands in for an async database or HTTP call
    return f'Query finished ({clicks} runs).'

result = pn.panel(pn.bind(run_query, button.param.clicks), loading_indicator=True)
app = pn.Column(button, result)
```

CPU-bound work in pure Python still holds the GIL, so threads help less. Move it to a separate process, or precompute and cache the results.

## Data Leaks Between Users, or Never Refreshes

**Symptom**: One user's selection appears for another user, or new data never shows up until the server restarts.

**Cause**: `panel serve app.py` re-runs `app.py` for every session, but modules that `app.py` imports run only once per process. Globals in those imported modules, `pn.state.cache`, and `pn.cache` without `per_session=True` are therefore shared by **every session in the process**. A cached result is only replaced when the function is called again after its `ttl` has expired, or after the cache is cleared. An object captured earlier keeps the old data.

**Fix**: Create per-user objects in the served script, or in a function that Panel calls for each session. Cache only shared, read-only data, give it a `ttl`, and call the cached function where the data is used, so that expired results are reloaded.

```python
import pandas as pd
import panel as pn

pn.extension()

@pn.cache(ttl=600)                    # shared by all sessions; reloaded on the first call after 10 minutes
def load_reference_data():
    return pd.DataFrame({'site': ['A', 'B'], 'capacity': [10, 20]})

@pn.cache(per_session=True)           # one cache per browser session
def user_scratch(key):
    return {'key': key}

def filter_site(site):
    data = load_reference_data()      # called on every update, so an expired entry is reloaded
    return data[data.site == site]

def create_app():
    selected = pn.widgets.Select(label='Site', options=['A', 'B'])   # new widget per session
    return pn.Column(selected, pn.bind(filter_site, selected))

app = create_app()
# pn.serve({'app': create_app})       # a function is called once per session
# pn.state.clear_caches()             # clear every pn.cache result, e.g. after a data reload
```

## OAuth Will Not Start

**Symptom**: `panel serve` exits with `ERROR: When enabling an OAuth provider you must supply a valid cookie_secret either using the --cookie-secret CLI argument or the PANEL_COOKIE_SECRET environment variable.`

**Cause**: OAuth stores the login in a signed cookie, so it needs a secret. Panel also encrypts the stored tokens when an encryption key is set.

**Fix**: Generate both secrets, keep them in environment variables, and make sure the redirect URI registered with the provider matches the URL users actually reach.

```bash
export PANEL_OAUTH_PROVIDER=github
export PANEL_OAUTH_KEY="$GITHUB_CLIENT_ID"
export PANEL_OAUTH_SECRET="$GITHUB_CLIENT_SECRET"  # env vars, not flags: flags show in the process list
export PANEL_COOKIE_SECRET=$(panel secret)
export PANEL_OAUTH_ENCRYPTION=$(panel oauth-secret)
panel serve app.py \
  --oauth-redirect-uri https://dashboard.example.org/ \
  --allow-websocket-origin dashboard.example.org
```

If the provider shows a "redirect URI mismatch" page, the `--oauth-redirect-uri` value and the URI registered in the provider's app settings differ. Compare scheme, host, port, prefix, and trailing slash. Inside the app, `pn.state.user` and `pn.state.user_info` describe the logged-in user. For a simple password gate without a provider, use `--basic-auth`.

## `PendingDeprecationWarning: Widget.name is deprecated`

**Symptom**: Creating a widget with `name=` logs `PendingDeprecationWarning: Widget.name is deprecated and will be removed in version 2.0. Use 'label' instead.`

**Cause**: Panel 1.10 separates the visible label from Param's `name` attribute.

**Fix**: Use `label=` for the text shown next to the widget.

```python
import panel as pn

pn.extension()

slider = pn.widgets.IntSlider(label='Window', value=3, start=1, end=10)
```

## Related

- [Panel Best Practices](../best-practices/panel.md)
- [Panel Patterns](../patterns/panel-patterns.md)
- [Deployment Best Practices](../best-practices/deployment.md)
- [Performance Patterns](../patterns/performance-patterns.md)
- [Panel how-to guides](https://panel.holoviz.org/how_to/index.html)
- [Configuring authentication](https://panel.holoviz.org/how_to/authentication/index.html)
