"""Anomaly detectors over per-window traffic features.

Protocol (all detectors):
    det.fit(F_train)          calibrate on the benign warm-up period
    det.score_batch(F_test)   causal anomaly score per window (higher = more
                              anomalous); state continues from the end of fit()
    det.score_one(x)          streaming equivalent (used for overhead timing
                              and for equivalence tests)

Thresholding and alarm post-processing (m-of-n persistence, CUSUM) live in
`alarms()` so one score stream can be swept over many operating points.

Univariate detectors look at column 0 (log packets/window), as an operator's
classic volume monitor would. Multivariate detectors use all 8 features.
"""
from __future__ import annotations

from collections import deque

import numpy as np
from sklearn.ensemble import IsolationForest

UNI = 0          # column used by univariate detectors (log_pkts)
LAM = 0.1        # covariance shrinkage toward its diagonal


def _reg_cov(S: np.ndarray, lam: float = LAM) -> np.ndarray:
    d = np.diag(np.diag(S)) + 1e-9 * np.eye(len(S))
    return (1 - lam) * S + lam * d


class Detector:
    name = "base"
    multivariate = False

    def fit(self, F_train): raise NotImplementedError
    def score_batch(self, F): return np.array([self.score_one(x) for x in F])
    def score_one(self, x): raise NotImplementedError


class FixedThreshold(Detector):
    """Alarm when packets/window exceeds a constant (constant chosen by tuning)."""
    name = "Fixed threshold"

    def fit(self, F_train): pass
    def score_batch(self, F): return F[:, UNI].copy()
    def score_one(self, x): return float(x[UNI])


class ZScore(Detector):
    """|z| of packets/window against mean/std frozen from the benign warm-up."""
    name = "Z-score (static)"

    def fit(self, F_train):
        self.mu = float(F_train[:, UNI].mean())
        self.sd = float(F_train[:, UNI].std() + 1e-9)

    def score_batch(self, F): return np.abs(F[:, UNI] - self.mu) / self.sd
    def score_one(self, x): return abs(float(x[UNI]) - self.mu) / self.sd


class MovingAverage(Detector):
    """|x - mean of previous w windows| on log packets (w=60)."""
    name = "Moving average"

    def __init__(self, w: int = 60):
        self.w = w

    def fit(self, F_train):
        self.buf = deque(F_train[-self.w:, UNI].tolist(), maxlen=self.w)
        self.sum = float(sum(self.buf))

    def score_one(self, x):
        v = float(x[UNI])
        s = abs(v - self.sum / len(self.buf))
        if len(self.buf) == self.w:
            self.sum -= self.buf[0]
        self.buf.append(v)
        self.sum += v
        return s

    def score_batch(self, F):
        tail = np.array(self.buf)
        v = np.concatenate([tail, F[:, UNI]])
        cs = np.concatenate([[0.0], np.cumsum(v)])
        n0 = len(tail)
        idx = np.arange(n0, len(v))
        ma = (cs[idx] - cs[idx - self.w]) / self.w
        out = np.abs(v[n0:] - ma)
        # keep streaming state consistent with having consumed F
        self.buf = deque(v[-self.w:].tolist(), maxlen=self.w)
        self.sum = float(sum(self.buf))
        return out


class MahalanobisStatic(Detector):
    """Multivariate statistical detector: Mahalanobis distance to frozen
    warm-up mean/covariance. Isolates the value of *adapting* (vs Adaptive)."""
    name = "Mahalanobis (static)"
    multivariate = True

    def fit(self, F_train):
        self.m = F_train.mean(0)
        self.P = np.linalg.inv(_reg_cov(np.cov(F_train.T)))
        self.p = F_train.shape[1]

    def score_batch(self, F):
        d = F - self.m
        return np.sqrt(np.einsum("ij,jk,ik->i", d, self.P, d) / self.p)

    def score_one(self, x):
        d = x - self.m
        return float(np.sqrt(d @ self.P @ d / self.p))


class IsolationForestDet(Detector):
    """Heavy-ML reference: Isolation Forest trained on the benign warm-up."""
    name = "Isolation Forest"
    multivariate = True

    def __init__(self, n_estimators: int = 100, seed: int = 0):
        self.n, self.seed = n_estimators, seed

    def fit(self, F_train):
        self.model = IsolationForest(n_estimators=self.n, random_state=self.seed).fit(F_train)

    def score_batch(self, F): return -self.model.score_samples(F)
    def score_one(self, x): return float(-self.model.score_samples(x[None, :])[0])


class Adaptive(Detector):
    """Proposed detector: online EWMA mean + covariance, multivariate score,
    selective (gated) updates.

    score_t = sqrt( d' S^-1 d / p ),  d = x_t - m_{t-1}
    agg     : 'mahal' (full covariance), 'diag' (z-scores only), 'maxz'
    Persistence (m-of-n) and CUSUM are applied afterwards in `alarms()`.

    Two gates (a single gate under-learns normal variance: with one low gate,
    every noisy-but-benign window also freezes the covariance, so variance is
    estimated from only the quietest traffic and calm-time false alarms rise):
      mean_gate : above it the MEAN creeps slowly (winsorised, x rho) instead
                  of tracking -> an attack cannot pull the baseline toward
                  itself, but a sustained real level shift is still learned.
      cov_gate  : only above this (>= mean_gate) is the COVARIANCE update
                  frozen -> ordinary benign fluctuation keeps calibrating the
                  spread, and only clear outliers are excluded.
    O(p^2) time and state per window.
    """
    multivariate = True

    # Defaults chosen on dev scenarios {default, high-noise, high-intensity,
    # drift} jointly (src/tune_adaptive.py), picking the max-FPR<=1% setting
    # with the best WORST-CASE event-F1. A sweep of cov_gate > mean_gate (the
    # ablation) confirms it hurts: admitting more windows lets attacks inflate
    # the covariance, which costs more detection than it saves in false alarms.
    def __init__(self, alpha: float = 0.005, mean_gate: float = 1.2,
                 cov_gate: float = 1.2, rho: float = 0.1, agg: str = "mahal",
                 selective: bool = True, name: str = "Adaptive (proposed)"):
        self.alpha, self.mean_gate, self.cov_gate, self.rho = alpha, mean_gate, cov_gate, rho
        self.agg, self.selective, self.name = agg, selective, name

    def fit(self, F_train):
        self.m = F_train.mean(0).copy()
        self.S = np.cov(F_train.T)
        self.p = F_train.shape[1]

    def score_one(self, x):
        d = x - self.m
        if self.agg == "mahal":
            d2 = float(d @ np.linalg.solve(_reg_cov(self.S), d))
            s = np.sqrt(max(d2, 0.0) / self.p)
        else:
            z = d / np.sqrt(np.diag(self.S) + 1e-9)
            s = float(np.sqrt(np.mean(z * z))) if self.agg == "diag" else float(np.abs(z).max())
        if self.selective and s > self.mean_gate:
            self.m = self.m + self.alpha * self.rho * d * (self.mean_gate / s)
        else:
            self.m = self.m + self.alpha * d
        if not (self.selective and s > self.cov_gate):
            # winsorise d into the covariance so a window just above mean_gate
            # contributes its spread without an attack-sized quadratic kick
            dc = d if s <= self.mean_gate else d * (self.mean_gate / s)
            self.S = (1 - self.alpha) * (self.S + self.alpha * np.outer(dc, dc))
        return float(s)


def default_detectors(seed: int = 0):
    return [FixedThreshold(), MovingAverage(), ZScore(), MahalanobisStatic(),
            IsolationForestDet(seed=seed), Adaptive()]


# --------------------------------------------------------------------------
# Alarm post-processing (shared by every detector)
# --------------------------------------------------------------------------
def alarms(scores: np.ndarray, thr: float, m: int = 1, n: int = 1,
           cusum: tuple | None = None) -> np.ndarray:
    """Boolean alarm per window from a score stream.

    m-of-n persistence: alarm at t iff >= m of windows t-n+1..t exceed thr.
    cusum=(k, h): additionally alarm while C_t > h*thr, where
        C_t = max(0, C_{t-1} + score_t - k*thr)   (catches slow drifts).
    Everything is causal.
    """
    exc = scores > thr
    if n > 1:
        cnt = np.convolve(exc.astype(int), np.ones(n, dtype=int))[:len(scores)]
        a = cnt >= m
    else:
        a = exc
    if cusum is not None:
        k, h = cusum
        steps = scores - k * thr
        S = np.concatenate([[0.0], np.cumsum(steps)])
        C = (S - np.minimum.accumulate(S))[1:]       # Lindley recursion, vectorised
        a = a | (C > h * thr)
    return a
