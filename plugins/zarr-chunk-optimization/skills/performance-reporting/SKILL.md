---
name: performance-reporting
description: Use when Zarr chunking benchmark results already exist, as benchmark_runner.py JSON or as read times per chunk shape, and someone needs them compared, ranked, turned into a chunk-shape recommendation, charted, or written up as a report for stakeholders. Also use when asked for a performance bias score, a memory-budget check, or a weighted score for a mixed map and time-series workload.
metadata:
  references: references/report-generation.md references/visualization-patterns.md
  assets: assets/comparison-table-template.md assets/recommendation-template.md
---

# Performance Reporting

Turns Zarr chunking benchmark results into a report that ranks chunk shapes and recommends one, using comparison tables, performance bias and memory-budget checks.

**Core principle:** every number in the report traces to a measured field. Unmeasured metrics (TTFB, chunk utilization, chunks read) stay out rather than being estimated.

## When to Use

- Results exist (the JSON from `chunking-strategy/scripts/benchmark_runner.py`, or per-shape read times the user pasted) and need ranking, a recommendation, charts or a write-up.
- Old results need re-ranking under new workload weights or a new memory budget.

**When NOT to use:**
- No results yet: use **chunking-strategy** to run the benchmarks.
- Workload weights not yet agreed: use **access-pattern-analysis** first.
- Applying the chosen shape: use **rechunking**. Need a test dataset: use **synthetic-data**.

## Input: What benchmark_runner.py Writes

Top level: `metadata` (timestamp, platform, Python version, dimensions) and `benchmarks`, one entry per (chunk config, access pattern, dimension):

- `chunk_config`, `dataset`, `shape`, `num_runs`, `dim_index`, `dimension_name`
- `access_pattern`: `slice` reads one index of `dimension_name` and all of the rest (a map at one time step); `traverse` reads all of `dimension_name` at the middle index of every other dimension (a time series at one point).
- `statistics.<metric>` = `{mean, std, min, max, values}`, `std` with ddof=0. Metrics: `wall_time` (s), `peak_memory_mb`, `throughput_mbps` (MB/s of returned data), `data_size_mb`, `dask_tasks`, `http_requests` (0 for local stores).
- `error` instead of `statistics`: that run failed. List it in the report.

`ttfb` and `chunk_utilization` are hardcoded to `None`: absent from `statistics`, or, in older runners, the cause of every entry failing with `unsupported operand type(s) for +: 'NoneType' and 'NoneType'`. That error is a runner bug, not a bad configuration, and leaves nothing to report.

**Check before ranking:**
1. **One chunk layout per store.** The runner does not rechunk: `chunk_config` is only a label, and it reads `dataset` with its stored chunks. Several configs sharing one `dataset` path measured the same layout, so their differences are noise. Stop and ask for one run per rechunked store.
2. **Name the patterns.** Map each `(access_pattern, dimension_name)` to the user's workload names, e.g. `("slice", "time")` is a map and `("traverse", "time")` is a time series. By default the runner tests both patterns on every dimension. Keep only the ones the workload uses.
3. **Every config has every kept pattern**, and `num_runs` ≥ 5.

## Quick Reference

| Quantity | Definition | Note |
|----------|------------|------|
| Pattern time `T_p` | `statistics.wall_time.mean` | Report as mean ± std |
| Peak memory | max of `peak_memory_mb.max` over a config's entries, / 1024 for GB | Python-heap peak per read, not RSS: a lower bound |
| Performance bias (PB) | `max_p T_p / min_p T_p` over the kept patterns | Unweighted, as in Nguyen et al. (2023); n/a with one pattern |
| Composite score | `Σ w_p T_p`, weights normalized to sum to 1 | Expected seconds per operation; equal weights by default |
| Noisy | `std / mean > 0.3` | Re-run with more runs; don't drop the config |
| Tie | mean ± std ranges overlap | Confirm with Welch's t-test on `values` if it decides the pick |

PB classes (plugin heuristics, not from the paper): < 1.5 Balanced, 1.5–3 Moderate, 3–10 Biased, > 10 Extreme.

## Ranking

1. Mark configs over the memory budget as infeasible. They cannot be the primary pick.
2. Rank feasible configs by composite score, or by `T_p` alone when one pattern dominates.
3. Break ties by lower PB, then lower peak memory, then smaller chunks.
4. **Primary:** rank 1. **Alternative:** a config ≥ 25% faster on one pattern, with the trade-off stated; if it is over budget, say how much memory it needs. **Avoid:** configs dominated on every metric, and over-budget configs not offered as the alternative.

For code that loads runner JSON, rejects shared-store or missing-pattern input, and computes these quantities, see [Loading Runner Output](references/report-generation.md#loading-runner-output).

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Weighted PB `max(w·T) / min(w·T)` | Mixes workload shares into balance: under 70/30 weights a config with equal times scores 2.33. Use weights only in the composite score |
| PB over all of the runner's patterns | PB over the workload's patterns only |
| Sorting formatted strings (`"12.50" < "2.64"`) | Sort numbers; format only when rendering |
| Methodology says sample std, OS cache cleared between runs, or several warm-ups | Runner: population std, fsspec cache cleared before each run, OS cache only if cleared by hand, 1 warm-up (`--warmup` is not passed through) |

## Report Structure

Dataset summary, environment, comparison table, per-pattern tables, PB summary, recommendations, methodology (with failed entries). Formatting and examples: [references/report-generation.md](references/report-generation.md). Charts: [references/visualization-patterns.md](references/visualization-patterns.md). Templates: [comparison table](assets/comparison-table-template.md), [recommendations](assets/recommendation-template.md).
