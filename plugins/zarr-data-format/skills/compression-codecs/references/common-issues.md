# Common Issues and Solutions

Error messages are from zarr-python 3.1.5, numcodecs 0.17.1 and xarray 2026.9.0.

## Contents

| Issue | Description |
|-------|-------------|
| 1. Suspected Corruption with Blosc | What to check, and the fork myth |
| 2. Poor Compression Ratio | Data limits, benchmark mistakes, what can still help |
| 3. Slow Decompression | Archival codecs on hot data |
| 4. Codec Not Found | `UnknownCodecError` when opening a store |
| 5. v2-Style Codec Code on zarr-python 3 | `compressor=`, numcodecs objects, `.compressor` |
| 6. Filter Order | Quantize before Delta |
| 7. Shuffle Mode Selection | No fixed rule per dtype |

---

## Issue 1: Suspected Corruption with Blosc

**Symptoms:** values look wrong after a multi-process write; old advice says Blosc in Dask or `multiprocessing` corrupts data.

**What the code says** (zarr 3.1.5; numcodecs 0.16.5 and 0.17.1):
- Importing zarr sets `numcodecs.blosc.use_threads = False`.
- numcodecs never uses Blosc's threaded global context in a forked child. Its source names the risk as a hang, not corruption. Details in [patterns.md](patterns.md#pattern-7-blosc-threads-and-multiprocessing).
- In a test, 8 forked workers wrote 64 Blosc chunks with `use_threads = True` set in the parent, and every chunk read back exactly.

**What to check instead:**
- Several processes writing to the **same chunk** without synchronization. The zarr user guide (Performance) promises safe multi-process writes only when processes write to different chunks. Align write regions to chunk boundaries (see **zarr-xarray-integration**).
- Corruption at rest or in transit: a flipped bit in a Blosc or Zstd chunk decoded to wrong, finite values with no error, so `np.isfinite` checks miss it. Write new data with `Crc32cCodec()` or `ZstdCodec(checksum=True)` (see [patterns.md](patterns.md#pattern-6-checksums-for-integrity)), and compare existing data against its source.

---

## Issue 2: Poor Compression Ratio

**Symptoms:** stored size close to raw size; ratio under 2x.

**Causes, in order of likelihood:**
1. **The data is noisy.** The real float samples in [examples.md](examples.md) compressed 1.5–4.8x losslessly, most configurations 2–3x, and random noise 1.0–1.3x under every codec. No codec swap changes this much.
2. **The benchmark was wrong.** `Blosc().encode(arr.tobytes())` gives Blosc typesize 1, which turns byte shuffle into a no-op. Benchmark through zarr or encode the ndarray.
3. **Wrong filter for the data.** Delta on non-monotonic data lowered the counts ratio from 6.32x to 3.34x.

**What can still help:** try each Blosc shuffle mode, since the best one varies (Issue 7). Or use a lossy filter at the precision the science needs, after measuring its error (examples.md, Example 4).

```python
import zarr

z = zarr.open_array("data.zarr", mode="r")
print(z.info_complete())                       # "No. bytes stored", "Storage ratio"
print(f"{z.nbytes / z.nbytes_stored():.2f}x")  # nbytes_stored is a method
```

---

## Issue 3: Slow Decompression

**Symptoms:** reads are CPU-bound; profiles show time in codec decode.

**Cause:** an archival codec on frequently read data. On the air sample (read MB/s): Blosc lz4 7,190, LZ4 7,100, default Zstd 4,460, Blosc zstd shuffle 3,130, Gzip 1,560, LZMA 490, BZ2 290. Higher Zstd levels slow writes, not reads (level 19 wrote at 14 MB/s and read at about the default speed).

**Solution:** rewrite hot data with the default `ZstdCodec()` or `BloscCodec(cname="lz4", ...)`. `zarr.from_array` copies an array and keeps its chunks while replacing the codecs:

```python
import zarr
from zarr.codecs import ZstdCodec

old = zarr.open_array("archive.zarr", mode="r")
new = zarr.from_array("hot.zarr", data=old, compressors=[ZstdCodec()])  # chunks, filters: "keep"
```

---

## Issue 4: Codec Not Found

**Symptoms:**
- v3 store: `UnknownCodecError: Unknown codec: 'name'` from `zarr.open_array`.
- v2 store or `numcodecs.get_codec`: `UnknownCodecError: codec not available: '...'`.

`UnknownCodecError` subclasses `ValueError`.

**Cause:** the store names a codec this environment has not registered, for example a third-party codec or a newer numcodecs codec.

```python
import json

print(json.load(open("data.zarr/zarr.json"))["codecs"])  # v3: the codec names the store needs
# v2: data.zarr/.zarray has "compressor" and "filters"
```

Install the package that provides the codec. `numcodecs.<id>` names are registered by zarr-python 3.1.3 and later (`zarr.codecs.numcodecs`), so they open without extra imports. Other Zarr implementations may not support them.

---

## Issue 5: v2-Style Codec Code on zarr-python 3

**Symptoms and fixes:**

| Code | Error on a v3 array | Fix |
|---|---|---|
| `zarr.open_array(..., compressor=numcodecs.Blosc())` | `ValueError: compressor cannot be used for arrays with zarr_format 3. Use bytes-to-bytes codecs instead.` | `compressors=[zarr.codecs.BloscCodec(...)]` |
| `zarr.open_array(..., filters=[numcodecs.Delta(...)])` | `ValueError: filters cannot be used for arrays with zarr_format 3. Use array-to-array codecs instead.` | `zarr.create_array(..., filters=[zarr.codecs.numcodecs.Delta(...)])` |
| `zarr.create_array(..., compressor=...)` | `TypeError: create_array() got an unexpected keyword argument 'compressor'` | `compressors=` |
| `zarr.create_array(..., compressors=numcodecs.Blosc())` | `TypeError: 'Blosc' object is not iterable` | a `zarr.codecs` object |
| `zarr.create_array(..., filters=[numcodecs.Delta(...)])` | `TypeError: Expected an ArrayArrayCodec. Got <class 'numcodecs.delta.Delta'> instead.` | `zarr.codecs.numcodecs.Delta` |
| `z.compressor` | `TypeError` saying `compressor` is not available for Zarr format 3 arrays | `z.compressors` |
| xarray `encoding={"v": {"compressor": ...}}` | `ValueError: unexpected encoding parameters for zarr backend: ['compressor']` (v2 and v3) | `"compressors"` |
| `from numcodecs.zarr3 import Delta` | `DeprecationWarning` | `from zarr.codecs.numcodecs import Delta` |

To keep numcodecs objects, write a v2 array: `zarr.create_array(..., zarr_format=2, compressors=numcodecs.Blosc(...))` ([patterns.md](patterns.md#pattern-8-zarr-v2-arrays)). An unset v2 compressor is `numcodecs.Zstd(level=0)` from `zarr.create_array`, but `Blosc(cname="lz4")` from `Group.create_array` and xarray.

---

## Issue 6: Filter Order

**Symptoms:** a lossy float pipeline has much larger errors than its precision setting suggests.

**Cause:** filters run in list order on write. With Delta first, Quantize rounds the differences, and decoding adds those rounding errors back up along the chunk.

Measured on a monotonic float64 series (`np.cumsum(uniform(0, 1, 100_000))`, chunks of 10,000, Blosc zstd):

| `filters=` | Ratio | Max abs error |
|---|---|---|
| `[Quantize(digits=3), Delta]` | 5.07x | 0.000488 |
| `[Delta, Quantize(digits=3)]` | 5.07x | 0.0696 |

```python
from zarr.codecs.numcodecs import Delta, Quantize

filters = [Quantize(digits=3, dtype="float64"), Delta(dtype="float64")]  # quantize first
```

With `BitRound(keepbits=20)` the order changed the ratio instead: 8.32x with BitRound first, 2.71x after Delta, both with max error about 0.015.

---

## Issue 7: Shuffle Mode Selection

**Symptoms:** unsure whether to use `"noshuffle"`, `"shuffle"` or `"bitshuffle"`.

Measured with Blosc zstd clevel 5 ([examples.md](examples.md)):

| Data | noshuffle | shuffle | bitshuffle |
|---|---|---|---|
| air, float32 | 2.89x | **2.97x** | 1.72x |
| rasm, float32 | 2.34x | **2.52x** | 2.14x |
| Poisson counts, uint32 | 4.62x | **6.32x** | 5.58x |
| random bool | 5.99x | 5.99x | **7.97x** |

With lz4 inside Blosc, bitshuffle won on the counts (5.15x against 3.94x). Start from `BloscCodec()`'s automatic choice (shuffle for multi-byte dtypes, bitshuffle for 1-byte) and measure the others on a sample. For booleans, `PackBits()` gave 8.0x.
