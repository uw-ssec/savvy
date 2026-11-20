---
name: compression-codecs
description: Use when choosing or configuring Zarr compression in zarr-python 3 (Blosc, Zstd, Gzip, LZ4, LZMA, BZ2; numcodecs filters such as Delta, Quantize, BitRound, FixedScaleOffset, PackBits; compressors=, filters=, serializer=), when v2-style compressor= or numcodecs code fails on a v3 array, or when a store compresses poorly, decompresses slowly, raises codec errors, or may hold corrupted chunks after Blosc multiprocessing use.
metadata:
  references: references/patterns.md references/examples.md references/common-issues.md
---

# Compression Codecs for Zarr

Configures the zarr-python 3 codec pipeline (filters, serializer, compressors) for an array and measures which codecs suit its data.

**Core principle:** the data sets the ratio more than the codec does. On real float32 climate data every lossless codec gave 1.5–4.8x, and the zarr 3 default (`ZstdCodec`) came within 10% of the best Blosc setting. Lossy filters gave the larger gains. Measure a sample of the real data before changing the default.

## When to Use

- Picking codecs, shuffle, levels or filters for a new or existing array.
- Porting zarr-python 2 code: `compressor=`, `numcodecs.Blosc(...)` or `numcodecs.Delta(...)` now raise on v3 arrays.
- A store is larger than expected, reads are bound by decompression, or chunks may be corrupt.

**When NOT to use:**
- Chunk or shard shapes: use `zarr-chunk-optimization`'s **chunking-strategy**.
- Array and group basics, v2 vs v3 format, sharding layout: use **zarr-fundamentals**.
- xarray `to_zarr` workflows beyond the codec keys, Dask alignment: use **zarr-xarray-integration**.

## Quick Reference (zarr-python 3)

| Slot | `create_array` argument | Codecs |
|---|---|---|
| array → array | `filters=[...]` | `TransposeCodec`; `zarr.codecs.numcodecs.Delta`, `Quantize`, `BitRound`, `FixedScaleOffset`, `PackBits` |
| array → bytes | `serializer=` | `BytesCodec()` (default); sharding via `shards=` |
| bytes → bytes | `compressors=[...]` | `ZstdCodec` (default, `level=0`), `BloscCodec`, `GzipCodec`, `Crc32cCodec`; `zarr.codecs.numcodecs.LZ4`, `LZMA`, `BZ2`, `Zlib` |

```python
import zarr
from zarr.codecs import BloscCodec, Crc32cCodec
from zarr.codecs.numcodecs import BitRound

z = zarr.create_array(
    store="air.zarr", shape=(2920, 25, 53), chunks=(730, 25, 53), dtype="float32",
    filters=[BitRound(keepbits=10)],  # lossy: keeps 10 of 23 mantissa bits
    compressors=[BloscCodec(cname="zstd", clevel=5, shuffle="shuffle"), Crc32cCodec()],
)
print(z.compressors)       # z.compressor raises TypeError on v3 arrays
print(z.info_complete())   # after writing: "No. bytes stored", "Storage ratio"
```

- `zarr.codecs.numcodecs.*` codecs are saved as `numcodecs.<id>`, outside the v3 spec: other Zarr implementations may not read them. `numcodecs.zarr3` is deprecated.
- `BloscCodec()` defaults to zstd, `clevel=5`, `"shuffle"` (`"bitshuffle"` for 1-byte dtypes), typesize from the dtype.
- `zarr_format=2` arrays take numcodecs objects (`compressors=numcodecs.Blosc(...)`). Their default depends on the call: `zarr.create_array` gives `Zstd(level=0)`, but `Group.create_array` (used by xarray) gives `Blosc(cname="lz4")`. Set it explicitly.
- xarray: `encoding={"var": {"compressors": [...], "filters": [...], "chunks": (730, 25, 53)}}`. The `"compressor"` key raises `ValueError`.

## Measured Ratios

NCEP air temperature (xarray tutorial `air_temperature`, float32, 15.5 MB, zarr 3.1.5, Apple M5 Max). More datasets in [examples.md](references/examples.md).

| Configuration | Ratio | Read MB/s |
|---|---|---|
| `ZstdCodec()` default | 2.83x | 4,460 |
| Blosc zstd 5: shuffle / noshuffle / bitshuffle | 2.97x / 2.89x / 1.72x | 3,100–4,500 |
| Blosc lz4 5, shuffle | 1.74x | 5,170 |
| `GzipCodec(level=5)` | 2.76x | 1,560 |
| BZ2 5 / LZMA 6 (numcodecs) | 4.80x / 4.15x | 290 / 490 |
| BitRound(10) + Blosc zstd (lossy, max error 0.11 K) | 5.18x | 2,800 |

Measure your own sample: `python assets/codec-comparison.py --zarr store.zarr/<var>` (or `--npy sample.npy`).

## Common Mistakes

| Mistake | Fix |
|---|---|
| `compressor=` or numcodecs objects on a v3 array (`ValueError: compressor cannot be used for arrays with zarr_format 3`, `TypeError: Expected an ArrayArrayCodec`) | `compressors=[zarr.codecs...]`, `filters=[zarr.codecs.numcodecs...]`, or `zarr_format=2` |
| `z.nbytes / z.nbytes_stored` | `nbytes_stored()` is a method |
| Benchmarking `Blosc().encode(arr.tobytes())` | Bytes have typesize 1, so shuffle does nothing. Encode the ndarray or benchmark through zarr. |
| `[Delta, Quantize]` on floats | Quantize or BitRound first. Delta-then-Quantize had 140x the max error. |
| "SHUFFLE for floats, BITSHUFFLE for ints" | Bitshuffle lost to shuffle with zstd on float32 and uint32. Measure. |
| `np.isfinite` as a corruption check | A flipped bit decoded to finite, wrong values. Add `Crc32cCodec()` or `ZstdCodec(checksum=True)`. |
| `numcodecs.blosc.use_threads = False` against corruption | Importing zarr already sets it, and numcodecs never uses Blosc threads in a forked child. Its source names a hang, not corruption. |
| Choosing codecs on synthetic noise | Noise gives 1.0–1.3x under every codec. Sample the real data. |
