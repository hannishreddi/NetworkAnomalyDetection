"""Summary tables and paired significance tests for results/sweeps.csv.

Usage: python -m src.analyze
Writes results/sweeps_summary.csv (mean +- 95% CI per setting/detector) and
results/sweeps_stats.csv (Adaptive vs each baseline: paired Wilcoxon on the
same 30 traces, Holm-corrected within each setting/policy/metric).
"""
import numpy as np
import pandas as pd
from scipy import stats

from .metrics import mean_ci

ADAPT = "Adaptive (proposed)"
METRICS = ["event_f1", "event_recall", "event_precision", "tpr", "fpr", "fa_per_1k", "delay_median"]


def holm(p):
    p = np.asarray(p, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, (len(p) - rank) * p[i])
        adj[i] = min(1.0, run)
    return adj


def summarize(df):
    rows = []
    for (sw, val, pol, det), g in df.groupby(["sweep", "value", "policy", "detector"], sort=False):
        row = dict(sweep=sw, value=val, policy=pol, detector=det, n=len(g))
        for m in METRICS:
            mu, h = mean_ci(g[m])
            row[m], row[m + "_ci"] = mu, h
        rows.append(row)
    return pd.DataFrame(rows)


def paired_tests(df, metrics=("event_f1", "fpr")):
    rows = []
    for (sw, val, pol), g in df.groupby(["sweep", "value", "policy"], sort=False):
        piv = {m: g.pivot(index="seed", columns="detector", values=m) for m in metrics}
        for m in metrics:
            res = []
            for det in piv[m].columns:
                if det == ADAPT:
                    continue
                d = piv[m][ADAPT] - piv[m][det]
                if np.allclose(d, 0):
                    p = 1.0
                else:
                    try:
                        p = float(stats.wilcoxon(d, zero_method="wilcox").pvalue)
                    except ValueError:
                        p = 1.0
                res.append(dict(sweep=sw, value=val, policy=pol, metric=m, versus=det,
                                mean_diff=float(d.mean()), median_diff=float(d.median()),
                                wins=int((d > 0).sum()), losses=int((d < 0).sum()), p=p))
            adj = holm([r["p"] for r in res])
            for r, a in zip(res, adj):
                r["p_holm"] = float(a)
            rows += res
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = pd.read_csv("results/sweeps.csv")
    summarize(df).to_csv("results/sweeps_summary.csv", index=False)
    paired_tests(df).to_csv("results/sweeps_stats.csv", index=False)
    print("wrote results/sweeps_summary.csv, results/sweeps_stats.csv")
