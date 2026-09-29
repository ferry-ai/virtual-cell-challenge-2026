"""Part A of action 6 (R-REV; protocol in RISULTATI.md of this folder): M1, M2 and D on the P9 pairs, the replications
and the strata S1, S1b, S2, S3, S5 present in the r2 dataset; M3a on the five P9 contexts. Runs where r2 is: on
Kaggle CPU from the mounted dataset, or locally for a smoke run on a slice. Numpy and pandas only (covar.py).

Order (RISULTATI.md, "Preparazione"): the tables and G*, the effects of every context on G*, the responsive targets,
then counts.csv -- the responsive shared targets of every pair and the M3a candidates -- written and flushed BEFORE
any statistic of M1, M2 or M3a. Then per pair (appended as it finishes, so a run cut short keeps what it computed):
pairs.csv, ceilings.csv, nulls.csv, per_target.csv; then m3a.csv, m3a_targets.csv, m3a_counts.csv; manifest.json;
verdict_parteA.json, the rule applied with the Part B checks still pending (W2 needs S0, W4, W5; W3 is read from the
calibration).

Three ways to run (the Kaggle kernel uses the second, one process per core):
- single process:   --out DIR                        (everything in DIR)
- in parallel:      --out DIR --counts-only          (DIR/counts.csv, before any statistic), then
                    --out DIR/shard_<i> --shard i/n  (pairs i, i+n, ...; M3a in the last shard), then
                    --merge DIR                      (DIR/pairs.csv ... from the shards, manifest, partial verdict)
The SE calibration (W3's kappa for the pseudobulk sources, the non-targeting ratios per expression bin for the
Replogle contexts) comes from run_parte_b.py (calibration.json), which runs first; --uncalibrated (kappa = 1) is for
smoke runs only and is written into the manifest and the verdict.

    scripts/py.cmd reports/modelli/covariazione_2026-09-28/run_parte_a.py --data C:/Users/ferra/vcc2026-data/processed/rete_contesti_r2 \
        --calibration <parte B folder>/calibration.json --out <new folder>
    smoke: ... --uncalibrated --max-targets 400 --max-genes 600 --pairs k562ess:rpe1,k562:rpe1 \
        --m3a-contexts k562,rpe1,k562ess --compute-below-w6 --seeds 0,1 --gene-perm 5 --target-perm 20 --boot 50
"""
from __future__ import annotations

import argparse
import json
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

OUTPUTS = ("pairs", "ceilings", "nulls", "per_target", "m3a", "m3a_targets", "m3a_counts")


def parse_list(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


def kappa_vector(calib: dict | None, ctx: str, gene_names: np.ndarray) -> np.ndarray:
    """SE calibration on the given genes: Replogle contexts per gene (non-targeting ratios), else kappa_pb."""
    if calib is None:
        return np.ones(gene_names.size)
    rep = calib.get("replogle", {})
    if ctx in rep:
        k = pd.Series(rep[ctx]["kappa"], index=rep[ctx]["genes"])
        return k.reindex(gene_names).fillna(1.0).to_numpy(dtype=np.float64)
    return np.full(gene_names.size, float(calib["kappa_pseudobulk"]))


def registered_config(args, seeds, k_list) -> bool:
    return (seeds == C.SEEDS and k_list == C.K_LIST and args.gene_perm == C.N_GENE_PERM
            and args.target_perm == C.N_TARGET_PERM and args.boot == C.N_BOOT and not args.max_targets
            and not args.max_genes and not args.pairs and not args.compute_below_w6 and not args.uncalibrated
            and args.m3a_contexts == ",".join(C.P9_CONTEXTS) and args.effect == "raw")


def load(args, r2: C.R2, gstar: np.ndarray, contexts: list) -> dict:
    """Every needed context's non-panel rows on G*: effects, SE, masks, significant genes per row."""
    subset = None
    if args.max_targets:
        seen = np.zeros(r2.target_names.size, dtype=np.int64)
        for c in contexts:
            seen[np.unique(r2.row_target[r2.rows(c)])] += 1
        pool = np.flatnonzero((seen >= 2) & ~r2.tgt_panel)
        subset = np.sort(C.rng_for("max-targets").choice(pool, min(args.max_targets, pool.size), replace=False))
    data = {}
    for c in contexts:
        rows = r2.rows(c)
        tids = r2.row_target[rows]
        keep = ~r2.tgt_panel[tids]
        if subset is not None:
            keep &= np.isin(tids, subset)
        rows, tids = rows[keep], tids[keep]
        raw = r2.read("raw", rows, gstar)
        se = r2.read("se", rows, gstar)
        masks = r2.mask_csr(tids, gstar)
        nsig = C.n_significant(raw, se, masks.dense())
        eff = raw if args.effect == "raw" else r2.read("shrunk", rows, gstar)
        del raw
        data[c] = {"rows": rows, "tids": tids, "eff": eff, "se": se, "masks": masks, "nsig": nsig,
                   "pos": {int(t): i for i, t in enumerate(tids)}}
        C.log(f"{c}: {rows.size} non-panel rows, {int((nsig >= C.MIN_SIG_GENES).sum())} responsive")
    return data


def pools_and_counts(r2, data, pairs, m3a_ctx) -> tuple[dict, list]:
    pools, counts = {}, []
    for stratum, a, b in pairs:
        A, B = data[a], data[b]
        shared = np.intersect1d(A["tids"], B["tids"])
        ia = np.array([A["pos"][int(t)] for t in shared], dtype=np.int64)
        ib = np.array([B["pos"][int(t)] for t in shared], dtype=np.int64)
        ra = A["nsig"][ia] >= C.MIN_SIG_GENES if ia.size else np.zeros(0, bool)
        rb = B["nsig"][ib] >= C.MIN_SIG_GENES if ib.size else np.zeros(0, bool)
        both = ra & rb
        pair = f"{a}|{b}"
        pools[pair] = (shared[both], ia[both], ib[both])
        counts.append({"pair": pair, "stratum": stratum, "a": a, "b": b, "shared_nonpanel": int(shared.size),
                       "responsive_a": int(ra.sum()), "responsive_b": int(rb.sum()), "n_P": int(both.sum()),
                       "n_P_essential": int(r2.tgt_essential[shared[both]].sum()),
                       "w6_pass": bool(both.sum() >= C.MIN_SHARED_RESPONSIVE)})
    for h in m3a_ctx:
        H = data[h]
        stored = r2.tgt_gene[H["tids"]] >= 0
        resp = H["nsig"] >= C.MIN_SIG_GENES
        counts.append({"pair": f"m3a:{h}", "stratum": "M3a", "a": h, "b": "", "shared_nonpanel": int(H["tids"].size),
                       "responsive_a": int(resp.sum()), "responsive_b": 0, "n_P": int((resp & stored).sum()),
                       "n_P_essential": int(r2.tgt_essential[H["tids"][resp & stored]].sum()), "w6_pass": True})
    return pools, counts


def run_pairs(args, r2, data, pools, pairs, gstar, calib, seeds, k_list) -> None:
    G = int(gstar.size)
    gnames = r2.gene_names[gstar]
    files = {k: args.out / f"{k}.csv" for k in ("pairs", "ceilings", "nulls", "per_target")}
    for stratum, a, b in pairs:
        pair = f"{a}|{b}"
        P, ia, ib = pools[pair]
        if P.size < C.MIN_SHARED_RESPONSIVE and not args.compute_below_w6:
            C.log(f"{pair}: {P.size} responsive shared targets < {C.MIN_SHARED_RESPONSIVE}: out (W6)")
            continue
        if P.size < 8:
            C.log(f"{pair}: {P.size} targets, too few to split")
            continue
        A, B = data[a], data[b]
        mask = A["masks"].take(ia).dense()
        same_family = r2.ctx_family(a) == r2.ctx_family(b)
        sa = C.Side(a, A["eff"][ia], A["se"][ia], kappa_vector(calib, a, gnames),
                    1.0 if same_family else r2.ctx_se_factor(a), r2.ctx_logcpm(a, gstar))
        sb = C.Side(b, B["eff"][ib], B["se"][ib], kappa_vector(calib, b, gnames),
                    1.0 if same_family else r2.ctx_se_factor(b), r2.ctx_logcpm(b, gstar))
        ess = r2.tgt_essential[P]
        common = dict(pair=pair, stratum=stratum, seeds=seeds, n_gene_perm=args.gene_perm,
                      n_target_perm=args.target_perm, subtract=args.jack_mode == "subtract")
        C.log(f"{pair} ({stratum}): {P.size} targets x {G} genes")
        rec = C.analyse_pair(sa, sb, mask, ess, A["nsig"][ia], B["nsig"][ib], k_list=k_list,
                             jack_k=tuple(k for k in C.K_JACK if k in k_list), targets=r2.target_names[P], **common)
        for key, path in files.items():
            C.append_csv(path, rec[key])
        if stratum == "P9" or stratum == "CUSTOM":
            gs = C.gsig_genes(sa, sb, mask)
            C.log(f"{pair}: G*_sig has {gs.size} genes (W4 fallback)")
            if gs.size >= 50:
                rec = C.analyse_pair(sa.cols(gs), sb.cols(gs), mask[:, gs], ess, A["nsig"][ia], B["nsig"][ib],
                                     gene_set="gsig", k_list=(C.K_MAIN,), jack_k=(C.K_MAIN,), **common)
                for key in ("pairs", "ceilings", "nulls"):
                    C.append_csv(files[key], rec[key])
            ne = np.flatnonzero(~ess)
            if ne.size >= C.MIN_SHARED_RESPONSIVE or (args.compute_below_w6 and ne.size >= 8):
                rec = C.analyse_pair(sa.rows(ne), sb.rows(ne), mask[ne], ess[ne], A["nsig"][ia][ne],
                                     B["nsig"][ib][ne], subset="nonessential", k_list=(C.K_MAIN, 0), jack_k=(),
                                     **common)
                for key in ("pairs", "ceilings", "nulls"):
                    C.append_csv(files[key], rec[key])
        C.log(f"{pair} done; peak RSS {C.peak_rss_mb()} MB, private {C.peak_private_mb()} MB")
        del sa, sb, mask, rec


def run_m3a(args, r2, data, gstar, calib, seeds, m3a_ctx) -> None:
    G = int(gstar.size)
    cand = set()
    for h in m3a_ctx:
        H = data[h]
        resp = (H["nsig"] >= C.MIN_SIG_GENES) & (r2.tgt_gene[H["tids"]] >= 0)
        cand |= set(r2.tgt_gene[H["tids"][resp]].tolist())
    extra = np.array(sorted(cand - set(gstar.tolist())), dtype=np.int64)
    cols_all = np.concatenate([gstar, extra])
    C.log(f"M3a: {extra.size} extra columns for the targets' own genes")
    pos_all = np.full(r2.G, -1, dtype=np.int64)
    pos_all[cols_all] = np.arange(cols_all.size)
    ctxs = {}
    for c in m3a_ctx:
        D = data[c]
        if extra.size:
            ex_eff = r2.read("raw" if args.effect == "raw" else "shrunk", D["rows"], extra)
            ex_se = r2.read("se", D["rows"], extra)
            raw_all, se_all = np.hstack([D["eff"], ex_eff]), np.hstack([D["se"], ex_se])
            del ex_eff, ex_se
        else:
            raw_all, se_all = D["eff"], D["se"]
        ctxs[c] = C.Ctx(c, D["tids"], raw_all, se_all, r2.mask_csr(D["tids"], cols_all), D["nsig"],
                        kappa_vector(calib, c, r2.gene_names[cols_all]), r2.ctx_se_factor(c))
    all_t = np.unique(np.concatenate([data[c]["tids"] for c in m3a_ctx]))
    xpos_of = {int(t): int(pos_all[r2.tgt_gene[t]]) if r2.tgt_gene[t] >= 0 else -1 for t in all_t}
    ess_of = {int(t): bool(r2.tgt_essential[t]) for t in all_t}
    counts = []
    for h in m3a_ctx:
        sources = [c for c in m3a_ctx if c != h]
        bl = C.basal_logcpm(r2.basal, int(r2.ctx[h]["basal_row"]), r2.tgt_axis.clip(0))
        lc = {int(t): (float(bl[t]) if r2.tgt_axis[t] >= 0 else np.nan) for t in all_t}
        C.log(f"M3a h = {h}, sources {sources}")
        rec = C.m3a_context(h, ctxs, sources, G=G, xpos_of=xpos_of, logcpm_h_x=lc, essential_of=ess_of,
                            seeds=seeds, n_boot=args.boot)
        for r in rec["m3a_targets"]:
            r["target"] = str(r2.target_names[r["target_id"]])
        C.append_csv(args.out / "m3a.csv", rec["m3a"])
        C.append_csv(args.out / "m3a_targets.csv", rec["m3a_targets"])
        counts.append(rec["counts"])
        C.log(f"M3a {h}: {rec['counts']}; peak RSS {C.peak_rss_mb()} MB, private {C.peak_private_mb()} MB")
    pd.DataFrame(counts).to_csv(args.out / "m3a_counts.csv", index=False)


def finish(out: Path, calib: dict | None, extra: dict, registered: bool, effect: str, counts_dir: Path) -> None:
    """manifest.json and verdict_parteA.json (the rule with the Part B checks pending)."""
    def read(name, d=out):
        p = d / f"{name}.csv"
        return pd.read_csv(p) if p.exists() else pd.DataFrame()

    kappa_pb = float(calib["kappa_pseudobulk"]) if calib else None
    tabs = {k: read(k) for k in ("pairs", "ceilings", "m3a")}
    tabs["counts"] = read("counts", counts_dir)
    verdict = None
    if len(tabs["pairs"]) and len(tabs["m3a"]):
        verdict = C.decide(tabs["pairs"], tabs["ceilings"], tabs["m3a"], kappa_pb=kappa_pb, w4=None, w5=None,
                           s0_pairs=None, counts=tabs["counts"])
    doc = {"stage": "covariazione_2026-09-28/run_parte_a.py", "partial": True, "registered_configuration": registered,
           "calibrated": calib is not None, "effect": effect,
           "note": "Part B checks pending: combine.py writes the verdict", "verdict": verdict}
    (out / "verdict_parteA.json").write_text(json.dumps(C.jsonable(doc), indent=1, ensure_ascii=False),
                                             encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps(C.jsonable(extra), indent=1), encoding="utf-8")


def merge(root: Path) -> None:
    """Concatenate root/shard_*/<table>.csv into root/<table>.csv (refused if one exists); manifest; verdict."""
    shards = sorted(p for p in root.glob("shard_*") if p.is_dir())
    if not shards or not (root / "counts.csv").exists():
        sys.exit(f"{root}: needs counts.csv and shard_* folders")
    for name in OUTPUTS:
        if (root / f"{name}.csv").exists():
            sys.exit(f"{root / name}.csv exists: nothing is overwritten")
    for name in OUTPUTS:
        parts = [pd.read_csv(s / f"{name}.csv") for s in shards if (s / f"{name}.csv").exists()]
        if parts:
            pd.concat(parts, ignore_index=True).to_csv(root / f"{name}.csv", index=False, float_format="%.6g")
    mans = [json.loads((s / "manifest.json").read_text(encoding="utf-8")) for s in shards
            if (s / "manifest.json").exists()]
    cm = json.loads((root / "counts_manifest.json").read_text(encoding="utf-8"))
    calib = cm.get("calibration_content")
    registered = bool(cm.get("registered_configuration")) and all(m.get("registered_configuration") for m in mans)
    extra = {"stage": "covariazione_2026-09-28/run_parte_a.py --merge", "argv": sys.argv,
             "merged_utc": datetime.now(timezone.utc).isoformat(), "shards": [s.name for s in shards],
             "shard_manifests": mans, "counts_manifest": {k: v for k, v in cm.items() if k != "calibration_content"},
             "registered_configuration": registered}
    finish(root, calib, extra, registered, cm.get("effect", "raw"), root)
    C.log(f"merged {len(shards)} shards into {root}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, help="the r2 dataset folder (processed/rete_contesti_r2)")
    ap.add_argument("--out", type=Path, help="new folder; refused if it exists")
    ap.add_argument("--merge", type=Path, default=None, help="merge the shards of this folder and stop")
    ap.add_argument("--counts-only", action="store_true", help="write counts.csv and stop (parallel runs)")
    ap.add_argument("--shard", default="", help="i/n: pairs i, i+n, ...; M3a runs in shard n-1")
    ap.add_argument("--calibration", type=Path, default=None, help="calibration.json from run_parte_b.py")
    ap.add_argument("--uncalibrated", action="store_true", help="kappa = 1 everywhere (smoke runs only)")
    ap.add_argument("--effect", choices=("raw", "shrunk"), default="raw", help="raw is primary, shrunk the sensitivity")
    ap.add_argument("--pairs", default="", help="override: a:b,c:d (stratum CUSTOM); default: every Part A pair")
    ap.add_argument("--groups", default="P9,REP,S1,S1b,S2,S3,S5", help="strata of the default pair list to run")
    ap.add_argument("--m3a-contexts", default=",".join(C.P9_CONTEXTS), help="'none' skips M3a")
    ap.add_argument("--max-targets", type=int, default=0, help="smoke: a random subset of targets")
    ap.add_argument("--max-genes", type=int, default=0, help="smoke: a random subset of G*")
    ap.add_argument("--compute-below-w6", action="store_true", help="smoke: compute pairs under 200 targets too")
    ap.add_argument("--seeds", default=",".join(map(str, C.SEEDS)))
    ap.add_argument("--k-list", default=",".join(map(str, C.K_LIST)))
    ap.add_argument("--gene-perm", type=int, default=C.N_GENE_PERM)
    ap.add_argument("--target-perm", type=int, default=C.N_TARGET_PERM)
    ap.add_argument("--boot", type=int, default=C.N_BOOT)
    ap.add_argument("--jack-mode", choices=("subtract", "recompute"), default="subtract",
                    help="subtract: keep the Grams (fast, 4 extra G x G matrices); recompute: less memory")
    args = ap.parse_args()
    if args.merge is not None:
        merge(args.merge)
        return
    if args.data is None or args.out is None:
        sys.exit("--data and --out are required")
    t0 = time.time()
    if args.calibration is None and not args.uncalibrated:
        sys.exit("--calibration is required (run run_parte_b.py first), or --uncalibrated for a smoke run")
    args.out.mkdir(parents=True, exist_ok=False)
    calib = json.loads(args.calibration.read_text(encoding="utf-8")) if args.calibration else None
    seeds = tuple(int(s) for s in parse_list(args.seeds))
    k_list = tuple(int(k) for k in parse_list(args.k_list))
    registered = registered_config(args, seeds, k_list)
    C.log(f"part A -> {args.out}; registered configuration: {registered}")

    r2 = C.R2(args.data)
    gstar = C.select_gstar(r2.basal, r2.basal_names, r2.genes_axis)
    n_gstar_full = int(gstar.size)
    C.log(f"G*: {gstar.size} genes (registered {C.GSTAR_EXPECTED})")
    if args.max_genes:
        gstar = np.sort(C.rng_for("max-genes").choice(gstar, min(args.max_genes, gstar.size), replace=False))

    if args.pairs:
        pairs = [("CUSTOM", *p.split(":")) for p in parse_list(args.pairs)]
    else:
        groups = set(parse_list(args.groups))
        pairs = [p for p in C.part_a_pairs() if p[0] in groups]
    m3a_ctx = [] if args.m3a_contexts.strip().lower() == "none" else parse_list(args.m3a_contexts)
    if args.shard:
        i, n = (int(x) for x in args.shard.split("/"))
        pairs = pairs[i::n]
        m3a_ctx = m3a_ctx if i == n - 1 else []
    contexts = sorted({c for _, a, b in pairs for c in (a, b)} | set(m3a_ctx))

    data = load(args, r2, gstar, contexts)
    pools, counts = pools_and_counts(r2, data, pairs, m3a_ctx)
    base = {"stage": "covariazione_2026-09-28/run_parte_a.py", "argv": sys.argv,
            "started_utc": datetime.fromtimestamp(t0, timezone.utc).isoformat(), "registered_configuration": registered,
            "seeds": list(seeds), "k_list": list(k_list), "gene_perm": args.gene_perm, "target_perm": args.target_perm,
            "boot": args.boot, "jack_mode": args.jack_mode, "effect": args.effect, "shard": args.shard,
            "pairs": [list(p) for p in pairs], "m3a_contexts": m3a_ctx, "gstar_genes_full": n_gstar_full,
            "genes_used": int(gstar.size), "max_targets": args.max_targets, "max_genes": args.max_genes,
            "calibration": ({"path": str(args.calibration), "sha256": C.sha256_file(args.calibration),
                             "kappa_pseudobulk": float(calib["kappa_pseudobulk"])} if calib else None),
            "r2": {"path": str(args.data), "manifest_started_utc": r2.manifest.get("started_utc"),
                   "files": r2.small_file_hashes()},
            "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__}
    if not args.shard:
        pd.DataFrame(counts).to_csv(args.out / "counts.csv", index=False)
        C.log("counts.csv written before any statistic:\n"
              + pd.DataFrame(counts)[["pair", "stratum", "n_P", "w6_pass"]].to_string(index=False))
    if args.counts_only:
        (args.out / "counts_manifest.json").write_text(json.dumps(C.jsonable({**base, "calibration_content": (
            {"kappa_pseudobulk": float(calib["kappa_pseudobulk"])} if calib else None)}),
                                                                  indent=1), encoding="utf-8")
        C.log("counts only: stop")
        return

    run_pairs(args, r2, data, pools, pairs, gstar, calib, seeds, k_list)
    if m3a_ctx:
        run_m3a(args, r2, data, gstar, calib, seeds, m3a_ctx)
    manifest = {**base, "finished_utc": datetime.now(timezone.utc).isoformat(),
                "seconds": round(time.time() - t0, 1), "peak_rss_mb": C.peak_rss_mb(), "peak_private_mb": C.peak_private_mb(),
                "disk_free_gb_at_end": round(shutil.disk_usage(args.out).free / 1e9, 2)}
    if args.shard:
        (args.out / "manifest.json").write_text(json.dumps(C.jsonable(manifest), indent=1), encoding="utf-8")
    else:
        finish(args.out, calib, manifest, registered, args.effect, args.out)
    C.log(f"part A done in {time.time() - t0:.0f} s; peak RSS {C.peak_rss_mb()} MB, private {C.peak_private_mb()} MB")


if __name__ == "__main__":
    main()
