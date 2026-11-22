# Plan: Full-text search over dataset descriptions

Status: approved.

## Phase 1: Schema

### Changes

- [x] Define the document record (id, title, description) in `src/documents.py`

### Success Criteria

#### Automated Verification

- [x] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [x] The schema covers every field the catalogue exports

## Phase 2: Tokenizer

### Changes

- [x] Add `tokenize()` to `src/tokenize.py`
- [x] Add `tests/test_tokenize.py`

### Success Criteria

#### Automated Verification

- [x] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [x] Tokens for ten sample descriptions look right

## Phase 3: Indexer and query API

### Changes

- [ ] Add `build_index(documents)` to `src/indexer.py` building an inverted index from `tokenize()` output
- [ ] Persist the index to `index.json` and reload it on start-up
- [ ] Add `search(query, limit)` to `src/query.py` returning matching document ids
- [ ] Expose `GET /search?q=...` in `src/api.py`
- [ ] Add `tests/test_indexer.py` and `tests/test_query.py`

### Success Criteria

#### Automated Verification

- [ ] `python -m unittest discover -s tests -t .` passes
- [ ] `python -m src.indexer data/catalogue.json` writes `index.json`

#### Manual Verification

- [ ] Searching for a known dataset title in the web client finds it first

## Phase 4: Ranking

### Changes

- [ ] Rank results by term frequency in `src/query.py`

### Success Criteria

#### Automated Verification

- [ ] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [ ] Relevance on the 20-query sample set is judged acceptable
