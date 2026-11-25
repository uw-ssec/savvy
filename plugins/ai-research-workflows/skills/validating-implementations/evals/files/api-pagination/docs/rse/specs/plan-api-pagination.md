# Plan: Paginate the records API

Status: approved.

## Phase 1: Page-number pagination

### Changes

- [x] `list_records(page, per_page)` in `src/api.py` returns `per_page` items and the next page number
- [x] The last page returns the remaining items and `next_page` of `None`
- [x] Add `tests/test_api.py`

### Success Criteria

#### Automated Verification

- [x] `python -m unittest discover -s tests -t .` passes with no failures

#### Manual Verification

- [ ] Paging through the records in the client shows every record exactly once
