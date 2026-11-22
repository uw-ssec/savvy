# Trigger fixture results

- Model: `ssec-claude-haiku-5-5`
- Repeats per case: 3; a case passes at >= 2/3 of its runs
- Skills passing every case: **1/76**
- Activation rate on `fire` runs: 40/729
- `no-fire` runs that loaded the target skill: 0/486
- Runs that failed (API or CLI errors, left out of the scores): 0

| Skill | Result | Failing cases (passes/runs, what was invoked) |
| --- | --- | --- |
| ai-research-workflows/creating-handoffs | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| ai-research-workflows/ensuring-reproducibility | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| ai-research-workflows/hardening-research-code | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| ai-research-workflows/implementing-plans | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| ai-research-workflows/iterating-plans | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| ai-research-workflows/planning-implementations | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| ai-research-workflows/researching | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| ai-research-workflows/running-experiments | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| ai-research-workflows/using-research-workflows | FAIL | `tired-01` tired 0/3 (none) |
| ai-research-workflows/validating-implementations | FAIL | `obvious-01` obvious 1/3 (ai-research-workflows:validating-implementations, none); `obvious-02` obvious 0/3 (none); `tired-01` tired 1/3 (ai-research-workflows:validating-implementations, none) |
| containerization/compose-orchestration | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| containerization/container-registries | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| containerization/container-security | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| containerization/devcontainers | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| containerization/dockerfile-patterns | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| containerization/gpu-containers | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| containerization/podman | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| containerization/singularity-apptainer | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| gaia-data-downloader/download-script-dev | FAIL | `obvious-01` obvious 1/3 (gaia-data-downloader:download-script-dev, none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| holoviz-visualization/advanced-rendering | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| holoviz-visualization/colormaps-styling | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 1/3 (holoviz-visualization:colormaps-styling, none); `tired-01` tired 0/3 (none) |
| holoviz-visualization/data-visualization | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 1/3 (holoviz-visualization:data-visualization, none); `tired-01` tired 0/3 (none) |
| holoviz-visualization/geospatial-visualization | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| holoviz-visualization/lumen-ai | FAIL | `obvious-02` obvious 0/3 (none) |
| holoviz-visualization/lumen-dashboards | FAIL | `tired-01` tired 0/3 (none) |
| holoviz-visualization/panel-dashboards | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| holoviz-visualization/parameterization | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| holoviz-visualization/plotting-fundamentals | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| project-management/community-health-files | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 1/3 (none, project-management:community-health-files); `tired-01` tired 0/3 (none) |
| project-management/documentation-validation | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| research-software-design/user-persona-discovery | FAIL | `obvious-01` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| scientific-domain-applications/astropy-fundamentals | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| scientific-domain-applications/xarray-for-multidimensional-data | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| scientific-python-development/code-quality-tools | FAIL | `obvious-01` obvious 1/3 (none, scientific-python-development:code-quality-tools); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| scientific-python-development/pixi-package-manager | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| scientific-python-development/python-packaging | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| scientific-python-development/python-testing | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| scientific-python-development/scientific-documentation | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| supply-chain-security/supply-chain-dependency-security | FAIL | `obvious-01` obvious 1/3 (none, supply-chain-security:supply-chain-dependency-security); `obvious-02` obvious 1/3 (none, supply-chain-security:supply-chain-dependency-security); `tired-01` tired 1/3 (none, supply-chain-security:supply-chain-dependency-security); `tired-02` tired 0/3 (none) |
| supply-chain-security/supply-chain-ecosystem-quirks | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| supply-chain-security/supply-chain-hardened-ci-cd | FAIL | `obvious-01` obvious 1/3 (none, supply-chain-security:supply-chain-hardened-ci-cd); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| supply-chain-security/supply-chain-incident-response | PASS |  |
| supply-chain-security/supply-chain-sbom-provenance | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| supply-chain-security/supply-chain-threat-awareness | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (supply-chain-security:supply-chain-audit); `tired-01` tired 0/3 (none) |
| uiux-design-team/ab-testing-strategy | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| uiux-design-team/accessibility-audit | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| uiux-design-team/color-systems | FAIL | `obvious-01` obvious 1/3 (none, uiux-design-team:color-systems); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| uiux-design-team/component-library | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/css-architecture | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/design-case-studies | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/design-handoff | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/design-philosophies | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/design-system-creation | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/design-tokens | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/frontend-components | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/grid-layout-systems | FAIL | `obvious-01` obvious 0/3 (dataviz, none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/information-architecture | FAIL | `obvious-01` obvious 1/3 (none, uiux-design-team:information-architecture); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/motion-design | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/responsive-design | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/typography-systems | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| uiux-design-team/usability-evaluation | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/user-journey-mapping | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/user-research | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/ux-writing | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| uiux-design-team/visual-design | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/wireframing | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| zarr-chunk-optimization/access-pattern-analysis | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| zarr-chunk-optimization/chunking-strategy | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| zarr-chunk-optimization/performance-reporting | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| zarr-chunk-optimization/rechunking | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| zarr-chunk-optimization/synthetic-data | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| zarr-data-format/cloud-storage-backends | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| zarr-data-format/compression-codecs | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| zarr-data-format/data-migration | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| zarr-data-format/zarr-fundamentals | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| zarr-data-format/zarr-xarray-integration | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
