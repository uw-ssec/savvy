---
name: docs
description:
  Use when work completed in this session needs writing up — a new or changed
  plugin, install or client-support changes, contributor conventions, a design
  or plan, or decisions and gotchas that should outlive the session.
---

# Docs

Write documentation for recent work in this session.

This repository has no docs site. Docs are Markdown files rendered by GitHub:
the root files, `docs/`, and each plugin's `README.md`. Decisions and gotchas go
to project memory in `knowledge/`, not to a docs page.

## Arguments

Optional: a topic, a file, or "all" to cover everything from the session.

## Instructions

1. **Gather context** — Run these in parallel to understand what changed:

   - `git log --oneline -20` (recent commits)
   - `git diff main...HEAD --stat` (if on a feature branch)
   - `git log --oneline --since="8 hours ago"` (today's work)
   - Review any open designs or plans in `docs/specs/`

2. **Determine scope** — Based on the argument and recent changes, decide which
   docs need writing or updating. Always read the existing file first — update
   rather than duplicate.

3. **Place documentation correctly:**

   | What changed                                     | Where it goes                                                                                         |
   | ------------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
   | What a plugin does, its commands, scripts, MCP   | That plugin's `README.md`                                                                             |
   | A plugin added or removed                        | The plugin's `README.md` and the "Available Plugins" section of the root `README.md`                  |
   | A skill's purpose or triggers                    | The skill's `description` frontmatter, then `pixi run catalog-sync`                                   |
   | A skill's example prompt, tier, or maintainer    | `docs/catalog.yml`, then `pixi run catalog-sync`                                                      |
   | Install steps or which clients load what         | `docs/install.md` (keep its support matrix current)                                                   |
   | What plugins can do to a user's machine          | `docs/trust-and-safety.md`                                                                            |
   | Contributor conventions, CI, evals, review steps | `CONTRIBUTING.md`                                                                                     |
   | How agents should work on this repository        | `.agents/rules/` — behavior-shaping; see the bar in `contribution-discipline.md` before changing them |
   | A design or implementation plan                  | `docs/specs/YYYY-MM-DD-topic-design.md` or `-plan.md`                                                 |
   | Decisions, constraints, non-obvious gotchas      | `knowledge/`, through the `okf-memory` skill                                                          |

   Never edit `docs/catalog.md` by hand; it is generated.

4. **Write documentation** covering these categories as relevant:

   ### Technical Details

   - What was built, changed, or fixed
   - New or changed pixi tasks, CI workflows, or scripts
   - Manifest or frontmatter conventions introduced or changed
   - Dependencies added, and why

   ### Design

   - How the pieces relate (Mermaid diagrams render on GitHub)
   - Which files are sources and which are generated from them
   - Trade-offs considered and which path was chosen

   ### Session Learnings

   Record these with the `okf-memory` skill rather than in a docs page:

   - Decisions made and their rationale
   - Technical issues encountered and how they were resolved
   - Gotchas, edge cases, or surprising behavior discovered
   - Things that didn't work and why

5. **Regenerate** — if you touched a skill `description` or
   `docs/catalog.yml`, run `pixi run catalog-sync`.

6. **Verify** — Run `pixi run check-all`. Its `plugins-check` step checks the
   relative links in root Markdown files, `docs/` (except `docs/specs/`), and
   plugin files outside `skills/`. If you added external URLs, also run
   `pixi run links-check`.

7. **Report** — Show the user:
   - Files created or updated (with paths)
   - Concepts recorded in `knowledge/`, if any
   - Check results (pass/fail)

## Documentation Style

- GitHub-flavored Markdown. For callouts use GitHub alerts (`> [!NOTE]`,
  `> [!WARNING]`, `> [!TIP]`, `> [!IMPORTANT]`)
- Start every doc with a level-1 heading and a 1-2 sentence summary
- Use tables for structured data (tasks, fields, client support)
- Keep headings hierarchical (h1 → h2 → h3, never skip levels)
- Use imperative voice for guides ("Run the sync", not "You should run the
  sync")
- Code blocks carry a language tag

## Mermaid Diagram Conventions

- Use `graph TD` for top-down architecture diagrams
- Use `sequenceDiagram` for request/response flows
- Keep diagrams focused — split complex systems into multiple diagrams
- Label edges with the mechanism (e.g., `-->|plugins-sync|`, `-->|CI|`)

## Rules

- Never delete existing documentation — update or extend it
- Always read existing docs before writing to avoid duplication
- Use relative links between docs (e.g., `../CONTRIBUTING.md` from `docs/`)
- Inside a skill, never link outside its directory; skills must stay
  self-contained
- Date-stamp designs and plans in their filenames
- `pixi run check-all` must pass before considering the task done
- NEVER include sensitive information in documentation (credentials, internal
  processes, etc.)
