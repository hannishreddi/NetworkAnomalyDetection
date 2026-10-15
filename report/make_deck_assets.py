"""Deck-native figures: re-tinted to the 'control chart' design system, with
transparent backgrounds, de-emphasised baselines, and larger type so they read
on a slide. Same data as the paper figures (read from results CSVs).

Usage: python -m report.make_deck_assets   (run from project root)  ->  report/deck_assets/*.png
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd

OUT = os.path.join(os.path.dirname(__file__), "deck_assets")
os.makedirs(OUT, exist_ok=True)

# ---- design tokens ------------------------------------------------------
INK = "#1A2B30"; PORC = "#ECEFEF"; TEAL = "#2E6E63"; AMBER = "#C77400"
STEEL = "#5E7A99"; MUT = "#8A979B"; HAIR = "#C9D1D0"
GREY1 = "#AEB9BC"; GREY2 = "#8C999D"; GREY3 = "#6E7C80"

plt.rcParams.update({
    "font.size": 13, "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
    "text.color": INK, "axes.labelcolor": INK, "axes.edgecolor": HAIR,
    "xtick.color": INK, "ytick.color": INK,
    "axes.grid": True, "grid.color": HAIR, "grid.alpha": 0.7, "grid.linewidth": 0.6,
    "axes.axisbelow": True, "axes.linewidth": 0.8,
    "figure.dpi": 220, "savefig.bbox": "tight", "savefig.transparent": True,
    "axes.spines.top": False, "axes.spines.right": False,
})

ORDER = ["Fixed threshold", "Moving average", "Z-score (static)",
         "Mahalanobis (static)", "Isolation Forest", "Adaptive (proposed)"]
SHORT = {"Fixed threshold": "Fixed thr.", "Moving average": "Moving avg",
         "Z-score (static)": "Z-score", "Mahalanobis (static)": "Mahalanobis",
         "Isolation Forest": "Iso. Forest", "Adaptive (proposed)": "Adaptive"}
COL = {"Fixed threshold": GREY1, "Moving average": GREY2, "Z-score (static)": GREY3,
       "Mahalanobis (static)": TEAL, "Isolation Forest": STEEL, "Adaptive (proposed)": AMBER}
RP = os.path.join(os.path.dirname(__file__), "..", "results")


def _sans(ax):
    for lbl in ax.get_xticklabels() + ax.get_yticklabels():
        lbl.set_fontsize(12)


def hero():
    """Title-slide hero: a drifting control band with points; a few breach it."""
    rng = np.random.default_rng(7)
    n = 180
    t = np.arange(n)
    base = 0.5 + 0.12 * np.sin(t / 34) + 0.0012 * t            # slow benign drift
    band = 0.16 + 0.02 * np.cos(t / 40)
    y = base + rng.normal(0, 0.045, n)
    anom_idx = np.array([52, 53, 96, 97, 98, 141])
    y[anom_idx] = base[anom_idx] + band[anom_idx] + rng.uniform(0.11, 0.26, len(anom_idx))
    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.fill_between(t, base - band, base + band, color=TEAL, alpha=0.14, linewidth=0)
    ax.plot(t, base + band, color=TEAL, lw=1.0, alpha=0.55)
    ax.plot(t, base - band, color=TEAL, lw=1.0, alpha=0.55)
    ax.plot(t, base, color=TEAL, lw=1.4, alpha=0.9)
    normal = np.setdiff1d(t, anom_idx)
    ax.scatter(normal, y[normal], s=14, color="#9FB7B0", alpha=0.9, zorder=3, edgecolors="none")
    ax.scatter(anom_idx, y[anom_idx], s=70, color=AMBER, zorder=5, edgecolors="white", linewidths=1.0)
    for i in anom_idx:
        ax.plot([i, i], [base[i] + band[i], y[i]], color=AMBER, lw=1.0, alpha=0.5, zorder=4)
    ax.set_xlim(0, n - 1); ax.set_ylim(0.1, 1.05)
    ax.axis("off")
    fig.savefig(f"{OUT}/hero.png", pad_inches=0); plt.close(fig)


def mini_band():
    """Small control-band glyph for dividers."""
    rng = np.random.default_rng(3)
    n = 60; t = np.arange(n)
    base = 0.5 + 0.06 * np.sin(t / 12)
    y = base + rng.normal(0, 0.04, n); y[[20, 44]] += 0.28
    fig, ax = plt.subplots(figsize=(4.2, 1.0))
    ax.fill_between(t, base - 0.14, base + 0.14, color="#FFFFFF", alpha=0.10, linewidth=0)
    ax.plot(t, base, color="#8FB0A8", lw=1.2)
    ax.scatter(t, y, s=6, color="#8FB0A8", alpha=0.7, edgecolors="none")
    ax.scatter([20, 44], y[[20, 44]], s=28, color=AMBER, edgecolors="none")
    ax.set_xlim(0, n - 1); ax.set_ylim(0.2, 1.0); ax.axis("off")
    fig.savefig(f"{OUT}/mini_band.png", pad_inches=0); plt.close(fig)


def main_f1():
    s = pd.read_csv(f"{RP}/final_summary.csv")
    g = s[s.setting == "mixed"].set_index("detector").reindex(ORDER)
    fig, ax = plt.subplots(figsize=(7.4, 4.3))
    x = np.arange(len(ORDER))
    bars = ax.bar(x, g.event_f1, yerr=g.event_f1_ci, capsize=3,
                  color=[COL[d] for d in ORDER], edgecolor="white", linewidth=0.8,
                  error_kw=dict(ecolor=INK, alpha=0.6))
    for xi, v, d in zip(x, g.event_f1, ORDER):
        ax.text(xi, v + 0.035, f"{v:.3f}", ha="center", va="bottom",
                fontsize=12, color=(AMBER if d == "Adaptive (proposed)" else INK),
                fontweight=("bold" if d in ("Adaptive (proposed)", "Mahalanobis (static)") else "normal"))
    ax.set_xticks(x); ax.set_xticklabels([SHORT[d] for d in ORDER], rotation=18, ha="right")
    ax.set_ylabel("Event F1"); ax.set_ylim(0, 1.1); ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    _sans(ax)
    fig.savefig(f"{OUT}/f1.png"); plt.close(fig)


def drift():
    s = pd.read_csv(f"{RP}/final_summary.csv")
    d = s[s.setting.str.startswith("drift")].copy()
    d["drift"] = d.setting.str.replace("drift=", "").astype(float)
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    for det in ["Fixed threshold", "Isolation Forest", "Mahalanobis (static)", "Adaptive (proposed)"]:
        gg = d[d.detector == det].sort_values("drift")
        hero = det == "Adaptive (proposed)"
        ax.plot(gg.drift, gg.event_f1, marker="o", ls="-" if hero else "--",
                color=COL[det], label=SHORT[det], lw=3.0 if hero else 1.6,
                ms=8 if hero else 5, zorder=5 if hero else 3)
    ax.set_xlabel("Benign drift strength"); ax.set_ylabel("Event F1")
    ax.set_ylim(0.3, 1.0); ax.legend(fontsize=11, loc="lower left", frameon=False)
    _sans(ax)
    fig.savefig(f"{OUT}/drift.png"); plt.close(fig)


def pertype():
    s = pd.read_csv(f"{RP}/final_summary.csv")
    types = ["burst", "flood", "scan", "proto_shift", "slow_ramp"]
    M = np.array([[s[(s.setting == t) & (s.detector == d)].event_recall.values[0]
                   for t in types] for d in ORDER])
    cmap = LinearSegmentedColormap.from_list("band", ["#F3F6F5", "#AFCac0".replace("C", "C"), TEAL, INK])
    cmap = LinearSegmentedColormap.from_list("band", ["#F3F6F5", "#A9C9BF", TEAL, "#19403A"])
    fig, ax = plt.subplots(figsize=(7.2, 4.1))
    im = ax.imshow(M, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(types)))
    ax.set_xticklabels(["Burst", "Flood", "Scan", "Proto-shift", "Slow ramp"], rotation=18, ha="right")
    ax.set_yticks(range(len(ORDER))); ax.set_yticklabels([SHORT[d] for d in ORDER])
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center",
                    color="white" if M[i, j] > 0.5 else INK, fontsize=11)
    ax.set_xticks(np.arange(-.5, len(types), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(ORDER), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=2); ax.tick_params(which="minor", length=0)
    _sans(ax)
    fig.savefig(f"{OUT}/pertype.png"); plt.close(fig)


def roc():
    from sklearn.metrics import roc_curve
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from src import cic_eval as ce
    from src.cic_pipeline import load_day, to_X
    from src.detectors import default_detectors
    from src.traffic_sim import to_features
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.9))
    for ax, (name, path) in zip(axes, ce.FILES.items()):
        w = load_day(path); y = w.y.to_numpy(); F = to_features(to_X(w))
        fa = int(y.argmax()) if y.any() else len(y); fit_end = max(10, int(fa * 0.6))
        yy = y[fit_end:]
        for det in default_detectors(seed=0):
            det.fit(F[:fit_end]); sc = det.score_batch(F[fit_end:])
            fpr, tpr, _ = roc_curve(yy, sc)
            hero = det.name == "Adaptive (proposed)"
            ax.plot(fpr, tpr, "-" if hero else "--", color=COL[det.name],
                    label=SHORT[det.name], lw=3.0 if hero else 1.3,
                    zorder=5 if hero else 3, alpha=1 if COL[det.name] in (TEAL, AMBER, STEEL) else 0.85)
        ax.plot([0, 1], [0, 1], ":", color=MUT, lw=0.9)
        ax.set_title(name, fontsize=13, color=INK); ax.set_xlabel("False positive rate")
        _sans(ax)
    axes[0].set_ylabel("True positive rate")
    axes[1].legend(fontsize=9, loc="lower right", frameon=False)
    fig.savefig(f"{OUT}/roc.png"); plt.close(fig)


def ablation():
    ab = pd.read_csv(f"{RP}/ablation.csv")
    g = ab.groupby(["scenario", "variant"], sort=False).event_f1.mean().reset_index()
    variants = ["Proposed (full)", "– no gating", "– cov_gate=3 (loosen)",
                "– diagonal cov", "+ persistence 2of3", "+ CUSUM", "static (no adaptation)"]
    labels = ["Full", "no gating", "loosen\ncov-gate", "diagonal\ncov", "+persist.", "+CUSUM", "static"]
    fig, ax = plt.subplots(figsize=(7.0, 4.1))
    x = np.arange(len(variants)); w = 0.4
    for i, (scen, col, lab) in enumerate([("stationary", TEAL, "Stationary"),
                                          ("drift2", AMBER, "Drift ×2")]):
        vals = [g[(g.scenario == scen) & (g.variant == v)].event_f1.values[0] for v in variants]
        ax.bar(x + (i - 0.5) * w, vals, w, label=lab, color=col, edgecolor="white", linewidth=0.7)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=10.5)
    ax.set_ylabel("Event F1"); ax.set_ylim(0, 1.0); ax.legend(fontsize=11, frameon=False)
    _sans(ax)
    fig.savefig(f"{OUT}/ablation.png"); plt.close(fig)


if __name__ == "__main__":
    hero(); mini_band(); main_f1(); drift(); pertype(); roc(); ablation()
    print("deck assets:", sorted(os.listdir(OUT)))
