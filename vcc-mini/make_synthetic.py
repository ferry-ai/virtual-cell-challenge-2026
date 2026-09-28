"""Write a synthetic dataset in the mini/ format, to test the pipeline end to end.

Planted structure: shared programs and target-specific effects, a response gated by the
gene's control expression in each line (a gene that is off cannot go down), per-line noise
shrinking with cells. It checks that the code runs and that the model can learn a gating the
equal-weight transfer ignores. It says nothing about real data.
"""
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(1)
out = Path(__file__).resolve().parent / "synth"
out.mkdir(exist_ok=True)
G, K = 600, 8
genes = np.array([f"G{i:04d}" for i in range(G)])
lines = [("K562_ess", "K562"), ("K562_gw", "K562"), ("RPE1", "RPE1"), ("HepG2", "HepG2"), ("Jurkat", "Jurkat")]
programs = rng.normal(size=(K, G)) / np.sqrt(G) * 6
core = [f"G{i:04d}" for i in rng.choice(G, 300, replace=False)] + [f"X{i}" for i in range(100)]
extra = [g for g in genes if g not in core][:250]
coef = {t: rng.normal(size=K) for t in core + extra}
own = {t: rng.normal(size=G) * 0.08 * (rng.random(G) < 0.1) for t in core + extra}
basal = []
for key, grp in lines:
    b = np.log1p(np.exp(rng.normal(0.5, 1.2, G)))
    if key == "K562_gw":
        b = basal[0] + rng.normal(0, 0.05, G)      # same line as K562_ess
    basal.append(b)
basal = np.array(basal, np.float32)
for li, (key, grp) in enumerate(lines):
    ts = core + (extra if key == "K562_gw" else [])
    gate = 1 / (1 + np.exp(-(basal[li] - 0.8) * 3))
    n = rng.integers(30, 300, len(ts)).astype(np.float32)
    delta = np.stack([(coef[t] @ programs + own[t]) * gate + rng.normal(0, 0.6 / np.sqrt(k), G)
                      for t, k in zip(ts, n)]).astype(np.float32)
    kd = np.array([-1.5 if t.startswith("G") else np.nan for t in ts], np.float32)
    tb = np.array([basal[li][int(t[1:])] if t.startswith("G") else np.nan for t in ts], np.float32)
    np.savez_compressed(out / f"effects_{key}.npz", delta=delta, targets=np.array(ts), n_cells=n, kd=kd,
                        target_basal=tb)
np.save(out / "basal.npy", basal)
pd.DataFrame({"gene": genes}).to_csv(out / "genes.csv", index=False)
pd.DataFrame([dict(line=k, group=g) for k, g in lines]).to_csv(out / "lines.csv", index=False)
allt = sorted(set(core + extra))
pd.DataFrame({"target": allt,
              "fold": [int(hashlib.md5(t.encode()).hexdigest(), 16) % 5 for t in allt]}).to_csv(
    out / "targets.csv", index=False)
print("synthetic dataset written to", out)
