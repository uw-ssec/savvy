---
name: color-systems
description: Generates comprehensive color systems including brand palette shade scales (50–950), semantic CSS custom property token mappings, dark mode variants, and WCAG contrast validation — delivered as ready-to-use CSS and design tokens. Use when defining a brand color palette, generating accessible shade scales, mapping semantic color tokens, building dark mode variants, or validating WCAG contrast compliance across a color system.
metadata:
   references: references/color-theory.md references/contrast-requirements.md references/palette-generation.md
---

# Color Systems

## Workflow

1. **Brand colors in** — collect primary, secondary, neutral seed hex values.
2. **Generate shade scales** (50–950) — script below.
3. **Validate contrast** — automated WCAG check.
4. **Map semantic tokens** — primary/success/warning/error → palette refs.
5. **Build dark mode variants** — remap aliases, do not invert.
6. **Re-validate dark mode contrast.**

Stop and fix before each next step if validation fails.

## Step 2 — Generate Shade Scale (Python, OKLCH)

```python
# scale.py — usage: python scale.py "#5B5BD6"
import sys, colorsys
from coloraide import Color

base = Color(sys.argv[1]).convert("oklch")
# Lightness anchors for 50..950
L = [0.97, 0.94, 0.88, 0.78, 0.66, 0.54, 0.47, 0.40, 0.33, 0.24, 0.16]
keys = [50,100,200,300,400,500,600,700,800,900,950]
for k, l in zip(keys, L):
    c = Color("oklch", [l, base["chroma"] * (1 if l > 0.4 else 0.85), base["hue"]])
    print(f"--color-brand-{k}: {c.convert('srgb').to_string(hex=True)};")
```

```bash
pip install coloraide && python scale.py "#5B5BD6" > tokens/brand-scale.css
```

## Step 3 — Validate Contrast

```bash
# Install once
npm i -D @adobe/leonardo-contrast-colors wcag-contrast

# Verify pairs from a JSON contract
cat > pairs.json <<'JSON'
[
  { "fg": "var(--color-on-surface)",    "bg": "var(--color-surface)",  "min": 4.5 },
  { "fg": "var(--color-on-primary)",    "bg": "var(--color-primary)",  "min": 4.5 },
  { "fg": "var(--color-on-surface-muted)","bg":"var(--color-surface)", "min": 4.5 },
  { "fg": "var(--color-border)",        "bg": "var(--color-surface)",  "min": 3.0 }
]
JSON
```

```js
// check-contrast.js
import { hex } from "wcag-contrast";
import fs from "node:fs";

const css   = fs.readFileSync("dist/tokens.css","utf8");
const pairs = JSON.parse(fs.readFileSync("pairs.json","utf8"));
const dark  = process.argv.includes("--theme=dark");
const rootBlock = css.match(/:root\s*\{([^}]*)\}/)?.[1] ?? "";
const darkBlock = css.match(/\[data-theme="dark"\]\s*\{([^}]*)\}/)?.[1] ?? "";
// Look up the token in the dark block first (with --theme=dark), then :root;
// follow var(--alias) references until a hex value is reached.
const resolve = (v) => {
  const name = v.match(/--[\w-]+/)[0];
  const re = new RegExp(`(?:^|[\\s;{])${name}:\\s*([^;]+);`);
  const m = (dark && darkBlock.match(re)) || rootBlock.match(re);
  if (!m) throw new Error(`${name} is not defined in dist/tokens.css`);
  const value = m[1].trim();
  return value.startsWith("var(") ? resolve(value) : value;
};
let failed = 0;
for (const p of pairs) {
  const ratio = hex(resolve(p.fg), resolve(p.bg));
  const ok = ratio >= p.min;
  console.log(`${ok ? "PASS" : "FAIL"} ${p.fg} on ${p.bg}: ${ratio.toFixed(2)} (need ${p.min})`);
  if (!ok) failed++;
}
process.exit(failed ? 1 : 0);
```

Run: `node check-contrast.js` — exits non-zero on any failure. Wire into CI before tokens publish.

## Step 4 — Semantic Token Mapping

```css
:root {
  --color-primary:       var(--color-brand-600);
  --color-primary-hover: var(--color-brand-500);
  --color-surface:       var(--color-gray-50);
  --color-on-surface:    var(--color-gray-900);
  --color-on-surface-muted: #4b5563;
  --color-on-primary:    #ffffff;
  --color-border:        #6b7280;  /* 4.63:1 on gray-50; #e5e7eb is only 1.18:1 */
  --color-success: #16a34a; --color-warning: #d97706; --color-error: #dc2626;
}
```

## Step 5 — Dark Mode Variants

```css
[data-theme="dark"] {
  --color-surface:        var(--color-gray-900);
  --color-surface-raised: #1f2937;
  --color-on-surface:     #e5e7eb;
  --color-on-surface-muted:#9ca3af;
  --color-border:         #6b7280;  /* 3.67:1 on gray-900; #374151 is only 1.72:1 */
  --color-primary:        var(--color-brand-400);  /* lighter for dark bg */
  --color-on-primary:     #0b0d12;
}
```

Rules: do not invert; reduce saturation 10–20% for highly saturated hues; elevate via lightness, not heavier shadows.

## Step 6 — Re-validate Dark Mode

Re-run `node check-contrast.js --theme=dark` (looks up each token in the `[data-theme="dark"]` block first, then falls back to `:root`). Same pass criteria: AA = 4.5:1 text, 3:1 non-text.

## Complete Example: `#5B5BD6` → CSS

```css
:root {
  --color-brand-500: #5b5bd6;  --color-brand-600: #4945be;
  --color-primary:    var(--color-brand-600);
  --color-on-primary: #ffffff;        /* 7.30:1 ✓ */
  --color-surface:    #f9fafb;
  --color-on-surface: #111827;        /* 16.98:1 ✓ */
}
[data-theme="dark"] {
  --color-primary:    var(--color-brand-400);  /* #7c81ff */
  --color-on-primary: #0b0d12;        /* 5.96:1 ✓ */
  --color-surface:    #111827;
  --color-on-surface: #e5e7eb;        /* 14.33:1 ✓ */
}
```

## References

- [Color Theory](references/color-theory.md) — color models, perceptual spaces, psychology
- [Palette Generation](references/palette-generation.md) — algorithmic generation, brand extraction
- [Contrast Requirements](references/contrast-requirements.md) — WCAG 2.2 specifics, common failures

## Next Steps

- **Visual Design (the `visual-design` skill)**: Apply color systems within a broader aesthetic framework
- **Typography Systems (the `typography-systems` skill)**: Ensure text colors work with the typographic system
- **Motion Design (the `motion-design` skill)**: Color transitions and animated color states
- **Grid Layout Systems (the `grid-layout-systems` skill)**: Surface colors that define layout zones
