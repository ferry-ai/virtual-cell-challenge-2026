"""The A/B/C candidate of the D-056 hybrid (PROTOCOLLO.md §13–§14): the correction R of the HepG2-fold network on the
official controls of each competition context, the frozen selector's weights, and the hybrid effects t25 + w R.

Steps, each as fixed by §14 before any of their outputs existed:
1. anchors of the panel targets by the fold's own rule: anchors.sources_for with the held-out group of the network
   (HepG2), rule `all` (nine cube groups), the J means of training (j_table_means with HepG2 skipped and the hidden keys
   kept out; their number must equal the fold's anchor manifest), t25 amplitude; on the cube genes (the "T" of the
   selector inputs) and on the model genes (the network's anchor, float16 as anchors.npz, 0 where no source measures);
   anchor info = (support / max_sources of the fold's manifest, 1);
2. the targets the network corrects: regime C of the network (a 'train' row in the fold's anchor index, a symbol not
   hidden by the split and a key not kept out of the means, an anchor); every other target keeps w = 0;
3. per context, 1,024 draws of 64 controls of the official file without replacement (one library, seed 20261004,
   cell_data.draw_controls_lib), the same draws for every target; z and beta once; for each corrected target
   s(N) = shift(mean softmax(beta + anchor + delta), mean softmax(beta)) and s(A) = shift(mean softmax(beta + anchor),
   mean softmax(beta)) with the version-4 estimator (cell_data.shift) on the genes the file measures, CRISPRi, pi = 1,
   both rounded to float16 as eval_shifts.npz; R = s(N) - s(A);
4. the selector inputs as hybrid_lanes.py rows (support and concordance of the nine groups, log RMS ratio and cosine of
   R against the anchor with the target's own gene left out, expression = the cube's basal competition_<ctx> at the
   target gene, 0 where absent); w = selector.apply of the frozen file, arm 'ibrido';
5. effects: lfc_t25 + w R on the (target, gene) pairs observed in t25, elsewhere unchanged; parity: the same function
   with w = 0 must return the t25 arrays exactly.

Writes, under --out: effects_<ctx>.npz (stage 100's format: targets, genes, lfc, observed), correction_<ctx>.npz (R and
s(A) on the official axis, float16), targets_<ctx>.csv (eligibility, inputs, w), manifest.json (inputs, hashes, parity,
diagnostics). Not a VCC score; nothing is generated or uploaded here.

    py export_abc.py --model <train/ibrido/model.pt> --anchor-index <anchors_HepG2_all> --splits <splits.json> \
        --cube <cube_r2> --protocol <bench PROTOCOLLO.json> --target-keys <target_keys.json> \
        --controls <raw/controls> --effects <effects_t25 dir> --selector <selector_final.json> --out <new dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RC = HERE.parent / "risposta_contesto_2026-10-02"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(RC))
import anchors as A  # noqa: E402
import cell_data as CD  # noqa: E402
import cellnet as CN  # noqa: E402
import selector as SEL  # noqa: E402
from hybrid_lanes import concordance, hidden_from_splits, selector_stats  # noqa: E402

CONTEXTS = ("A", "B", "C")
DRAWS, CTRL_K, SEED = 1024, 64, 20261004
MODALITY = "CRISPRi"
ARM = "ibrido"
F32 = np.float32


def sha(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(8 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_model(path: Path):
    """The network of a version-5 model.pt, rebuilt with its own arguments and loaded strictly."""
    import torch
    ck = torch.load(path, map_location="cpu", weights_only=False)
    state = ck["state"]
    desc = np.zeros(tuple(state["desc"].shape), F32) if "desc" in state else None
    model = CN.build_model(len(ck["genes"]), len(ck["symbols"]), len(ck["modalities"]), len(ck["studies"]),
                           np.asarray(ck["input_genes"], np.int64), dim=ck["dim"], rank=ck["rank"], target_desc=desc,
                           target_code=ck["target_code"], pi_floor=ck["pi_floor"], context_mode=ck["context_mode"],
                           delta_bound=ck["delta_bound"], anchor_rank=ck["anchor_rank"],
                           anchor_U=state["anchor_U"].numpy() if "anchor_U" in state else None,
                           gain_mode=ck["gain_mode"], common_head=ck["common_head"])
    model.load_state_dict(state, strict=True)
    model.eval()
    if ck.get("gate_mode") != "off":
        raise SystemExit(f"gate mode {ck.get('gate_mode')}: the export assumes pi = 1 (gate off)")
    return model, ck


def read_controls(path: Path, model_genes: list, input_genes: np.ndarray) -> dict:
    """What the context encoder reads of the official control file, as the prepass reservoir holds it: the counts of
    each cell on the input genes (float16, capped at 65,504), its library (counts on the model genes the file measures)
    and the measured mask on the model's axis."""
    import h5py
    import scipy.sparse as sp
    with h5py.File(path, "r") as f:
        X = f["X"]
        shape = tuple(int(v) for v in X.attrs["shape"])
        x = sp.csr_matrix((X["data"][:], X["indices"][:], X["indptr"][:]), shape=shape)
        var = [str(v) for v in CN.h5_column(f["var"], f["var"].attrs.get("_index", "_index"))]
    pos = {g: i for i, g in enumerate(model_genes)}
    col = np.array([pos.get(g, -1) for g in var], np.int64)
    measured = np.zeros(len(model_genes), bool)
    measured[col[col >= 0]] = True
    lib = np.asarray(x @ (col >= 0).astype(np.float64)).ravel().astype(F32)
    vpos = {g: j for j, g in enumerate(var)}
    in_var = np.array([vpos.get(model_genes[g], -1) for g in input_genes], np.int64)
    x_in = np.zeros((shape[0], input_genes.size), np.float32)
    have = in_var >= 0
    x_in[:, have] = x[:, in_var[have]].toarray()
    return {"x_in": np.minimum(x_in, 65504).astype(np.float16), "measured": measured, "lib": lib,
            "cells": int(shape[0]), "var_genes": len(var), "var_off_model": int((col < 0).sum()),
            "input_genes_absent": int((~have).sum())}


def panel_anchors(a, model_genes: list, targets: list) -> dict:
    """Anchors, support, inputs and eligibility of the panel targets (§14, points 1, 2 and 4)."""
    arms, fitting, splits_mod = A.bench(RC)
    P = json.loads(a.protocol.read_text(encoding="utf-8"))["parameters"]
    man = json.loads((a.anchor_index / "manifest.json").read_text(encoding="utf-8"))
    index = json.loads((a.anchor_index / "anchors.json").read_text(encoding="utf-8"))
    held = man["held_group"]
    cube_all = arms.Cube(a.cube, min_cells=P["min_cells"])
    cube_src = A.source_cube(arms, a.cube, P["min_cells"], man["sources"]["rule"])
    hidden, fold, n_folds = hidden_from_splits(a.splits)
    keys_of_symbol = json.loads(a.target_keys.read_text(encoding="utf-8"))
    forbidden = A.hidden_keys(cube_all, {"hidden": sorted(hidden)}, keys_of_symbol, fold, n_folds, splits_mod)
    if len(forbidden) != man["commons"]["keys_kept_out"]:
        raise SystemExit(f"{len(forbidden)} keys kept out here, {man['commons']['keys_kept_out']} in the fold's anchors")
    commons, _ = A.j_table_means(cube_all, held, forbidden)
    sources = A.sources_for("COMPETITION", held, cube_src.groups)
    if sources != list(man["sources"]["groups"]) or held in sources:
        raise SystemExit(f"sources {sources}, the fold's anchors {man['sources']['groups']}")
    keys = [keys_of_symbol.get(s) or f"SYM:{s}" for s in targets]
    s_cube, support = fitting.transfer_for(cube_src, keys, sources, commons)
    T_cube = (s_cube * arms.AMPLITUDE_T25).astype(F32)
    parts = [arms.group_mean(cube_src, h, keys, commons) for h in sources]
    conc = concordance(parts)
    mpos = {g: i for i, g in enumerate(model_genes)}
    cube_col = np.array([mpos.get(g, -1) for g in cube_src.genes], np.int64)
    have = cube_col >= 0
    G = len(model_genes)
    rows16 = np.full((len(targets), G), np.nan, np.float16)
    for i in range(len(targets)):
        v = np.full(G, np.nan, F32)
        v[cube_col[have]] = s_cube[i, have] * arms.AMPLITUDE_T25
        rows16[i] = v.astype(np.float16)
    anchor = np.nan_to_num(rows16, nan=0.0).astype(np.float16)
    info = np.zeros((len(targets), 2), F32)
    info[:, 0] = support / float(man["max_sources"])
    info[:, 1] = 1.0
    trained = {r["symbol"] for r in index if r["role"] == "train"}
    reasons = []
    for s, k, sup in zip(targets, keys, support):
        why = []
        if s not in trained:
            why.append("no CRISPRi training row")
        if s in hidden or k in forbidden:
            why.append("hidden")
        if sup <= 0:
            why.append("no anchor")
        reasons.append("; ".join(why))
    from common import coords_path
    cf = pd.read_csv(coords_path(P["gene_coordinates"]), sep="\t")
    ens_to_sym = {str(g).split(".")[0]: s for s, g in zip(cf["symbol"], cf["gene_id"]) if isinstance(g, str)}
    tpos = cube_all.target_gene_positions(keys, ens_to_sym)
    reads_of_held = sorted(t for t, purpose in cube_all.reads | cube_src.reads
                           if purpose == "fit" and cube_all.group[t] == held)
    if reads_of_held:
        raise AssertionError(f"an anchor read the held-out tables {reads_of_held}")
    return {"keys": keys, "support": support.astype(int), "concordance": conc, "T_cube": T_cube, "anchor": anchor,
            "info": info, "reasons": reasons, "eligible": np.array([r == "" for r in reasons]), "tpos": tpos,
            "cube": cube_all, "cube_col": cube_col, "have": have, "sources": sources, "held": held,
            "kept_out": len(forbidden), "max_sources": man["max_sources"], "trained_symbols": len(trained)}


def corrections(model, ck, ctrl: dict, anc: dict, targets: list, log=print) -> tuple[np.ndarray, np.ndarray, dict]:
    """s(N) - s(A) and s(A) [targets, G] float32 (NaN where undefined or not corrected), §14 point 3."""
    import torch
    torch.manual_seed(0)
    G = len(ck["genes"])
    symbols = [str(s) for s in ck["symbols"]]
    sidx = {s: i for i, s in enumerate(symbols)}
    gpos = {str(g): i for i, g in enumerate(ck["genes"])}
    tg_of = np.array([gpos.get(s, -1) for s in symbols] + [-1], np.int64)
    mods = [str(m) for m in ck["modalities"]]
    mod = mods.index(MODALITY)
    inp = np.asarray(ck["input_genes"], np.int64)
    x_in_all = ctrl["x_in"]
    lib_all = ctrl["lib"]
    m_in = torch.as_tensor(ctrl["measured"][inp]).bool()
    rng = np.random.default_rng(SEED)
    pools = {0: {0: np.arange(ctrl["cells"])}}
    draws = np.stack([CD.draw_controls_lib(pools, 0, 0, CTRL_K, rng, 8)[0] for _ in range(DRAWS)])
    mask = torch.as_tensor(ctrl["measured"]).bool()
    zs, betas = [], []
    with torch.no_grad():
        for b0 in range(0, DRAWS, 128):
            d = draws[b0:b0 + 128]
            xb = torch.as_tensor(x_in_all[d]).float()
            mb = m_in[None, None, :].expand(xb.shape[0], CTRL_K, -1)
            lb = torch.as_tensor(lib_all[d]).float()
            z, beta = model.context(xb, mb, lb)
            zs.append(z)
            betas.append(beta)
        z_all, beta_all = torch.cat(zs), torch.cat(betas)
        p0 = torch.softmax(beta_all.masked_fill(~mask, float("-inf")), -1)
        pb = p0.double().mean(0).numpy()
    R = np.full((len(targets), G), np.nan, F32)
    SA = np.full((len(targets), G), np.nan, F32)
    done = 0
    t0 = time.time()
    with torch.no_grad():
        for i, s in enumerate(targets):
            if not anc["eligible"][i]:
                continue
            tgt = sidx[s]
            a_row = torch.as_tensor(anc["anchor"][i].astype(F32))
            a_info = torch.as_tensor(anc["info"][i])
            pm = np.zeros(G)
            pa = np.zeros(G)
            for b0 in range(0, DRAWS, 256):
                z, beta = z_all[b0:b0 + 256], beta_all[b0:b0 + 256]
                n = z.shape[0]
                t_t = torch.full((n,), tgt, dtype=torch.long)
                tg_t = torch.full((n,), int(tg_of[tgt]), dtype=torch.long)
                m_t = torch.full((n,), mod, dtype=torch.long)
                a_b = a_row[None, :].expand(n, -1)
                i_b = a_info[None, :].expand(n, -1)
                delta, _ = model(z, beta, t_t, tg_t, m_t, a_b, i_b)
                p1 = torch.softmax((beta + delta).masked_fill(~mask, float("-inf")), -1)
                pA = torch.softmax((beta + a_b).masked_fill(~mask, float("-inf")), -1)
                pm += p1.double().sum(0).numpy()
                pa += pA.double().sum(0).numpy()
            sN, okN = CD.shift(pm / DRAWS, pb, ctrl["measured"])
            sA, okA = CD.shift(pa / DRAWS, pb, ctrl["measured"])
            n16 = np.where(okN, sN, np.nan).astype(np.float16).astype(F32)
            a16 = np.where(okA, sA, np.nan).astype(np.float16).astype(F32)
            R[i] = n16 - a16
            SA[i] = a16
            done += 1
            if done % 50 == 0:
                log(f"  {done} targets, {time.time() - t0:.0f} s")
    return R, SA, {"draws": DRAWS, "ctrl_k": CTRL_K, "seed": SEED, "modality": MODALITY, "corrected": done,
                   "seconds": round(time.time() - t0, 1)}


def hybrid_effects(lfc: np.ndarray, observed: np.ndarray, R_off: np.ndarray, w: np.ndarray) -> np.ndarray:
    """lfc + w R on observed pairs (an undefined R counts as 0), elsewhere lfc; rows with w = 0 are returned as they are."""
    out = lfc.copy()
    for i in np.flatnonzero(w > 0):
        add = lfc[i].astype(np.float64) + float(w[i]) * np.nan_to_num(R_off[i].astype(np.float64), nan=0.0)
        out[i] = np.where(observed[i], add, lfc[i]).astype(lfc.dtype)
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ("model", "anchor-index", "splits", "cube", "protocol", "target-keys", "controls", "effects", "selector",
                 "out"):
        p.add_argument(f"--{name}", type=Path, required=True)
    p.add_argument("--contexts", nargs="+", default=list(CONTEXTS))
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    t_start = time.time()
    log = lambda m: print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}", flush=True)  # noqa: E731
    model, ck = load_model(a.model)
    model_genes = [str(g) for g in ck["genes"]]
    frozen = json.loads(a.selector.read_text(encoding="utf-8"))
    sel_model = frozen["models"][ARM]
    ref = {c: np.load(a.effects / f"effects_{c}.npz", allow_pickle=False) for c in a.contexts}
    targets = [str(t) for t in ref[a.contexts[0]]["targets"]]
    for c in a.contexts:
        if [str(t) for t in ref[c]["targets"]] != targets:
            raise SystemExit(f"context {c}: the t25 targets differ")
    log(f"model: {len(model_genes)} genes, {len(ck['symbols'])} symbols; {len(targets)} panel targets")
    anc = panel_anchors(a, model_genes, targets)
    log(f"anchors: {int((anc['support'] > 0).sum())} with support, {int(anc['eligible'].sum())} targets corrected; "
        f"sources {anc['sources']}")
    a.out.mkdir(parents=True)
    cube = anc["cube"]
    mcol = np.array([{g: i for i, g in enumerate(model_genes)}.get(g, -1) for g in cube.genes], np.int64)
    hc = mcol >= 0
    own = np.zeros(anc["T_cube"].shape, bool)
    ok_t = np.flatnonzero(anc["tpos"] >= 0)
    own[ok_t, anc["tpos"][ok_t]] = True
    manifest = {"stage": "D-056 export for A/B/C (PROTOCOLLO.md §13-§14)", "started_utc": datetime.now(timezone.utc)
                .isoformat(timespec="seconds"), "argv": sys.argv, "contexts": {},
                "anchors": {k: anc[k] for k in ("sources", "held", "kept_out", "max_sources", "trained_symbols")},
                "targets": len(targets), "corrected_targets": int(anc["eligible"].sum()),
                "not_corrected": {r: int(sum(1 for x in anc["reasons"] if x == r)) for r in sorted(set(anc["reasons"]))
                                  if r},
                "inputs": {"model": sha(a.model), "anchor_manifest": sha(a.anchor_index / "manifest.json"),
                           "anchor_index": sha(a.anchor_index / "anchors.json"), "splits": sha(a.splits),
                           "cube_manifest": sha(a.cube / "manifest.json"), "protocol": sha(a.protocol),
                           "target_keys": sha(a.target_keys), "selector": sha(a.selector),
                           **{f"effects_{c}": sha(a.effects / f"effects_{c}.npz") for c in a.contexts},
                           **{f"controls_{c}": sha(a.controls / f"context_{c}.h5ad") for c in a.contexts}},
                "model": {k: ck.get(k) for k in ("exported", "prepass_sha256", "anchors_sha256", "gain_mode",
                                                  "common_head", "delta_l2", "code_version")}}
    for c in a.contexts:
        log(f"context {c}: reading the controls")
        ctrl = read_controls(a.controls / f"context_{c}.h5ad", model_genes, np.asarray(ck["input_genes"], np.int64))
        R, SA, how = corrections(model, ck, ctrl, anc, targets, log=log)
        R_cube = np.full(anc["T_cube"].shape, np.nan, F32)
        R_cube[:, hc] = R[:, mcol[hc]]
        st = selector_stats(anc["T_cube"], R_cube, np.zeros_like(anc["T_cube"]), np.ones(len(cube.genes)), own)
        basal = cube.basal[f"competition_{c}"]
        expr = np.array([float(basal[q]) if q >= 0 else 0.0 for q in anc["tpos"]])
        df = pd.DataFrame({"symbol": targets, "target_key": anc["keys"], "eligible": anc["eligible"],
                           "not_corrected_because": anc["reasons"], "support": anc["support"],
                           "f_support": np.log1p(anc["support"].astype(float)), "f_concordance": anc["concordance"],
                           f"{ARM}__f_log_ratio": st["log_ratio"], f"{ARM}__f_cos_rt": st["cos_rt"],
                           "f_expression": expr, "rms_r": st["rms_r"], "rms_t": st["rms_t"]})
        w = np.where(anc["eligible"], SEL.apply(sel_model, df), 0.0)
        df["w"] = w
        eff = ref[c]
        lfc, observed, genes = eff["lfc"], eff["observed"], [str(g) for g in eff["genes"]]
        gcol = np.array([{g: i for i, g in enumerate(model_genes)}.get(g, -1) for g in genes], np.int64)
        R_off = np.full(lfc.shape, np.nan, F32)
        R_off[:, gcol >= 0] = R[:, gcol[gcol >= 0]]
        parity = hybrid_effects(lfc, observed, R_off, np.zeros(len(targets)))
        parity_ok = bool(np.array_equal(parity, lfc))
        if not parity_ok:
            raise SystemExit(f"context {c}: parity failed, w = 0 does not return the t25 effects")
        new = hybrid_effects(lfc, observed, R_off, w)
        np.savez_compressed(a.out / f"effects_{c}.npz", targets=eff["targets"], genes=eff["genes"],
                            lfc=new.astype(F32), observed=observed)
        sa_off = np.full(lfc.shape, np.nan, F32)
        sa_off[:, gcol >= 0] = SA[:, gcol[gcol >= 0]]
        np.savez_compressed(a.out / f"correction_{c}.npz", R=R_off.astype(np.float16), s_anchor=sa_off.astype(np.float16),
                            targets=eff["targets"], genes=eff["genes"])
        df.to_csv(a.out / f"targets_{c}.csv", index=False)
        e = df[df.eligible]
        moved = new != lfc
        rms = lambda v: float(np.sqrt(np.nanmean(np.square(v))))  # noqa: E731
        manifest["contexts"][c] = {
            "controls": {k: ctrl[k] for k in ("cells", "var_genes", "var_off_model", "input_genes_absent")},
            "measured_genes": int(ctrl["measured"].sum()), "draws": how, "parity_w0_equal_t25": parity_ok,
            "w": {"mean_corrected": float(e["w"].mean()) if len(e) else None,
                  "mean_all_targets": float(df["w"].mean()), "share_above_0.5": float((e["w"] > 0.5).mean()) if len(e)
                  else None, "share_below_0.1": float((e["w"] < 0.1).mean()) if len(e) else None,
                  "quantiles": [float(q) for q in np.quantile(e["w"], [0, 0.1, 0.5, 0.9, 1])] if len(e) else None},
            "inputs_mean_corrected": {k: float(e[k].mean()) for k in ("f_support", "f_concordance", f"{ARM}__f_log_ratio",
                                                                       f"{ARM}__f_cos_rt", "f_expression")} if len(e)
            else None,
            "rms": {"R_on_observed": rms(np.where(observed & anc["eligible"][:, None], R_off, np.nan)),
                    "lfc_t25_on_observed": rms(np.where(observed & anc["eligible"][:, None], lfc, np.nan)),
                    "added_on_observed": rms(np.where(observed, new - lfc, np.nan))},
            "pairs_moved": int(moved.sum()), "targets_moved": int(moved.any(1).sum()),
            "outputs": {f"effects_{c}.npz": sha(a.out / f"effects_{c}.npz"),
                        f"correction_{c}.npz": sha(a.out / f"correction_{c}.npz"),
                        f"targets_{c}.csv": sha(a.out / f"targets_{c}.csv")}}
        log(f"context {c}: {int(moved.any(1).sum())} targets moved, mean w (corrected) "
            f"{manifest['contexts'][c]['w']['mean_corrected']:.3f}")
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest["seconds"] = round(time.time() - t_start, 1)
    manifest["note"] = ("effects of the D-056 hybrid for A/B/C: t25 + w R (PROTOCOLLO.md §13-§14); generation and "
                        "packaging follow with the t25 arguments of stages 45 and 48; not a VCC score")
    (a.out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=float), encoding="utf-8")
    log(f"wrote {a.out}")


if __name__ == "__main__":
    main()
