# Experiment: Batched writes versus one write per put

## Question

Do batched writes (Phase 2 of plan-results-caching.md) beat writing on every put?

## Results (median of 5 runs, 100,000 puts)

| Approach | Throughput (puts/s) | p99 latency (ms) |
| --- | ---: | ---: |
| Baseline: write on every put | 41,200 | 3.1 |
| Batched writes (500 per flush) | 28,700 | 19.4 |
| Write-through (write on put, cache updated after the write succeeds) | 40,800 | 3.2 |

## Conclusion

Batched writes are slower than the baseline: the flush blocks every 500th put and the database already pipelines small writes. Write-through matches the baseline and keeps the cache consistent.
