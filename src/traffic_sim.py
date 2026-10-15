"""Window-level network traffic simulator with labeled anomalies.

One record per time window (think: 1 second). Raw per-window features:
    pkts, bytes, dports (unique destination ports), srcs (unique source IPs),
    syn_ratio (fraction of SYN packets), udp_frac (fraction of UDP packets).

Benign traffic = slow diurnal drift + AR(1) wander + iid noise + *benign
bursts* (flash crowds: many users -> pkts, bytes and srcs rise together).
Anomalies are injected as labeled events of five types:
    burst       volumetric spike from a few sources (pkts up, srcs ~flat)
    flood       SYN-flood-like (pkts up, SYN ratio up, small packets)
    scan        port-scan-like (many dports, little volume, SYN up)
    proto_shift UDP share jumps, volume ~normal
    slow_ramp   gradual volume growth over a long period

`intensity` in (0, 1] scales anomaly magnitude; `noise` scales benign
variability; `benign_burst_rate` is flash crowds per 1000 windows; `drift`
scales slow benign non-stationarity (drift=1: +42% trend and a +-0.15 log
random walk over the trace, on top of the diurnal cycle).
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np
from scipy.signal import lfilter

RAW_FEATURES = ["pkts", "bytes", "dports", "srcs", "syn_ratio", "udp_frac"]
ANOMALY_TYPES = ("burst", "flood", "scan", "proto_shift", "slow_ramp")

# Baseline traffic constants
P0, S0, D0, SRC0 = 2000.0, 600.0, 12.0, 40.0   # pkts/window, bytes/pkt, dports, srcs
SYN0, UDP0 = 0.08, 0.18


@dataclass(frozen=True)
class SimConfig:
    T: int = 6000                 # windows per trace
    warmup: int = 600             # benign calibration period (no anomalies)
    n_events: int = 14            # anomaly events after warm-up
    anomaly_types: tuple = ANOMALY_TYPES
    intensity: float = 0.6
    noise: float = 1.0
    benign_burst_rate: float = 3.0
    drift: float = 0.0            # benign non-stationarity: trend + random walk of the level
    min_gap: int = 60             # min windows between anomaly events
    grace: int = 5                # windows after an event excluded from FP counting
    seed: int = 0

    def with_(self, **kw) -> "SimConfig":
        return replace(self, **kw)


@dataclass
class Trace:
    X: np.ndarray                 # (T, 6) raw features
    y: np.ndarray                 # (T,) 1 inside anomaly events
    events: list = field(default_factory=list)   # dicts: start,end,type
    bursts: list = field(default_factory=list)   # benign bursts: start,end
    cfg: SimConfig = None


def _place(rng, occupied, lo, hi, dur, gap, tries=200):
    """Pick a start in [lo, hi-dur) so [start-gap, start+dur+gap) is free."""
    for _ in range(tries):
        s = int(rng.integers(lo, hi - dur))
        a, b = max(0, s - gap), min(len(occupied), s + dur + gap)
        if not occupied[a:b].any():
            occupied[s:s + dur] = True
            return s
    return None


def _shape_plateau(d):
    s = np.ones(d)
    if d > 2:
        s[0] = 0.6
        s[-1] = 0.6
    return s


def _shape_flash(d):
    tau = np.arange(d)
    return (1 - np.exp(-(tau + 1) / 1.5)) * np.exp(-tau / (0.6 * d))


def simulate(cfg: SimConfig) -> Trace:
    rng = np.random.default_rng(cfg.seed)
    T = cfg.T
    t = np.arange(T)

    # --- benign base level: diurnal drift x AR(1) wander --------------------
    diurnal = 1 + 0.25 * np.sin(2 * np.pi * (t / 2400.0 + rng.uniform()))
    ar = lfilter([1.0], [1.0, -0.9], rng.normal(0, 0.03 * cfg.noise, T))
    level = diurnal * np.exp(ar)
    if cfg.drift > 0:
        # slow benign drift (growth trend + random walk), on its own RNG stream
        # so the event layout for a given seed is identical across drift values
        rd = np.random.default_rng([cfg.seed, 7919])
        rw = np.cumsum(rd.normal(0, 0.002, T))
        level = level * np.exp(cfg.drift * (0.35 * t / T + rw))

    m_pkts, m_srcs, m_bpp = np.ones(T), np.ones(T), np.ones(T)
    add_dp, add_syn, add_udp = np.zeros(T), np.zeros(T), np.zeros(T)
    y = np.zeros(T, dtype=int)
    occupied = np.zeros(T, dtype=bool)
    events, bursts = [], []
    s = cfg.intensity

    # --- anomaly events (after warm-up) -------------------------------------
    reps = -(-cfg.n_events // len(cfg.anomaly_types))        # balanced, shuffled
    types = rng.permutation(np.tile(np.array(cfg.anomaly_types), reps))[:cfg.n_events]
    for typ in types:
        if typ == "slow_ramp":
            dur = int(rng.integers(60, 151))
        elif typ == "proto_shift":
            dur = int(rng.integers(20, 61))
        else:
            dur = int(rng.integers(10, 41))
        st = _place(rng, occupied, cfg.warmup + 20, T - 20, dur, cfg.min_gap)
        if st is None:
            continue
        en = st + dur
        sl = slice(st, en)
        u = rng.uniform(0.7, 1.3)
        sh = _shape_plateau(dur)
        if typ == "burst":
            m_pkts[sl] *= 1 + 4 * s * u * sh
            m_srcs[sl] *= 1 + 0.1 * sh
        elif typ == "flood":
            m_pkts[sl] *= 1 + 8 * s * u * sh
            add_syn[sl] += np.minimum(0.85, 0.8 * s * u) * sh
            m_bpp[sl] *= 1 - 0.6 * s * sh
            m_srcs[sl] *= 1 + 0.2 * sh
        elif typ == "scan":
            add_dp[sl] += (15 + 400 * s * u) * sh
            m_pkts[sl] *= 1 + 0.25 * s * sh
            add_syn[sl] += 0.3 * s * sh
            m_bpp[sl] *= 1 - 0.3 * s * sh
            m_srcs[sl] *= 1 + 0.05 * sh
        elif typ == "proto_shift":
            add_udp[sl] += np.minimum(0.77, 0.5 * s * u) * sh
            m_pkts[sl] *= 1 + 0.1 * s * sh
        elif typ == "slow_ramp":
            m_pkts[sl] *= 1 + 3 * s * u * np.linspace(0, 1, dur)
            m_srcs[sl] *= 1 + 0.1 * np.linspace(0, 1, dur)
        y[sl] = 1
        events.append({"start": st, "end": en, "type": str(typ)})
    events.sort(key=lambda e: e["start"])

    # --- benign bursts (flash crowds); never overlap anomalies --------------
    block = occupied.copy()
    # pad anomaly intervals so a flash crowd does not bleed into a label
    for e in events:
        block[max(0, e["start"] - 10):min(T, e["end"] + 10)] = True
    n_b = rng.poisson(cfg.benign_burst_rate * T / 1000.0)
    forced = 2 if cfg.benign_burst_rate > 0 else 0   # calibration sees bursts
    starts = []
    for i in range(n_b + forced):
        dur = int(rng.integers(5, 26))
        lo, hi = (30, cfg.warmup - 5) if i < forced else (cfg.warmup, T - 5)
        st = _place(rng, block, lo, hi, dur, 15)
        if st is None:
            continue
        mult = rng.uniform(1.5, 3.0)
        sh = _shape_flash(dur)
        sl = slice(st, st + dur)
        m_pkts[sl] *= 1 + (mult - 1) * sh
        m_srcs[sl] *= 1 + 0.6 * (mult - 1) * sh      # many users -> srcs rise too
        bursts.append({"start": st, "end": st + dur})

    # --- realise features ----------------------------------------------------
    pkts_mean = P0 * level * m_pkts * rng.lognormal(0, 0.08 * cfg.noise, T)
    pkts = np.maximum(1, rng.poisson(pkts_mean)).astype(float)
    bpp = S0 * m_bpp * rng.lognormal(0, 0.05 * cfg.noise, T)
    bytes_ = pkts * bpp
    dports = rng.poisson(D0 + add_dp).astype(float) + 1
    srcs = np.maximum(1, rng.poisson(SRC0 * np.sqrt(level) * m_srcs)).astype(float)
    syn = np.clip(rng.normal(SYN0 + add_syn, 0.015 * cfg.noise), 0, 1)
    udp = np.clip(rng.normal(UDP0 + add_udp, 0.03 * cfg.noise), 0, 1)

    X = np.column_stack([pkts, bytes_, dports, srcs, syn, udp])
    return Trace(X=X, y=y, events=events, bursts=bursts, cfg=cfg)


def to_features(X: np.ndarray) -> np.ndarray:
    """Raw window counts -> detector feature matrix (T, 8).

    cols: log pkts, log bytes, log dports, log srcs, syn_ratio, udp_frac,
          log(pkts/srcs), log(bytes/pkt)
    Shared with the real-data pipeline so one detector code path serves both.
    """
    pkts, byt, dp, src, syn, udp = (X[:, i] for i in range(6))
    return np.column_stack([
        np.log1p(pkts), np.log1p(byt), np.log1p(dp), np.log1p(src),
        syn, udp,
        np.log((pkts + 1.0) / (src + 1.0)),
        np.log((byt + 1.0) / (pkts + 1.0)),
    ])


FEATURE_NAMES = ["log_pkts", "log_bytes", "log_dports", "log_srcs", "syn_ratio",
                 "udp_frac", "log_pkts_per_src", "log_bytes_per_pkt"]
