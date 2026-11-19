# Hardening Patterns

Worked examples for [SKILL.md](../SKILL.md). Each action is pinned to the commit its tag pointed to on 2026-11-17. Re-resolve the pins with the command in SKILL.md before copying, because newer releases will exist.

## Release workflow: build, then publish to PyPI with OIDC

```yaml
name: release

on:
  push:
    tags: ["v*"]

permissions: {}  # deny everything; each job opts in

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: step-security/harden-runner@1d88384fd173af6ecb012dfd0264a306b711241a  # v2.22.4
        with:
          egress-policy: audit
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0  # v7.1.0
        with:
          python-version: "3.13"
      # Quoted: unquoted, the ": " in ":all: " makes this line invalid YAML
      - run: "python -m pip install --only-binary=:all: build"
      - run: python -m build
        env:
          PIP_ONLY_BINARY: ":all:"  # build installs the build requirements with its own pip run
      - uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9  # v7.0.2
        with:
          name: dist
          path: dist/

  publish:
    needs: build
    runs-on: ubuntu-latest
    environment: pypi  # add required reviewers in Settings → Environments
    permissions:
      id-token: write  # OIDC for trusted publishing; no PyPI token
    steps:
      - uses: step-security/harden-runner@1d88384fd173af6ecb012dfd0264a306b711241a  # v2.22.4
        with:
          egress-policy: audit
      - uses: actions/download-artifact@9000827ccba6bdab643e8b6fd33ac0654aef8333  # v8.0.2
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@7245906fb61fa33a13554f9d5fb856fe61758086  # v1.14.3
```

- **Before the first run**, add a trusted publisher on PyPI with the repository owner, repository name, workflow filename (`release.yml`) and environment (`pypi`). Then delete any `PYPI_TOKEN` secret.
- **The publish job** has no checkout and runs no project or dependency code. It only downloads `dist/` and uploads it. It is the only job with `id-token: write`.
- **`environment: pypi`** gates nothing until the environment has required reviewers.
- **harden-runner** starts in `audit` mode. After a clean run, switch to `egress-policy: block` and list the endpoints that run used under `allowed-endpoints`.
- **`PIP_ONLY_BINARY`** on the build step: `--only-binary` on the install line covers only `build` itself. `python -m build` installs the project's build requirements in a fresh environment with another pip run, and without the variable it built an sdist-only requirement and ran its code.
- **npm:** keep the same two jobs. The build job runs `npm ci --ignore-scripts`, then `npm pack`, and uploads the `.tgz`. The publish job downloads it and runs `npm publish ./<name>-<version>.tgz --ignore-scripts` with `id-token: write` and a trusted publisher configured on npmjs.com. Don't run `npm publish` on a checkout there: it runs `prepublishOnly`, `prepack`, `prepare`, `postpack`, `publish` and `postpublish` from `package.json`, in the job that holds the publish credential. Trusted publishing needs npm CLI 11.5.1 or later and Node 22.14.0 or later, and npm then adds provenance on its own.

## Pwn Request

A `pull_request_target` workflow runs with the base repository's token, secrets and cache. Checking out the pull request's code there runs a stranger's code with those credentials:

```yaml
# Dangerous: do not copy
on: pull_request_target
permissions: {}
jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          ref: ${{ github.event.pull_request.head.sha }}
          allow-unsafe-pr-checkout: true  # checkout v7 refuses fork PR code without this
      - run: make test
```

Run untrusted code under `on: pull_request` instead. For pull requests from forks, GitHub passes no secrets except `GITHUB_TOKEN`, and that token is read-only. A private repository can override both under Settings → Actions → General → Fork pull request workflows, with "Send write tokens to workflows from pull requests" and "Send secrets to workflows from pull requests". Check that both are off before fork code runs. An organization that disables them stops repositories from turning them on. Keep `pull_request_target` for jobs that never check out or run pull request code, such as labelling.
