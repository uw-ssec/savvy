# Writing the provenance record

Read this when you write or audit the `## Reproducibility` record: it has the
full field list, where the record goes, what to do without a lockfile, how to
state a tolerance, and a record skeleton.

## What to capture

A complete provenance record includes:

- **Environment**: interpreter or compiler version (e.g., `python 3.12.3`),
  OS, and the dependency lockfile that was active (e.g., `pixi.lock`,
  `uv.lock`, a frozen requirements file).
- **Code version**: the commit hash of the analysis/model code itself
  (`git rev-parse HEAD`); note if the working tree was dirty
  (`git status --porcelain`). Pinning the environment but not the code that
  produced the result defeats reproduction. If the copy has no git history,
  say so and record content hashes of the scripts instead.
- **Hardware / accelerator**: for GPU, accelerated, or parallel runs, record
  the device, CUDA/driver version, and thread/process counts; these change
  numerical results and explain nondeterminism. If they can only be read on
  the original machine, say that in the record rather than guessing.
- **Data inputs**: file paths or URLs, plus a version tag, commit hash, or
  content hash (e.g., `sha256:abc123`) for each dataset. For remote data,
  record the retrieval date.
- **Random seeds**: every seed passed to NumPy, PyTorch, stdlib `random`, or
  any other RNG. If the code reads seeds from config, pin that config value.
  For each RNG in use, state whether its seed was found; an unseeded RNG is a
  finding, not an omission.
- **Configuration and parameters**: all non-default flags, hyperparameters,
  or config file contents that affect the result. A seed written in a README
  or comment is not captured if the code reads it from a config file that was
  not pinned; record the config file's contents or the commit that holds it.
- **Exact commands**: the full shell commands run, in order, from a fresh
  checkout to the result, so someone can copy-paste them into a clean
  environment. One command per line, no paraphrase ("run the training
  script" is not a command):

  ```bash
  pixi run python train.py --config configs/baseline.yaml --seed 42
  pixi run python evaluate.py --checkpoint outputs/run-001/best.ckpt
  ```

- **Result**: the reported values themselves (metric, figure, file hash), so
  a reproduction has something to be compared with.
- **Verification**: the outcome of the clean-room reproduction (success,
  failure, or the tolerance applied), or the technical reason it was
  impossible.

If reproducing someone else's work, note what was missing from their record.

## No lockfile

If the project has no lockfile, the environment is not pinned yet. Do not
stop there and do not invent one silently:

1. Record the exact installed versions of every dependency the result uses
   (for example `python -m pip freeze`, `pixi list`, `conda list --export`, or
   `importlib.metadata.version(...)` for each import) in the record itself.
2. State in the record that no lockfile existed, so the reader knows the
   versions were read from the running environment, not from a pin.
3. In the clean-room run, install exactly those versions, and suggest adding
   a lockfile as a follow-up (see the environment-pinning skills below).

## Where the record lives

Append a `## Reproducibility` section to the relevant artifact in
`docs/rse/specs/` (or its legacy `.agents/` location):

- experiment result → `docs/rse/specs/experiment-<slug>.md`
- implementation result → `docs/rse/specs/implement-<slug>.md`
- no existing artifact → create `docs/rse/specs/reproducibility-<slug>.md`

A new `reproducibility-<slug>.md` still carries a `## Reproducibility`
heading, so the record is found the same way wherever it lives. The
`ai-research-workflows:running-experiments` and
`ai-research-workflows:implementing-plans` skills write the experiment and
implementation artifacts.

Keep credentials out of the record: no tokens in recorded URLs, no secret
values from config files, no environment dumps.

## Tolerance for nondeterministic outputs

For nondeterministic outputs (parallelism, GPU float accumulation, stochastic
sampling with no fixed seed), define and document a tolerance from repeated
runs, and name the seeds and hardware that produced it:

```
Metric: validation accuracy
Expected: 0.847 ± 0.003 (3 independent runs with seeds 42, 123, 999)
Hardware: 1x A100 80GB, CUDA 12.4, driver 550.54, 8 data-loader workers
```

A value inside the documented tolerance reproduces; one outside it does not.
For deterministic outputs, say that the comparison is exact (identical value
or identical file hash) and why no tolerance is needed.

## Environment pinning mechanics

This skill decides **what** provenance to record; other skills handle **how**
to pin the environment:

- **conda + PyPI, multi-platform lockfiles** → defer to
  `scientific-python-development:pixi-package-manager`
- **PyPI-only lockfiles** → commit `uv.lock` and install with
  `uv sync --frozen` (no dedicated skill here)

The provenance principles are language-agnostic: apply them the same way to
R, Julia, Rust, or any other runtime.

## Record skeleton

```markdown
## Reproducibility

**Status:** verified | unverified (reason)

- Environment: Python 3.12.3 on Ubuntu 24.04; lockfile `pixi.lock`
  (or: no lockfile; versions below read with `pip freeze`)
- Code: commit `3f2c1e9`, working tree clean
- Hardware: CPU only, 1 thread
- Data: `data/measurements.parquet` sha256:`9b1d4c07e2a8`, retrieved 2026-05-04
- Seeds: `42` (NumPy and stdlib `random`, from `configs/run.yaml`)
- Config: `configs/run.yaml` at commit `3f2c1e9` (contents below)
- Result: validation F1 0.912

Commands, in a fresh clone checked out at the recorded commit:

    pixi install --frozen
    pixi run python evaluate.py --config configs/run.yaml

Verification: re-ran in a fresh clone with a clean environment on
2026-05-06; F1 0.912, identical to the reported value.
```
