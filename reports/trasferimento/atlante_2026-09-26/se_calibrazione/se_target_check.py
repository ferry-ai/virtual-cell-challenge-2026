"""Observed centred squared effects against the SE of stage 98 on the first 600 targets of a universe (argv: name, folder)."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, r"C:\Users\ferra\OneDrive\Desktop\vcc2026\reports\trasferimento\atlante_2026-09-26")
from atlas_bench import Universe, DATA
from vcc2026.genes import official_axis
axis = np.asarray(official_axis().symbols)
basal = pd.read_csv(DATA / "processed/basal_sources_2026-09-26.csv").set_index("gene_name").reindex(axis)
cpm = basal[["A", "B", "C"]].mean(axis=1).to_numpy(); x = 0.05 * cpm; w = x / (1 + x); gate = cpm >= 5
u = Universe(sys.argv[1], DATA / f"processed/{sys.argv[2]}")
ts = sorted(u.targets)[:600]
tab = u.table(ts)
y = tab.raw.astype(np.float64); se = tab.se.astype(np.float64)
yc = y - np.nanmean(y, axis=0)[None, :]
ok = np.isfinite(yc) & np.isfinite(se) & gate[None, :]
W = (w ** 2)[None, :]
print(sys.argv[1], "targets", len(ts), "genes gated&finite per target (median)", int(np.median(ok.sum(axis=1))))
print(" sum w2 yc2:", float(np.where(ok, W * yc ** 2, 0).sum()), " sum w2 se2:", float(np.where(ok, W * se ** 2, 0).sum()))
print(" unweighted: mean yc2", float(np.nanmean(np.where(ok, yc ** 2, np.nan))), " mean se2", float(np.nanmean(np.where(ok, se ** 2, np.nan))))
r = np.where(ok, yc ** 2, np.nan) / np.where(ok, se ** 2, np.nan)
print(" per-entry yc2/se2 quantiles", np.round(np.nanquantile(r, [0.1, 0.25, 0.5, 0.75, 0.9]), 3))
big = np.where(ok, se, np.nan)
print(" se quantiles", np.round(np.nanquantile(big, [0.5, 0.9, 0.99, 0.999]), 3), " |yc| quantiles", np.round(np.nanquantile(np.where(ok, np.abs(yc), np.nan), [0.5, 0.9, 0.99, 0.999]), 3))
