# Changelog

All notable changes to this repository are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this repository follows the [versioning policy](docs/versioning.md) — Ubuntu-style Calendar Versioning, with each plugin's manifest version set to the release in which that plugin last changed.

## How to add an entry

Add your entry under `## [Unreleased]`, inside the `###` subsection for the plugin you changed. Use the Keep a Changelog categories as `####` headings: **Added**, **Changed**, **Deprecated**, **Removed**, **Fixed**, **Security**.

A `Deprecated` entry must say what replaces the deprecated thing — or state that nothing does, and why — and give the earliest removal date, as required by the [deprecation policy](docs/deprecation.md).

Changes that touch no plugin — CI, repository documentation, tooling — go under [Repository](#repository) rather than a plugin subsection.

## [Unreleased]

### containerization

#### Added

- Initial tagged release.

#### Fixed

- `podman`: Quadlet examples no longer run `systemctl --user enable` on the generated unit, which systemctl refuses ("transient or generated"); the `[Install]` section handles auto-start, and the examples now use `start`.
- `dockerfile-patterns`: "Mistake 4" no longer claims stage names are case-sensitive. BuildKit lowercases them; the real trap is a misspelled `--from`, which is pulled as an image.
- `compose-orchestration`: merge rules say volumes merge by container path instead of concatenating, and that identical ports appear once (use `!override` to replace the list). Interpolation priority drops `env_file:`, which never feeds interpolation, and says `--env-file` replaces the project `.env`. An unset `${VAR}` warns and becomes empty instead of failing, and `.env` files do support inline comments and quoted multi-line values.
- `devcontainers`: the Codespaces prebuild lifecycle no longer runs `postCreateCommand` during the prebuild; it runs when the codespace is created. The multi-file Compose example adds the required `workspaceFolder`.
- `gpu-containers`: the driver/CUDA rules no longer say a 535 driver tops out at CUDA 12.2. They explain minor version compatibility (CUDA 12.x on 525+, without PTX JIT) and that each `nvidia/cuda` tag lists the extra driver branches it starts on, and the GPU brands each applies to, in `NVIDIA_REQUIRE_CUDA`, with a command to check. The forward/backward compatibility terms now match NVIDIA's, and the compat package is limited to data center and select GPUs.
- `singularity-apptainer`: the MPI hybrid model now matches the Apptainer docs: the host's launcher starts the containers and the container's MPI must be compatible with the host's. Running `mpirun` inside one container is labeled a single-node test. The three definition-file assets no longer fail to build: comment lines inside `\`-continued `apt-get install` lists ended the command in `%post`, the MPI asset deleted its own working directory before `pip` ran, and the GPU asset's base image `nvidia/cuda:12.4.1-devel-ubuntu24.04` (and the ROCm alternative `rocm/dev-ubuntu-24.04:6.1`) don't exist, so they now use the Ubuntu 22.04 tags.
- `container-security` and `container-registries`: keyless `cosign verify` and `verify-attestation` examples name the signer identity and OIDC issuer, which cosign v3 requires. The Chainguard example uses its exact identity and the SLSA v1 predicate type.
- `container-security` and `container-registries`: SBOMs are attached as signed attestations (`cosign attest --type spdxjson`) instead of the deprecated `cosign attach sbom`, and the SBOM verification uses the matching `spdxjson` type. The obsolete `COSIGN_EXPERIMENTAL` setting is gone.
- `container-security` and `container-registries`: the SLSA generator examples call `generator_container_slsa3.yml` as a job, as reusable workflows must be, with the permissions and inputs its docs list, a GHCR image that matches the `GITHUB_TOKEN` it passes, and a note that the generator is no longer maintained and GitHub artifact attestations are the suggested replacement.
- `container-registries`: the Azure ACR example runs `az acr login` after the OIDC login instead of `azure/docker-login`, which is unmaintained and needs a username and password. The multi-platform matrix names its digest artifacts by runner, since artifact names can't contain `/`.
- `container-security`: the nightly scans log in to GHCR before reading the image, the SARIF jobs grant `actions: read` for private repositories, and the complete verification pipeline runs on pushes to `main` with `id-token: write` (a pull request from a fork can't sign) and lists its tool prerequisites.
- `container-security`: the PR scan examples lowercase the image name (`${GITHUB_REPOSITORY,,}`), so `docker build -t` no longer fails for owners with capital letters.

#### Security

- `container-security`: Trivy, Grype and Syft installs no longer pipe `install.sh` from the `main` branch into `sh`. They download a pinned release, check it with `sha256sum` against the release checksums (with an optional `cosign verify-blob` of the checksums file), and pin the Docker image tags. The Trivy apt setup drops the deprecated `apt-key add` for a dearmored keyring with `signed-by`.
- `devcontainers`: the example Feature `install.sh`, which runs as root, downloads a versioned artifact and checks a pinned SHA-256 instead of piping a script into `bash`.
- `container-security`: the nightly CI scans resolve the published tag to a digest once and scan that, instead of pulling `:latest`.
- `container-security`, `container-registries` and `dockerfile-patterns`: every `uses:` in the workflow assets and Markdown examples is pinned to a commit SHA with a version comment, keeping each example's major version (except `sigstore/cosign-installer`, moved from v3.10.1 to v4.1.3 because v3 installs cosign v2.6.1, affected by CVE-2026-22703), replacing mutable refs such as `aquasecurity/trivy-action@master` and `@0.28.0` (the TeamPCP tag hijack moved 76 `trivy-action` tags). The Grype example moves to `anchore/scan-action` v7.4.2 with Grype pinned to v0.121.3, since v4.1.2 ran a Grype too old to get database updates. Checkout no longer persists credentials in these assets. The SLSA generator stays on its `v2.0.0` tag, which slsa-verifier requires, with a comment saying why.
- `container-security` and `container-registries`: the workflow assets deny permissions at the top level and grant each job only what it needs (the GHCR publish job drops unused `attestations: write` and `id-token: write`), and pass step outputs to `run:` through `env`.
- `singularity-apptainer`: the MPI definition asset and the Open MPI, MPICH and PMIx builds in `references/mpi-containers.md` verify each source tarball's SHA-256 before building. MPICH downloads from the project's GitHub release. The PMIx example notes that 4.2.9 ends its series.
- `compose-orchestration`: the pgAdmin default email uses the reserved `example.com` instead of the registrable `localhost.com`.

### gaia-data-downloader

#### Added

- Initial tagged release.

### holoviz-visualization

#### Added

- Initial tagged release.

#### Fixed

- Fixed broken HoloViz, Panel, Lumen, hvPlot, and Param documentation links in the README and the `colormaps-styling`, `lumen-ai`, `lumen-dashboards`, and `parameterization` skills, refs #249.

### project-management

#### Added

- Initial tagged release.

#### Fixed

- Fixed broken links in the `community-health-files` and `documentation-validation` skill references, refs #249.

### research-software-design

#### Added

- Initial tagged release.

### scientific-domain-applications

#### Added

- Initial tagged release.

#### Fixed

- Fixed broken rioxarray and Geocube documentation links in the README, refs #249.

### scientific-python-development

#### Added

- Initial tagged release.

#### Fixed

- Fixed broken links in the `scientific-documentation` skill references, refs #249.

### supply-chain-security

#### Added

- Initial tagged release.
- `supply-chain-ecosystem-quirks`: `scripts/quick-check.sh` runs the npm, PyPI, conda/pixi, cargo and Go checks and reports each finding with its `file:line`. Its `--pth-only` mode is the canonical Python `.pth`/`.start` startup-code check that other supply-chain skills point to: known-good files are INFO only when name and content match what their tool writes, and unknown code-executing files FAIL.

#### Changed

- `supply-chain-dependency-security`: the description lists triggers only and leaves reported compromises to `supply-chain-incident-response`. CI install commands now fail on a stale lockfile (`pixi install --locked`, `uv sync --locked`, and a `--check-input-hash` step for conda-lock), and Yarn disables install scripts explicitly. The 7-day cooldown gains a resolver setting per tool and a publish-time check for versions a lockfile diff adds. The skill now has When to Use, Quick Reference, rationalization, red-flag and Common Mistakes sections.
- `supply-chain-ecosystem-quirks`: the description is trigger-only, and the quick-check battery moves from `SKILL.md` into the script.
- `supply-chain-hardened-ci-cd`: the description lists only when to use the skill, and the body is restructured around a quick reference, rationalizations and red flags. Every example action is pinned to a commit SHA, including the PyPI publish action that was on `@release/v1`. The OIDC example, which wasn't valid YAML, is now a complete build/publish workflow in `references/hardening-patterns.md`, where the publish job runs no project code: PyPI builds with `PIP_ONLY_BINARY=:all:`, and npm packs the tarball in the build job and publishes it with `--ignore-scripts`.
- `supply-chain-threat-awareness`: the description lists triggers only, and the audit commands moved to `references/audit-commands.md`. Each campaign now has the dates it was observed and primary sources; Shai-Hulud is described as a self-propagating worm with a second wave in November 2025, and TeamPCP as running from March to April 2026.

#### Fixed

- `supply-chain-ecosystem-quirks`: references corrected against current tools: npm 12's `allowScripts`, pnpm's `allowBuilds` and Yarn 4.14's `enableScripts` default; `uv sync --locked`, `pixi install --locked` and `poetry check --lock` in place of flags that skip the lockfile check or don't exist; Go's `-mod=readonly` is already the default, so `-mod=mod` is flagged instead; the removed `-insecure` flag; `Cargo.lock` guidance; and the PyTorch-nightly compromise no longer attributed to `setup.py`.
- `supply-chain-threat-awareness` and `/supply-chain-audit`: the action-pinning scan flags every mutable `uses:` ref, including `.yaml` files, local composite actions anywhere in the repository, untracked files, flow-style and quoted-key YAML, `docker://` tags and SHA-prefixed branches.
- `supply-chain-threat-awareness`: cooldown is measured as each version's age when the change adopting it was merged, locked installs require `--locked`, the lifecycle-script query lists all eight hooks npm runs for the project on install, and the LiteLLM check no longer runs `pip show` in the suspect environment.
- Fixed broken links in the `supply-chain-ecosystem-quirks` skill references, refs #249.
- `supply-chain-incident-response`: the description is now trigger-only, and commands that did nothing or reported a false PASS are replaced: the advisory lookup, lockfile grep and history, `gh cache` listing and deletion by id, `find -newermt`, the postinstall query and the tag-hijack audit loop. Recovery re-enables the disabled workflows and starts a fresh run from the fixed commit. The npm rotation creates a granular, package-scoped token with an expiry (npm 11.6.3 or later, or npmjs.com for older clients).
- `/supply-chain-incident` is now user-invoked only (`disable-model-invocation: true`), so incident prompts load `supply-chain-incident-response` instead of the command, and its paths to the rotation guide and report template now go through the skill.

### uiux-design-team

#### Added

- Initial tagged release.

### zarr-chunk-optimization

#### Added

- Initial tagged release.

#### Changed

- `access-pattern-analysis`: each pattern now records the `--slice-dims`/`--traverse-dims` arguments `benchmark_runner.py` actually takes, and the skill checks coordinate order and longitude convention before writing any `sel()`. The description is now trigger-only.
- `access-pattern-analysis`: corrects the example byte counts, chunk-shape recommendations (now ~1 MB), sharding and Kerchunk/VirtualiZarr claims, and outdated pandas/xarray calls (`resample("1M")`, `DataArray.visualize()`).
- `rechunking` works under zarr-python 3, where `rechunker` can't be installed: it routes single arrays, sharded targets, flat groups and nested groups to `zarr.from_array`, xarray or dask, and its description is trigger-only.
- `rechunking` validation examples run on Zarr v3 stores and compare values exactly, with NaN treated as equal in float and complex data, instead of checking shape alone.

#### Fixed

- `chunking-strategy`: benchmark each candidate as its own rechunked store, since `benchmark_runner.py` only labels results with `--configs` and never applies them. Also corrects the time-series `--traverse-dims` flag, the rechunk example (stale `encoding["chunks"]`), `sel` vs `isel` on datetime coordinates, the overhead, cost and memory arithmetic, KB-sized "optimal" chunks, zarr 2-only APIs, and the statistics guidance.
- `chunking-strategy`: the description is now trigger-only ("Use when ...").
- `performance-reporting` now reads the JSON that `benchmark_runner.py` actually writes, with a tested loader, and stops reporting TTFB and chunk utilization, which the runner never measures.
- `performance-reporting` drops the weighted pattern-bias score, which rated equal times as unbalanced, and corrects the example numbers, table sorting and ranking rules to match `chunking-strategy`.
- Fixed the broken DOI and title for the Nguyen et al. (2023) paper cited in the README, refs #249.

### zarr-data-format

#### Added

- Initial tagged release.

#### Changed

- `zarr-fundamentals`: the description now says only when to use the skill, and no longer covers the cloud, codec, migration and xarray topics that belong to sibling skills.
- `compression-codecs`: rewritten for zarr 3. Examples use `compressors=[zarr.codecs...]` and `zarr.codecs.numcodecs` filters instead of the v2 `compressor=` and numcodecs filters that raise on v3 arrays (v2 is kept as an explicit `zarr_format=2` path), invented compression ratios are replaced with measured ones, and the description is now trigger-only.
- `compression-codecs`: `assets/codec-comparison.py` now benchmarks through zarr on real or supplied data, and the skill corrects filter order (Quantize before Delta), uses `Crc32cCodec`/Zstd checksums for integrity checks, and drops the unsupported Blosc fork-corruption claim.
- `data-migration`: the description is trigger-only, and a Zarr v2 to v3 route is added. `zarr.copy` (`NotImplementedError` in zarr 3) and `rechunker` (needs `zarr<3`) are dropped in favor of `zarr-chunk-optimization:rechunking`.

#### Fixed

- `zarr-fundamentals`: examples and advice now match zarr-python 3. The sharding example no longer swaps chunks and shards, `resize` takes a tuple, the removed synchronizers give way to a one-writer-per-chunk (or shard) rule, and the quickstart script runs without `rich` and removes its temp directory.
- `zarr-xarray-integration`: encoding examples and the bundled round-trip script now pass `chunks` as a tuple, which xarray requires, and drop stale chunk encoding before rechunked writes. Append and region-write recipes now avoid silent data damage, and the guidance on consolidated metadata, `open_zarr` chunk defaults and `compressors=` codecs is corrected. The description now says only when to use the skill.
- `cloud-storage-backends`: rewrite the Icechunk examples for the current `Repository` and session API (the 0.1 `StorageConfig`/`IcechunkStore` API no longer exists), document which fsspec and zarr caches actually work with `FsspecStore`, and correct the CMIP6 example, the `zarr[remote]` extra, GCS anonymous access, v3 consolidated metadata, slow-open causes and broken helper snippets.
- `cloud-storage-backends`: replace hard-coded MinIO, Azure and AWS credentials in the examples with environment variables, profiles or managed identity.
- `data-migration`: recipes that corrupted data with no error. `encoding=` now keeps packing, fill values, `missing_value` and `_Unsigned` data; appended finer time steps get correct dates; kerchunk merges keep every file's times; and validation compares attribute values, including global attributes, without loading whole arrays. The VirtualiZarr 2.x, Icechunk and h5py code runs on current releases.

## [26.11.0] -- 2026-11-25

First tagged release. Only `ai-research-workflows` ships in it and moves to this release's version. The other plugins are marked `released: false` in [docs/catalog.yml](docs/catalog.yml) until they are ready, so no marketplace lists them yet, and their entries stay under [Unreleased](#unreleased) until the release that ships them.

### ai-research-workflows

#### Added

- Initial tagged release.
- Capability metadata, a skill card and a public eval task set on each skill, as part of the skill trust evidence pilot ([#293](https://github.com/uw-ssec/savvy/issues/293)).

#### Changed

- `ensuring-reproducibility`: `SKILL.md` is now a short entry point (Iron Law, field table, clean-room steps, red flags). The full field list, record location and tolerance example moved to a new `references/provenance-record.md`, which also adds steps for a project with no lockfile and a record skeleton. The description gains triggers for numbers that differ across runs or machines, reviewer or journal requests and reporting a number in a paper, and names the neighboring skills it doesn't own ([#155](https://github.com/uw-ssec/savvy/issues/155)).
- `validating-implementations`: slimmer `SKILL.md` (detail moved to `references/`) with explicit rules to investigate "flaky" failures, write the report file even for chat-only requests, choose one overall status and leave the code under review unchanged ([#163](https://github.com/uw-ssec/savvy/issues/163)).
- `creating-handoffs`: slimmed `SKILL.md` to an entry point with a quick-reference table and moved the section-by-section detail, next-skill table and summary format to `references/writing-guide.md`; the skill now has the agent re-run the tests, leave the working tree as it found it, and check its account of the work against the repository, and its description names more triggers and its neighbors ([#154](https://github.com/uw-ssec/savvy/issues/154)).
- `hardening-research-code`: SKILL.md is now a short entry point (Iron Law, a criteria quick-reference table, the tolerance rule, the workflow and red flags), with the per-test-type detail moved to `references/techniques.md`; it now says what to do when a correctness test fails on the current code, and its description covers more trigger phrasings and names neighboring skills ([#156](https://github.com/uw-ssec/savvy/issues/156)).
- `implementing-plans`: SKILL.md is now a short entry point (hard gates, workflow, red flags) with the step detail in `references/workflow.md`; it now says when drift becomes a mismatch, that it may create a feature branch, and that it commits only at the plan's commit steps, and its summary template no longer shows unconfirmed manual checks as done ([#157](https://github.com/uw-ssec/savvy/issues/157)).
- `researching`: the description lists triggers only and names `running-experiments` and `planning-implementations` as the neighbors it doesn't cover. `SKILL.md` is cut to a quick reference, the interaction-mode rule and the hard rules; the presenting, writing, self-review and user-review detail moves to `references/writing-and-review.md`, and the research template gains a **Codebase state** field for the commit SHA. The false claim that `using-research-workflows` surveys this skill automatically is gone ([#160](https://github.com/uw-ssec/savvy/issues/160)).
- `running-experiments`: `SKILL.md` is a short entry point (Iron Law, red flags, process table, checklist) with detail moved to `references/running-the-comparison.md` and `references/reporting.md`. It now says what to do when the user asks not to run anything and how to keep and clean up prototypes, and its description adds "prototype both" and "which is faster on our data" triggers ([#161](https://github.com/uw-ssec/savvy/issues/161)).
- `iterating-plans`: SKILL.md cut to a short entry point (from about 1,000 words) with a numbered, required consistency scan, a Quick Reference table and confirmation keyed to the interaction mode (Collaborative confirms before editing; Direct states the edits, then applies them). The message templates and edit guidance moved to `references/iteration-patterns.md`, and the description adds split, reorder and feedback triggers and names its neighbors ([#158](https://github.com/uw-ssec/savvy/issues/158)).
- `planning-implementations`: `SKILL.md` is now a short entry point (when to use, mode, process, hard rules), and the section, task-shape, placeholder and checklist detail moves to `references/plan-writing.md`. The plan template's "Open Questions" section becomes "Resolved Decisions", so filling in the template no longer reintroduces the section the skill forbids. A request to leave a decision open now gets options and a recommendation instead of an unresolved plan, and Direct mode applies only when the user asks for it or can't be consulted.
- `using-research-workflows`: slim the entry point to the rule, instruction priority, decision tree and pointers; move workflow patterns, red flags and common mistakes to `references/workflow-patterns.md` and document naming and deferral to `references/conventions.md`; an explicitly skipped step is skipped while urgency only selects Direct mode, and the agent states the route and writes the research document before editing ([#162](https://github.com/uw-ssec/savvy/issues/162)).

### Repository

#### Added

- Skill trust evidence pilot for `ai-research-workflows` ([#293](https://github.com/uw-ssec/savvy/issues/293)): a skill card and a public eval task set (`evals/evals.json`) for each skill, a manually run benchmark workflow (`BENCHMARK.md`, reported and never gating), and per-skill archives signed with Sigstore by `release-sign.yml` when a release is published. These files don't count as plugin changes for [versioning](docs/versioning.md). See [Checking a skill before you install it](docs/trust-and-safety.md#checking-a-skill-before-you-install-it) and [Signed skill archives](docs/releasing.md#signed-skill-archives). Signing starts with the first release cut after this change merges, and the `release` skill no longer builds an unsigned zip for `ai-research-workflows`.
- `CHANGELOG.md`, a [versioning policy](docs/versioning.md), and a [deprecation policy](docs/deprecation.md).
- `zenodo-publish.yml` and the `zenodo-publish` action archive savvy on Zenodo through the API, in place of the Zenodo GitHub integration: a published release goes to zenodo.org, and a push to `main` or a manual run goes to sandbox.zenodo.org. See [Citation and DOI](docs/releasing.md#citation-and-doi).
- [docs/codespaces.md](docs/codespaces.md), with the Codespaces and LiteLLM gateway setup moved out of the README.
- README badges for CI, the Zenodo DOI, the license, and pixi.
- `released: false` in [docs/catalog.yml](docs/catalog.yml) holds a plugin back from a release: no marketplace lists it and the [skill catalog](docs/catalog.md) leaves it out, while CI still checks it. Every plugin except `ai-research-workflows` is held back for now.

#### Changed

- The README is shorter and points to the [skill catalog](docs/catalog.md) and the other docs instead of listing every plugin, skill, and agent itself.
- [docs/install.md](docs/install.md) and [docs/trust-and-safety.md](docs/trust-and-safety.md) cover Antigravity CLI instead of Gemini CLI, which Google retired for most users in June 2026. Each plugin README's note on client support now says which parts Antigravity CLI loads.

#### Fixed

- Removed the `lychee.toml` link-check exclusions for the links fixed in #249 and the `softwareheritage.org` TLS workaround; `vizier.cds.unistra.fr` stays excluded, with the reason noted, as do the README's Zenodo DOI badge links until the first release is archived.
