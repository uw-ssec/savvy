"""Bracketing root finder."""


def bisect(f, lo, hi, tol=1e-10, max_iter=200):
    flo = f(lo)
    if flo * f(hi) > 0:
        raise ValueError("root is not bracketed")
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        fmid = f(mid)
        if fmid == 0 or hi - lo < tol:
            return mid
        if flo * fmid < 0:
            hi = mid
        else:
            lo, flo = mid, fmid
    return 0.5 * (lo + hi)
