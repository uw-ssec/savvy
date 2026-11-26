# Accessibility Best Practices

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions.

## Overview

Bokeh plots draw onto an HTML canvas. Screen readers can't read a canvas, and its pan, zoom and hover tools are built for a pointer. An accessible HoloViz app therefore pairs every chart with an accessible equivalent, and uses color and contrast that work for everyone. This file covers color contrast, keyboard access, screen readers, and how to approach WCAG conformance.

**Load when**: Building a public-facing or organization-wide app, choosing colors, or preparing for an accessibility review.

## 1. Don't Rely on Color Alone

About 1 in 12 men and 1 in 200 women have a color vision deficiency. Encode categories redundantly (color plus marker or line style), and choose colormaps designed for color-vision deficiency.

```python
import holoviews as hv
import numpy as np
import pandas as pd

hv.extension('bokeh')

rng = np.random.default_rng(1)
df = pd.DataFrame({
    'x': rng.normal(size=150), 'y': rng.normal(size=150),
    'group': np.repeat(['control', 'treated', 'placebo'], 50),
})

# ✅ Good: color AND marker distinguish groups
scatter = hv.Scatter(df, 'x', ['y', 'group']).opts(
    color='group', cmap=['#0072B2', '#D55E00', '#009E73'],  # Okabe-Ito colors, each >= 3:1 on white
    marker=hv.dim('group').categorize({'control': 'circle', 'treated': 'triangle', 'placebo': 'square'}),
    size=8, legend_position='right', width=550,
)

# ✅ Good: line style as well as color
x = np.linspace(0, 10, 100)
styles = {'low': 'solid', 'mid': 'dashed', 'high': 'dotted'}
lines = hv.Overlay([
    hv.Curve((x, np.sin(x) * k), label=name).opts(line_dash=styles[name], line_width=2)
    for k, name in [(1, 'low'), (2, 'mid'), (3, 'high')]
]).opts(width=550)
```

Colormaps for continuous data:

| Data | Colormap |
|------|----------|
| Sequential, CVD-safe | `cet_CET_CBL1`, `cet_CET_CBL2` (Colorcet) or `cividis` |
| Diverging, CVD-safe | `cet_CET_CBD1` |
| Avoid | `jet`, `rainbow`, red/green diverging maps |

Label lines and regions directly (`hv.Text`, `hv.Labels`) where you can, so readers don't need to match colors to a legend. The `colormaps-styling` skill covers palette choice in depth.

## 2. Meet Contrast Ratios

WCAG 2.2 requires a contrast ratio of at least **4.5:1** for normal text and **3:1** for large text and for graphical objects that carry meaning (lines, markers, bars against their background, under success criterion 1.4.11). Check your palette against the plot background:

```python
def relative_luminance(hex_color: str) -> float:
    r, g, b = (int(hex_color.lstrip('#')[i:i + 2], 16) / 255 for i in (0, 2, 4))
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

def contrast_ratio(fg: str, bg: str) -> float:
    l1, l2 = sorted((relative_luminance(fg), relative_luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)

for color in ['#0072B2', '#D55E00', '#009E73', '#E69F00', '#F0E442']:
    ratio = contrast_ratio(color, '#FFFFFF')
    print(f'{color} on white: {ratio:.2f}:1', 'OK' if ratio >= 3 else 'too light for marks')
```

Orange (`#E69F00`, 2.25:1) and yellow (`#F0E442`, 1.32:1) fail on white even though they belong to the colorblind-safe Okabe-Ito palette. Use them on dark backgrounds, or give markers a dark outline (`line_color`).

Also:

- Keep tick labels and axis titles readable. Use `fontscale=1.2` or `fontsize={'ticks': 12, 'labels': 14}` on plots viewed on large screens or by low-vision users.
- With `pn.extension(theme='dark')` or a dark template, re-check every color. Palettes tuned for white backgrounds often fail on dark ones.

## 3. Provide Text and Table Alternatives

For every chart, give screen-reader users the same information another way:

```python
import holoviews as hv
import numpy as np
import pandas as pd
import panel as pn

pn.extension('tabulator')
hv.extension('bokeh')

df = pd.DataFrame({'month': pd.date_range('2025-01-01', periods=12, freq='MS'),
                   'sales': np.random.default_rng(2).integers(80, 120, 12)})
peak = df.loc[df.sales.idxmax()]

chart = hv.Curve(df, 'month', 'sales').opts(title='Monthly sales, 2025', width=600)
summary = pn.pane.Markdown(
    f"**Summary:** Sales ranged from {df.sales.min()} to {df.sales.max()} units; "
    f"the peak was {peak.sales} units in {peak.month:%B}."
)
table = pn.widgets.Tabulator(df, disabled=True, show_index=False, pagination='local', page_size=12)

app = pn.Column(
    pn.pane.Markdown('## Monthly sales'),   # real heading for navigation
    summary,
    chart,
    pn.Card(table, title='Data table', collapsed=True),
)
```

- Put a one-sentence takeaway next to each chart. It helps every user, not just screen-reader users.
- Offer the underlying data as a table or a download (`pn.widgets.FileDownload`).
- Give static images alternative text: `pn.pane.PNG('chart.png', alt_text='Line chart of monthly sales, peaking in June')`.
- Structure pages with Markdown headings (`##`, `###`) in order, so assistive technology can navigate by heading.

## 4. Keyboard Access

Most of Panel's standard widgets render native HTML form controls, which can be focused and operated from the keyboard. Bokeh's plot tools (pan, box zoom, lasso, tap) can't be. So:

- Make every interaction possible without the plot tools. Pair box-select with a widget that filters the same data, and pair zoom with a range slider.
- Don't hide essential information in hover tooltips alone. Hover requires a pointer.
- Keep the tab order logical: controls before the content they affect, in reading order. Avoid layouts that visually reorder content.
- Check that focus is visible. Custom CSS (`stylesheets=`) must not remove focus outlines.

```python
import holoviews as hv
import numpy as np
import panel as pn

pn.extension()
hv.extension('bokeh')

x = np.linspace(0, 100, 1000)
y = np.sin(x / 5)
x_range = pn.widgets.RangeSlider(label='X range', start=0, end=100, value=(0, 100), step=1)

# The slider gives keyboard users the same zoom the box-zoom tool gives mouse users
def view(xr):
    return hv.Curve((x, y)).opts(xlim=xr, width=600, framewise=True)

app = pn.Column(x_range, hv.DynamicMap(pn.bind(view, x_range)))
```

## 5. Respect User Settings and Avoid Distraction

- Don't autoplay animations or `Player` widgets. Let the user start them.
- Use `responsive=True` or `sizing_mode='stretch_width'` so content reflows when users zoom the browser to 200% and beyond, rather than overflowing.
- Keep periodic refreshes infrequent, and announce them in text. Don't let them steal focus or reset widget state.

## 6. WCAG Conformance: Test, Don't Assume

Neither Panel nor Bokeh claims WCAG conformance for apps built with them. Conformance belongs to your page, so test it:

1. **Automated**: run axe DevTools or Lighthouse on the served app. They catch missing labels, contrast failures and heading-order problems.
2. **Keyboard-only pass**: unplug the mouse and complete every task with Tab, Shift+Tab, Enter, Space and the arrow keys.
3. **Screen reader pass**: use VoiceOver (macOS), NVDA (Windows) or Orca (Linux). Can a user reach the summary and the data table for every chart?
4. **Color pass**: view the app through a color-vision-deficiency simulator, such as the one in the browser DevTools rendering panel.
5. **Zoom pass**: set browser zoom to 200% and check nothing is cut off.

Record known gaps (for example, "plot interaction requires a pointer; the data table and filters provide equivalent access") in an accessibility statement.

## Accessibility Checklist

- [ ] Color is never the only encoding
- [ ] CVD-safe colormaps; contrast ≥ 3:1 for marks, ≥ 4.5:1 for text
- [ ] Every chart has a text summary and a data table or download
- [ ] Images have `alt_text`; headings are in order
- [ ] All tasks are possible by keyboard, without plot tools or hover
- [ ] Tested with axe/Lighthouse, a keyboard-only pass and a screen reader

## Related

- [HoloViews Best Practices](./holoviews.md) — styling
- [Panel Best Practices](./panel.md)
- [Documentation Best Practices](./documentation.md) — in-app help
- [WCAG 2.2 quick reference](https://www.w3.org/WAI/WCAG22/quickref/)
- [Colorcet colormaps](https://colorcet.holoviz.org/user_guide/index.html)
