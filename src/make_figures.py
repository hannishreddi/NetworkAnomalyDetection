"""Generate publication figures (vector PDF) from the result CSVs.

Usage: python -m src.make_figures   -> report/figures/*.pdf
Palette is colourblind-safe (Okabe-Ito) and distinguishable in grayscale via
distinct markers / linestyles; no chartjunk, direct labels where it helps.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({
    "font.size": 9, "font.family": "serif", "axes.grid": True,
    "grid.alpha": 0.25, "grid.linewidth": 0.5, "axes.axisbelow": True,
    "figure.dpi": 150, "savefig.bbox": "tight", "axes.linewidth": 0.6,
})
FIG = "report/figures"

# Okabe-Ito
C = {"black": "#000000", "orange": "#E69F00", "sky": "#56B4E9", "green": "#009E73",
     "yellow": "#F0E442", "blue": "#0072B2", "verm": "#D55E00", "purple": "#CC79A7"}
DET_ORDER = ["Fixed threshold", "Moving average", "Z-score (static)",
             "Mahalanobis (static)", "Isolation Forest", "Adaptive (proposed)"]
DET_SHORT = {"Fixed threshold": "Fixed thr.", "Moving average": "Moving avg",
             "Z-score (static)": "Z-score", "Mahalanobis (static)": "Mahalanobis",
             "Isolation Forest": "Iso. Forest", "Adaptive (proposed)": "Adaptive*"}
DET_COLOR = {"Fixed threshold": C["sky"], "Moving average": C["yellow"],
             "Z-score (static)": C["green"], "Mahalanobis (static)": C["orange"],
             "Isolation Forest": C["purple"], "Adaptive (proposed)": C["verm"]}


def fig_main_f1():
    s = pd.read_csv("results/final_summary.csv")
    g = s[s.setting == "mixed"].set_index("detector").reindex(DET_ORDER)
    fig, ax = plt.subplots(figsize=(5.2, 2.7))
    x = np.arange(len(DET_ORDER))
    ax.bar(x, g.event_f1, yerr=g.event_f1_ci, capsize=3,
           color=[DET_COLOR[d] for d in DET_ORDER], edgecolor="black", linewidth=0.5)
    for xi, v in zip(x, g.event_f1):
        ax.text(xi, v + 0.03, f"{v:.3f}", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(x); ax.set_xticklabels([DET_SHORT[d] for d in DET_ORDER], rotation=20, ha="right")
    ax.set_ylabel("Event F1"); ax.set_ylim(0, 1.08)
    ax.set_title("Mixed-anomaly detection (held-out seeds 2000–2029)", fontsize=9)
    fig.savefig(f"{FIG}/fig_main_f1.pdf"); plt.close(fig)


def fig_drift():
    s = pd.read_csv("results/final_summary.csv")
    d = s[s.setting.str.startswith("drift")].copy()
    d["drift"] = d.setting.str.replace("drift=", "").astype(float)
    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    for det in ["Fixed threshold", "Isolation Forest", "Mahalanobis (static)", "Adaptive (proposed)"]:
        gg = d[d.detector == det].sort_values("drift")
        ls = "--" if det != "Adaptive (proposed)" else "-"
        mk = {"Fixed threshold": "s", "Isolation Forest": "^",
              "Mahalanobis (static)": "o", "Adaptive (proposed)": "D"}[det]
        ax.errorbar(gg.drift, gg.event_f1, yerr=gg.event_f1_ci, marker=mk, ls=ls,
                    color=DET_COLOR[det], label=DET_SHORT[det], capsize=2, lw=1.4, ms=5)
    ax.set_xlabel("Benign drift strength"); ax.set_ylabel("Event F1")
    ax.set_title("Robustness to non-stationary traffic", fontsize=9)
    ax.legend(fontsize=7.5, loc="lower left"); ax.set_ylim(0.3, 1.0)
    fig.savefig(f"{FIG}/fig_drift.pdf"); plt.close(fig)


def fig_pertype():
    s = pd.read_csv("results/final_summary.csv")
    types = ["burst", "flood", "scan", "proto_shift", "slow_ramp"]
    M = np.array([[s[(s.setting == t) & (s.detector == d)].event_recall.values[0]
                   for t in types] for d in DET_ORDER])
    fig, ax = plt.subplots(figsize=(5.4, 2.9))
    im = ax.imshow(M, cmap="YlGnBu", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(types))); ax.set_xticklabels(
        ["Burst", "Flood", "Scan", "Proto-shift", "Slow ramp"], rotation=20, ha="right")
    ax.set_yticks(range(len(DET_ORDER))); ax.set_yticklabels([DET_SHORT[d] for d in DET_ORDER])
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center",
                    color="white" if M[i, j] > 0.55 else "black", fontsize=7)
    ax.set_title("Per-attack-type event recall", fontsize=9)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Recall")
    fig.savefig(f"{FIG}/fig_pertype.pdf"); plt.close(fig)


def fig_sweeps():
    s = pd.read_csv("results/sweeps_summary.csv")
    s = s[s.policy == "fixed"]
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.8))
    for ax, sw, xlab in [(axes[0], "intensity", "Attack intensity"),
                         (axes[1], "noise", "Benign noise level")]:
        for det in ["Fixed threshold", "Isolation Forest", "Mahalanobis (static)", "Adaptive (proposed)"]:
            gg = s[(s.sweep == sw) & (s.detector == det)].sort_values("value")
            mk = {"Fixed threshold": "s", "Isolation Forest": "^",
                  "Mahalanobis (static)": "o", "Adaptive (proposed)": "D"}[det]
            ls = "-" if det == "Adaptive (proposed)" else "--"
            ax.plot(gg.value, gg.event_f1, marker=mk, ls=ls, color=DET_COLOR[det],
                    label=DET_SHORT[det], lw=1.3, ms=4)
        ax.set_xlabel(xlab); ax.set_ylim(0, 1.0)
    axes[0].set_ylabel("Event F1")
    axes[1].legend(fontsize=7, loc="lower left")
    fig.suptitle("Sensitivity to attack intensity and benign noise", fontsize=9)
    fig.savefig(f"{FIG}/fig_sweeps.pdf"); plt.close(fig)


def fig_ablation():
    ab = pd.read_csv("results/ablation.csv")
    g = ab.groupby(["scenario", "variant"], sort=False).event_f1.mean().reset_index()
    variants = ["Proposed (full)", "– no gating", "– cov_gate=3 (loosen)",
                "– diagonal cov", "+ persistence 2of3", "+ CUSUM", "static (no adaptation)"]
    fig, ax = plt.subplots(figsize=(6.2, 2.9))
    x = np.arange(len(variants)); w = 0.38
    for i, (scen, col, lab) in enumerate([("stationary", C["blue"], "Stationary"),
                                          ("drift2", C["verm"], "Drift ×2")]):
        vals = [g[(g.scenario == scen) & (g.variant == v)].event_f1.values[0] for v in variants]
        ax.bar(x + (i - 0.5) * w, vals, w, label=lab, color=col, edgecolor="black", linewidth=0.4)
    ax.set_xticks(x); ax.set_xticklabels(
        ["Full*", "no gating", "loosen\ncov-gate", "diagonal\ncov", "+persist.", "+CUSUM", "static"],
        rotation=0, fontsize=7)
    ax.set_ylabel("Event F1"); ax.set_ylim(0, 1.0); ax.legend(fontsize=8)
    ax.set_title("Ablation of proposed components", fontsize=9)
    fig.savefig(f"{FIG}/fig_ablation.pdf"); plt.close(fig)


def fig_roc_cic():
    # recompute ROC curves from processed windows
    from sklearn.metrics import roc_curve
    from . import cic_eval as ce
    from .cic_pipeline import load_day, to_X
    from .detectors import default_detectors
    from .traffic_sim import to_features
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 3.1))
    for ax, (name, path) in zip(axes, ce.FILES.items()):
        w = load_day(path); y = w.y.to_numpy(); F = to_features(to_X(w))
        fa = int(y.argmax()) if y.any() else len(y); fit_end = max(10, int(fa * 0.6))
        yy = y[fit_end:]
        for det in default_detectors(seed=0):
            det.fit(F[:fit_end]); s = det.score_batch(F[fit_end:])
            fpr, tpr, _ = roc_curve(yy, s)
            ls = "-" if det.name == "Adaptive (proposed)" else "--"
            lw = 1.8 if det.name == "Adaptive (proposed)" else 1.0
            ax.plot(fpr, tpr, ls, color=DET_COLOR[det.name], label=DET_SHORT[det.name], lw=lw)
        ax.plot([0, 1], [0, 1], ":", color="gray", lw=0.8)
        ax.set_title(f"{name} (real traffic)", fontsize=9)
        ax.set_xlabel("False positive rate")
    axes[0].set_ylabel("True positive rate")
    axes[0].legend(fontsize=6.5, loc="lower right")
    fig.suptitle("CIC-IDS2017 detection (ROC)", fontsize=9)
    fig.savefig(f"{FIG}/fig_roc_cic.pdf"); plt.close(fig)


def fig_overhead():
    ov = pd.read_csv("results/overhead.csv")
    fig, ax = plt.subplots(figsize=(4.6, 3.0))
    for _, r in ov.iterrows():
        nm = r.detector
        col = DET_COLOR.get(nm, "black")
        ax.scatter(r.state_floats, r.us_per_window, s=55, color=col,
                   edgecolor="black", linewidth=0.5, zorder=3)
        ax.annotate(DET_SHORT.get(nm, nm), (r.state_floats, r.us_per_window),
                    textcoords="offset points", xytext=(6, 4), fontsize=7)
    ax.set_xscale("log"); ax.set_xlabel("Model state (floats, log scale)")
    ax.set_ylabel("Compute per window (µs)")
    ax.set_title("Per-window cost vs. memory footprint", fontsize=9)
    fig.savefig(f"{FIG}/fig_overhead.pdf"); plt.close(fig)


if __name__ == "__main__":
    fig_main_f1(); fig_drift(); fig_pertype(); fig_sweeps()
    fig_ablation(); fig_roc_cic(); fig_overhead()
    import os
    print("figures:", sorted(os.listdir(FIG)))
