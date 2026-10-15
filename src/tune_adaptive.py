"""Choose the adaptive detector's EWMA rate and the two gates on DEV seeds only,
across SEVERAL dev scenarios at once (so the choice is not fit to one condition).

Usage: python -m src.tune_adaptive
"""
import itertools

import numpy as np

from .detectors import Adaptive, alarms
from .experiments import DEV_SEEDS, POST, threshold_grid, tune
from .metrics import evaluate
from .traffic_sim import SimConfig, simulate, to_features

NAME = "Adaptive (proposed)"
POST[NAME] = dict(m=1, n=1, cusum=None)

# dev scenarios the gates must work across (NOT the test settings' seeds)
SCENARIOS = {
    "default": SimConfig(),
    "highnoise": SimConfig(noise=2.0),
    "highint": SimConfig(intensity=1.0),
    "drift": SimConfig(drift=2.0),
}


def eval_cfg(cfg, alpha, mg, cg):
    dev = [simulate(cfg.with_(seed=s)) for s in DEV_SEEDS]
    F = [to_features(t.X) for t in dev]
    n = cfg.warmup
    scs = []
    for f in F:
        d = Adaptive(alpha=alpha, mean_gate=mg, cov_gate=cg); d.fit(f[:n])
        scs.append({NAME: np.concatenate([np.zeros(n), d.score_batch(f[n:])])})
    thr = tune(NAME, dev, scs, threshold_grid([s[NAME] for s in scs], n))
    r = [evaluate(alarms(s[NAME], thr, **POST[NAME]), t, n) for t, s in zip(dev, scs)]
    return (float(np.mean([x["event_f1"] for x in r])),
            float(np.mean([x["fpr"] for x in r])))


if __name__ == "__main__":
    grid = []
    for alpha in (0.005, 0.01, 0.02):
        for mg in (0.8, 1.0, 1.2):
            for cg in (mg, 2.0, 3.0, 4.0):           # cov_gate >= mean_gate
                if cg < mg:
                    continue
                f1s, fprs = [], []
                for cfg in SCENARIOS.values():
                    f1, fpr = eval_cfg(cfg, alpha, mg, cg)
                    f1s.append(f1); fprs.append(fpr)
                grid.append(dict(alpha=alpha, mean_gate=mg, cov_gate=cg,
                                 min_f1=min(f1s), mean_f1=float(np.mean(f1s)),
                                 max_fpr=max(fprs)))
                print(grid[-1], flush=True)
    # pick: respect FPR budget across all scenarios, then maximise the WORST-case F1
    ok = [g for g in grid if g["max_fpr"] <= 0.01]
    best = max(ok or grid, key=lambda g: g["min_f1"])
    print("BEST (robust across dev scenarios):", best)
