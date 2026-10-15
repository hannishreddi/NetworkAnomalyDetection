import unittest

import numpy as np

from src.detectors import (Adaptive, MovingAverage, MahalanobisStatic, ZScore,
                           alarms)
from src.metrics import evaluate
from src.traffic_sim import SimConfig, simulate, to_features


def _trace(seed=0, **kw):
    return simulate(SimConfig(seed=seed, **kw))


class TestSimulator(unittest.TestCase):
    def test_deterministic(self):
        a, b = _trace(3), _trace(3)
        np.testing.assert_array_equal(a.X, b.X)
        self.assertNotEqual(float(a.X.sum()), float(_trace(4).X.sum()))

    def test_warmup_is_benign_and_bursts_dont_overlap_events(self):
        tr = _trace(1)
        self.assertEqual(tr.y[:tr.cfg.warmup].sum(), 0)
        bm = np.zeros(len(tr.y), bool)
        for b in tr.bursts:
            bm[b["start"]:b["end"]] = True
        self.assertEqual((bm & (tr.y == 1)).sum(), 0)

    def test_labels_match_events(self):
        tr = _trace(2)
        self.assertEqual(tr.y.sum(), sum(e["end"] - e["start"] for e in tr.events))

    def test_balanced_types(self):
        tr = _trace(5)
        types = [e["type"] for e in tr.events]
        self.assertGreaterEqual(len(set(types)), 4)


class TestDetectors(unittest.TestCase):
    def setUp(self):
        tr = _trace(7)
        self.F = to_features(tr.X)
        self.n = tr.cfg.warmup

    def _causal(self, make):
        d1, d2 = make(), make()
        d1.fit(self.F[:self.n]); d2.fit(self.F[:self.n])
        full = d1.score_batch(self.F[self.n:])
        k = 777
        pref = d2.score_batch(self.F[self.n:self.n + k])
        np.testing.assert_allclose(full[:k], pref, rtol=1e-9, atol=1e-12)

    def test_causality(self):
        for make in (ZScore, MovingAverage, MahalanobisStatic, Adaptive):
            self._causal(make)

    def test_moving_average_batch_equals_streaming(self):
        a, b = MovingAverage(), MovingAverage()
        a.fit(self.F[:self.n]); b.fit(self.F[:self.n])
        batch = a.score_batch(self.F[self.n:self.n + 500])
        stream = np.array([b.score_one(x) for x in self.F[self.n:self.n + 500]])
        np.testing.assert_allclose(batch, stream, rtol=1e-9, atol=1e-12)

    def test_static_mahalanobis_batch_equals_one(self):
        d = MahalanobisStatic(); d.fit(self.F[:self.n])
        batch = d.score_batch(self.F[self.n:self.n + 50])
        one = np.array([d.score_one(x) for x in self.F[self.n:self.n + 50]])
        np.testing.assert_allclose(batch, one, rtol=1e-9)

    def test_adaptive_updates_state(self):
        d = Adaptive(); d.fit(self.F[:self.n])
        m0 = d.m.copy()
        d.score_batch(self.F[self.n:self.n + 100])
        self.assertGreater(np.abs(d.m - m0).max(), 0)


class TestAlarms(unittest.TestCase):
    def test_persistence(self):
        s = np.array([0, 5, 0, 5, 5, 0, 0, 5, 5, 5], float)
        a = alarms(s, 1.0, m=2, n=3)
        self.assertEqual(a.tolist(), [0, 0, 0, 1, 1, 1, 0, 0, 1, 1])
        np.testing.assert_array_equal(alarms(s, 1.0), s > 1)

    def test_cusum_matches_loop(self):
        rng = np.random.default_rng(0)
        s = rng.gamma(2.0, 0.6, 500)
        thr, k, h = 3.0, 0.5, 2.0
        C, ref = 0.0, []
        for v in s:
            C = max(0.0, C + v - k * thr)
            ref.append(C > h * thr)
        expected = np.array(ref) | (s > thr)      # alarms() = threshold OR cusum
        np.testing.assert_array_equal(alarms(s, thr, cusum=(k, h)), expected)


class TestMetrics(unittest.TestCase):
    def test_perfect_and_empty(self):
        tr = _trace(11)
        T = len(tr.y)
        perfect = np.zeros(T, bool); perfect[tr.y == 1] = True
        r = evaluate(perfect, tr, tr.cfg.warmup)
        self.assertEqual(r["fpr"], 0.0); self.assertEqual(r["event_f1"], 1.0)
        self.assertEqual(r["tpr"], 1.0); self.assertEqual(r["delay_median"], 0.0)
        r0 = evaluate(np.zeros(T, bool), tr, tr.cfg.warmup)
        self.assertEqual(r0["event_f1"], 0.0); self.assertEqual(r0["fnr"], 1.0)

    def test_false_alarm_counted(self):
        tr = _trace(12)
        a = np.zeros(len(tr.y), bool)
        a[tr.cfg.warmup + 3] = True      # warm-up + 3 is benign (events start >= +20)
        r = evaluate(a, tr, tr.cfg.warmup)
        self.assertGreater(r["fpr"], 0.0)
        self.assertEqual(r["event_precision"], 0.0)


if __name__ == "__main__":
    unittest.main()


class TestDrift(unittest.TestCase):
    def test_drift_zero_unchanged_and_layout_shared(self):
        a = simulate(SimConfig(seed=5, drift=0.0))
        b = simulate(SimConfig(seed=5))
        np.testing.assert_array_equal(a.X, b.X)
        c = simulate(SimConfig(seed=5, drift=1.0))
        self.assertEqual(a.events, c.events)           # same event layout
        np.testing.assert_array_equal(a.y, c.y)
        self.assertFalse(np.array_equal(a.X, c.X))

    def test_drift_moves_the_level(self):
        tr = simulate(SimConfig(seed=5, drift=2.0, n_events=0, benign_burst_rate=0))
        lp = np.log(tr.X[:, 0])
        self.assertGreater(lp[-600:].mean() - lp[:600].mean(), 0.3)
