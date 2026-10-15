"""Experiment harness: simulate -> score -> tune on dev seeds -> evaluate on test seeds."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .detectors import Adaptive, alarms, default_detectors
from .metrics import evaluate
from .traffic_sim import SimConfig, simulate, to_features

DEV_SEEDS = list(range(100, 110))     # disjoint from test seeds
TEST_SEEDS = list(range(1000, 1030))  # fresh held-out seeds, never used for debugging
DEBUG_SEEDS = list(range(0, 30))      # used while debugging -> NOT used for reported results

# Alarm post-processing per detector in the *main* comparison.
# Every detector uses raw threshold crossing here. Persistence (m-of-n) and
# CUSUM were evaluated on DEV seeds: CUSUM fired on benign flash crowds and
# persistence gave no gain, so neither is in the main design. The ablation
# (separate script) applies every option to every detector.
POST = {
    "Fixed threshold": dict(m=1, n=1, cusum=None),
    "Moving average": dict(m=1, n=1, cusum=None),
    "Z-score (static)": dict(m=1, n=1, cusum=None),
    "Mahalanobis (static)": dict(m=1, n=1, cusum=None),
    "Isolation Forest": dict(m=1, n=1, cusum=None),
    "Adaptive (proposed)": dict(m=1, n=1, cusum=None),
}


def score_trace(tr, detectors, with_time: bool = False):
    """Fit on the warm-up, score the rest. Returns {name: full-length scores}."""
    F = to_features(tr.X)
    n_tr = tr.cfg.warmup
    out, timing = {}, {}
    for det in detectors:
        det.fit(F[:n_tr])
        t0 = time.perf_counter()
        s = det.score_batch(F[n_tr:])
        timing[det.name] = (time.perf_counter() - t0) / (len(F) - n_tr) * 1e6
        out[det.name] = np.concatenate([np.zeros(n_tr), s])
    return (out, timing) if with_time else out


def threshold_grid(score_list, n_train, nq: int = 80):
    v = np.concatenate([s[n_train:] for s in score_list])
    return np.unique(np.quantile(v, np.linspace(0.5, 0.9998, nq)))


def tune(name, traces, scores, grid, fpr_cap: float = 0.01):
    """Pick the threshold maximising mean event-F1 subject to mean window FPR <= cap."""
    post = POST[name]
    best, best_key = None, None
    for thr in grid:
        res = [evaluate(alarms(sc[name], thr, **post), tr, tr.cfg.warmup)
               for tr, sc in zip(traces, scores)]
        f1 = np.mean([r["event_f1"] for r in res])
        fpr = np.mean([r["fpr"] for r in res])
        key = (fpr <= fpr_cap, f1 if fpr <= fpr_cap else -fpr)
        if best_key is None or key > best_key:
            best, best_key = float(thr), key
    return best


def tune_all(base_cfg: SimConfig, detectors_factory=default_detectors, seeds=DEV_SEEDS):
    dev = [simulate(base_cfg.with_(seed=s)) for s in seeds]
    dev_scores = [score_trace(tr, detectors_factory(seed=s)) for tr, s in zip(dev, seeds)]
    ops = {}
    for name in POST:
        grid = threshold_grid([sc[name] for sc in dev_scores], base_cfg.warmup)
        ops[name] = tune(name, dev, dev_scores, grid)
    return ops


def run_scenario(label, cfg, ops, seeds=TEST_SEEDS, detectors_factory=default_detectors):
    rows = []
    for s in seeds:
        tr = simulate(cfg.with_(seed=s))
        sc = score_trace(tr, detectors_factory(seed=s))
        for name, post in POST.items():
            r = evaluate(alarms(sc[name], ops[name], **post), tr, cfg.warmup)
            rows.append(dict(scenario=label, seed=s, detector=name, **r))
    return pd.DataFrame(rows)


def save_json(obj, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2))
