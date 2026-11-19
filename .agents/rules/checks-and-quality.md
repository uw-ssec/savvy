# Checks & Quality Standards

**Load when:** you are about to commit, open a PR, or claim that checks pass.

## The Minimum Gate

```bash
pixi run check-all
```

This runs the offline CI gates — `plugins-check`, `catalog-check`, and
`test-scripts` — and must pass before any PR. Read the output; don't infer a
pass from a zero exit you didn't see.

## Checks By What You Changed

| You changed                                             | Also run                                                                                         |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| A `plugin.json`, `.claude-plugin/marketplace.json`      | `pixi run plugins-sync` first, then commit the regenerated files                                 |
| A skill's `description`, or `docs/catalog.yml`          | `pixi run catalog-sync` first, then commit `docs/catalog.md`                                     |
| A skill under `plugins/` or `community-plugins/`        | `pixi run -e ci skill-quality-check <skill-dir>` (CI fails below 70)                             |
| Added a skill                                           | A `docs/catalog.yml` example, then `pixi run -e ci python evals/catalog-triggers/trigger_test.py <plugin>/<skill>` |
| A plugin's agents, commands, or MCP config              | `pixi run plugins-check-claude` if `claude` is installed                                         |
| External URLs in Markdown                               | `pixi run links-check` (network; set `GITHUB_TOKEN`)                                             |
| `.github/workflows/`                                    | Keep `zizmor` passing; it runs in CI                                                             |
| Anything a plugin tells an agent to run, fetch, or obey | The security review checklist in `CONTRIBUTING.md`                                               |

Generated files (`.claude-plugin/plugin.json` inside a plugin,
`.agents/plugins/marketplace.json`, `.cursor-plugin/marketplace.json`,
`docs/catalog.md`) are never edited by hand. `plugins-check` and
`catalog-check` fail on drift.

## Validated Workflow

1. **Setup:** `pixi install`.
2. **Make your changes** — surgically, per
   [working-agreement.md](working-agreement.md).
3. **Regenerate** whatever the table above says, if anything.
4. **Verify:** `pixi run check-all` plus the rows that apply.
5. **Create PR:** work through
   [contribution-discipline.md](contribution-discipline.md) first.
   - Follow Conventional Commits for commit messages and PR titles
   - Link related issues with `Resolves #<issue-number>` (or `Refs #` when the
     PR only partly addresses it)

## Documentation Standards

- Conventional Commits for commit messages and PR titles
- Keep each skill self-contained: no relative links out of its directory
- Skill `metadata` values are strings; agent `skills:` is a YAML list
