"""Window-level and event-level evaluation for alarm streams."""
from __future__ import annotations

import numpy as np
from scipy import stats


def _runs(a: np.ndarray):
    """[start, end) of each contiguous True run."""
    d = np.diff(np.concatenate([[0], a.astype(int), [0]]))
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))


def evaluate(alarm: np.ndarray, tr, n_train: int) -> dict:
    """Metrics for one alarm stream on one trace (windows < n_train ignored).

    Window level: detection rate (TPR), FPR, FNR. Windows in the `grace`
    period after an event are excluded from FP counting.
    Event level: an event is detected if any alarm falls in
    [start, end + grace); detection time = first such alarm - start.
    An alarm *episode* (contiguous alarms) is a true episode if it overlaps an
    event, else a false alarm; event_f1 combines episode precision and event recall.
    """
    T, y, g = len(alarm), tr.y, tr.cfg.grace
    idx = np.arange(T)
    live = idx >= n_train
    grace = np.zeros(T, bool)
    for e in tr.events:
        grace[e["end"]:min(T, e["end"] + g)] = True
    burst = np.zeros(T, bool)
    for b in tr.bursts:
        burst[b["start"]:b["end"]] = True

    pos = (y == 1) & live
    ben = (y == 0) & live & ~grace
    tpr = float(alarm[pos].mean()) if pos.any() else np.nan
    fpr = float(alarm[ben].mean())
    fpr_burst = float(alarm[ben & burst].mean()) if (ben & burst).any() else np.nan
    fpr_calm = float(alarm[ben & ~burst].mean())

    delays, n_det = [], 0
    for e in tr.events:
        seg = alarm[e["start"]:min(T, e["end"] + g)]
        if seg.any():
            n_det += 1
            delays.append(int(np.argmax(seg)))
    n_ev = len(tr.events)
    ev_recall = n_det / n_ev if n_ev else np.nan

    a_live = alarm & live
    tp_ep = fp_ep = 0
    for s, e_ in _runs(a_live):
        hit = any(s < ev["end"] + g and e_ > ev["start"] for ev in tr.events)
        tp_ep += hit
        fp_ep += (not hit)
    prec = tp_ep / (tp_ep + fp_ep) if (tp_ep + fp_ep) else 0.0
    f1 = 2 * prec * ev_recall / (prec + ev_recall) if (prec + ev_recall) > 0 else 0.0

    return dict(
        tpr=tpr, fpr=fpr, fnr=1 - tpr, fpr_burst=fpr_burst, fpr_calm=fpr_calm,
        event_recall=ev_recall, event_precision=prec, event_f1=f1,
        delay_median=float(np.median(delays)) if delays else np.nan,
        delay_mean=float(np.mean(delays)) if delays else np.nan,
        fa_per_1k=1000.0 * fp_ep / max(1, int(ben.sum())),
        n_alarm_episodes=tp_ep + fp_ep,
    )


def mean_ci(x, conf: float = 0.95):
    """Mean and half-width of the t-based confidence interval (NaNs ignored)."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) < 2:
        return (float(x.mean()) if len(x) else np.nan), np.nan
    h = stats.sem(x) * stats.t.ppf((1 + conf) / 2, len(x) - 1)
    return float(x.mean()), float(h)
