"""Power spectrum of an evenly sampled time series (pure Python; numpy is not installed)."""
import cmath


def fft(x):
    """Radix-2 Cooley-Tukey FFT; len(x) must be a power of two."""
    n = len(x)
    if n == 1:
        return [complex(x[0])]
    if n % 2:
        raise ValueError("length must be a power of two")
    even, odd = fft(x[0::2]), fft(x[1::2])
    out = [0j] * n
    for k in range(n // 2):
        tw = cmath.exp(-2j * cmath.pi * k / n) * odd[k]
        out[k] = even[k] + tw
        out[k + n // 2] = even[k] - tw
    return out


def power_spectrum(x, fs):
    """One-sided spectrum: (frequencies in Hz, power |X_k|^2 / n) for k = 0..n/2."""
    n = len(x)
    spec = fft(x)
    freqs = [k * fs / n for k in range(n // 2 + 1)]
    power = [abs(spec[k]) ** 2 / n for k in range(n // 2 + 1)]
    return freqs, power


if __name__ == "__main__":
    import math

    fs, n = 64.0, 256
    signal = [math.sin(2 * math.pi * 5.0 * i / fs) for i in range(n)]
    freqs, power = power_spectrum(signal, fs)
    peak = max(range(len(power)), key=power.__getitem__)
    print(f"peak at {freqs[peak]:.2f} Hz, power {power[peak]:.3f}")
