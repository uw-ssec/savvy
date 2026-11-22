# Trigger fixture results

- Model: `ssec-claude-opus-5-5`
- Repeats per case: 3; a case passes at >= 2/3 of its runs
- Skills passing every case: **12/76**
- Activation rate on `fire` runs: 304/729
- False-trigger rate on `no-fire` runs: 0/486

| Skill | Result | Failing cases (passes/runs, what was invoked) |
| --- | --- | --- |
| ai-research-workflows/creating-handoffs | FAIL | `tired-01` tired 0/3 (none) |
| ai-research-workflows/ensuring-reproducibility | PASS |  |
| ai-research-workflows/hardening-research-code | FAIL | `tired-01` tired 0/3 (none) |
| ai-research-workflows/implementing-plans | FAIL | `tired-01` tired 0/3 (none) |
| ai-research-workflows/iterating-plans | PASS |  |
| ai-research-workflows/planning-implementations | FAIL | `tired-01` tired 0/3 (none) |
| ai-research-workflows/researching | FAIL | `tired-01` tired 0/3 (none) |
| ai-research-workflows/running-experiments | FAIL | `tired-01` tired 1/3 (ai-research-workflows:running-experiments, none) |
| ai-research-workflows/using-research-workflows | PASS |  |
| ai-research-workflows/validating-implementations | PASS |  |
| containerization/compose-orchestration | FAIL | `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| containerization/container-registries | FAIL | `tired-01` tired 0/3 (none) |
| containerization/container-security | PASS |  |
| containerization/devcontainers | FAIL | `tired-01` tired 0/3 (none) |
| containerization/dockerfile-patterns | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| containerization/gpu-containers | FAIL | `obvious-01` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| containerization/podman | FAIL | `tired-01` tired 0/3 (none) |
| containerization/singularity-apptainer | FAIL | `obvious-02` obvious 1/3 (containerization:singularity-apptainer, none); `tired-01` tired 0/3 (none) |
| gaia-data-downloader/download-script-dev | PASS |  |
| holoviz-visualization/advanced-rendering | FAIL | `obvious-02` obvious 0/3 (none) |
| holoviz-visualization/colormaps-styling | FAIL | `tired-01` tired 0/3 (none) |
| holoviz-visualization/data-visualization | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (dataviz) |
| holoviz-visualization/geospatial-visualization | FAIL | `tired-01` tired 0/3 (none) |
| holoviz-visualization/lumen-ai | PASS |  |
| holoviz-visualization/lumen-dashboards | PASS |  |
| holoviz-visualization/panel-dashboards | FAIL | `tired-01` tired 0/3 (none) |
| holoviz-visualization/parameterization | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| holoviz-visualization/plotting-fundamentals | FAIL | `tired-01` tired 0/3 (none) |
| project-management/community-health-files | FAIL | `obvious-01` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| project-management/documentation-validation | FAIL | `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| research-software-design/user-persona-discovery | PASS |  |
| scientific-domain-applications/astropy-fundamentals | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| scientific-domain-applications/xarray-for-multidimensional-data | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| scientific-python-development/code-quality-tools | FAIL | `tired-01` tired 0/3 (none) |
| scientific-python-development/pixi-package-manager | FAIL | `tired-01` tired 0/3 (none) |
| scientific-python-development/python-packaging | FAIL | `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| scientific-python-development/python-testing | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| scientific-python-development/scientific-documentation | FAIL | `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| supply-chain-security/supply-chain-dependency-security | PASS |  |
| supply-chain-security/supply-chain-ecosystem-quirks | FAIL | `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| supply-chain-security/supply-chain-hardened-ci-cd | FAIL | `tired-02` tired 0/3 (none) |
| supply-chain-security/supply-chain-incident-response | PASS |  |
| supply-chain-security/supply-chain-sbom-provenance | FAIL | `obvious-02` obvious 0/3 (none) |
| supply-chain-security/supply-chain-threat-awareness | FAIL | `obvious-01` obvious 0/3 (supply-chain-security:supply-chain-incident-response); `obvious-02` obvious 0/3 (supply-chain-security:supply-chain-audit); `tired-01` tired 0/3 (none) |
| uiux-design-team/ab-testing-strategy | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| uiux-design-team/accessibility-audit | FAIL | `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| uiux-design-team/color-systems | FAIL | `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| uiux-design-team/component-library | FAIL | `tired-01` tired 0/3 (none) |
| uiux-design-team/css-architecture | FAIL | `obvious-01` obvious 1/3 (none, uiux-design-team:css-architecture); `obvious-02` obvious 0/3 (none) |
| uiux-design-team/design-case-studies | FAIL | `tired-01` tired 0/3 (none) |
| uiux-design-team/design-handoff | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/design-philosophies | FAIL | `tired-01` tired 0/3 (none) |
| uiux-design-team/design-system-creation | FAIL | `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none, uiux-design-team:create-design-system) |
| uiux-design-team/design-tokens | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/frontend-components | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/grid-layout-systems | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/information-architecture | FAIL | `obvious-02` obvious 0/3 (none) |
| uiux-design-team/motion-design | FAIL | `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/responsive-design | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/typography-systems | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| uiux-design-team/usability-evaluation | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/user-journey-mapping | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 1/3 (none, uiux-design-team:user-journey-mapping); `tired-01` tired 0/3 (uiux-design-team:map-journey) |
| uiux-design-team/user-research | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/ux-writing | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none); `tired-02` tired 0/3 (none) |
| uiux-design-team/visual-design | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| uiux-design-team/wireframing | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none, uiux-design-team:information-architecture); `tired-01` tired 0/3 (none) |
| zarr-chunk-optimization/access-pattern-analysis | PASS |  |
| zarr-chunk-optimization/chunking-strategy | FAIL | `obvious-01` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| zarr-chunk-optimization/performance-reporting | FAIL | `obvious-01` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| zarr-chunk-optimization/rechunking | FAIL | `obvious-01` obvious 0/3 (none) |
| zarr-chunk-optimization/synthetic-data | FAIL | `obvious-02` obvious 0/3 (none) |
| zarr-data-format/cloud-storage-backends | FAIL | `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| zarr-data-format/compression-codecs | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| zarr-data-format/data-migration | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| zarr-data-format/zarr-fundamentals | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
| zarr-data-format/zarr-xarray-integration | FAIL | `obvious-01` obvious 0/3 (none); `obvious-02` obvious 0/3 (none); `tired-01` tired 0/3 (none) |
