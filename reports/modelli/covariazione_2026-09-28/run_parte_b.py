"""Part B of action 6 (R-REV; protocol in RISULTATI.md of this folder), on the laptop: the pieces that are not in r2.

- calibrate: W3's kappa for the pseudobulk sources, fitted on the two VIPerturb cell halves (the predicted mean
  sqrt(r_A r_B) equals the observed mean cosine between halves, k = 3 as M2; k = 0 reported), and the per-gene SE
  calibration of the Replogle contexts (k562, k562ess, rpe1) from their non-targeting rows, per expression bin, as
  reports/trasferimento/atlante_2026-09-26/se_calibrazione/se_ntc_check.py. Writes calibration.json, which Part A
  reads: run this step first.
- s0: M1, M2, D on the S0 pairs: VIPerturb half A x half B, and the five HIPSCI same-donor pairs.
- s1b: hipsci_kolf_2 x kolf (r2).
- w4: on viperturb x k562, rho_cov with one cell half's matrices against the cross-half matrix.
- w5: for k562 x {cd4_Rest, orion_hct116, kolf}, Q_cov(k562, d) - Q_cov(k562 non-targeting pseudo-effects, d).
- hipsci: the S3 pairs of HIPSCI lines of different donors (reported as the lab-versus-line decomposition; they do
  not decide). --s3 k3 keeps k = 3 and one seed, --s3 skip leaves them out (declared in the manifest).

Everything is read on G* in float16 and streamed (one universe shard key at a time, r2 in row blocks); counts.csv
(the responsive shared targets of every pair) is written before any statistic. Output: a NEW folder.

    scripts/py.cmd reports/modelli/covariazione_2026-09-28/run_parte_b.py --data C:/Users/ferra/vcc2026-data/processed/rete_contesti_r2 \
        --data-root C:/Users/ferra/vcc2026-data --steps calibrate --out <new folder>          (first, for Part A)
    scripts/py.cmd reports/modelli/covariazione_2026-09-28/run_parte_b.py ... --steps s0,s1b,w4,w5,hipsci \
        --calibration <that folder>/calibration.json --out <another new folder>
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import covar as C  # noqa: E402

STEPS = ("calibrate", "s0", "s1b", "w4", "w5", "hipsci")
VIP_HALVES = ("processed/universe_viperturb_2026-09-28_halfa", "processed/universe_viperturb_2026-09-28_halfb")
HIPSCI_DIR = "processed/universe_hipsci_{line}_2026-09-28_p2"
NTC_FILES = {"k562": "external/K562_gwps_raw_bulk_01.h5ad", "k562ess": "external/K562_essential_raw_bulk_01.h5ad",
             "rpe1": "external/rpe1_raw_bulk_01.h5ad"}
COORDS = "external/annotation/gene_coordinates_gencode_v50.tsv"
W5_OTHERS = ("cd4_Rest", "orion_hct116", "kolf")


def parse_list(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


class Source:
    """One context on G*: target names, float16 raw and se, masks (coordinates rule), significant genes per row."""

    def __init__(self, name, targets, raw, se, masks: C.MaskCSR, nsig):
        self.name, self.targets, self.raw, self.se, self.masks, self.nsig = name, targets, raw, se, masks, nsig
        self.pos = {t: i for i, t in enumerate(targets)}

    def keep(self, names) -> "Source":
        idx = np.array([self.pos[t] for t in names if t in self.pos], dtype=np.int64)
        return Source(self.name, self.targets[idx], self.raw[idx], self.se[idx], self.masks.take(idx), self.nsig[idx])

    def rows_of(self, names) -> np.ndarray:
        return np.array([self.pos[t] for t in names], dtype=np.int64)


def universe_source(name, folder, prefix, axis_cols, gnames, coords, subset) -> Source:
    u = C.read_universe(folder, prefix, axis_cols, keys=("raw", "se"), keep_targets=subset)
    masks = C.coord_mask(u["targets"], gnames, coords)
    nsig = C.n_significant(u["raw"], u["se"], masks.dense())
    return Source(name, u["targets"].astype(str), u["raw"], u["se"], masks, nsig)


def r2_nsig(r2: C.R2, ctx: str, gstar, subset, block: int = 1024) -> tuple[np.ndarray, np.ndarray]:
    """Non-panel rows of a context: (target names, significant genes per row), streamed in row blocks."""
    rows = r2.rows(ctx)
    tids = r2.row_target[rows]
    keep = ~r2.tgt_panel[tids]
    if subset is not None:
        keep &= np.isin(r2.target_names[tids], list(subset))
    rows, tids = rows[keep], tids[keep]
    nsig = np.zeros(rows.size, dtype=np.int64)
    for i in range(0, rows.size, block):
        r, t = rows[i:i + block], tids[i:i + block]
        raw, se = r2.read("raw", r, gstar), r2.read("se", r, gstar)
        nsig[i:i + block] = C.n_significant(raw, se, r2.mask_csr(t, gstar).dense())
    return r2.target_names[tids].astype(str), nsig


def r2_rows(r2: C.R2, ctx: str, names, gstar, keys=("raw",)) -> dict:
    """The rows of `names` (in that order) of one r2 context, on G*."""
    rows = r2.rows(ctx)
    pos = {str(r2.target_names[t]): int(r) for r, t in zip(rows, r2.row_target[rows])}
    rr = np.array([pos[n] for n in names], dtype=np.int64)
    order = np.argsort(rr, kind="stable")
    out = {}
    for k in keys:
        a = r2.read(k, rr[order], gstar)
        b = np.empty_like(a)
        b[order] = a
        out[k] = b
    return out


def responsive_shared(na, sa, nb, sb) -> np.ndarray:
    """Target names present in both with >= 30 significant genes in both."""
    a = {t for t, s in zip(na, sa) if s >= C.MIN_SIG_GENES}
    b = {t for t, s in zip(nb, sb) if s >= C.MIN_SIG_GENES}
    return np.array(sorted(a & b), dtype=str)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, required=True, help="the r2 dataset folder")
    ap.add_argument("--data-root", type=Path, default=Path(os.environ["VCC2026_DATA_ROOT"])
                    if os.environ.get("VCC2026_DATA_ROOT") else None)
    ap.add_argument("--out", type=Path, required=True, help="new folder; refused if it exists")
    ap.add_argument("--steps", default=",".join(STEPS))
    ap.add_argument("--calibration", type=Path, default=None, help="an existing calibration.json (without 'calibrate')")
    ap.add_argument("--s3", choices=("full", "k3", "skip"), default="full", help="HIPSCI different-donor pairs")
    ap.add_argument("--max-targets", type=int, default=0, help="smoke: a random subset of target names")
    ap.add_argument("--max-genes", type=int, default=0, help="smoke: a random subset of G*")
    ap.add_argument("--compute-below-w6", action="store_true", help="smoke: compute pairs under 200 targets too")
    ap.add_argument("--hipsci-lines", default="", help="smoke: restrict the HIPSCI lines")
    ap.add_argument("--seeds", default=",".join(map(str, C.SEEDS)))
    ap.add_argument("--k-list", default=",".join(map(str, C.K_LIST)))
    ap.add_argument("--gene-perm", type=int, default=C.N_GENE_PERM)
    ap.add_argument("--target-perm", type=int, default=C.N_TARGET_PERM)
    args = ap.parse_args()
    t0 = time.time()
    if args.data_root is None:
        sys.exit("--data-root (or VCC2026_DATA_ROOT) is required")
    steps = [s for s in parse_list(args.steps) if s in STEPS]
    if "calibrate" not in steps and args.calibration is None:
        sys.exit("--calibration is required when 'calibrate' is not among the steps")
    free = shutil.disk_usage(args.out.parent if args.out.parent.exists() else Path.cwd()).free / 1e9
    if free < 1.5:
        sys.exit(f"only {free:.2f} GB free on disk: stop")
    args.out.mkdir(parents=True, exist_ok=False)
    seeds = tuple(int(s) for s in parse_list(args.seeds))
    k_list = tuple(int(k) for k in parse_list(args.k_list))
    registered = (seeds == C.SEEDS and k_list == C.K_LIST and args.gene_perm == C.N_GENE_PERM
                  and args.target_perm == C.N_TARGET_PERM and not args.max_targets and not args.max_genes
                  and not args.compute_below_w6 and not args.hipsci_lines and args.s3 == "full")
    C.log(f"part B -> {args.out}; steps {steps}; registered configuration: {registered}")
    root = args.data_root
    r2 = C.R2(args.data)
    gstar = C.select_gstar(r2.basal, r2.basal_names, r2.genes_axis)
    n_full = int(gstar.size)
    if args.max_genes:
        gstar = np.sort(C.rng_for("max-genes").choice(gstar, min(args.max_genes, gstar.size), replace=False))
    gnames = r2.gene_names[gstar]
    axis_cols = r2.genes_axis[gstar]
    G = int(gstar.size)
    coords = C.load_coords(root / COORDS)
    ess_of = dict(zip(r2.target_names.astype(str), r2.tgt_essential))
    tindex = {str(t): i for i, t in enumerate(r2.target_names)}
    lines = parse_list(args.hipsci_lines) or [x for x in C.HIPSCI_LINES if x not in C.HIPSCI_WEAK]
    hp = [p for p in C.hipsci_pairs() if p[1] in lines and p[2] in lines]
    if args.s3 == "skip":
        hp = [p for p in hp if p[0] != "S3"]
    subset = None
    if args.max_targets:
        pool = np.unique(r2.target_names[r2.row_target[r2.rows("viperturb")]].astype(str))
        pool = pool[~np.isin(pool, r2.target_names[r2.tgt_panel])]
        subset = set(C.rng_for("max-targets").choice(pool, min(args.max_targets, pool.size), replace=False).tolist())
        for line in lines:  # HIPSCI targeted screen: 444 genes, most outside the viperturb draw
            idx = pd.read_csv(root / HIPSCI_DIR.format(line=line) / "index.csv", dtype={"target": str})
            subset |= set(idx["target"].astype(str).head(args.max_targets // 4))
    need_vip = bool({"calibrate", "s0", "w4"} & set(steps))
    need_hip = ("s0" in steps or "hipsci" in steps or "s1b" in steps)
    lc_vip = r2.ctx_logcpm("viperturb", gstar)
    lc_hip = r2.ctx_logcpm("hipsci_fit", gstar)

    # ---- effects and responsiveness (no statistic yet)
    src, r2n, counts, plan = {}, {}, [], {}
    if need_vip:
        for lab, rel in zip(("vip_halfa", "vip_halfb"), VIP_HALVES):
            src[lab] = universe_source(lab, root / rel, "viperturb", axis_cols, gnames, coords, subset)
            C.log(f"{lab}: {src[lab].targets.size} targets, {int((src[lab].nsig >= C.MIN_SIG_GENES).sum())} responsive")
    for ctx in sorted(({"viperturb", "k562"} if "w4" in steps else set()) | ({"k562", *W5_OTHERS} if "w5" in steps
                                                                             else set()) | ({"kolf"} if "s1b" in steps else set())):
        r2n[ctx] = r2_nsig(r2, ctx, gstar, subset)
        C.log(f"r2 {ctx}: {r2n[ctx][0].size} rows, {int((r2n[ctx][1] >= C.MIN_SIG_GENES).sum())} responsive")
    hip_meta, hip_cache = {}, {}

    def hsrc(name: str) -> Source:
        """A HIPSCI line's responsive rows, read again when needed (at most three lines held at once)."""
        if name not in hip_cache:
            if len(hip_cache) >= 3:
                hip_cache.pop(next(iter(hip_cache)))
            line = name[len("hipsci_"):]
            s = universe_source(name, root / HIPSCI_DIR.format(line=line), name, axis_cols, gnames, coords, subset)
            hip_cache[name] = s.keep(s.targets[s.nsig >= C.MIN_SIG_GENES])
        return hip_cache[name]

    if need_hip:
        for line in sorted({x for p in hp for x in p[1:]} | ({"kolf_2"} if "s1b" in steps else set())):
            s = hsrc(f"hipsci_{line}")
            hip_meta[f"hipsci_{line}"] = (s.targets, s.nsig)
            C.log(f"hipsci_{line}: {s.targets.size} responsive targets")
    if need_vip:
        a, b = src["vip_halfa"], src["vip_halfb"]
        plan["S0:vip"] = ("S0", "vip_halfa", "vip_halfb", responsive_shared(a.targets, a.nsig, b.targets, b.nsig))
    if "w4" in steps:
        both = np.intersect1d(src["vip_halfa"].targets, src["vip_halfb"].targets)
        P = responsive_shared(*r2n["viperturb"], *r2n["k562"])
        plan["W4"] = ("W4", "viperturb(halves)", "k562", np.intersect1d(P, both))
    if "w5" in steps:
        for d in W5_OTHERS:
            plan[f"W5:{d}"] = ("W5", "k562", d, responsive_shared(*r2n["k562"], *r2n[d]))
    if "s1b" in steps:
        plan["S1b"] = ("S1b", "hipsci_kolf_2", "kolf", responsive_shared(*hip_meta["hipsci_kolf_2"], *r2n["kolf"]))
    for stratum, x, y in hp:
        if ("s0" in steps and stratum == "S0") or ("hipsci" in steps and stratum == "S3"):
            plan[f"{stratum}:{x}|{y}"] = (stratum, f"hipsci_{x}", f"hipsci_{y}",
                                          np.intersect1d(hip_meta[f"hipsci_{x}"][0], hip_meta[f"hipsci_{y}"][0]))
    for key, (stratum, a, b, P) in plan.items():
        counts.append({"pair": f"{a}|{b}", "stratum": stratum, "a": a, "b": b, "n_P": int(P.size),
                       "n_P_essential": int(sum(ess_of.get(t, False) for t in P)),
                       "w6_pass": bool(P.size >= C.MIN_SHARED_RESPONSIVE)})
    pd.DataFrame(counts).to_csv(args.out / "counts.csv", index=False)
    C.log("counts.csv written before any statistic:\n"
          + pd.DataFrame(counts)[["pair", "stratum", "n_P", "w6_pass"]].to_string(index=False))
    if need_vip:  # keep only the VIPerturb rows some pair uses
        keepv = np.union1d(plan["S0:vip"][3], plan["W4"][3] if "W4" in plan else np.zeros(0, str))
        src["vip_halfa"], src["vip_halfb"] = src["vip_halfa"].keep(keepv), src["vip_halfb"].keep(keepv)

    def ok_size(P):
        return P.size >= C.MIN_SHARED_RESPONSIVE or (args.compute_below_w6 and P.size >= 8)

    # ---- calibration (W3)
    calib_doc = None
    if "calibrate" in steps:
        _, _, _, P = plan["S0:vip"]
        a, b = src["vip_halfa"], src["vip_halfb"]
        ia, ib = a.rows_of(P), b.rows_of(P)
        mask = a.masks.take(ia).dense()
        fits = {}
        if P.size < 8:
            sys.exit(f"calibration: {P.size} VIPerturb targets respond in both halves; too few to fit kappa")
        pa = C.prepare(a.raw[ia], mask, a.se[ia], C.K_MAIN)
        pb = C.prepare(b.raw[ib], mask, b.se[ib], C.K_MAIN)
        for k in (C.K_MAIN, 0):
            Ua, Ub = C.project(pa.u, pa.V, k), C.project(pb.u, pb.V, k)
            cos = np.einsum("ij,ij->i", C.unit_rows(Ua), C.unit_rows(Ub))
            w = 1.0 - (pa.V[:, :k] ** 2).sum(axis=1) if k else np.ones(G)
            wb = 1.0 - (pb.V[:, :k] ** 2).sum(axis=1) if k else np.ones(G)
            EA = pa.zn2 * np.einsum("ij,ij->i", Ua, Ua)
            EB = pb.zn2 * np.einsum("ij,ij->i", Ub, Ub)
            kap, status = C.fit_kappa(cos, EA, pa.d2 @ w.astype(np.float32), EB, pb.d2 @ wb.astype(np.float32))
            fits[f"k{k}"] = {"kappa": kap, "status": status, "mean_cos": float(cos.mean()), "n_targets": int(P.size)}
            C.log(f"kappa (k = {k}): {kap:.4g} ({status}) on {P.size} targets")
        del pa, pb
        rep = {}
        for ctx, rel in NTC_FILES.items():
            kap, table = C.ntc_kappa(root / rel, r2.gene_names)
            rep[ctx] = {"file": rel, "genes": r2.gene_names.tolist(), "kappa": [float(x) for x in kap], "bins": table}
            C.log(f"{ctx} non-targeting ratios: " + ", ".join(f"{t['bin']}: {t['ratio']:.2f}" for t in table))
        kp = fits[f"k{C.K_MAIN}"]["kappa"]
        calib_doc = {"stage": "covariazione_2026-09-28/run_parte_b.py calibrate", "kappa_pseudobulk": kp,
                     "fits": fits, "w3": {"range": list(C.W3_KAPPA_RANGE),
                                          "pass": bool(C.W3_KAPPA_RANGE[0] <= kp <= C.W3_KAPPA_RANGE[1])},
                     "replogle": rep, "registered_configuration": registered, "genes_used": G}
        (args.out / "calibration.json").write_text(json.dumps(C.jsonable(calib_doc)), encoding="utf-8")
        calib = calib_doc
    else:
        calib = json.loads(args.calibration.read_text(encoding="utf-8"))
    kappa_pb = float(calib["kappa_pseudobulk"])
    files = {k: args.out / f"{k}.csv" for k in ("pairs", "ceilings", "nulls", "per_target")}

    def run_pair(key, a: Source, b: Source, lc_a, lc_b, k_list_=k_list, seeds_=seeds):
        stratum, na, nb, P = plan[key]
        if not ok_size(P):
            C.log(f"{na}|{nb}: {P.size} targets: out (W6)")
            return
        ia, ib = a.rows_of(P), b.rows_of(P)
        mask = a.masks.take(ia).dense()
        kv = np.full(G, kappa_pb)
        sa = C.Side(na, a.raw[ia], a.se[ia], kv, 1.0, lc_a)
        sb = C.Side(nb, b.raw[ib], b.se[ib], kv, 1.0, lc_b)
        rec = C.analyse_pair(sa, sb, mask, np.array([ess_of.get(t, False) for t in P]), a.nsig[ia], b.nsig[ib],
                             pair=f"{na}|{nb}", stratum=stratum, k_list=k_list_,
                             jack_k=tuple(k for k in C.K_JACK if k in k_list_), seeds=seeds_,
                             n_gene_perm=args.gene_perm, n_target_perm=args.target_perm, subtract=False, targets=P)
        for k, path in files.items():
            C.append_csv(path, rec[k])
        C.log(f"{na}|{nb} ({stratum}): {P.size} targets done; peak RSS {C.peak_rss_mb()} MB, private {C.peak_private_mb()} MB")

    if "s0" in steps:
        run_pair("S0:vip", src["vip_halfa"], src["vip_halfb"], lc_vip, lc_vip)
        for key in [k for k in plan if k.startswith("S0:") and k != "S0:vip"]:
            _, x, y, _ = plan[key]
            run_pair(key, hsrc(x), hsrc(y), lc_hip, lc_hip)
    if "s1b" in steps:
        _, _, _, P = plan["S1b"]
        if ok_size(P):
            rows = r2_rows(r2, "kolf", P, gstar, ("raw", "se"))
            nk = dict(zip(*r2n["kolf"]))
            kolf = Source("kolf", P, rows["raw"], rows["se"], C.coord_mask(P, gnames, coords),
                          np.array([nk[t] for t in P]))
            run_pair("S1b", hsrc("hipsci_kolf_2"), kolf, lc_hip, r2.ctx_logcpm("kolf", gstar))
            del kolf, rows
    if "w4" in steps:
        _, _, _, P = plan["W4"]
        if ok_size(P):
            a, b = src["vip_halfa"], src["vip_halfb"]
            masks = C.coord_mask(P, gnames, coords)
            k562 = r2_rows(r2, "k562", P, gstar)["raw"]
            nv, nk = dict(zip(*r2n["viperturb"])), dict(zip(*r2n["k562"]))
            strata = C.pair_strata([nv[t] for t in P], [nk[t] for t in P], [ess_of.get(t, False) for t in P])
            rows = C.analyse_w4(C.SSide("vip_halfa", a.raw[a.rows_of(P)], masks, lc_vip),
                                C.SSide("vip_halfb", b.raw[b.rows_of(P)], masks, lc_vip),
                                C.SSide("k562", k562, masks, r2.ctx_logcpm("k562", gstar)), strata,
                                k_list=(C.K_MAIN, 0), seeds=seeds, n_gene_perm=args.gene_perm)
            C.append_csv(args.out / "w4.csv", rows)
            C.log(f"W4 done on {P.size} targets; peak RSS {C.peak_rss_mb()} MB, private {C.peak_private_mb()} MB")
            del k562
    if need_vip:
        del src["vip_halfa"], src["vip_halfb"]
    if "w5" in steps:
        ntc, ncell = C.ntc_pseudo_effects(root / NTC_FILES["k562"], gnames)
        C.log(f"k562 non-targeting pseudo-effects: {ntc.shape[0]} rows (>= 20 cells)")
        ntc_side = C.SSide("k562_ntc", ntc, C.MaskCSR.from_lists([[]] * ntc.shape[0], G), r2.ctx_logcpm("k562", gstar))
        for d in W5_OTHERS:
            _, _, _, P = plan[f"W5:{d}"]
            if not ok_size(P):
                C.log(f"W5 k562|{d}: {P.size} targets: out (W6)")
                continue
            tid = np.array([tindex[t] for t in P], dtype=np.int64)
            masks = r2.mask_csr(tid, gstar)
            ref = r2_rows(r2, "k562", P, gstar)["raw"]
            oth = r2_rows(r2, d, P, gstar)["raw"]
            nk, nd = dict(zip(*r2n["k562"])), dict(zip(*r2n[d]))
            strata = C.pair_strata([nk[t] for t in P], [nd[t] for t in P], [ess_of.get(t, False) for t in P])
            rows = C.analyse_w5(C.SSide("k562", ref, masks, r2.ctx_logcpm("k562", gstar)),
                                C.SSide(d, oth, masks, r2.ctx_logcpm(d, gstar)), ntc_side, strata,
                                k_list=(C.K_MAIN, 0), seeds=seeds)
            C.append_csv(args.out / "w5.csv", rows)
            C.log(f"W5 k562|{d} done on {P.size} targets; peak RSS {C.peak_rss_mb()} MB, private {C.peak_private_mb()} MB")
            del ref, oth
    if "hipsci" in steps:
        for key in [k for k in plan if k.startswith("S3:")]:
            _, x, y, _ = plan[key]
            if args.s3 == "k3":
                run_pair(key, hsrc(x), hsrc(y), lc_hip, lc_hip, k_list_=(C.K_MAIN,), seeds_=seeds[:1])
            else:
                run_pair(key, hsrc(x), hsrc(y), lc_hip, lc_hip)
    manifest = {"stage": "covariazione_2026-09-28/run_parte_b.py", "argv": sys.argv,
                "started_utc": datetime.fromtimestamp(t0, timezone.utc).isoformat(),
                "finished_utc": datetime.now(timezone.utc).isoformat(), "seconds": round(time.time() - t0, 1),
                "steps": steps, "registered_configuration": registered, "s3": args.s3, "seeds": list(seeds),
                "k_list": list(k_list), "gene_perm": args.gene_perm, "target_perm": args.target_perm,
                "gstar_genes_full": n_full, "genes_used": G, "max_targets": args.max_targets,
                "hipsci_lines": lines, "kappa_pseudobulk": kappa_pb,
                "calibration": (str(args.out / "calibration.json") if calib_doc else
                                {"path": str(args.calibration), "sha256": C.sha256_file(args.calibration)}),
                "inputs": {"r2_manifest_sha256": C.sha256_file(args.data / "manifest.json"),
                           "vip_halves": list(VIP_HALVES), "ntc_files": NTC_FILES, "coords": COORDS},
                "notes": ["S0 VIPerturb: kappa is fitted on this same pair, so its rho_eff is normalised by "
                          "construction (declared)",
                          "HIPSCI lines: expression bins from r2's hipsci_fit basal row; donor = name before '_'"],
                "peak_rss_mb": C.peak_rss_mb(), "peak_private_mb": C.peak_private_mb(), "python": platform.python_version(), "numpy": np.__version__}
    (args.out / "manifest.json").write_text(json.dumps(C.jsonable(manifest), indent=1), encoding="utf-8")
    C.log(f"part B done in {time.time() - t0:.0f} s; peak RSS {C.peak_rss_mb()} MB, private {C.peak_private_mb()} MB")


if __name__ == "__main__":
    main()
