# Trigger fixtures

One file per skill, `<plugin>/<skill>.json`, holding the prompts for the skill's
[three-way trigger test](../../../CONTRIBUTING.md#the-three-way-trigger-test).
`trigger_test.py --fixtures` runs them in headless Claude Code with only this
repository's plugins loaded. `pixi run test-scripts` checks every file against
the rules below.

```json
{
  "skill": "scientific-python-development/pixi-package-manager",
  "cases": [
    {"id": "obvious-01", "kind": "obvious", "expect": "fire", "prompt": "..."},
    {"id": "tired-01", "kind": "tired", "expect": "fire", "prompt": "..."},
    {"id": "obvious-02", "kind": "obvious", "expect": "fire", "prompt": "..."},
    {"id": "neighbor-01", "kind": "neighbor", "expect": "no-fire",
     "owner": "scientific-python-development/python-packaging", "prompt": "..."},
    {"id": "negative-01", "kind": "negative", "expect": "no-fire", "owner": null, "prompt": "..."}
  ]
}
```

| `kind` | `expect` | What it is |
| --- | --- | --- |
| `obvious` | `fire` | The request phrased the way the skill's docs would phrase it. |
| `tired` | `fire` | The same kind of request typed the way a tired person would: short, informal, few or none of the description's keywords. |
| `neighbor` | `no-fire` | A request that belongs to a sibling skill or command. `owner` names it as `<plugin>/<skill>` or `<plugin>:<command>`. A command that uses the target skill can't be the owner, since loading the skill is then correct. |
| `negative` | `no-fire` | A request no savvy skill should take. `owner` is `null`. |

Each file needs at least three `fire` cases, including at least one `tired`, and
at least two `no-fire` cases, including at least one `neighbor`. Prompts must be
self-contained: Claude stops to ask for files that don't exist instead of
loading a skill, so describe the situation instead of pointing at a file. Don't
name the skill or quote its description.
