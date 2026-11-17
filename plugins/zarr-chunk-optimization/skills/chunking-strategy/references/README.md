# References

## Available References

### [nguyen-2023.md](nguyen-2023.md)
Citation and summary of "Impact of Chunk Size on Read Performance of Zarr Data in Cloud-based Object Stores" by Nguyen et al. (2023). Covers the empirical findings about time-series vs spatial access trade-offs, the all-or-nothing memory constraint, middle-range chunking recommendations (3-5 MB), and the performance bias metric for evaluating balanced chunking strategies.

**Load this when:** The agent needs to understand the research basis for chunking recommendations or explain the theoretical foundation of the benchmarking methodology.

### [access-patterns.md](access-patterns.md)
Technical explanation of three common access patterns: spatial, time-series, and spectral. Describes what each pattern means for multi-dimensional Zarr arrays, the xarray operations that trigger each pattern, the `benchmark_runner.py` flag (`--slice-dims` or `--traverse-dims`) that reproduces it, and which chunk shapes favor it.

**Load this when:** The agent needs to generate benchmark code, explain access pattern trade-offs, or help the user map their workflow to one of the three patterns.

### [memory-constraints.md](memory-constraints.md)
Detailed explanation of the all-or-nothing chunk memory constraint—why entire chunks (inner chunks, for sharded stores) must be loaded and decompressed to access any single value. Explains why peak memory is a first-class metric alongside wall-clock time, and how to interpret memory measurements when making chunking recommendations.

**Load this when:** The agent is analyzing benchmark results where memory usage is a concern, or when the user asks why certain chunk sizes cause memory issues.

### [benchmarking-methodology.md](benchmarking-methodology.md)
Best practices for running reproducible chunking benchmarks: minimum run counts, cache clearing procedures (macOS/Linux), fsspec caching considerations, parameter variation strategy, building one store per candidate, environment recording, common pitfalls, and the `benchmark_runner.py` output format.

**Load this when:** The agent is setting up a benchmarking script, the user asks about reproducibility, or benchmark results show unexpected variance.

### [cloud-storage-patterns.md](cloud-storage-patterns.md)
Object store behavior that shapes chunk choices: Zarr v2 and v3 key layouts, per-request latency and throughput, sharding, authentication and fsspec configuration, caching layers, request and egress costs, and cloud vs local benchmarking.

**Load this when:** The data lives on S3 or GCS, or the user asks about request latency, sharding, caching, or the cost of reads and rechunking.

### [performance-interpretation.md](performance-interpretation.md)
How to read benchmark results: what each metric means, performance bias ranges, statistical significance, common performance profiles, inconclusive results, weighted scoring, and turning results into recommendations.

**Load this when:** The agent has benchmark results to compare, rank, or translate into a recommendation.
