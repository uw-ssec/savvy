# Documentation Best Practices

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions.

## Overview

A HoloViz project needs documentation for two audiences: developers who read the code, and users of the running app. Param and Panel let much of both live next to the code. This file covers docstrings, parameter docs, runnable examples, API docs and user-facing guides.

**Load when**: Documenting a HoloViz library or app, or adding in-app help for users.

## 1. Docstrings: NumPy Style, Focused on Behavior

The HoloViz libraries use NumPy-style docstrings. Follow that convention so your docs read like theirs and render with the same Sphinx tooling (`numpydoc` or `sphinx.ext.napoleon`).

```python
import holoviews as hv
import pandas as pd

def revenue_plot(df: pd.DataFrame, freq: str = 'W') -> hv.Curve:
    """Plot revenue resampled to a fixed frequency.

    Parameters
    ----------
    df : pandas.DataFrame
        Must contain a datetime ``day`` column and a numeric ``revenue`` column.
    freq : str, default 'W'
        Any pandas offset alias, such as ``'D'``, ``'W'`` or ``'MS'``.

    Returns
    -------
    holoviews.Curve
        Curve with key dimension ``day`` and value dimension ``revenue``.

    Examples
    --------
    >>> df = pd.DataFrame({'day': pd.date_range('2025-01-01', periods=14),
    ...                    'revenue': range(14)})
    >>> revenue_plot(df).vdims
    [Dimension('revenue')]
    """
    resampled = df.set_index('day')['revenue'].resample(freq).sum().reset_index()
    return hv.Curve(resampled, 'day', 'revenue')
```

- Document what the function **returns** (element type and dimensions). Users compose the result, so they need to know what it is.
- Keep the `Examples` section runnable and check it with `pytest --doctest-modules`.

## 2. Parameter Docs Are the API Docs

For `Parameterized` classes, the parameters are the public API. Give each one a `doc`, and describe the class's purpose in the class docstring. Don't repeat each parameter in the docstring.

```python
import panel as pn
import param

pn.extension()

class ExportSettings(param.Parameterized):
    """Settings for exporting the current view."""

    fmt = param.Selector(default='png', objects=['png', 'svg', 'html'], doc='Output file format.')
    filename = param.String(default='figure', doc='File name without extension.')
    dpi = param.Integer(default=150, bounds=(72, 600), doc='Resolution for raster formats.')

settings = ExportSettings()
for name, p in ExportSettings.param.objects().items():
    if name != 'name':
        print(f'{name}: {p.doc}')

# Widgets that support it (Select, TextInput, ...) show `doc` as a tooltip
form = pn.Param(settings.param, parameters=['fmt', 'filename', 'dpi'])
```

## 3. Examples as Notebooks That Run

HoloViz projects document through example notebooks. Treat yours as tests:

- Keep each notebook focused on one task, and start it with the imports and `hv.extension`/`pn.extension` calls it needs.
- Use small synthetic or bundled sample data so it runs offline and quickly.
- Execute notebooks in CI (for example with `nbval`, or `jupyter nbconvert --execute`). A notebook that doesn't run is worse than no notebook.
- Don't commit large outputs. Rasterized Bokeh plots embed their data in the notebook file.

```bash
pixi add nbval   # or: conda install -c conda-forge nbval / pip install nbval
pixi run pytest --nbval-lax examples/
```

## 4. API Reference

- Generate reference pages from docstrings with Sphinx `autodoc` (with `numpydoc`) or `mkdocstrings`. HoloViz itself builds its sites with Sphinx and the `pydata-sphinx-theme`.
- Document HoloViews options you set by default (`hv.opts.defaults(...)`) in one place, so users know what they get without calling `.opts`.
- Link to the upstream reference gallery (for example `https://panel.holoviz.org/reference/index.html`) for library components. Don't copy their docs.

## 5. Live Examples in Static Docs

`panel convert` compiles a Panel app to run in the browser via Pyodide, with no server. That's useful for interactive examples on a static docs site (GitHub Pages).

```bash
panel convert app.py --to pyodide-worker --out docs/_static/app
```

Only pure-Python dependencies and packages that Pyodide provides will work, so check the app runs after converting it.

## 6. User-Facing Help Inside the App

Users read the app, not your README. Put help where the question comes up.

```python
import panel as pn

pn.extension()

help_text = pn.pane.Markdown("""
### How to use
1. Choose a **region** in the sidebar.
2. Drag on the chart to zoom; double-click to reset.
3. Hover a point to see its exact value.

Data: synthetic sample, refreshed daily.
""")

region = pn.widgets.Select(label='Region', options=['north', 'south'],
                           description='Filters every chart on the page.')
info = pn.widgets.TooltipIcon(value='Revenue is shown in thousands of USD, before tax.')

app = pn.template.FastListTemplate(
    title='Sales Dashboard',
    sidebar=[region, pn.Row('Units', info), pn.Card(help_text, title='Help', collapsed=True)],
    main=['Charts here'],
)
```

- Label axes with units (`hv.Dimension('revenue', unit='kUSD')`), and title every plot with the question it answers.
- State the data source and the last refresh time on the page.
- Use widget `description` and `TooltipIcon` for short help, and a collapsible `Card` or the template's `modal` for longer guides.

## 7. Project-Level Docs

A README for a HoloViz app should answer, in order:

1. What does the app show, and for whom?
2. How do I run it locally? Give the exact commands, such as `pixi run serve` or `panel serve apps/main.py --dev`.
3. Where does the data come from, and what environment variables configure it?
4. How is it deployed? Link to the deployment notes.

## Related

- [Code Organization Best Practices](./code-organization.md)
- [Testing Best Practices](./testing.md) — doctests and notebook execution
- [Accessibility Best Practices](./accessibility.md) — writing for all users
- [Param: Parameters](https://param.holoviz.org/user_guide/Parameters.html)
- [Panel: Convert apps to WebAssembly](https://panel.holoviz.org/how_to/wasm/convert.html)
- [numpydoc style guide](https://numpydoc.readthedocs.io/en/latest/format.html)
