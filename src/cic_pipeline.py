"""CIC-IDS2017 real-data pipeline: flow CSVs -> per-minute window features.

CIC-IDS2017 timestamps are minute-granular in the Friday attack files, so the
window is 1 minute. Each window aggregates all flows whose (floored) timestamp
falls in it into the SAME six raw features the simulator produces, so one
detector/feature code path (traffic_sim.to_features) serves both.

A window's label is 'attack' when > `attack_frac_thr` of its flows are attack
flows (mixed boundary windows below the threshold are left benign).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

RAW = [" Source IP", " Destination Port", " Protocol", " Timestamp",
       " Total Fwd Packets", " Total Backward Packets",
       "Total Length of Fwd Packets", " Total Length of Bwd Packets",
       " SYN Flag Count", " Label"]


def _parse_ts(s: pd.Series) -> pd.Series:
    # Friday files: M/D/YYYY H:MM (12h afternoon). Monday: DD/MM/YYYY H:MM:SS.
    t = pd.to_datetime(s, errors="coerce", dayfirst=False)
    if t.isna().mean() > 0.3:
        t = pd.to_datetime(s, errors="coerce", dayfirst=True)
    return t


def load_day(path: str, window="1min", attack_frac_thr=0.5):
    df = pd.read_csv(path, encoding="latin-1", low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    df["ts"] = _parse_ts(df["Timestamp"])
    df = df.dropna(subset=["ts"]).copy()
    df["pkts"] = df["Total Fwd Packets"] + df["Total Backward Packets"]
    df["bytes"] = df["Total Length of Fwd Packets"] + df["Total Length of Bwd Packets"]
    df["is_attack"] = (df["Label"].str.upper() != "BENIGN").astype(int)
    df["syn"] = pd.to_numeric(df["SYN Flag Count"], errors="coerce").fillna(0)
    df["is_udp"] = (df["Protocol"] == 17).astype(int)
    df["win"] = df["ts"].dt.floor(window)

    g = df.groupby("win")
    w = pd.DataFrame({
        "pkts": g["pkts"].sum(),
        "bytes": g["bytes"].sum(),
        "dports": g["Destination Port"].nunique(),
        "srcs": g["Source IP"].nunique(),
        "syn_sum": g["syn"].sum(),
        "udp_pkts": g.apply(lambda x: x.loc[x.is_udp == 1, "pkts"].sum(), include_groups=False),
        "n_flows": g.size(),
        "attack_flows": g["is_attack"].sum(),
    }).sort_index()
    w = w[w["pkts"] > 0]
    w["syn_ratio"] = (w["syn_sum"] / w["pkts"]).clip(0, 1)
    w["udp_frac"] = (w["udp_pkts"] / w["pkts"]).clip(0, 1)
    w["attack_frac"] = w["attack_flows"] / w["n_flows"]
    w["y"] = (w["attack_frac"] > attack_frac_thr).astype(int)
    return w


def to_X(w: pd.DataFrame) -> np.ndarray:
    return w[["pkts", "bytes", "dports", "srcs", "syn_ratio", "udp_frac"]].to_numpy(float)


if __name__ == "__main__":
    import sys
    base = "/mnt/user-data/uploads/Downloads/cic_extract/TrafficLabelling "
    files = {
        "PortScan": base + "/Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
        "DDoS": base + "/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
    }
    for name, f in files.items():
        w = load_day(f)
        w.to_csv(f"data/processed/cic_{name}.csv")
        n, na = len(w), int(w.y.sum())
        # leading benign run
        lead = int((w.y.values == 0).argmin()) if w.y.any() else n
        print(f"\n== {name}: {n} windows, {na} attack ({100*na/n:.0f}%), "
              f"leading benign windows = {lead}")
        print("   per-window attack_frac timeline (every ~Nth window):")
        step = max(1, n // 40)
        print("   " + "".join("#" if v > 0.5 else ("." if v == 0 else "o")
                              for v in w.y.values[::1][:n]))
