# Compression Codec Patterns

Checked with zarr-python 3.1.5, numcodecs 0.17.1 and xarray 2026.9.0. Each snippet runs on its own and writes to the local path it names.

## Contents

| Pattern | Description |
|---------|-------------|
| 1. Default and General-Purpose Codecs | Zstd default, explicit Blosc, reading the pipeline back |
| 2. Fastest Decompression | Blosc with LZ4 |
| 3. Smallest Lossless Stores | High Zstd levels, LZMA and BZ2, and their read cost |
| 4. Filters | Delta, Quantize, BitRound, FixedScaleOffset, PackBits on v3 arrays |
| 5. Per-Variable Codecs in xarray | `encoding` with `compressors` and `filters` |
| 6. Checksums for Integrity | `Crc32cCodec` and `ZstdCodec(checksum=True)` |
| 7. Blosc Threads and Multiprocessing | What zarr and numcodecs already do |
| 8. Zarr v2 Arrays | numcodecs objects with `zarr_format=2` |

---

## Pattern 1: Default and General-Purpose Codecs

**When to use:** a new array with no measurement yet. The default is a reasonable start: on the datasets in [examples.md](examples.md) it was within 10% of the best Blosc setting.

```python
import zarr
from zarr.codecs import BloscCodec

# Default pipeline: BytesCodec serializer, then ZstdCodec(level=0) (zstd's default level, 3)
z = zarr.create_array("default.zarr", shape=(1000, 1000), chunks=(250, 250),
                      dtype="float32", overwrite=True)
print(z.filters, z.serializer, z.compressors)

# Explicit Blosc: zstd inside, byte shuffle; typesize is taken from the dtype
zb = zarr.create_array("blosc.zarr", shape=(1000, 1000), chunks=(250, 250), dtype="float32",
                       compressors=[BloscCodec(cname="zstd", clevel=5, shuffle="shuffle")],
                       overwrite=True)
print(zb.compressors)
```

`BloscCodec` accepts `cname` in `lz4`, `lz4hc`, `blosclz`, `zstd`, `snappy`, `zlib`; `clevel` 0–9; `shuffle` in `"noshuffle"`, `"shuffle"`, `"bitshuffle"`. Left unset, `shuffle` becomes `"bitshuffle"` for 1-byte dtypes and `"shuffle"` otherwise. `GzipCodec(level=...)` takes 0–9.

---

## Pattern 2: Fastest Decompression

**When to use:** decode time dominates, such as repeated reads from local disk or memory. On object storage fewer bytes usually matter more, so measure end to end before giving up ratio.

```python
import zarr
from zarr.codecs import BloscCodec

z = zarr.create_array("fast.zarr", shape=(2920, 25, 53), chunks=(730, 25, 53), dtype="float32",
                      compressors=[BloscCodec(cname="lz4", clevel=5, shuffle="shuffle")],
                      overwrite=True)
```

On the NCEP air temperature sample, Blosc lz4 read at 5,170 MB/s with a 1.74x ratio, against 4,460 MB/s and 2.83x for the default Zstd ([examples.md](examples.md)).

---

## Pattern 3: Smallest Lossless Stores

**When to use:** archives that are written once and rarely read.

```python
import zarr
from zarr.codecs import ZstdCodec
from zarr.codecs.numcodecs import BZ2, LZMA

kw = dict(shape=(2920, 25, 53), chunks=(730, 25, 53), dtype="float32", overwrite=True)

# In the v3 spec; any Zarr v3 reader can decode it
z = zarr.create_array("archive_zstd.zarr", compressors=[ZstdCodec(level=19)], **kw)

# numcodecs-only: saved as "numcodecs.lzma" / "numcodecs.bz2"
z = zarr.create_array("archive_lzma.zarr", compressors=[LZMA(preset=6)], **kw)
z = zarr.create_array("archive_bz2.zarr", compressors=[BZ2(level=5)], **kw)
```

Measured on the air sample: Zstd level 19 gave 3.59x but wrote at 14 MB/s, with reads unchanged. BZ2 gave 4.80x and LZMA 4.15x, but read at 290 and 490 MB/s against 4,460 MB/s for the default. On the RASM sample all three were within 10% of the default ratio.

---

## Pattern 4: Filters

**When to use:** monotonic integers (Delta), floats with more precision than the science needs (Quantize, BitRound, FixedScaleOffset: all lossy), or booleans (PackBits). On v3 arrays these come from `zarr.codecs.numcodecs`. A plain `numcodecs.Delta` raises `TypeError: Expected an ArrayArrayCodec`.

```python
import numpy as np
import zarr
from zarr.codecs.numcodecs import BitRound, Delta, FixedScaleOffset, PackBits, Quantize

# Monotonic int64 timestamps: Delta stores the differences
ts = zarr.create_array("timestamps.zarr", shape=(1_000_000,), chunks=(100_000,), dtype="int64",
                       filters=[Delta(dtype="int64")], overwrite=True)
ts[:] = np.arange(1_000_000, dtype="int64") * 60_000_000_000  # one-minute cadence in ns

# Lossy float filters: pick one
kw = dict(shape=(2920, 25, 53), chunks=(730, 25, 53), dtype="float32", overwrite=True)
zarr.create_array("bitround.zarr", filters=[BitRound(keepbits=10)], **kw)       # keep 10 mantissa bits
zarr.create_array("quantize.zarr", filters=[Quantize(digits=2, dtype="float32")], **kw)
zarr.create_array("scaled.zarr", **kw,
                  filters=[FixedScaleOffset(offset=273.15, scale=100, dtype="float32", astype="int16")])

# Booleans: 8 values per byte
mask = zarr.create_array("mask.zarr", shape=(2000, 2000), chunks=(1000, 1000), dtype="bool",
                         filters=[PackBits()], overwrite=True)
```

- Put Quantize or BitRound **before** Delta. Delta-then-Quantize quantizes the differences, and the rounding errors add up on decode (see [common-issues.md](common-issues.md#issue-6-filter-order)).
- FixedScaleOffset stores `round((x - offset) * scale)` as `astype`. Check that the range fits: `int16` holds ±327.67 at `scale=100`.
- Record the precision kept in the array attributes so readers know the data is lossy.

---

## Pattern 5: Per-Variable Codecs in xarray

**When to use:** a Dataset whose variables need different codecs. xarray takes `compressors` and `filters`, and `chunks` as a tuple. `"compressor"` raises `ValueError: unexpected encoding parameters for zarr backend`.

```python
import numpy as np
import xarray as xr
from zarr.codecs import BloscCodec
from zarr.codecs.numcodecs import PackBits

rng = np.random.default_rng(42)
dims = ("time", "lat", "lon")
ds = xr.Dataset({
    "temperature": (dims, rng.normal(280, 15, (60, 90, 180)).astype("float32")),
    "obs_count": (dims, rng.poisson(50, (60, 90, 180)).astype("uint16")),
    "cloud_mask": (dims, rng.integers(0, 2, (60, 90, 180), dtype="bool")),
})

encoding = {
    "temperature": {"compressors": [BloscCodec(cname="zstd", clevel=5, shuffle="shuffle")],
                    "chunks": (30, 90, 180)},
    "obs_count": {"compressors": [BloscCodec(cname="zstd", clevel=5, shuffle="shuffle")],
                  "chunks": (30, 90, 180)},
    "cloud_mask": {"filters": [PackBits()], "chunks": (30, 90, 180)},
}
ds.to_zarr("multi_codec.zarr", mode="w", encoding=encoding, consolidated=False)
```

For a `zarr_format=2` store, pass numcodecs objects instead, still under `compressors` (for example `numcodecs.Blosc(cname="zstd")`).

---

## Pattern 6: Checksums for Integrity

**When to use:** data that must be trusted after copies, transfers or long storage. Without a checksum, a flipped bit in a Blosc or Zstd chunk decoded to wrong but finite values with no error. With one, the read raised.

```python
import zarr
from zarr.codecs import BloscCodec, Crc32cCodec, ZstdCodec

kw = dict(shape=(1000, 1000), chunks=(250, 250), dtype="float32", overwrite=True)

# CRC32C appended after compression (any compressor)
z = zarr.create_array("checked.zarr", **kw,
                      compressors=[BloscCodec(cname="zstd", clevel=5, shuffle="shuffle"), Crc32cCodec()])

# Or zstd's own frame checksum
z = zarr.create_array("checked_zstd.zarr", compressors=[ZstdCodec(level=3, checksum=True)], **kw)
```

A mismatch raises `ValueError: Stored and computed checksum do not match` (Crc32c) or `RuntimeError: Zstd decompression error: b"Restored data doesn't match checksum"`. Sharded arrays already checksum the shard index with CRC32C, not the chunk data.

---

## Pattern 7: Blosc Threads and Multiprocessing

**When to use:** Blosc with Dask, `multiprocessing` or joblib, or old advice to set `use_threads`.

- Importing `zarr` sets `numcodecs.blosc.use_threads = False` (zarr's `BloscCodec` does it at import, "to avoid threading issues in asyncio contexts").
- numcodecs never uses Blosc's threaded global context in a forked child: `_get_use_threads()` returns False when the process ID differs from the one that imported numcodecs (present in numcodecs 0.10.0, 0.14.0 and current `main`). Its source says threaded mode after a fork "will cause a program hang". Nothing in it describes corruption.
- A forked `multiprocessing` pool of 8 workers writing 64 Blosc chunks, with `use_threads = True` set in the parent, read back with 0 mismatches (numcodecs 0.17.1).

Measured `numcodecs.blosc._get_use_threads()` with zarr 3.1.5 on numcodecs 0.16.5 and 0.17.1 (same results):

| Where | Before `import zarr` | After `import zarr` |
|---|---|---|
| Main thread of the parent | True (`use_threads` is `None`, adaptive) | False |
| `fork` child | False | False |

```python
import numcodecs.blosc
import zarr  # noqa: F401  (importing zarr sets use_threads to False)

print(numcodecs.blosc.use_threads)  # False
```

Nothing more is needed. Setting `use_threads = True` re-enables Blosc's internal threads in that process, never in its forked children.

---

## Pattern 8: Zarr v2 Arrays

**When to use:** writing for readers that only support Zarr v2. zarr-python 3 accepts numcodecs objects here, and `open_array` still accepts the old `compressor=` keyword.

```python
import numcodecs
import zarr

z = zarr.create_array("v2.zarr", shape=(1000,), chunks=(100,), dtype="int64", zarr_format=2,
                      filters=[numcodecs.Delta(dtype="int64")],
                      compressors=numcodecs.Blosc(cname="zstd", clevel=5, shuffle=numcodecs.Blosc.SHUFFLE),
                      overwrite=True)
print(z.filters, z.compressors)

# Legacy spelling, v2 only
z2 = zarr.open_array("v2_legacy.zarr", mode="w", shape=(1000,), chunks=(100,), dtype="float32",
                     zarr_format=2, compressor=numcodecs.Zstd(level=3))
```

A v2 array holds one compressor. Left unset, it is `numcodecs.Zstd(level=0)` from `zarr.create_array`/`open_array`, but `Blosc(cname="lz4", clevel=5, shuffle=SHUFFLE)` from `Group.create_array` in a v2 group, the path xarray takes. `numcodecs.Blosc()` itself defaults to `cname="lz4"`, `clevel=5`, `SHUFFLE`, and, for a raw `bytes` input, typesize 1.
