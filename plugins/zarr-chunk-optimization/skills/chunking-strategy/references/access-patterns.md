# Access Patterns for Multi-Dimensional Zarr Data — Deep Reference

## Contents

| Section | Lines | Description |
|---------|-------|-------------|
| Pattern 1: Spatial Access | 18–44 | Reading complete spatial slices at a single time step |
| Pattern 2: Time-Series Access | 45–70 | Reading all time steps at a single spatial location |
| Pattern 3: Spectral Access | 71–95 | Reading all frequency values at a fixed spatial-temporal point |
| The Trade-Off Problem | 96–105 | Why optimal chunking for all patterns is mutually exclusive |
| How This Plugin Uses Access Patterns | 106–112 | Workflow from user input to chunking recommendation |
| Domain-Agnostic Design | 113–121 | Applying the framework beyond radio astronomy |

---

**Three access patterns** represent common ways scientists read multi-dimensional data. Understanding these patterns is essential for choosing appropriate chunking strategies.

## Pattern 1: Spatial Access

### Definition
Reading a complete 2D or 3D spatial slice at a **single time step** (or other non-spatial coordinate value).

### Example Operations
```python
# OVRO-LWA radio telescope data (time × frequency × baseline)
ds = xr.open_zarr("s3://bucket/data.zarr")

# Load all frequencies and baselines at time index 42 (positional)
spatial_slice = ds.isel(time=42).compute()

# By label, when time is a datetime coordinate
spatial_slice = ds.sel(time="2024-03-08T12:00").compute()
```

**benchmark_runner.py:** `--slice-dims 0` (fix the middle index of dim 0, read the rest).

### Optimal Chunking
- **Small chunks** along the slicing dimension (time)
- **Large chunks** along the loaded dimensions (frequency, baseline)

**Example:** For time×frequency×baseline float32 data, optimal might be `(1, 1024, 512)` (2 MiB per chunk) — one time step per chunk, but large frequency and baseline chunks.

**Why this works:** Xarray/Zarr only loads chunks that intersect the requested time slice. Small time chunks mean less unneeded data is loaded with each chunk. Large frequency/baseline chunks mean fewer HTTP requests to assemble the full spatial extent.

## Pattern 2: Time-Series Access

### Definition
Reading **all time steps** at a single position in every other dimension (or a small subset of positions).

### Example Operations
```python
# Time series at one frequency channel and one baseline (positional)
time_series = ds.isel(frequency=512, baseline=123).compute()

# A few baselines at once
time_series = ds.isel(frequency=512, baseline=[10, 20, 30]).compute()
```

Selecting only `baseline=123` is not a time series: it reads every time step of every frequency, a full time × frequency plane.

**benchmark_runner.py:** `--traverse-dims 0` (fix every other dim at its middle, read the line along time).

### Optimal Chunking
- **Large chunks** along the dimension being read (time)
- **Small chunks** along the fixed dimensions (frequency, baseline)

**Example:** For time×frequency×baseline float32 data, optimal might be `(1024, 64, 16)` (4 MiB per chunk) — many time steps per chunk, small frequency and baseline extents. Don't shrink the fixed dims to 1: `(512, 64, 1)` is a 128 KiB chunk, latency-bound on object storage.

**Why this works:** Large time chunks mean each HTTP request retrieves many time steps, reducing total request count. Small frequency and baseline extents mean little unneeded data comes along with each chunk.

## Pattern 3: Spectral Access

### Definition
Reading **all values along the frequency axis** (or similar spectral/wavelength dimension) at a single spatial-temporal location.

### Example Operations
```python
# Load full spectrum at a specific time and baseline (positional)
spectrum = ds.isel(time=42, baseline=123).compute()

# Access the frequency dimension
frequencies = spectrum['frequency']
intensities = spectrum['data']
```

### Optimal Chunking
- **Large chunks** along the frequency dimension
- **Small chunks** along time and baseline dimensions

**benchmark_runner.py:** `--traverse-dims 1` (dim 1 is frequency here).

**Example:** For time×frequency×baseline float32 data, optimal might be `(8, 2048, 64)` (4 MiB per chunk) — the full frequency axis in one chunk, with small time and baseline extents. `(1, 2048, 1)` would be an 8 KiB chunk, far too small for object storage.

**Why this works:** Similar to time-series access, but optimizing for frequency instead of time. Large frequency chunks mean the full spectrum is retrieved with fewer requests.

## The Trade-Off Problem

**Critical insight:** These three patterns have **mutually exclusive** optimal chunking strategies.

- Spatial access wants: small time, large frequency, large baseline
- Time-series access wants: large time, small frequency, small baseline
- Spectral access wants: small time, large frequency, small baseline

You **cannot optimize for all three simultaneously**. Chunking is a trade-off.

## How This Plugin Uses Access Patterns

1. **User specifies workflow:** Which access pattern(s) dominate their analysis?
2. **Benchmark each pattern:** Measure wall time, memory, HTTP requests for each candidate chunking strategy
3. **Analyze trade-offs:** Identify configurations that favor specific patterns or balance across all three
4. **Recommend chunking:** Based on user priorities (optimize for one pattern, or compromise across multiple)

## Domain-Agnostic Design

While the examples above use OVRO-LWA dimensions (time, frequency, baseline), this plugin is **domain-agnostic**:

- Climate data: `time × latitude × longitude` → spatial (maps), time-series (station data)
- Medical imaging: `patient × slice × x × y` → spatial (full scan), patient-series (longitudinal)
- Hyperspectral imagery: `x × y × wavelength` → spatial (images), spectral (material signatures)

Users define their own dimension names and which dimensions are sliced vs loaded for each pattern.
