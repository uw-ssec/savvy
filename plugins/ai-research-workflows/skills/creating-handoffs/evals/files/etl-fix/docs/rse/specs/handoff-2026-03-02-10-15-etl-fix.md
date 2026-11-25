# Handoff: ETL load failures

**Date:** 2026-03-02 10:15
**Status:** in progress

## Tasks

- Diagnose the nightly load failures: done (transient warehouse timeouts)
- Retry logic for transient failures in `src/etl/retry.py`: planned
- Schema migration adding `ingested_at`: planned

## Next steps

1. Write `with_retry()` and use it in `src/etl/load.py`
2. Write `migrations/002_add_ingested_at.sql`
