# PyPI / pip / uv / poetry Supply Chain Quirks

## Contents

- [Threat Relevance](#threat-relevance)
- [.pth Check (Canonical)](#pth-check-canonical)
- [setup.py Execution at Install](#setuppy-execution-at-install)
- [build_wheel and backend-path in pyproject.toml](#build_wheel-and-backend-path-in-pyprojecttoml)
- [OIDC Trusted Publishing for PyPI](#oidc-trusted-publishing-for-pypi)
- [uv and poetry Lockfile Differences](#uv-and-poetry-lockfile-differences)
- [References](#references)

## Threat Relevance

Python's packaging history has accumulated several arbitrary-code-execution surfaces that don't exist in other ecosystems: `.pth` files run at every interpreter start, `setup.py` runs at install for source distributions, custom `build_wheel` backends run in build-isolated subprocesses, and `--no-build-isolation` removes the isolation. LiteLLM 1.82.8 (March 2026) exploited `.pth` execution by shipping `litellm_init.pth` in its wheel. The general "pin to lockfile and scan" pattern from `supply-chain-dependency-security` doesn't help if the install step itself runs adversary-controlled Python.

## .pth Check (Canonical)

Other supply-chain skills point here for the `.pth` check. It covers `.pth` files and, from Python 3.15, `.start` files.

**What runs.** At every interpreter start, `site` reads each `*.pth` file in every site directory. Lines are `sys.path` entries, except lines starting with `import ` or `import<TAB>`, which are executed. No `import` of the package is needed. Details that a `grep '^import'` misses:

- A `\r` starts a new, executable line. Python 3.12+ splits like `str.splitlines()`, so a form feed does too, and a UTF-8 BOM is dropped.
- Python 3.15 strips leading whitespace before the `import` test.
- Python 3.15 also runs every `pkg.mod:callable` entry in `<name>.start` files (PEP 829). `import` lines in `.pth` are deprecated there and expected to be ignored from 3.18.
- Lines starting with `exec(`, `os.` or `subprocess` are not executed. They are path entries.
- Python 3.9 also processes dot-named `.pth` files. 3.12 and later skip them.

**Run it:**

```bash
bash scripts/quick-check.sh --pth-only <project-dir>
bash scripts/quick-check.sh --pth-only --env <env-prefix> <project-dir>  # repeat --env per extra venv/conda/pixi env
```

It scans the site directories of `python3` and `python` on `PATH` (`site.getsitepackages()` for the interpreter, its base install and any venv, plus `site.getusersitepackages()`), `$VIRTUAL_ENV`, `$CONDA_PREFIX`, `./.venv`, `./venv`, `./.pixi/envs/*`, and each `--env`. Interpreters are started with `-I -S`, so the scan never executes a `.pth` file. A plain `python -c "import site; ..."` does.

**How it reports:**

- `pypi INFO: scanned N .pth/.start files in DIR`: one line per site directory, so an empty scan is visible.
- Path-only `.pth` files run no code and are not reported.
- `pypi INFO: known startup code in FILE: ORIGIN (owner: DIST)`: the file name and every code line match the exact text written by one of the tools below, and the file and the module it imports belong to that tool.
- `pypi FAIL: startup code in FILE looks like ORIGIN, but PROBLEM (owner: DIST)`: name and code match, but another package installed the file or its module. This is how a wheel imitates a known file: it ships `_editable_impl_<name>.pth` and its own `_editable_impl_<name>.py`, or overwrites `_distutils_hack`.
- `pypi WARN: startup code in FILE looks like ORIGIN, but no RECORD or conda-meta names its owner`: installed outside pip, uv and conda, for example by an OS package manager. Confirm the owner with it (`dpkg -S FILE`, `rpm -qf FILE`). A wheel always writes a `RECORD`, so a wheel-installed file never lands here.
- `pypi FAIL: unknown startup code in FILE (owner: DIST): FIRST-LINE`: any other code-executing `.pth` or `.start`.

Owners come from the `RECORD` files of installed wheels and, in a conda or pixi env, from `conda-meta/*.json` (conda-forge's setuptools has no `RECORD`). `none recorded` means neither lists the file.

| File | Written by | Code line | File and imported module must belong to |
|------|------------|-----------|------------------------------------------|
| `distutils-precedence.pth` | setuptools >= 49.3 | `import os; ... 'SETUPTOOLS_USE_DISTUTILS' ... add_shim();` | `setuptools` only |
| `_virtualenv.pth` | `uv venv`, virtualenv 20.x | `import _virtualenv` | no package, in a venv whose `pyvenv.cfg` has a `uv` or `virtualenv` key |
| `__editable__.<dist>-<ver>.pth` | setuptools editable install (finder mode) | `import __editable___<dist>_<ver>_finder; ...install()` | one package whose `direct_url.json` has `"editable": true` |
| `_editable_impl_<dist>.pth` | `editables` (hatchling `dev-mode-exact`) | `import _editable_impl_<dist>` | same |
| `_editable_skbc_<dist>.pth` / `.start` | scikit-build-core editable install | `import _editable_skbc_<dist>` / `_editable_skbc_<dist>:entrypoint` | same |
| `<dist>-editable.pth` / `.start` | meson-python editable install | `import _<dist>_editable_loader; ...init()` / `..._loader:init` | same |
| `<dist>-<ver>-py3.X-nspkg.pth` | setuptools namespace packages (matplotlib <= 3.7) | setuptools' generated line (31.x, 36–69 or 75+ template) for the package it names, character for character | not checked: the line imports no module |
| `a1_coverage.pth` | coverage >= 7.13 | `import sys; exec(...)` that starts coverage only if `COVERAGE_PROCESS_START`/`_CONFIG` is set | `coverage` only |
| `pytest-cov.pth` | pytest-cov < 7 | `import os, sys;exec(...)` gated on `COV_CORE_SOURCE` | `pytest-cov` only |

A known file name is not enough: a known name with any extra code FAILs, and so does a known file from the wrong owner. A tool that changes its text in a new release also FAILs. Read the whole file, and if it does only what the table row describes and its owner fits, report it as INFO and quote the new text.

**On a FAIL:** don't start that interpreter, because every start runs the code. Copy the file for evidence and treat the environment as compromised. Follow the `supply-chain-incident-response` skill.

`sitecustomize.py` and `usercustomize.py` also run at startup and are not scanned. Check by hand: `find <site-dir> -name '*customize.py'`.

## setup.py Execution at Install

Legacy sdist packages execute `setup.py` (arbitrary Python) at install time. PEP 517 build isolation runs this in a temporary venv, which limits some damage but still grants the script full filesystem read, outbound network, and write to the build temp dir. Wheel installs skip this, since wheels are pre-built artifacts.

Force the source path (and trigger `setup.py`):

```bash
pip install --no-binary <pkg> <pkg>   # forces source build, runs setup.py
```

Prefer wheels in CI and lockfiles:

```bash
pip install --only-binary :all: -r requirements.txt
```

If a package has no wheels for your platform, audit its `setup.py` before installing, or build the wheel once in a sandboxed environment and host it on an internal index.

## build_wheel and backend-path in pyproject.toml

PEP 517 lets a project declare a custom build backend in `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
# or, dangerously:
backend-path = ["./_custom_build"]   # backend is project-supplied code
```

A `backend-path` pointing to project code means installing the package executes that project-supplied backend in an isolated env. `pip install --no-build-isolation` (also `uv pip install --no-build-isolation`, `uv sync --no-build-isolation`, `no-build-isolation` / `no-build-isolation-package` under `[tool.uv]` or in `uv.toml`, or `no-build-isolation` under pixi's `[pypi-options]`) removes the isolation, so build backends run in the install environment.

`scripts/quick-check.sh` FAILs `--no-build-isolation` (and `--no-build-isolation-package`) in CI files, `Makefile` and `*.sh`, reading shell `\` continuations and folded YAML as one command. In `pyproject.toml`, `uv.toml` and `pixi.toml` it judges the value: `true` or a non-empty package list FAILs, `false` and `[]` pass. It WARNs on `backend-path`. Also review any non-standard `build-backend`:

```bash
grep -nE '^(build-backend|backend-path)' pyproject.toml
```

## OIDC Trusted Publishing for PyPI

The modern way to publish to PyPI from GitHub Actions, with no long-lived API tokens.

Setup steps:

1. On <https://pypi.org/manage/account/publishing/>, register a trusted publisher: owner, repo, workflow filename, environment (optional but recommended).
2. In the publish workflow, grant `id-token: write` and use the official action:

```yaml
permissions:
  id-token: write
jobs:
  release:
    environment: pypi
    steps:
      - uses: pypa/gh-action-pypi-publish@release/v1
```

3. No `PYPI_API_TOKEN` secret. PyPI verifies the GitHub OIDC token against the trusted-publisher record at upload time.

Cross-link: `supply-chain-hardened-ci-cd` for the broader OIDC + permissions story; `supply-chain-sbom-provenance` for PyPI's automatic Sigstore attestation on OIDC uploads.

## uv and poetry Lockfile Differences

`uv.lock` is a TOML lockfile with per-package hashes and platform markers. `poetry.lock` is a TOML lockfile with hashes. Both must be committed.

Lockfile-respecting installs (CI):

```bash
uv sync --locked                       # uv: errors if uv.lock is out of date
poetry check --lock && poetry install  # poetry: errors if poetry.lock is missing or stale
pip install --require-hashes -r requirements.txt  # pip-tools compiled
```

`uv sync --frozen` installs from `uv.lock` without checking it against `pyproject.toml`, so a stale lock passes. Use `--locked` in CI. Poetry 2.x has no `poetry install --no-update`. `poetry install` already errors on a stale lock but resolves from scratch when `poetry.lock` is missing, which `poetry check --lock` catches.

Plain `pip install -r requirements.txt` does not enforce hashes unless the requirements file uses `--hash=sha256:...` lines. Generate hash-pinned requirements with `pip-compile --generate-hashes` (pip-tools) or `uv pip compile --generate-hashes`.

## References

- PEP 517 build backends: <https://peps.python.org/pep-0517/>
- PEP 829 `.start` files: <https://peps.python.org/pep-0829/>
- `site` module (`.pth` processing): <https://docs.python.org/3/library/site.html>
- PyPI trusted publishing: <https://docs.pypi.org/trusted-publishers/>
- uv lockfile: <https://docs.astral.sh/uv/concepts/projects/lock/>
