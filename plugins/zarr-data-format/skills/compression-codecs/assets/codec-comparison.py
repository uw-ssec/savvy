#!/usr/bin/env python3
"""Compare Zarr v3 codec pipelines on a sample of your own data.

Each configuration writes the sample with ``zarr.create_array`` into an
in-memory store and reads it back. The script reports the compression ratio
(``nbytes / nbytes_stored()``), write and read throughput (median of
``--runs``), and whether the round trip was lossless.

Usage:
    python assets/codec-comparison.py --zarr data.zarr/temperature
    python assets/codec-comparison.py --npy sample.npy --chunks 730,25,53
    python assets/codec-comparison.py   # synthetic demo; its ratios are not representative

Requires zarr>=3.1.3 (for ``zarr.codecs.numcodecs``) and numpy.
Throughput is from memory on this machine, so compare rows with each other,
not with storage bandwidth.
"""

import argparse
import time
import warnings

import numpy as np
import zarr
import zarr.codecs.numcodecs as znc
from zarr.codecs import BloscCodec, GzipCodec, ZstdCodec

# zarr warns on every numcodecs.* codec; the table marks them instead.
warnings.filterwarnings("ignore", message="Numcodecs codecs are not in the Zarr")


def load_sample(args):
    if args.zarr:
        src = zarr.open_array(args.zarr, mode="r")
        row_bytes = src.nbytes // max(src.shape[0], 1)
        rows = max(1, min(src.shape[0], int(args.max_mb * 1e6) // max(row_bytes, 1)))
        return src[:rows], src.chunks, f"{args.zarr} (first {rows} of {src.shape[0]} along axis 0)"
    if args.npy:
        data = np.load(args.npy)
        return data, "auto", args.npy
    rng = np.random.default_rng(42)
    data = np.cumsum(rng.normal(size=(1000, 1000)), axis=1).astype("float32")
    return data, (250, 250), "SYNTHETIC random walk (noise compresses ~1.0-1.3x; use --zarr or --npy)"


def configs(dtype, keepbits):
    """(label, filters, compressors); a label ending in * uses a numcodecs.* codec outside the v3 spec."""
    rows = [
        ("no compression", None, ()),
        ("ZstdCodec() (zarr 3 default)", None, None),
        ("ZstdCodec(level=9)", None, [ZstdCodec(level=9)]),
        ("GzipCodec(level=5)", None, [GzipCodec(level=5)]),
    ]
    for cname in ("lz4", "zstd"):
        for shuffle in ("noshuffle", "shuffle", "bitshuffle"):
            rows.append((f"Blosc {cname} clevel=5 {shuffle}", None,
                         [BloscCodec(cname=cname, clevel=5, shuffle=shuffle)]))
    rows += [
        ("LZ4 *", None, [znc.LZ4()]),
        ("BZ2(level=5) *", None, [znc.BZ2(level=5)]),
        ("LZMA(preset=6) *", None, [znc.LZMA(preset=6)]),
    ]
    blosc = [BloscCodec(cname="zstd", clevel=5, shuffle="shuffle")]
    if dtype.kind == "f":
        rows.append((f"BitRound({keepbits}) + Blosc zstd shuffle *", [znc.BitRound(keepbits=keepbits)], blosc))
    elif dtype.kind in "iu":
        rows.append(("Delta + Blosc zstd shuffle *", [znc.Delta(dtype=dtype.str)], blosc))
    elif dtype.kind == "b":
        rows.append(("PackBits + ZstdCodec() *", [znc.PackBits()], None))
    return rows


def bench(data, chunks, filters, compressors, runs):
    kwargs = {}
    if filters is not None:
        kwargs["filters"] = filters
    if compressors is not None:
        kwargs["compressors"] = compressors
    write_s, read_s = [], []
    for _ in range(runs):
        arr = zarr.create_array(store=zarr.storage.MemoryStore(), shape=data.shape,
                                chunks=chunks, dtype=data.dtype, **kwargs)
        t0 = time.perf_counter()
        arr[...] = data
        write_s.append(time.perf_counter() - t0)
        t0 = time.perf_counter()
        back = arr[...]
        read_s.append(time.perf_counter() - t0)
    lossless = np.array_equal(back, data, equal_nan=data.dtype.kind in "fc")
    if lossless:
        error = "lossless"
    else:
        diff = np.abs(back.astype("float64") - data.astype("float64"))
        error = f"max err {np.nanmax(diff):.3g}"
    mb = data.nbytes / 1e6
    return arr.nbytes / arr.nbytes_stored(), mb / np.median(write_s), mb / np.median(read_s), error


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--zarr", help="path to a Zarr array (for an xarray store: store.zarr/<variable>)")
    source.add_argument("--npy", help="path to a .npy file")
    parser.add_argument("--chunks", help="chunk shape, e.g. 730,25,53 (default: source chunks or 'auto')")
    parser.add_argument("--max-mb", type=float, default=64, help="sample size cap for --zarr (default 64)")
    parser.add_argument("--keepbits", type=int, default=10, help="mantissa bits kept by BitRound (default 10)")
    parser.add_argument("--runs", type=int, default=3, help="timing repetitions (default 3)")
    args = parser.parse_args()

    data, chunks, label = load_sample(args)
    if args.chunks:
        chunks = tuple(int(c) for c in args.chunks.split(","))
    if chunks != "auto":
        chunks = tuple(min(c, s) for c, s in zip(chunks, data.shape))
    print(f"Sample: {label}")
    print(f"        shape={data.shape} dtype={data.dtype} chunks={chunks} ({data.nbytes / 1e6:.1f} MB)\n")
    print(f"{'Configuration':<42} {'Ratio':>7} {'Write MB/s':>11} {'Read MB/s':>10}  Round trip")
    print("-" * 86)

    results = []
    for name, filters, compressors in configs(data.dtype, args.keepbits):
        ratio, write, read, error = bench(data, chunks, filters, compressors, args.runs)
        results.append((name, ratio, read, error))
        print(f"{name:<42} {ratio:>6.2f}x {write:>11.0f} {read:>10.0f}  {error}")

    lossless = [r for r in results if r[3] == "lossless" and r[0] != "no compression"]
    best = max(lossless, key=lambda r: r[1])
    fastest = max(lossless, key=lambda r: r[2])
    default = next(r for r in results if r[0].startswith("ZstdCodec()"))
    print(f"\nBest lossless ratio: {best[0]} ({best[1]:.2f}x); default Zstd: {default[1]:.2f}x")
    print(f"Fastest lossless read: {fastest[0]} ({fastest[2]:.0f} MB/s)")
    print("* = numcodecs.* codec: zarr-python reads it, other Zarr v3 implementations may not.")


if __name__ == "__main__":
    main()
