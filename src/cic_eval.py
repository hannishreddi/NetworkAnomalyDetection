"""Evaluate the frozen detectors on CIC-IDS2017 windows.

Protocol (per day, no per-dataset tuning of the METHOD — only the alarm
threshold is calibrated on benign, as a deployed monitor would):
  * fit each detector on the first `n_fit` benign windows,
  * threshold-free: ROC-AUC and PR-AUC of the score over all post-fit windows,
  * operating point: threshold = benign-calibration quantile so benign
    FPR ~= target; report detection rate (recall) and benign FPR on the test
    windows (those after n_fit).
"""
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from .cic_pipeline import load_day, to_X
from .detectors import default_detectors
from .traffic_sim import to_features

BASE = "/mnt/user-data/uploads/Downloads/cic_extract/TrafficLabelling "
FILES = {
    "PortScan": BASE + "/Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
    "DDoS": BASE + "/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
}


def evaluate_day(name, path, n_fit_frac=0.6, fpr_target=0.05):
    w = load_day(path)
    y = w.y.to_numpy()
    F = to_features(to_X(w))
    # fit on the LEADING benign run only (the clean pre-attack period); the
    # attack can sit mid-file, so "60% of all benign windows" would run past it
    first_attack = int(y.argmax()) if y.any() else len(y)
    fit_end = max(10, int(first_attack * n_fit_frac))
    rows = []
    for det in default_detectors(seed=0):
        det.fit(F[:fit_end])
        s = det.score_batch(F[fit_end:])
        yy = y[fit_end:]
        if yy.sum() == 0 or yy.sum() == len(yy):
            continue
        roc = roc_auc_score(yy, s)
        pr = average_precision_score(yy, s)
        # calibrate threshold on the HELD-OUT benign calibration windows in test
        benign_scores = s[yy == 0]
        thr = np.quantile(benign_scores, 1 - fpr_target)
        alarm = s > thr
        tpr = float(alarm[yy == 1].mean())
        fpr = float(alarm[yy == 0].mean())
        rows.append(dict(day=name, detector=det.name, n_test=len(yy),
                         n_attack=int(yy.sum()), roc_auc=roc, pr_auc=pr,
                         recall_at_fpr=tpr, fpr=fpr, base_rate=float(yy.mean())))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    out = pd.concat([evaluate_day(n, f) for n, f in FILES.items()], ignore_index=True)
    out.to_csv("results/cic_results.csv", index=False)
    order = ["Fixed threshold", "Moving average", "Z-score (static)",
             "Mahalanobis (static)", "Isolation Forest", "Adaptive (proposed)"]
    for day in out.day.unique():
        g = out[out.day == day].set_index("detector").reindex(order)
        print(f"\n== {day}  (test windows={int(g.n_test.iloc[0])}, attack={int(g.n_attack.iloc[0])})")
        print(g[["roc_auc", "pr_auc", "recall_at_fpr", "fpr"]].round(3).to_string())
