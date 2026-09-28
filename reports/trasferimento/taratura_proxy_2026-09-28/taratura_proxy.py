"""Does the benches' proxy predict the sign of the official differences already measured? (R-REV, action 2.)

For the four one-factor pairs above the seed noise (t10 - t08, t11 - t08, t15 - t11, t16 - t15), the two recipes of
each pair are rebuilt exactly (configs/recipes: raw effects, gamma 1, reliability n / (n + 100), the recipe's weights
and amplitude, no cis head; caches: stage-98 r3 for t08 and t10, r4 for t11, t15, t16) and read against a public
source that is not one of their inputs. Primary truth: HEK293T (cache r5), in none of these recipes. Extra readings:
HCT116 for t10 - t08; for the amplitude pairs K562, CD4 and HCT116, each removed from both recipes' inputs. Targets:
the panel targets the truth measures; a target no input covers gets no effect, as in the submissions.

Members, as reports/trasferimento/quattro_sorgenti_2026-09-26/four_sources_bench.py (pinned by
tests/test_proxy_banchi.py): PDS in effect space; PDS_gen and nMAE_gen after the trial-01 profile step and a
400-cell pseudobulk on the A, B and C basal profiles, three seeds; combined 0.36 dPDS_gen - 0.27 dnMAE_gen, paired
bootstrap over targets. The rule (RISULTATI.md, fixed before running) reads the combined sign on HEK293T.

    scripts/py.cmd reports/trasferimento/taratura_proxy_2026-09-28/taratura_proxy.py \
        --out reports/trasferimento/taratura_proxy_2026-09-28/r1
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "reports" / "trasferimento" / "modulo_cis_2026-09-26"))
sys.path.insert(0, str(REPO / "reports" / "trasferimento" / "banco_varianti_2026-09-25"))

from cis_bench import DATA, SEED, boot, pds_proxy  # noqa: E402
from noise_sim import rank_pds  # noqa: E402
from noise_sim2 import realise  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402
from vcc2026.multisource import mix  # noqa: E402

_spec = importlib.util.spec_from_file_location("stage104", REPO / "scripts" / "104_learned_reweighting.py")
stage104 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stage104)

W_PDS, W_NMAE = 0.36, 0.27
CACHE = {"t08": "multisource_2026-09-22_r3", "t10": "multisource_2026-09-22_r3",
         "t11": "multisource_2026-09-23_r4", "t15": "multisource_2026-09-23_r4", "t16": "multisource_2026-09-23_r4"}
TRUTH_CACHE = "multisource_2026-09-23_r5"
# (after, before, official delta, official member signs as contributions to the score: pds, nmae, fidelity, reach)
PAIRS = [("t10", "t08", -0.010179, {"pds": -1, "nmae": -1, "fid": +1, "reach": -1}, ["orion_hek293t", "orion_hct116"]),
         ("t11", "t08", +0.010407, {"pds": +1, "nmae": 0, "fid": -1, "reach": +1}, ["orion_hek293t"]),
         ("t15", "t11", +0.036756, {"pds": +1, "nmae": +1, "fid": +1, "reach": +1},
          ["orion_hek293t", "k562", "cd4_mix", "orion_hct116"]),
         ("t16", "t15", +0.030094, {"pds": +1, "nmae": +1, "fid": +1, "reach": +1},
          ["orion_hek293t", "k562", "cd4_mix", "orion_hct116"])]


def recipe(name: str) -> tuple[dict, float]:
    r = json.loads((REPO / "configs" / "recipes" / f"{name}.json").read_text(encoding="utf-8"))
    assert r["effect"] == "raw" and r["gamma"] == 1.0 and r["reliability_scale"] == 100, name
    ctx = r["contexts"]
    assert ctx["A"] == ctx["B"] == ctx["C"], f"{name}: contexts differ"
    return dict(ctx["A"]["weights"]), float(ctx["A"]["amplitude"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--basal", type=Path, default=DATA / "processed/basal_sources_2026-09-26.csv")
    ap.add_argument("--panel", type=Path, default=DATA / "raw/controls/pert_counts.csv")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    axis = np.asarray(official_axis().symbols)
    G = axis.size
    col = {g: i for i, g in enumerate(axis)}
    panel = pd.read_csv(args.panel).iloc[:, 0].astype(str).tolist()
    panel_cols = np.array([col[g] for g in panel if g in col])
    basal = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)
    cpm_abc = basal[["A", "B", "C"]].mean(axis=1).to_numpy()
    xa = 0.05 * cpm_abc
    w_eval = (xa / (1.0 + xa)).astype(np.float32)
    gate = cpm_abc >= 5.0
    keep = np.ones(G, dtype=bool)
    keep[panel_cols] = False
    raw_cache = {}

    def table(cache: str, name: str):
        key = (cache, name)
        if key not in raw_cache:
            raw_cache[key] = stage104.load(DATA / "processed" / cache, name)[0]     # the raw view
        return raw_cache[key]

    rows, brng = [], np.random.default_rng(SEED)
    for after, before, official, members, truths in PAIRS:
        for truth_name in truths:
            truth = table(TRUTH_CACHE, truth_name)
            tix = truth.index()
            targets = [t for t in panel if t in tix]
            T = len(targets)
            y = truth.raw[np.array([tix[t] for t in targets])].astype(np.float32)
            Zt = y / stage104.source_se(DATA / "processed" / TRUTH_CACHE, truth, targets, G)
            tcols = np.array([col.get(t, -1) for t in targets])
            own = np.zeros((T, G), dtype=bool)
            own[np.arange(T)[tcols >= 0], tcols[tcols >= 0]] = True
            sig = np.isfinite(y) & (np.abs(np.nan_to_num(Zt)) >= 3) & gate[None, :] & ~own
            arms, used = {}, {}
            for rname in (before, after):
                weights, amp = recipe(rname)
                weights = {k: v for k, v in weights.items() if k != truth_name}
                srcs = [n for n in weights if weights[n] > 0]
                m, d = mix([table(CACHE[rname], n) for n in srcs], targets, weights=weights, gamma=1.0,
                           reliability_scale=100.0)
                arms[rname] = (np.where(d > 0, np.nan_to_num(m), 0.0) * amp).astype(np.float32)
                used[rname] = {"sources": srcs, "weights": weights, "amplitude": amp, "cache": CACHE[rname],
                               "targets_with_effect": int((np.abs(arms[rname]).sum(axis=1) > 0).sum())}
            observed = (np.abs(arms[before]) > 0) | (np.abs(arms[after]) > 0)
            per = {}
            for rname, E in arms.items():
                pds_gen, nmae_gen = [], []
                for c in ("A", "B", "C"):
                    cpm = basal[c].to_numpy(dtype=float)
                    x = 0.05 * cpm
                    lv = keep & (cpm > 0)
                    Tl = (np.log1p(x * np.exp(np.clip(np.nan_to_num(y), -20, 20))) - np.log1p(x))[:, lv]
                    for seed in (1, 2, 3):
                        noisy, _, _ = realise(E, cpm, observed | (np.abs(E) > 0), np.random.default_rng([seed, ord(c)]))
                        D = (np.log1p(x * np.exp(np.clip(noisy, -20, 20))) - np.log1p(x))[:, lv]
                        pds_gen.append(rank_pds(D, Tl))
                        err = np.where(sig, np.abs(noisy - np.nan_to_num(y)), 0.0).sum(axis=1)
                        ref = np.where(sig, np.abs(np.nan_to_num(y)), 0.0).sum(axis=1)
                        nmae_gen.append(np.where(ref > 0, err / np.maximum(ref, 1e-12), np.nan))
                per[rname] = {"pds": pds_proxy(E, y, w_eval, panel_cols), "pds_gen": np.mean(pds_gen, axis=0),
                              "nmae_gen": np.nanmean(nmae_gen, axis=0)}
            a, b = per[after], per[before]
            row = {"after": after, "before": before, "truth": truth_name, "targets": T,
                   "official_delta": official, "official_members": members,
                   "inputs_after": used[after], "inputs_before": used[before]}
            for key in ("pds", "pds_gen", "nmae_gen"):
                diff = np.asarray(a[key], dtype=np.float64) - np.asarray(b[key], dtype=np.float64)
                row[f"d_{key}"], row[f"d_{key}_ci95"] = boot(diff[np.isfinite(diff)], brng)
            combo = W_PDS * (a["pds_gen"] - b["pds_gen"]) - W_NMAE * (a["nmae_gen"] - b["nmae_gen"])
            row["d_combined"], row["d_combined_ci95"] = boot(combo[np.isfinite(combo)], brng)
            lo, hi = row["d_combined_ci95"]
            read = lo > 0 or hi < 0
            row["combined_read"] = bool(read)
            row["combined_sign_right"] = bool(read and np.sign(row["d_combined"]) == np.sign(official))
            row["pds_gen_sign_vs_official_pds"] = (int(np.sign(row["d_pds_gen"])), members["pds"])
            row["nmae_gen_sign_vs_official_nmae"] = (int(-np.sign(row["d_nmae_gen"])), members["nmae"])
            rows.append(row)
            print(f"{after}-{before} on {truth_name}: combined {row['d_combined']:+.4f} [{lo:+.4f},{hi:+.4f}] "
                  f"official {official:+.4f}; dPDS_gen {row['d_pds_gen']:+.4f}, dnMAE_gen {row['d_nmae_gen']:+.4f}",
                  flush=True)
    primary = [r for r in rows if r["truth"] == "orion_hek293t"]
    passes = all(r["combined_sign_right"] for r in primary)
    out = {"stage": "trasferimento/taratura_proxy_2026-09-28/taratura_proxy.py",
           "claim_type": "proxy against held-out public sources compared with official score differences",
           "rule": "the combined proxy must read the right sign on all four pairs, truth HEK293T",
           "proxy_reads_all_four_right": passes, "rows": rows}
    with (args.out / "summary.json").open("x", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=float)
    flat = pd.DataFrame([{k: (json.dumps(v) if isinstance(v, (dict, list, tuple)) else v) for k, v in r.items()}
                         for r in rows])
    flat.to_csv(args.out / "summary.csv", index=False)
    print("rule: proxy right on all four pairs (HEK293T):", passes, flush=True)


if __name__ == "__main__":
    main()
