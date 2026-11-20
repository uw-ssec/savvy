# Measured Examples

All numbers below were measured with zarr-python 3.1.5 and numcodecs 0.17.1 on an Apple M5 Max, through an in-memory store. Throughput depends on the machine, so compare rows with each other. Ratios depend on the data, so measure your own.

## Contents

| Example | Description |
|---------|-------------|
| 1. Codec Comparison on Four Datasets | Ratios from `assets/codec-comparison.py` |
| 2. Delta Filter for Timestamps | When Delta helps and when it doesn't |
| 3. Shuffle Modes on Integer Counts | Shuffle choice depends on the inner codec |
| 4. Choosing BitRound Precision | Ratio against error before adopting a lossy filter |

---

## Example 1: Codec Comparison on Four Datasets

Datasets:
- **air**: xarray tutorial `air_temperature` (NCEP reanalysis), `air` as float32, shape `(2920, 25, 53)`, chunks `(730, 25, 53)`. The source file packs it as int16 × 0.01 K.
- **rasm**: xarray tutorial `rasm` (RASM model output), `Tair` as float32, shape `(36, 205, 275)`, chunks `(12, 205, 275)`, 54% NaN.
- **counts**: `rng.poisson(50, (2000, 2000))` as uint32, chunks `(500, 500)`.
- **noise**: the script's default random walk (float32, `(1000, 1000)`).

| Configuration | air | rasm | counts | noise | air read MB/s |
|---|---|---|---|---|---|
| `ZstdCodec()` (default) | 2.83x | 2.32x | 4.21x | 1.08x | 4,460 |
| `ZstdCodec(level=9)` | 3.09x | 2.34x | 4.49x | 1.08x | 4,510 |
| `GzipCodec(level=5)` | 2.76x | 2.34x | 4.02x | 1.08x | 1,560 |
| Blosc lz4 5, noshuffle | 1.49x | 2.04x | 2.62x | 1.00x | 7,190 |
| Blosc lz4 5, shuffle | 1.74x | 2.23x | 3.94x | 1.24x | 5,170 |
| Blosc lz4 5, bitshuffle | 1.60x | 1.66x | 5.15x | 1.00x | 5,590 |
| Blosc zstd 5, noshuffle | 2.89x | 2.34x | 4.62x | 1.08x | 4,460 |
| Blosc zstd 5, shuffle | 2.97x | 2.52x | 6.32x | 1.28x | 3,130 |
| Blosc zstd 5, bitshuffle | 1.72x | 2.14x | 5.58x | 1.08x | 3,390 |
| LZ4 (numcodecs) | 1.71x | 2.06x | 2.65x | 1.00x | 7,100 |
| BZ2 level 5 (numcodecs) | 4.80x | 2.27x | 6.16x | 1.05x | 290 |
| LZMA preset 6 (numcodecs) | 4.15x | 2.51x | 5.92x | 1.23x | 490 |
| BitRound(10) + Blosc zstd shuffle (lossy) | 5.18x | 4.80x | — | 2.52x | 2,800 |

What the table supports:
- No lossless codec reached 5x on the float data, and none passed 1.3x on noise. Synthetic noise cannot rank codecs.
- The default Zstd was within 10% of the best Blosc setting on air and rasm, and 33% behind it on counts.
- Shuffle helped the integer counts most (4.62x to 6.32x with zstd). On air it changed little, and with zstd, bitshuffle was worse than no shuffle.
- BZ2 and LZMA gave the highest lossless ratios on air but read 9–15x slower than the default.

Reproduce a column on your own data:

```bash
python assets/codec-comparison.py --zarr store.zarr/air --runs 5
python assets/codec-comparison.py --npy counts.npy --chunks 500,500
```

---

## Example 2: Delta Filter for Timestamps

Delta stores differences between neighbours. It pays off when the differences repeat.

```python
import numpy as np
import zarr
from zarr.codecs.numcodecs import Delta

rng = np.random.default_rng(42)
series = {
    "regular 1-minute cadence": np.arange(1_000_000, dtype="int64") * 60_000_000_000,
    "random 1-10 ms steps": np.cumsum(rng.integers(1_000_000, 10_000_000, 1_000_000)),
}
for name, ts in series.items():
    for label, kw in (("no filter", {}), ("Delta", {"filters": [Delta(dtype="int64")]})):
        z = zarr.create_array(zarr.storage.MemoryStore(), shape=ts.shape, chunks=(100_000,),
                              dtype="int64", **kw)
        z[:] = ts
        print(f"{name:<26} {label:<10} {z.nbytes / z.nbytes_stored():8.1f}x")
```

Output:

```
regular 1-minute cadence   no filter       1.3x
regular 1-minute cadence   Delta        4491.9x
random 1-10 ms steps       no filter       2.2x
random 1-10 ms steps       Delta           2.3x
```

On non-monotonic counts, Delta made things worse (6.32x to 3.34x with Blosc zstd shuffle).

---

## Example 3: Shuffle Modes on Integer Counts

The best shuffle mode depended on the codec inside Blosc. Benchmark through zarr so that Blosc gets the dtype's typesize.

```python
import numpy as np
import zarr
from zarr.codecs import BloscCodec

counts = np.random.default_rng(42).poisson(50, (2000, 2000)).astype("uint32")

for cname in ("lz4", "zstd"):
    for shuffle in ("noshuffle", "shuffle", "bitshuffle"):
        z = zarr.create_array(zarr.storage.MemoryStore(), shape=counts.shape, chunks=(500, 500),
                              dtype=counts.dtype,
                              compressors=[BloscCodec(cname=cname, clevel=5, shuffle=shuffle)])
        z[:] = counts
        print(f"{cname:<5} {shuffle:<11} {z.nbytes / z.nbytes_stored():.2f}x")
```

Output:

```
lz4   noshuffle   2.62x
lz4   shuffle     3.94x
lz4   bitshuffle  5.15x
zstd  noshuffle   4.62x
zstd  shuffle     6.32x
zstd  bitshuffle  5.58x
```

Calling `Blosc().encode(counts.tobytes())` directly would hide the difference: a `bytes` buffer has typesize 1, so byte shuffle does nothing.

---

## Example 4: Choosing BitRound Precision

BitRound zeroes the low mantissa bits. Measure ratio against error on a sample before adopting it, and keep at least the precision the data was recorded with.

```python
import numpy as np
import zarr
from zarr.codecs import BloscCodec
from zarr.codecs.numcodecs import BitRound

sample = np.load("air.npy")  # float32 sample of the real variable

for keepbits in (4, 7, 10, 13, 23):
    z = zarr.create_array(zarr.storage.MemoryStore(), shape=sample.shape, chunks=(730, 25, 53),
                          dtype=sample.dtype, filters=[BitRound(keepbits=keepbits)],
                          compressors=[BloscCodec(cname="zstd", clevel=5, shuffle="shuffle")])
    z[:] = sample
    err = np.abs(z[:] - sample)
    print(f"keepbits={keepbits:>2}  ratio={z.nbytes / z.nbytes_stored():5.2f}x  "
          f"max abs err={np.nanmax(err):.3g}  mean abs err={np.nanmean(err):.3g}")
```

Output on the air sample (221–317 K, recorded to 0.01 K):

```
keepbits= 4  ratio=45.10x  max abs err=8  mean abs err=4.06
keepbits= 7  ratio=11.94x  max abs err=1  mean abs err=0.474
keepbits=10  ratio= 5.18x  max abs err=0.11  mean abs err=0.0552
keepbits=13  ratio= 4.37x  max abs err=0.015  mean abs err=0.00647
keepbits=23  ratio= 2.97x  max abs err=0  mean abs err=0
```

Even `keepbits=13` loses more than the 0.01 K recording step, so here every BitRound gain discards recorded precision. `FixedScaleOffset(offset=0, scale=100, dtype="float32", astype="int16")` keeps the recorded values exactly, at 2.94x with Blosc zstd shuffle.
