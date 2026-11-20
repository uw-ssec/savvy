# Zarr Chunk Optimization Plugin

Benchmarks Zarr chunking strategies for multi-dimensional datasets on cloud object stores (S3, GCS). Based on Nguyen et al. (2023) methodology. Measures wall-clock time, peak memory, and I/O metrics across spatial, time-series, and spectral access patterns.

> [!NOTE]
> **Client-specific parts:** this plugin's agents and commands are written for Claude Code. Cursor loads them too, Antigravity CLI loads the agents but not the commands, and GitHub Copilot, Codex and OpenCode load neither. Its skills follow the [Agent Skills](https://agentskills.io/) format and work in all of these clients. See [Installing the plugins](https://github.com/uw-ssec/savvy/blob/main/docs/install.md) for what each client loads.

## Agents

| Agent | Description |
|-------|-------------|
| **benchmarking-agent** | Zarr chunking optimization expert — coordinates benchmarking, synthetic data generation, and rechunking workflows |
| **performance-analyst** | Interprets benchmark results, analyzes trade-offs across access patterns, and generates actionable recommendations |

## Skills

| Skill | Description |
|-------|-------------|
| **chunking-strategy** | Core benchmarking methodology, cloud storage patterns, and performance interpretation references |
| **synthetic-data** | Generate synthetic Zarr datasets with configurable dimensions, shapes, and compression for controlled benchmarks |
| **rechunking** | Safely apply chunking configurations with validation, progress reporting, and rollback safety |
| **access-pattern-analysis** | Identify, formalize, and prioritize data access patterns from user workflow descriptions |
| **performance-reporting** | Generate structured benchmark reports with comparisons, bias analysis, and ranked recommendations |

## Commands

| Command | Description |
|---------|-------------|
| `/benchmark` | Run chunking benchmarks across access patterns and collect wall-clock time, peak memory, and I/O metrics |
| `/rechunk` | Rechunk a production dataset with validation and safety checks |
| `/tradeoffs` | Analyze trade-offs between spatial, temporal, and spectral access performance for a given chunk configuration |
| `/generate-synthetic` | Generate a synthetic Zarr dataset for controlled chunking benchmarks |
| `/analyze-performance` | Analyze benchmark results and generate a performance report with ranked recommendations |

## When to Use

- Optimizing chunk shapes for Zarr datasets with mixed access patterns
- Benchmarking chunking configurations before committing to rechunking
- Analyzing trade-offs between spatial, temporal, and spectral access performance
- Rechunking production datasets with validation and safety checks
- Generating synthetic datasets for controlled benchmarking experiments

## Out of Scope

- General-purpose array storage format selection (Zarr vs HDF5 vs NetCDF)
- Cloud infrastructure provisioning
- Data pipeline orchestration
- Compression algorithm selection (focus is on chunk shape, not codec)

## Related Plugins

| Plugin | Use For |
|--------|---------|
| **scientific-domain-applications** | Xarray/Zarr data handling and multidimensional scientific data analysis |
| **scientific-python-development** | Packaging, testing, and modern Scientific Python development practices |

## Research Basis

This plugin implements the benchmarking methodology described in Nguyen et al. (2023), "Impact of Chunk Size on Read Performance of Zarr Data in Cloud-based Object Stores." DOI: [10.1002/essoar.10511054.2](https://doi.org/10.1002/essoar.10511054.2)
