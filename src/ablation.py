"""Ablation of the proposed adaptive detector's components, and overhead.

Runs on the exploratory seeds (1000-1029) across a stationary (default) and a
non-stationary (drift=2.0) scenario, since the design claim is specifically
about non-stationarity. The FINAL held-out comparison (seeds 2000-2029) is a
separate script. Each variant is tuned (threshold) on dev seeds, as in the
main comparison.

Usage: python -m src.ablation   ->  results/ablation.csv, results/overhead.csv
"""
import time

import numpy as np
import pandas as pd

from .detectors import (Adaptive, FixedThreshold, IsolationForestDet,
                        MahalanobisStatic, MovingAverage, ZScore, alarms)
from .experiments import DEV_SEEDS, threshold_grid, tune
from .metrics import evaluate, mean_ci
from .traffic_sim import SimConfig, simulate, to_features

ABL_SEEDS = list(range(1000, 1030))
SCEN = {"stationary": SimConfig(), "drift2": SimConfig(drift=2.0)}

# name -> (detector factory, alarm post-processing)
VARIANTS = {
    "Proposed (full)":        (lambda: Adaptive(), dict(m=1, n=1, cusum=None)),
    "– no gating":            (lambda: Adaptive(selective=False), dict(m=1, n=1, cusum=None)),
    "– cov_gate=3 (loosen)":  (lambda: Adaptive(cov_gate=3.0), dict(m=1, n=1, cusum=None)),
    "– diagonal cov":         (lambda: Adaptive(agg="diag"), dict(m=1, n=1, cusum=None)),
    "+ persistence 2of3":     (lambda: Adaptive(), dict(m=2, n=3, cusum=None)),
    "+ CUSUM":                (lambda: Adaptive(), dict(m=1, n=1, cusum=(0.5, 2.0))),
    "static (no adaptation)": (lambda: MahalanobisStatic(), dict(m=1, n=1, cusum=None)),
}


def _score(cfg, seeds, make):
    out = []
    for s in seeds:
        tr = simulate(cfg.with_(seed=s))
        F = to_features(tr.X); n = tr.cfg.warmup
        d = make(); d.fit(F[:n])
        out.append((tr, np.concatenate([np.zeros(n), d.score_batch(F[n:])])))
    return out


def _calm_fpr(alarm, tr):
    T = len(tr.y); g = tr.cfg.grace
    burst = np.zeros(T, bool)
    for b in tr.bursts:
        burst[b["start"]:b["end"]] = True
    grace = np.zeros(T, bool)
    for e in tr.events:
        grace[e["end"]:e["end"] + g] = True
    live = np.arange(T) >= tr.cfg.warmup
    calm = live & (tr.y == 0) & ~grace & ~burst
    return float(alarm[calm].mean()) if calm.any() else np.nan


def run_ablation():
    rows = []
    for scen, cfg in SCEN.items():
        for name, (make, post) in VARIANTS.items():
            dev = _score(cfg, DEV_SEEDS, make)
            grid = threshold_grid([s for _, s in dev], cfg.warmup)
            # reuse experiments.tune via a light wrapper
            devtr = [t for t, _ in dev]; devsc = [{name: s} for _, s in dev]
            from .experiments import POST
            POST[name] = post
            thr = tune(name, devtr, devsc, grid)
            test = _score(cfg, ABL_SEEDS, make)
            for tr, sc in test:
                r = evaluate(alarms(sc, thr, **post), tr, tr.cfg.warmup)
                rows.append(dict(scenario=scen, variant=name, thr=thr,
                                 calm_fpr=_calm_fpr(alarms(sc, thr, **post), tr), **r))
    return pd.DataFrame(rows)


def run_overhead(T=20000):
    """Per-window compute time (us) and model state size (floats)."""
    cfg = SimConfig(T=T + 600)
    tr = simulate(cfg); F = to_features(tr.X); n = cfg.warmup
    dets = [FixedThreshold(), MovingAverage(), ZScore(), MahalanobisStatic(),
            IsolationForestDet(), Adaptive()]
    rows = []
    for d in dets:
        d.fit(F[:n])
        # streaming timing (score_one) for a fair per-window number
        xs = F[n:n + 5000]
        if hasattr(d, "score_one") and d.name != "Isolation Forest":
            t0 = time.perf_counter()
            for x in xs:
                d.score_one(x)
            us = (time.perf_counter() - t0) / len(xs) * 1e6
        else:  # IF: batch scoring, amortised
            t0 = time.perf_counter(); d.score_batch(xs)
            us = (time.perf_counter() - t0) / len(xs) * 1e6
        # state size
        if d.name == "Adaptive (proposed)":
            state = d.m.size + d.S.size
        elif d.name == "Mahalanobis (static)":
            state = d.m.size + d.P.size
        elif d.name == "Z-score (static)":
            state = 2
        elif d.name == "Moving average":
            state = d.w
        elif d.name == "Isolation Forest":
            state = sum(t.tree_.node_count for t in d.model.estimators_)
        else:
            state = 1
        rows.append(dict(detector=d.name, us_per_window=round(us, 3),
                         state_floats=int(state),
                         multivariate=getattr(d, "multivariate", False)))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    ab = run_ablation()
    ab.to_csv("results/ablation.csv", index=False)
    g = ab.groupby(["scenario", "variant"], sort=False)
    summ = g.agg(event_f1=("event_f1", "mean"), event_recall=("event_recall", "mean"),
                 fpr=("fpr", "mean"), calm_fpr=("calm_fpr", "mean")).round(4)
    print(summ.to_string())
    ov = run_overhead()
    ov.to_csv("results/overhead.csv", index=False)
    print("\n", ov.to_string(index=False))
