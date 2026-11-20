---
name: python-packaging
description: Use when writing or migrating (from setup.py) a scientific Python package's pyproject.toml, building wheels with Hatchling, or publishing to PyPI or TestPyPI. Not for environments, tests, or docs.
metadata:
  author: SSEC Engineering Team
  tags: packaging pyproject hatchling pypi trusted-publishing
  assets: assets/pyproject-minimal.toml assets/pyproject-full-featured.toml assets/readme-template.md assets/github-actions-publish.yml assets/sphinx-conf.py assets/.gitignore assets/cli-example.py
  references: references/common-issues.md references/docstrings.md references/metadata.md references/patterns.md
---

# Scientific Python Packaging

Package scientific Python code the way the Scientific Python Development Guide recommends: a `src/` layout, Hatchling, all metadata in `pyproject.toml`, and releases published from CI with Trusted Publishing.

## Purpose

- Start a package, or migrate `setup.py`/`setup.cfg` to `pyproject.toml`
- Build, check, and publish a release
- Find out why a data file, entry point, or dependency is missing from the installed package

Not for environments and lockfiles (`scientific-python-development:pixi-package-manager`), test setup (`scientific-python-development:python-testing`), or Sphinx and Read the Docs (`scientific-python-development:scientific-documentation`).

## Prerequisites

- Python ≥ 3.13 with `build` and `twine` (`pip install build twine`)
- pip ≥ 25.1 for `pip install --group`
- To publish: a GitHub repository with Actions, and a PyPI account (plus a separate TestPyPI account for dry runs)

## Quick Reference

| Situation | Use |
|-----------|-----|
| New package | `src/<pkg>/` plus the [assets/pyproject-minimal.toml](assets/pyproject-minimal.toml) template |
| Migrating `setup.py` | `install_requires` → `dependencies`, `extras_require` → `[project.optional-dependencies]`, `console_scripts` → `[project.scripts]`, `python_requires` → `requires-python` |
| `package_data` | Nothing to configure: Hatchling ships every file in the package that git doesn't ignore |
| Python floor | `requires-python = ">=3.13"` (SPEC 0 as of late 2026; check [SPEC 0](https://scientific-python.org/specs/spec-0000/)), no upper cap |
| License | `license = "BSD-3-Clause"` plus `license-files = ["LICENSE"]`; no `License ::` classifier (PEP 639 deprecates it) |
| Dev tools | `[dependency-groups]`; `pip install -e . --group dev` |
| Optional user features | `[project.optional-dependencies]` |
| Version from git tags | `hatch-vcs`; see [references/patterns.md](references/patterns.md) |
| CLI | `[project.scripts] sci-analyze = "my_sci_package.cli:main"`; Click template in [assets/cli-example.py](assets/cli-example.py) |
| Build and check | `python -m build` then `twine check --strict dist/*` |
| Release | [assets/github-actions-publish.yml](assets/github-actions-publish.yml) |

## Publishing

Publish from CI with Trusted Publishing, not an API token. Copy `assets/github-actions-publish.yml`, keep its actions pinned to commit SHAs, then add a trusted publisher on PyPI for that workflow file and the environment `pypi`. The build job has no credentials; only the publish job can request a token, and it never checks out code.

Dry-run on TestPyPI first, installing only your package from it:

```bash
twine upload --repository testpypi dist/*
pip install numpy scipy        # your dependencies, from PyPI
pip install --no-deps --index-url https://test.pypi.org/simple/ <your-package>
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ValueError: Unable to determine which files to ship inside the wheel` | The import name differs from the project name, so Hatchling can't find the package | Set `[tool.hatch.build.targets.wheel] packages = ["src/<pkg>"]` |
| `no such option: --group` | pip is older than 25.1 | `python -m pip install -U "pip>=25.1"` |
| A data file is missing from the wheel | Hatchling skips git-ignored files | Check `.gitignore`, then list the wheel with `python -m zipfile -l dist/*.whl` before uploading |
| `400 File already exists` on upload | PyPI and TestPyPI never accept the same filename twice, even after deletion | Bump the version (for example `1.4.0rc2`) and rebuild |
| A TestPyPI install pulls in a look-alike dependency | `--extra-index-url https://test.pypi.org/simple/` lets pip take the highest version from either index | Install dependencies from PyPI, then your package with `--no-deps`, as above |
| Users on newer Python get an old release | An upper cap such as `<3.12` on `requires-python`, often kept from `setup.py` | Drop the cap |
| Tests pass, but the installed package fails | The tests ran against the source tree | Install `dist/*.whl` in a fresh environment and run the tests there |

## Limitations

- Covers pure-Python packages built with Hatchling. Compiled extensions need another backend (scikit-build-core or meson-python) and cibuildwheel.
- Doesn't cover conda-forge recipes.
- The Python floor and the action SHAs in the assets date from November 2026. Re-check SPEC 0 and re-resolve the SHAs when you copy them.

## References

- Version constraints, classifiers, extras, dependency groups: [references/metadata.md](references/metadata.md)
- Data files, versioning, building, install testing: [references/patterns.md](references/patterns.md)
- NumPy-style docstrings: [references/docstrings.md](references/docstrings.md)
- Import errors, missing files, dependency conflicts: [references/common-issues.md](references/common-issues.md)
- Scientific Python Development Guide: https://learn.scientific-python.org/development/guides/packaging-simple/
