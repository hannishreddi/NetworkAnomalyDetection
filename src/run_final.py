"""FINAL held-out evaluation. Method is frozen; run ONCE on seeds 2000-2029,
which were never used for tuning or diagnosis.

Usage: python -m src.run_final
Writes results/final_main.csv, results/final_summary.csv,
       results/final_drift.csv, results/final_stats.csv
"""
import numpy as np
import pandas as pd

from .analyze import holm
from .detectors import alarms, default_detectors
from .experiments import POST, score_trace, tune_all
from .metrics import evaluate, mean_ci
from .traffic_sim import ANOMALY_TYPES, SimConfig
from scipy import stats

FINAL_SEEDS = list(range(2000, 2030))
ADAPT = "Adaptive (proposed)"
ORDER = ["Fixed threshold", "Moving average", "Z-score (static)",
         "Mahalanobis (static)", "Isolation Forest", ADAPT]


def eval_setting(cfg, ops, label):
    rows = []
    for s in FINAL_SEEDS:
        tr = simulate_seed(cfg, s)
        sc = score_trace(tr, default_detectors(seed=s))
        for name, post in POST.items():
            rows.append(dict(setting=label, seed=s, detector=name,
                             **evaluate(alarms(sc[name], ops[name], **post), tr, cfg.warmup)))
    return pd.DataFrame(rows)


def simulate_seed(cfg, s):
    from .traffic_sim import simulate
    return simulate(cfg.with_(seed=s))


def paired(df, metric="event_f1"):
    rows = []
    for setting, g in df.groupby("setting", sort=False):
        piv = g.pivot(index="seed", columns="detector", values=metric)
        res = []
        for det in ORDER:
            if det == ADAPT:
                continue
            d = piv[ADAPT] - piv[det]
            p = 1.0 if np.allclose(d, 0) else float(stats.wilcoxon(d).pvalue)
            res.append(dict(setting=setting, versus=det, mean_diff=float(d.mean()),
                            wins=int((d > 0).sum()), losses=int((d < 0).sum()), p=p))
        for r, a in zip(res, holm([r["p"] for r in res])):
            r["p_holm"] = float(a)
        rows += res
    return pd.DataFrame(rows)


if __name__ == "__main__":
    base = SimConfig()
    ops = tune_all(base)                      # ops tuned on dev seeds (unchanged)

    # main comparison (mixed + per-type) and the key drift contrast
    frames = [eval_setting(base, ops, "mixed")]
    for typ in ANOMALY_TYPES:
        frames.append(eval_setting(base.with_(anomaly_types=(typ,)), ops, typ))
    main = pd.concat(frames, ignore_index=True)
    main.to_csv("results/final_main.csv", index=False)

    drift = pd.concat([eval_setting(base.with_(drift=d), ops, f"drift={d}")
                       for d in (0.0, 0.5, 1.0, 2.0)], ignore_index=True)
    drift.to_csv("results/final_drift.csv", index=False)

    rows = []
    for (setting, det), gg in pd.concat([main, drift]).groupby(["setting", "detector"], sort=False):
        row = dict(setting=setting, detector=det)
        for m in ["event_f1", "event_recall", "tpr", "fpr", "fa_per_1k", "delay_median"]:
            mu, h = mean_ci(gg[m]); row[m], row[m + "_ci"] = mu, h
        rows.append(row)
    pd.DataFrame(rows).to_csv("results/final_summary.csv", index=False)

    pd.concat([paired(main), paired(drift)], ignore_index=True).to_csv(
        "results/final_stats.csv", index=False)
    print("FINAL held-out written. mixed-scenario event_f1:")
    sm = pd.DataFrame(rows)
    print(sm[sm.setting == "mixed"].set_index("detector").reindex(ORDER)[["event_f1", "event_f1_ci", "fpr", "fa_per_1k"]].round(3).to_string())
