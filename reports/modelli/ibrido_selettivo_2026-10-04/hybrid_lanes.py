"""The rows, lane A and lane B of the D-056 hybrid (PROTOCOLLO.md §6–7), for one held-out line and one D-056 training.

Components, all on the held-out line's C rows (the regime the selector and lane B use):
- T: transfer_all_J of version 4 (bench_effects.py, lane_b.py): the same-target transfer from every cube group but the
  held-out one, regime-J table means, times the t25 amplitude;
- R = s(N) - s(A): the network's exported shift minus the anchor alone through the same estimator and baseline
  (eval_shifts.npz of the arm and of 'ancora_sola'); an untrained network gives R = 0 exactly;
- the hybrid T + w R lives on the genes where T is defined; there an undefined R counts as 0, elsewhere the hybrid is
  undefined like T. With w = 0 it is T bit for bit.

Subcommands:
- rows: one row per (table, target key) of the held-out line's C rows, with the statistics the selector needs,
  a = sum_g om_g R_g^2 / sum om and b = sum_g om_g R_g (y_g - T_g) / sum om on the genes where T and the truth are defined
  (the target's own gene left out, as in the bench), om the bench's gene weights; the base loss sum om (T - y)^2 / sum om;
  and the selector's inputs: log(1 + support), concordance of the source groups, log(RMS(R)/RMS(T)), cos(R, T), the
  target gene's control expression. For every arm (ibrido, ibrido_mean). No weight is chosen here.
- laneA: the bench indices (metrics.score_table) of the arms transfer, rete (w = 1), miscela_fissa (w_fix),
  ibrido_selettivo (w per target), rete_mean, selettivo_mean, the references transfer_cells_J and transfer_prod_J on the
  C rows; the generic reference and the network's own prediction on the J rows (regime J, reported apart); diagnostics
  of R (ratio to T, common share per table) and of the weights.
- laneB: the six members in local scale (vcc2026.bench.Bench) on the real cells and targets, for the arms transfer,
  ibrido_w0 (the parity control: its cells must equal transfer's, else the lane is invalid), rete, miscela_fissa,
  ibrido_selettivo, rete_mean, selettivo_mean, transfer_cells_J, transfer_prod_J; one generator (trial-01, the same seed
  stream for every arm).
Weights come from selector.py (a JSON with w_fix per arm and w per target key per arm), never from this line's truth.
Not VCC scores.

    py hybrid_lanes.py rows  --run <train> --cube <cube_r2> --protocol <PROTOCOLLO.json> --target-keys <json> \
        --held-group H1 --splits <prepass splits.json> --anchors-manifest <manifest> --out <new dir>
    py hybrid_lanes.py laneA <same> --weights <weights.json> --out <new dir>
    py hybrid_lanes.py laneB <same> --weights <weights.json> --real <real_cells.npz> --targets <targets.json> --out <dir>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "risposta_contesto_2026-10-02"))
import anchors as A  # noqa: E402
import splits as SPLITS  # noqa: E402
from arms import AMPLITUDE_T25, Cube, gene_weight, generic_vector, group_mean  # noqa: E402
from common import coords_path, now_utc, sha256, write_json  # noqa: E402
from fitting import transfer_for  # noqa: E402
from metrics import blocks_of, score_table  # noqa: E402

F32 = np.float32
ARMS = ("ibrido", "ibrido_mean")
REFERENCES = (("transfer_all_J", "all"), ("transfer_cells_J", "cells"), ("transfer_prod_J", "production"))
MEAN_ARM = {"ibrido": ("rete", "ibrido_selettivo"), "ibrido_mean": ("rete_mean", "selettivo_mean")}


def hidden_from_splits(path: Path):
    s = json.loads(path.read_text(encoding="utf-8"))
    rule = s["hidden_rule"].split()
    return set(s["hidden_symbols"]), int(rule[rule.index("fold") + 1]), int(rule[rule.index("of") + 1])


def hybrid(T: np.ndarray, R: np.ndarray, w) -> np.ndarray:
    """T + w R on the genes where T is defined (an undefined R counts as 0); NaN where T is. w scalar or [rows]."""
    w = np.asarray(w, dtype=np.float64)
    if w.ndim == 1:
        w = w[:, None]
    out = T.astype(np.float64) + w * np.nan_to_num(R.astype(np.float64), nan=0.0)
    return np.where(np.isfinite(T), out, np.nan)


def selector_stats(T, R, y, om, own):
    """Per row: a, b, base loss and the RMS/cos inputs, on genes where T and y are defined and not the own gene."""
    ok = np.isfinite(T) & np.isfinite(y) & ~own
    Rz = np.where(ok, np.nan_to_num(R, nan=0.0), 0.0).astype(np.float64)
    Tz = np.where(ok, T, 0.0).astype(np.float64)
    yz = np.where(ok, y, 0.0).astype(np.float64)
    W = np.where(ok, om[None, :], 0.0)
    sw = W.sum(1)
    sw = np.where(sw > 0, sw, np.nan)
    a = (W * Rz * Rz).sum(1) / sw
    b = (W * Rz * (yz - Tz)).sum(1) / sw
    base = (W * (Tz - yz) ** 2).sum(1) / sw
    n = ok.sum(1)
    # the selector's inputs never depend on the truth, not even on where it is defined: genes where T is defined
    okT = np.isfinite(T) & ~own
    Ri = np.where(okT, np.nan_to_num(R, nan=0.0), 0.0).astype(np.float64)
    Ti = np.where(okT, T, 0.0).astype(np.float64)
    nT = okT.sum(1)
    rms_r = np.sqrt((Ri ** 2).sum(1) / np.maximum(nT, 1))
    rms_t = np.sqrt((Ti ** 2).sum(1) / np.maximum(nT, 1))
    nr, nt = np.linalg.norm(Ri, axis=1), np.linalg.norm(Ti, axis=1)
    cos_rt = np.where((nr > 0) & (nt > 0), (Ri * Ti).sum(1) / np.maximum(nr * nt, 1e-30), 0.0)
    return dict(a=a, b=b, base=base, genes=n, log_ratio=np.log((rms_r + 1e-6) / (rms_t + 1e-6)), cos_rt=cos_rt,
                rms_r=rms_r, rms_t=rms_t)


def concordance(parts: list[np.ndarray]) -> np.ndarray:
    """Per key: mean pairwise cosine between the source groups' effects (genes finite in both); 0 below two groups."""
    K = parts[0].shape[0]
    out = np.zeros(K)
    for i in range(K):
        vs = [p[i] for p in parts if np.isfinite(p[i]).any()]
        cs = []
        for u in range(len(vs)):
            for v in range(u + 1, len(vs)):
                ok = np.isfinite(vs[u]) & np.isfinite(vs[v])
                if ok.sum() < 2:
                    continue
                x, z = vs[u][ok].astype(np.float64), vs[v][ok].astype(np.float64)
                nx, nz = np.linalg.norm(x), np.linalg.norm(z)
                if nx > 0 and nz > 0:
                    cs.append(float(x @ z / (nx * nz)))
        out[i] = float(np.mean(cs)) if cs else 0.0
    return out


class Setup:
    """What every subcommand shares: the cube, the hidden keys, the regime-J means, the network's shifts."""

    def __init__(self, a):
        import arms as ARMS_MOD
        self.P = json.loads(a.protocol.read_text(encoding="utf-8"))["parameters"]
        self.cube = Cube(a.cube, min_cells=self.P["min_cells"])
        self.held = a.held_group
        if self.held not in self.cube.groups:
            raise SystemExit(f"{self.held} is not a group of the cube: {self.cube.groups}")
        hidden, fold, n_folds = hidden_from_splits(a.splits)
        self.keys_of_symbol = json.loads(a.target_keys.read_text(encoding="utf-8"))
        self.forbidden = A.hidden_keys(self.cube, {"hidden": sorted(hidden)}, self.keys_of_symbol, fold, n_folds,
                                       SPLITS)
        kept_out = json.loads(a.anchors_manifest.read_text(encoding="utf-8"))["commons"]["keys_kept_out"]
        if kept_out != len(self.forbidden):
            raise SystemExit(f"{len(self.forbidden)} keys left out of the means here, {kept_out} in the anchors")
        self.commons, self.raw_means = A.j_table_means(self.cube, self.held, self.forbidden)
        self.cubes = {name: A.source_cube(ARMS_MOD, a.cube, self.P["min_cells"], rule) for name, rule in REFERENCES}
        self.sources = {name: [h for h in cb.groups if h != self.held] for name, cb in self.cubes.items()}
        coords = pd.read_csv(coords_path(self.P["gene_coordinates"]), sep="\t")
        self.ens_to_sym = {str(g).split(".")[0]: s for s, g in zip(coords["symbol"], coords["gene_id"])
                           if isinstance(g, str)}
        self.groups = json.loads((a.run / "eval_groups.json").read_text(encoding="utf-8"))
        with np.load(a.run / "eval_observed.npz", allow_pickle=False) as z:
            self.model_genes = [str(g) for g in z["genes"]]
        self.pred = {}
        for arm in (*ARMS, "ancora_sola"):
            with np.load(a.run / arm / "eval_shifts.npz", allow_pickle=False) as z:
                self.pred[arm] = z["predicted"].astype(F32)
        self.inputs = {"eval_groups": sha256(a.run / "eval_groups.json"), "cube_manifest": sha256(a.cube / "manifest.json"),
                       "target_keys": sha256(a.target_keys), "splits": sha256(a.splits),
                       **{arm: sha256(a.run / arm / "eval_shifts.npz") for arm in (*ARMS, "ancora_sola")}}
        mpos = {g: i for i, g in enumerate(self.model_genes)}
        self.col = np.array([mpos.get(g, -1) for g in self.cube.genes], np.int64)
        self.have_col = self.col >= 0
        table_of = {}
        for t in self.cube.tables_of(self.held):
            for k in self.cube.keys_of(t):
                table_of.setdefault(k, t)
        rows, unmatched = [], {"no_key_in_cube": 0, "not_held": 0}
        for gi, g in enumerate(self.groups):
            if g["class"] not in ("C", "J"):
                unmatched["not_held"] += 1
                continue
            k = self.keys_of_symbol.get(g["symbol"]) or f"SYM:{g['symbol']}"
            t = table_of.get(k)
            if t is None:
                unmatched["no_key_in_cube"] += 1
                continue
            rows.append(dict(gi=gi, cls=g["class"], key=k, symbol=g["symbol"], table=t, cells=g["evaluated_cells"]))
        self.rows = pd.DataFrame(rows).drop_duplicates(["table", "key"])
        self.unmatched = unmatched

    def on_cube(self, arm: str, gis) -> np.ndarray:
        """An arm's exported shifts of these evaluation groups on the cube genes (NaN off the model genes)."""
        x = np.full((len(gis), len(self.cube.genes)), np.nan, F32)
        x[:, self.have_col] = self.pred[arm][np.asarray(gis)][:, self.col[self.have_col]]
        return x

    def correction(self, arm: str, gis) -> np.ndarray:
        return self.on_cube(arm, gis) - self.on_cube("ancora_sola", gis)

    def block_inputs(self, table: str, bk: list, is_c: np.ndarray):
        truth, _ = self.cube.get(table, "raw", bk, purpose="truth")
        se, _ = self.cube.get(table, "se", bk, purpose="truth")
        tpos = self.cube.target_gene_positions(bk, self.ens_to_sym)
        refs, support = {}, {}
        for name, cb in self.cubes.items():
            s, sup = transfer_for(cb, bk, self.sources[name], self.commons)
            s = s * AMPLITUDE_T25
            s[~is_c] = np.nan                      # J targets were hidden from the network: no transfer row
            refs[name], support[name] = s, sup
        return truth, se, tpos, refs, support

    def check_reads(self):
        bad = sorted(t for cb in (self.cube, *self.cubes.values()) for t, purpose in cb.reads
                     if purpose == "fit" and self.cube.group[t] == self.held)
        if bad:
            raise AssertionError(f"a component read the held-out tables {bad} for a fit")


def cmd_rows(a):
    S = Setup(a)
    cb_all = S.cubes["transfer_all_J"]
    out = []
    diag = []
    for t, rt in S.rows[S.rows.cls == "C"].groupby("table"):
        keys = rt["key"].tolist()
        om = gene_weight(S.cube.basal[t]).astype(np.float64)
        for blk in blocks_of(keys, S.P["pds_block"]):
            bk = [keys[i] for i in blk]
            br = rt.iloc[blk]
            is_c = np.ones(len(bk), bool)
            truth, se, tpos, refs, support = S.block_inputs(t, bk, is_c)
            T = refs["transfer_all_J"]
            own = np.zeros(truth.shape, bool)
            r_ok = np.flatnonzero(tpos >= 0)
            own[r_ok, tpos[r_ok]] = True
            parts = [group_mean(cb_all, h, bk, S.commons) for h in S.sources["transfer_all_J"]]
            conc = concordance(parts)
            expr = np.array([float(S.cube.basal[t][p]) if p >= 0 else 0.0 for p in tpos])
            rec = {"table": t, "target_key": bk, "symbol": br["symbol"].tolist(), "eval_cells": br["cells"].tolist(),
                   "support": support["transfer_all_J"].astype(int).tolist(), "f_support": np.log1p(
                       support["transfer_all_J"].astype(float)).tolist(), "f_concordance": conc.tolist(),
                   "f_expression": expr.tolist()}
            for arm in ARMS:
                R = S.correction(arm, br["gi"].to_numpy())
                st = selector_stats(T, R, truth, om, own)
                for k in ("a", "b", "base", "genes", "rms_r", "rms_t"):
                    rec[f"{arm}__{k}"] = st[k].tolist()
                rec[f"{arm}__f_log_ratio"] = st["log_ratio"].tolist()
                rec[f"{arm}__f_cos_rt"] = st["cos_rt"].tolist()
                okT = np.isfinite(T)
                Rz = np.where(okT, np.nan_to_num(R, nan=0.0), 0.0)
                e = (Rz ** 2).sum(1).mean()
                diag.append({"table": t, "arm": arm, "rows": len(bk),
                             "common_share": float((Rz.mean(0) ** 2).sum() / e) if e > 0 else 0.0,
                             "ratio_rms": float(np.sqrt((Rz ** 2).sum() / max((np.where(okT, T, 0) ** 2).sum(),
                                                                                1e-30)))})
            out.append(pd.DataFrame(rec))
    S.check_reads()
    df = pd.concat(out, ignore_index=True)
    a.out.mkdir(parents=True)
    df.to_csv(a.out / f"rows_{S.held}.csv.gz", index=False, compression="gzip")
    write_json(a.out / "rows_summary.json", {
        "written_utc": now_utc(), "held_group": S.held, "run": str(a.run), "rows": int(len(df)),
        "tables": sorted(df["table"].unique().tolist()), "unmatched_groups": S.unmatched,
        "sources": S.sources["transfer_all_J"],
        "commons": {"regime": "J", "keys_kept_out": len(S.forbidden)}, "inputs": S.inputs,
        "diagnostics_of_R": diag,
        "note": "selector statistics and inputs of PROTOCOLLO.md §6 on the C rows; no weight chosen, not a VCC score"})
    print(json.dumps({"held": S.held, "rows": int(len(df))}))


def load_weights(path: Path) -> dict:
    W = json.loads(path.read_text(encoding="utf-8"))
    for arm in ARMS:
        if arm not in W["fixed"] or arm not in W["selective"]:
            raise SystemExit(f"weights: {arm} missing")
    return W


def arm_weights(W: dict, arm: str, keys: list) -> np.ndarray:
    sel = W["selective"][arm]
    missing = [k for k in keys if k not in sel]
    if missing:
        raise SystemExit(f"weights: {len(missing)} target keys without a selective weight for {arm}, e.g. {missing[:3]}")
    return np.array([sel[k] for k in keys], np.float64)


def cmd_lane_a(a):
    S = Setup(a)
    W = load_weights(a.weights)
    generic = generic_vector(S.cube, S.raw_means, {S.held})
    records, wdiag = [], []
    for t, rt in S.rows.groupby("table"):
        keys = rt["key"].tolist()
        w = gene_weight(S.cube.basal[t])
        for blk in blocks_of(keys, S.P["pds_block"]):
            bk = [keys[i] for i in blk]
            br = rt.iloc[blk]
            is_c = (br["cls"] == "C").to_numpy()
            truth, se, tpos, refs, support = S.block_inputs(t, bk, is_c)
            T = refs["transfer_all_J"]
            preds = {"transfer": T, "transfer_cells_J": refs["transfer_cells_J"],
                     "transfer_prod_J": refs["transfer_prod_J"],
                     "generic_pseudobulk": np.broadcast_to(generic, truth.shape).copy()}
            gis = br["gi"].to_numpy()
            for arm in ARMS:
                rete, sel = MEAN_ARM[arm]
                R = S.correction(arm, gis)
                wsel = np.zeros(len(bk))
                if is_c.any():
                    wsel[is_c] = arm_weights(W, arm, [k for k, c in zip(bk, is_c) if c])
                preds[rete] = hybrid(T, R, 1.0)
                preds[sel] = hybrid(T, R, wsel)
                if arm == "ibrido":
                    preds["miscela_fissa"] = hybrid(T, R, float(W["fixed"][arm]))
                    preds["rete_J"] = np.where(is_c[:, None], np.nan, S.on_cube(arm, gis))
                    wdiag += [{"table": t, "target_key": k, "w": float(x)} for k, x, c in zip(bk, wsel, is_c) if c]
            for name, pred in preds.items():
                sc = score_table(pred, truth, se, w, bk, tpos, block_size=len(bk))
                for i, (_, r) in enumerate(br.iterrows()):
                    if not np.isfinite(pred[i]).any():      # an arm without a prediction for this row (C or J)
                        continue
                    records.append(dict(held_group=S.held, table=t, target_key=r["key"], symbol=r["symbol"],
                                        cls=r["cls"], eval_cells=int(r["cells"]), arm=name,
                                        support=int(support["transfer_all_J"][i]),
                                        **{m: float(v[i]) for m, v in sc.items()}))
    S.check_reads()
    df = pd.DataFrame(records)
    a.out.mkdir(parents=True)
    df.to_csv(a.out / f"per_target_{S.held}.csv.gz", index=False, compression="gzip")
    metrics = ["pds", "cos", "cos_spec", "mse_ratio", "sign_sig"]
    wd = pd.DataFrame(wdiag)
    means = {c: df[df.cls == c].groupby("arm")[metrics].mean().round(5).to_dict(orient="index") for c in ("C", "J")}
    write_json(a.out / "summary.json", {
        "written_utc": now_utc(), "held_group": S.held, "run": str(a.run),
        "rows": {c: int((S.rows["cls"] == c).sum()) for c in ("C", "J")}, "unmatched_groups": S.unmatched,
        "weights_file": {"path": str(a.weights), "sha256": sha256(a.weights), "fit_on": W.get("fit_on")},
        "w_fixed": W["fixed"], "w_selective_ibrido": {
            "mean": float(wd["w"].mean()) if len(wd) else None,
            "share_above_0.5": float((wd["w"] > 0.5).mean()) if len(wd) else None,
            "share_below_0.1": float((wd["w"] < 0.1).mean()) if len(wd) else None},
        "commons": {"regime": "J", "keys_kept_out": len(S.forbidden)}, "inputs": S.inputs, "means": means,
        "note": "lane A of the D-056 hybrid: bench indices on the held-out line's cube rows; J rows (generic_pseudobulk, "
                "rete_J) reported apart; not VCC scores"})
    print(json.dumps({"held": S.held, "rows": {c: int((S.rows["cls"] == c).sum()) for c in ("C", "J")}}))


def cmd_lane_b(a):
    import scipy.sparse as sp
    from vcc2026.bench import Bench
    from vcc2026.config import challenge
    from vcc2026.inference import trial01_cells
    S = Setup(a)
    W = load_weights(a.weights)
    z = np.load(a.real, allow_pickle=False)
    x = sp.csr_matrix((z["data"], z["indices"], z["indptr"]), shape=tuple(z["shape"]))
    lab, genes = z["labels"].astype(str), z["genes"].astype(str)
    targets = [t for t in json.loads(a.targets.read_text(encoding="utf-8")) if (lab == t["symbol"]).sum() >= 4]
    labels = [t["symbol"] for t in targets]
    tkeys = [t["target_key"] for t in targets]
    target_rows = {t: np.flatnonzero(lab == t) for t in labels}
    ctrl_rows = np.flatnonzero(lab == "non-targeting")
    a.out.mkdir(parents=True)
    bench = Bench(x, target_rows, ctrl_rows, genes, a.out / "bench", seed=a.seed)
    bench.anchors()
    ctrl_x = x[ctrl_rows]
    basal = np.asarray(ctrl_x.sum(0), dtype=np.float64).ravel()
    libs = np.asarray(ctrl_x.sum(1)).ravel().astype(np.int64)
    ch = challenge()
    cpos = pd.Index(S.cube.genes).get_indexer(genes)
    have = cpos >= 0
    mcol = pd.Index(S.model_genes).get_indexer(genes)
    if (mcol < 0).any():
        raise SystemExit(f"{int((mcol < 0).sum())} real genes are not model genes")
    gi_of = {(g["key"], g["symbol"]): i for i, g in enumerate(S.groups)}
    gis = [gi_of[(t["key"], t["symbol"])] for t in targets]
    if any(S.groups[i]["class"] != "C" for i in gis):
        raise SystemExit("lane B targets must be C groups")

    def on_real(s_cube):
        lfc = np.full((len(tkeys), genes.size), np.nan, F32)
        lfc[:, have] = s_cube[:, cpos[have]]
        return lfc

    T_ref = {}
    for name, cb in S.cubes.items():
        s, _ = transfer_for(cb, tkeys, S.sources[name], S.commons)
        T_ref[name] = on_real(s * AMPLITUDE_T25)
    T = T_ref["transfer_all_J"]
    effects = {"transfer": T}
    wsel = {}
    for arm in ARMS:
        rete, sel = MEAN_ARM[arm]
        R = (S.pred[arm][gis][:, mcol] - S.pred["ancora_sola"][gis][:, mcol]).astype(F32)
        wsel[arm] = arm_weights(W, arm, tkeys)
        if arm == "ibrido":
            effects["ibrido_w0"] = hybrid(T, R, 0.0)            # the parity control, with the real correction
        effects[rete] = hybrid(T, R, 1.0)
        effects[sel] = hybrid(T, R, wsel[arm])
        if arm == "ibrido":
            effects["miscela_fissa"] = hybrid(T, R, float(W["fixed"][arm]))
    effects["transfer_cells_J"], effects["transfer_prod_J"] = T_ref["transfer_cells_J"], T_ref["transfer_prod_J"]
    cells_of = {}
    for name, lfc_raw in effects.items():
        obs = np.isfinite(lfc_raw)
        lfc = np.where(obs, np.nan_to_num(lfc_raw), 0.0).astype(F32)
        stream = np.random.default_rng(a.gen_seed)
        blocks, labs = [], []
        for i, t in enumerate(labels):
            n = bench.n_pred(t)
            cells, _ = trial01_cells(basal, lfc[i], obs[i], libs, n, stream,
                                     max_stored_per_cell=ch.max_stored_per_cell,
                                     max_counts_per_cell=ch.max_counts_per_cell)
            blocks.append(cells)
            labs.append(np.full(n, t))
        mat = sp.vstack(blocks).tocsr()
        if name in ("transfer", "ibrido_w0"):
            cells_of[name] = mat
        bench.score(name, mat, np.concatenate(labs), {"observed_share": float(obs.mean())})
    d = (cells_of["transfer"] != cells_of["ibrido_w0"])
    parity = {"cells_equal": bool(d.nnz == 0), "differing_entries": int(d.nnz),
              "rule": "PROTOCOLLO.md §7: ibrido_w0 = T + 0 R must give the transfer's cells exactly"}
    bench.finish(dict(stage=f"D-056 hybrid lane B {S.held}", targets=labels, target_keys=tkeys, genes=int(genes.size),
                      real=str(a.real), real_sha256=sha256(a.real), seed=a.seed, gen_seed=a.gen_seed,
                      commons={"regime": "J", "keys_kept_out": len(S.forbidden)}, parity=parity,
                      weights={"path": str(a.weights), "sha256": sha256(a.weights), "w_fixed": W["fixed"],
                               "w_selective_mean": {arm: float(v.mean()) for arm, v in wsel.items()}},
                      generator="trial-01, one seed stream per arm", run=str(a.run)))
    S.check_reads()
    write_json(a.out / "parity.json", parity)
    write_json(a.out / "run.json", dict(written_utc=now_utc(), arguments={k: str(v) for k, v in vars(a).items()},
                                        inputs=S.inputs))
    if not parity["cells_equal"]:
        raise SystemExit(f"parity failed: {parity}")
    print(json.dumps({"held": S.held, "targets": len(labels), "parity": parity["cells_equal"]}))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("rows", "laneA", "laneB"):
        q = sub.add_parser(name)
        q.add_argument("--run", type=Path, required=True)
        q.add_argument("--cube", type=Path, required=True)
        q.add_argument("--protocol", type=Path, required=True)
        q.add_argument("--target-keys", type=Path, required=True)
        q.add_argument("--held-group", required=True)
        q.add_argument("--splits", type=Path, required=True)
        q.add_argument("--anchors-manifest", type=Path, required=True)
        q.add_argument("--out", type=Path, required=True)
        if name != "rows":
            q.add_argument("--weights", type=Path, required=True)
        if name == "laneB":
            q.add_argument("--real", type=Path, required=True)
            q.add_argument("--targets", type=Path, required=True)
            q.add_argument("--seed", type=int, default=2026)
            q.add_argument("--gen-seed", type=int, default=20260912)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    {"rows": cmd_rows, "laneA": cmd_lane_a, "laneB": cmd_lane_b}[a.cmd](a)


if __name__ == "__main__":
    main()
