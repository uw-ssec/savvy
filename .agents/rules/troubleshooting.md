# Troubleshooting

**Load when:** a documented command fails or behaves unexpectedly.

## Issue: `plugins-check` fails with manifest drift

**Cause:** a source manifest changed but the generated copies did not.

**Solution:** `pixi run plugins-sync`, then commit the regenerated files.

## Issue: `catalog-check` fails

**Cause:** `docs/catalog.md` is stale, or a skill has no `docs/catalog.yml`
entry.

**Solution:** add the missing `example:` under the skill's plugin in
`docs/catalog.yml`, run `pixi run catalog-sync`, and commit `docs/catalog.md`.

## Issue: `plugins-check` reports a broken relative link

**Cause:** a link points outside a skill's directory, or at a file that moved.
Skills must be self-contained because skills-only clients install one skill
directory on its own.

**Solution:** name the sibling skill in prose instead of linking to it, or copy
the material into the skill's `references/`.

## Issue: `pixi.lock` shows unrelated churn

**Cause:** the lock was regenerated with a different pixi version than CI's
pinned `v0.82.0`.

**Solution:** regenerate with the pinned version, or revert the unrelated hunks.

## Issue: `links-check` hits rate limits

**Solution:** export `GITHUB_TOKEN` before running it. A URL that blocks
automated requests goes in `lychee.toml`'s `exclude` list with a comment giving
the reason.

## Issue: `okf` command not found

**Solution:** run `pixi install` (the `okf` feature is in the default
environment) and call it as `pixi run okf`, not `okf-agent-memory`.

## Issue: Modifying `pixi.toml` breaks the environment

```bash
pixi install
# If still broken:
rm -rf .pixi
pixi install
```
