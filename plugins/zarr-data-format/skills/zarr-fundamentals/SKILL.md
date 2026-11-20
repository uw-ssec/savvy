---
name: zarr-fundamentals
description: Use when creating, opening, indexing or organizing Zarr arrays and groups with zarr-python (.zarr stores, zarr.json or .zarray metadata), setting attributes, fill values, dimension names or shards, choosing between Zarr format v2 and v3, porting zarr 2 code that breaks on zarr 3 (FSStore, ProcessSynchronizer, len(), .compressor), or when parallel writes to one Zarr array lose data.
metadata:
  references: references/patterns.md references/examples.md references/common-issues.md
---

# Zarr Fundamentals

Creates, opens, indexes and organizes chunked N-dimensional Zarr arrays and groups with the zarr-python 3 API, in Zarr format v3 (the default) or v2.

**Core principle:** zarr reads, decodes and writes whole chunks. In a sharded array the inner chunk is the read unit and the shard is the stored object, so every write rewrites its whole shard. Match chunks to reads, and give each parallel writer whole chunks (whole shards when sharded).

**Docs**: https://zarr.readthedocs.io/ | **Spec**: https://zarr-specs.readthedocs.io/

## When to Use

- Creating or opening arrays and groups; attributes, fill values, dimension names, sharding
- Indexing beyond slices: `oindex`, `vindex`, `blocks`
- Choosing format v2 or v3, or reading v2 stores with zarr-python 3
- zarr 2 code failing on zarr 3 with `AttributeError` or `TypeError`
- Parallel writes leaving fill values or stale data in the array

**When NOT to use:**
- S3, GCS, Azure, fsspec, obstore or Icechunk: **cloud-storage-backends**
- Choosing compressors or filters, Blosc threading: **compression-codecs**
- HDF5 or NetCDF to Zarr, VirtualiZarr, kerchunk: **data-migration**
- xarray or Dask (`to_zarr`, `open_zarr`, `append_dim`, region writes): **zarr-xarray-integration**
- Picking chunk shapes by benchmark, or rechunking: the **zarr-chunk-optimization** plugin

## Quick Reference

Install `zarr` (pip or pixi); numcodecs comes with it. There is no `zarr[extra]`.

```python
import numpy as np
import zarr

z = zarr.create_array("data.zarr", shape=(2000, 2000), chunks=(500, 500), dtype="float32",
                      fill_value=np.nan, dimension_names=("y", "x"), attributes={"units": "K"})
z[:500, :] = 1.0                       # covers 4 whole chunks
z = zarr.open_array("data.zarr", mode="r")

root = zarr.open_group("experiment.zarr", mode="w")
temp = root.create_group("observations").create_array(
    "temperature", shape=(365, 180, 360), chunks=(30, 90, 180), dtype="float32")
root.attrs["project"] = "Climate Study"
print(root.tree())                     # needs the optional `rich` package
```

- **Modes:** `r` read-only and `r+` read-write (both need an existing node), `w-` create (fails if anything exists), `a` open or create, `w` replace (deletes existing data and attributes). Store classes take `read_only=True`, not `mode`.
- **Sharding (v3 only):** `chunks=` is the inner chunk, `shards=` a multiple of it.
- **Chunk size:** at least 1 MB uncompressed. Size for access patterns with **zarr-chunk-optimization**.
- **Fill value:** defaults to 0. Use `np.nan` for floats when 0 is valid data.
- **Consolidated metadata:** `zarr.consolidate_metadata(path)` lets a group open in one read. Re-run it after adding nodes.
- **Indexing:** `z.oindex[rows, cols]` takes the outer product, `z.vindex[rows, cols]` takes point pairs (or a mask shaped like `z`), and `z.blocks[i, j]` takes one chunk (one shard when sharded).

**Format v2 vs v3.** zarr-python 3 reads and writes both, with async I/O for both:

| | v2 | v3 |
|---|---|---|
| Metadata | `.zarray`, `.zgroup`, `.zattrs` | One `zarr.json` per node |
| Default chunk keys | `0.0` | `c/0/0` |
| Default compressor (zarr-python 3.1.5) | `zarr.create_array`: Zstd; `Group.create_array` / xarray: Blosc lz4 | Zstd |
| `shards=`, `dimension_names=` | `ValueError` | Supported |
| Consolidated metadata | `.zmetadata` | Inside root `zarr.json` (zarr-python extension, warns) |

Default to v3. Fixed-length `U`/`S` and structured dtypes raise `UnstableSpecificationWarning` in v3: other readers may fail.

**Parallel writes:** concurrent reads are safe, and so are writers that each cover whole, distinct chunks (shards when sharded), in threads or processes. Two writers in one chunk or shard each rewrite the whole object, so the later one erases the other's values. zarr-python 3 has no synchronizers.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| `FSStore`, `DirectoryStore`, `LRUStoreCache`: `AttributeError` | `FsspecStore.from_url(...)`, `LocalStore` or a path string |
| `zarr.ProcessSynchronizer`: `AttributeError`; `synchronizer=` does nothing but warn | Partition writes on chunk or shard boundaries |
| `create_array(compressor=...)`, or `z.compressor` on v3: `TypeError` | `compressors=`, `z.compressors` |
| `len(z)`; `z.resize(200, 10)`: `TypeError` | `z.shape[0]`; `z.resize((200, 10))` |
| `chunks=` larger than `shards=`: `ValueError` | `shards` is a multiple of `chunks` |
| `z["field"]` on a structured array: `TypeError` | Read records first: `z[0:1000]["field"]` |
| `mode="w"` to edit an existing store | `mode="r+"` or `"a"` |

## Resources

| Resource | Load when |
|----------|-----------|
| [references/patterns.md](references/patterns.md) | Hierarchies, appending, indexing, sharding, parallel writes |
| [references/examples.md](references/examples.md) | CF-style dataset, multi-instrument store, structured dtypes |
| [references/common-issues.md](references/common-issues.md) | Format confusion, lost attributes, OOM, lost writes |
| `python assets/zarr-quickstart.py` | Runnable demo in a temporary directory |
