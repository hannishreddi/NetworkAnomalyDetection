"""Sweeps over drift, attack intensity, benign noise and flash-crowd rate.

Every setting is evaluated on the 30 fresh test seeds under two operating-point
policies:
  fixed   thresholds tuned ONCE on the drift-free default dev scenario
          (a deployed monitor calibrated on a clean period, then traffic changes)
  oracle  thresholds re-tuned on dev seeds of the SAME setting (upper bound)
Detector hyper-parameters (adaptive alpha/gate) are identical in both.

Usage: python -m src.run_sweeps      -> results/sweeps.csv
"""
import time
from multiprocessing import Pool

import pandas as pd

from .detectors import alarms, default_detectors
from .experiments import (DEV_SEEDS, POST, TEST_SEEDS, score_trace,
                          threshold_grid, tune, tune_all)
from .metrics import evaluate
from .traffic_sim import SimConfig, simulate

BASE = SimConfig()
SWEEPS = {
    "drift": [0.0, 0.5, 1.0, 2.0],
    "intensity": [0.2, 0.4, 0.6, 0.8, 1.0],
    "noise": [0.5, 1.0, 1.5, 2.0],
    "benign_burst_rate": [0.0, 1.5, 3.0, 6.0, 12.0],
}
FIXED_OPS = None


def _init():
    global FIXED_OPS
    FIXED_OPS = tune_all(BASE)


def _one(job):
    sweep, value = job
    cfg = BASE.with_(**{sweep: value})
    # oracle ops for this setting (dev seeds)
    dev = [simulate(cfg.with_(seed=s)) for s in DEV_SEEDS]
    dev_sc = [score_trace(t, default_detectors(seed=s)) for t, s in zip(dev, DEV_SEEDS)]
    oracle = {n: tune(n, dev, dev_sc, threshold_grid([sc[n] for sc in dev_sc], cfg.warmup))
              for n in POST}
    rows = []
    for s in TEST_SEEDS:
        tr = simulate(cfg.with_(seed=s))
        sc = score_trace(tr, default_detectors(seed=s))
        for policy, ops in (("fixed", FIXED_OPS), ("oracle", oracle)):
            for name, post in POST.items():
                r = evaluate(alarms(sc[name], ops[name], **post), tr, cfg.warmup)
                rows.append(dict(sweep=sweep, value=value, policy=policy, seed=s,
                                 detector=name, **r))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    t0 = time.time()
    jobs = [(k, v) for k, vals in SWEEPS.items() for v in vals]
    with Pool(2, initializer=_init) as pool:
        frames = []
        for i, df in enumerate(pool.imap_unordered(_one, jobs), 1):
            frames.append(df)
            print(f"[{i}/{len(jobs)}] {df.sweep.iloc[0]}={df.value.iloc[0]}  ({time.time() - t0:.0f}s)", flush=True)
    pd.concat(frames, ignore_index=True).to_csv("results/sweeps.csv", index=False)
    print(f"done in {time.time() - t0:.0f}s")
