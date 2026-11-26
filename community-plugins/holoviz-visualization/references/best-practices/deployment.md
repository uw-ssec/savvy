# Deployment Best Practices

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions; `panel serve` flags were checked against `panel serve --help`.

## Overview

A Panel app in production is a long-running server that holds a websocket session for each open browser tab. Each session keeps its own Python state. This shapes deployment: memory grows with concurrent users, load balancers need sticky sessions, and the proxy must pass websockets through. This file covers environment setup, security, monitoring and scaling.

**Load when**: Moving a Panel app from `panel serve --dev` on a laptop to a shared server, container or cloud platform.

## 1. Reproducible Environment

- Lock exact versions. Use a `pixi.lock` (or `conda-lock`, or a pip lock file) committed with the app, and build production from the lock file.
- Pin Panel and Bokeh together. Panel releases target specific Bokeh versions, and mismatched JS/Python versions break rendering.
- Install only what the app imports. Datashader pulls in Numba, and GeoViews pulls in Cartopy and its system libraries, so omit them if they aren't used.

```bash
pixi add panel holoviews hvplot        # conda-forge, recorded in pixi.lock
pixi install --locked                  # CI / container: fail if the lock is stale
# pip alternative: pip install panel holoviews hvplot && pip freeze > requirements.txt
```

## 2. The Production Command

```bash
panel serve apps/main.py \
  --address 0.0.0.0 --port 5006 \
  --allow-websocket-origin=dashboard.example.com \
  --num-procs 2 --num-threads 4 \
  --warm --liveness \
  --use-xheaders \
  --log-level info
```

| Flag | Why |
|------|-----|
| `--allow-websocket-origin` | Required when the public hostname differs from the bind address; lists the allowed origins |
| `--num-procs N` | N server processes sharing the port (not available on Windows) |
| `--num-threads N` | Run callbacks on a thread pool so one slow callback doesn't block other sessions |
| `--warm` | Execute the scripts once at startup so imports and caches are warm |
| `--setup script.py` | Run setup code (load models, schedule tasks) at startup; with `--num-procs N` it runs once in each process |
| `--liveness` | Adds a `/liveness` health endpoint for load balancers and orchestrators |
| `--use-xheaders` | Trust `X-Forwarded-*` from a reverse proxy (only when behind one) |
| `--prefix /app` | Serve under a URL path behind a proxy |
| `--static-dirs assets=./assets` | Serve static files |

Never use `--dev` or `--autoreload` in production. Leave out `--show`.

Because `--setup` runs in every process, a task scheduled there with `pn.state.schedule_task` runs N times under `--num-procs N`. That is fine for per-process work such as refreshing an in-memory cache. Work that must happen once for the whole deployment (writing a shared file, emailing a report) belongs outside `panel serve`, in cron or a separate worker, or in a server started with `--num-procs 1`.

## 3. Behind a Reverse Proxy

The proxy must forward websocket upgrade headers. A minimal nginx location block:

```text
location / {
    proxy_pass http://127.0.0.1:5006;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 86400;
}
```

Terminate TLS at the proxy, or pass `--ssl-certfile`/`--ssl-keyfile` to `panel serve`.

## 4. Security

**Authentication.** Panel has built-in OAuth (GitHub, Google, Azure, Okta, Auth0, generic OIDC and others) and basic auth. Pass secrets through environment variables, never on the command line in shared shells or in source.

```bash
export PANEL_OAUTH_PROVIDER=github
export PANEL_OAUTH_KEY=...           # client id
export PANEL_OAUTH_SECRET=...        # client secret
export PANEL_COOKIE_SECRET=$(panel secret)
export PANEL_OAUTH_ENCRYPTION=$(panel oauth-secret)
panel serve apps/main.py --oauth-redirect-uri=https://dashboard.example.com
```

**Authorization.** Authentication only proves who the user is. Restrict access with an `authorize_callback`. Set it in a `--setup` script to check every request, or in the app script to check one app. The callback returns `True`/`False`, or a URL string to redirect to.

```python
import panel as pn

ALLOWED = {'alice', 'bob'}

def authorize(user_info, request_path):
    # user_info comes from the OAuth provider; key names depend on the provider
    return user_info.get('user') in ALLOWED

pn.config.authorize_callback = authorize
```

**Untrusted content and input.**

- Markdown and HTML panes pass embedded HTML through to the page. Escape user-supplied text with `html.escape()` before putting it in either, or set `sanitize_html=True` on `pn.pane.HTML`.
- Validate uploaded files (`FileInput`) by size and type before parsing them. Never `eval` or `pickle.loads` user input.
- Parameterize database queries. Don't build SQL from widget values with string formatting.

**Hardening.**

- Protect `--admin` with `--admin-users` (or `--admin-password`), or don't enable it on public deployments.
- Set `--unused-session-lifetime` and `--check-unused-sessions` so sessions whose browser never connected (or has gone) are cleaned up. `--session-token-expiration` limits how long a session token can be used to connect.
- Keep secrets out of `pn.state.cache` and module globals that end up in logs or the admin page.

## 5. Monitoring

- `--admin` adds `/admin`, a live view of sessions, CPU, memory and logs. It's good for debugging, but it isn't a monitoring system.
- `--liveness` is for health checks. Point the platform's health probe at `/liveness`.
- Use `--log-level info` (plus `--log-file`) to send server logs to your log aggregation. Add app-level logging with the standard `logging` module.
- `--mem-log-frequency` and `--stats-log-frequency` (in milliseconds) log memory and session counts periodically.
- Watch memory per session in a load test before launch. A per-session DataFrame copy is the usual cause of memory growth.

```python
import logging

import panel as pn

log = logging.getLogger('my_dashboard')

def on_load():
    log.info('session started for %s', pn.state.user or 'anonymous')

pn.state.onload(on_load)
```

## 6. Scaling

- **Vertical first.** `--num-threads` and caching usually go further than adding machines.
- **Sticky sessions.** Each browser tab holds a websocket to one process. With multiple processes or hosts behind a load balancer, enable session affinity, or the websocket can land on a process that doesn't know the session.
- **Share expensive data across sessions** with `pn.cache` (per process) or an external store (database, Redis, Parquet on object storage) shared by all processes.
- **Offload heavy compute** to a job queue or a Dask cluster, and keep the Panel process responsive.
- **No server at all**: for apps without server-side data access, `panel convert --to pyodide-worker` produces a static site that scales like any static files.

## 7. Containers

```text
FROM ghcr.io/prefix-dev/pixi:latest
WORKDIR /app
COPY pixi.toml pixi.lock ./
RUN pixi install --locked
COPY . .
EXPOSE 5006
CMD ["pixi", "run", "panel", "serve", "apps/main.py", "--address", "0.0.0.0", "--port", "5006", \
     "--allow-websocket-origin", "dashboard.example.com", "--num-procs", "2", "--liveness"]
```

Set `--allow-websocket-origin` to the real public hostname. Avoid `"*"`: a wildcard turns off the websocket origin check that stops other sites from connecting to your app. Run as a non-root user where the base image allows it.

## Deployment Checklist

- [ ] Lock file committed; production built from it
- [ ] `--allow-websocket-origin` set to the real hostname(s)
- [ ] Websocket upgrade headers forwarded by the proxy
- [ ] Auth configured via environment variables; authorization checked
- [ ] `--admin` disabled or restricted
- [ ] Health check on `/liveness`
- [ ] Load-tested memory per session
- [ ] Sticky sessions enabled with more than one process

## Related

- [Panel Best Practices](./panel.md)
- [Performance Best Practices](./performance.md)
- [Panel Troubleshooting](../troubleshooting/panel-troubleshooting.md)
- [Panel: Server deployment](https://panel.holoviz.org/how_to/server/index.html)
- [Panel: Authentication](https://panel.holoviz.org/how_to/authentication/index.html)
