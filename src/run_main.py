"""Main simulator comparison: tune on dev seeds, evaluate on 30 test seeds.

Usage:  python -m src.run_main
Writes: results/operating_points.json, results/main_results.csv, results/summary_main.csv
"""
import time

import pandas as pd

from .experiments import TEST_SEEDS, run_scenario, save_json, tune_all
from .metrics import mean_ci
from .traffic_sim import ANOMALY_TYPES, SimConfig

if __name__ == "__main__":
    t0 = time.time()
    base = SimConfig()                       # mixed anomalies, intensity 0.6
    ops = tune_all(base)
    save_json(ops, "results/operating_points.json")
    print("operating points (tuned on dev seeds 100-109):", ops, flush=True)

    frames = [run_scenario("mixed", base, ops)]
    for typ in ANOMALY_TYPES:
        frames.append(run_scenario(typ, base.with_(anomaly_types=(typ,)), ops))
    df = pd.concat(frames, ignore_index=True)
    df.to_csv("results/main_results.csv", index=False)

    rows = []
    for (sc, det), g in df.groupby(["scenario", "detector"], sort=False):
        row = dict(scenario=sc, detector=det)
        for m in ["event_recall", "event_f1", "tpr", "fpr", "fnr", "fa_per_1k", "delay_median"]:
            mu, h = mean_ci(g[m])
            row[m], row[m + "_ci"] = mu, h
        rows.append(row)
    pd.DataFrame(rows).to_csv("results/summary_main.csv", index=False)
    print(f"done in {time.time() - t0:.0f}s, {len(TEST_SEEDS)} test seeds")
