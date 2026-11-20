# Benchmark Comparison Table

**Dataset:** [DATASET_NAME]
**Date:** [BENCHMARK_DATE]
**Memory Budget:** [MEMORY_BUDGET] GB

## Configuration Comparison

| Config | Chunk Shape | Spatial Time (s) | Temporal Time (s) | Spectral Time (s) | Peak Memory (GB) | Performance Bias |
|--------|-------------|-------------------|--------------------|--------------------|-------------------|------------------|
| B | (50, 512, 512) | 8.3 +/- 0.7 | 11.2 +/- 0.9 | 10.1 +/- 0.6 | 3.8 | 1.35 |
| C | (100, 256, 256) | 9.1 +/- 0.8 | 9.8 +/- 0.7 | 11.5 +/- 0.9 | 5.1 | 1.26 |
| D | (200, 128, 128) | 15.3 +/- 1.1 | 5.8 +/- 0.4 | 14.2 +/- 1.0 | 4.3 | 2.64 |
| A | (10, 1024, 1024) | 6.1 +/- 0.5 | 18.4 +/- 1.2 | 12.7 +/- 0.8 | 10.2 | 3.02 |

**Status key:** Configs with Peak Memory exceeding [MEMORY_BUDGET] GB budget are infeasible.

## Usage Notes

- Replace placeholder values with actual benchmark results.
- Times are reported as `mean +/- std` across all timed runs (`statistics.wall_time`; the runner's std is population std, ddof=0).
- Peak Memory is the maximum observed across all runs and all access patterns for that configuration: the largest `peak_memory_mb.max` / 1024.
- Performance Bias = max(pattern time) / min(pattern time). Lower is more balanced.
- Sort rows in ranking order: within-budget configs first, then composite score ascending (the example uses equal weights). For a single-pattern workload, sort by that pattern's time.
- Bold the best value in each numeric column to highlight winners.
- If fewer than three access patterns were tested, remove unused columns. With a single pattern, write `n/a` for Performance Bias: 1.0 would read as Balanced.
