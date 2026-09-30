"""Export the effects a trained cell network predicts in the competition contexts, in the format of stage 100
(effects_<ctx>.npz: targets, genes, lfc in ln units, observed), so stages 45 and 48 turn them into a submission.

For each context the network reads control cells of that context (rows drawn from the official control file, seeded),
encodes the context from them, and for each target predicts the mixture of responders and escapers:
    lfc_g = ln( pi * softmax(beta + delta)_g + (1 - pi) * softmax(beta)_g ) - ln softmax(beta)_g
on the genes the control file measures and the network knows; the other genes are not observed (stage 45 leaves them
at the control profile). A target the network never saw gets its biological descriptors (arm `descriptors`) or the
code of an unknown target (arm `identity`, which has nothing else to say about it).

    python export_effects.py --run <run dir> --prepass <prepass dir> --descriptors <dir> \
        --controls A=<h5ad> B=<h5ad> C=<h5ad> --axis-from <an effects_A.npz> --out <new dir> [--controls-k 2048]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cellnet as CN  # noqa: E402


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(8 << 20), b""):
            h.update(b)
    return h.hexdigest()


def control_rows(path, genes, k, seed):
    """k control cells of an h5ad (CSR X), drawn with a seeded generator, on the network's genes; the mask of the
    network genes the file measures. Reads only the drawn rows."""
    with h5py.File(path, "r") as f:
        g = f["X"]
        n, _ = (int(v) for v in g.attrs["shape"])
        var = CN.h5_column(f["var"], f["var"].attrs.get("_index", "_index"))
        pos = {s: i for i, s in enumerate(genes)}
        col = np.array([pos.get(str(s), -1) for s in var])
        rows = np.sort(np.random.default_rng(seed).choice(n, min(k, n), replace=False))
        indptr = g["indptr"][:]
        x = np.zeros((rows.size, len(genes)), np.float32)
        for j, r in enumerate(rows):
            a, b = int(indptr[r]), int(indptr[r + 1])
            idx, val = g["indices"][a:b], g["data"][a:b]
            keep = col[idx] >= 0
            x[j, col[idx[keep]]] = val[keep]
    mask = np.zeros(len(genes), bool)
    mask[col[col >= 0]] = True
    return x, mask, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--prepass", required=True, type=Path)
    ap.add_argument("--descriptors", type=Path)
    ap.add_argument("--controls", nargs="+", required=True, metavar="CTX=H5AD")
    ap.add_argument("--axis-from", required=True, type=Path, help="an effects npz whose targets and genes to use")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--controls-k", type=int, default=2048)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="cpu")
    a = ap.parse_args()
    import torch
    if a.out.exists():
        sys.exit(f"refusing: {a.out} exists")
    with open(a.prepass / "prepass.pkl", "rb") as fh:
        st = pickle.load(fh)
    saved = torch.load(a.run / "model.pt", map_location="cpu", weights_only=False)
    cfg = json.loads((a.run / "config.json").read_text(encoding="utf-8"))["args"]
    genes, symbols = saved["genes"], saved["symbols"]
    G, n_sym = len(genes), len(symbols)
    ref = np.load(a.axis_from, allow_pickle=False)
    targets, out_genes = [str(t) for t in ref["targets"]], [str(g) for g in ref["genes"]]
    new = [t for t in targets if t not in set(symbols)]
    # the target table grows by the new symbols; their identity rows are the unknown target's
    desc = None
    if a.descriptors is not None and (a.descriptors / "descriptors.npy").is_file():
        Dm = np.load(a.descriptors / "descriptors.npy")
        drow = {g: k for k, g in enumerate((a.descriptors / "genes.txt").read_text(encoding="utf-8").split())}
        desc = np.zeros((n_sym + len(new) + 1, Dm.shape[1]), np.float32)
        for k, s in enumerate(symbols + new):
            if s in drow:
                desc[k] = Dm[drow[s]]
    model = CN.build_model(G, n_sym + len(new), len(saved["modalities"]), len(saved["studies"]),
                           np.array(saved["input_genes"]), dim=int(cfg["dim"]), rank=int(cfg["rank"]),
                           target_desc=desc, target_code=saved["target_code"])
    state = dict(saved["state"])
    emb = state["target_emb.weight"]
    state["target_emb.weight"] = torch.cat([emb[:n_sym], emb[n_sym:].repeat(len(new) + 1, 1)])
    if "desc" in state:
        state["desc"] = model.state_dict()["desc"]
    model.load_state_dict(state)
    model.eval().to(a.device)
    sidx = {s: k for k, s in enumerate(symbols + new)}
    gene_pos = {g: i for i, g in enumerate(genes)}
    tgt = torch.as_tensor([sidx[t] for t in targets], device=a.device)
    tgene = torch.as_tensor([gene_pos.get(t, -1) for t in targets], device=a.device)
    mod = torch.as_tensor([saved["modalities"].index("CRISPRi")] * len(targets), device=a.device)
    ig = np.array(saved["input_genes"])
    out_pos = np.array([gene_pos.get(g, -1) for g in out_genes])
    a.out.mkdir(parents=True)
    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(), "run": str(a.run),
                "model_sha256": sha(a.run / "model.pt"), "prepass_sha256": sha(a.prepass / "prepass.pkl"),
                "target_code": saved["target_code"], "targets": len(targets), "targets_new_to_the_network": len(new),
                "controls_k": a.controls_k, "seed": a.seed, "contexts": {}}
    for spec in a.controls:
        ctx, path = spec.split("=", 1)
        x, mask, rows = control_rows(path, genes, a.controls_k, a.seed)
        lib = torch.as_tensor(x.sum(1)[None], device=a.device)
        xin = torch.as_tensor(x[:, ig][None], device=a.device)
        min_ = torch.as_tensor(np.broadcast_to(mask[ig], (1,) + x[:, ig].shape).copy(), device=a.device)
        with torch.no_grad():
            z, beta = model.context(xin, min_, lib)
            zz, bb = z.expand(len(targets), -1), beta.expand(len(targets), -1)
            delta, pi = model(zz, bb, tgt, torch.as_tensor(tgene), mod)
            m = torch.as_tensor(mask, device=a.device)
            p0 = torch.softmax(bb.masked_fill(~m, float("-inf")), -1)
            p1 = torch.softmax((bb + delta).masked_fill(~m, float("-inf")), -1)
            pm = pi[:, None] * p1 + (1 - pi[:, None]) * p0
            lfc_net = (torch.log(pm.clamp_min(1e-30)) - torch.log(p0.clamp_min(1e-30))).cpu().numpy()
        lfc = np.zeros((len(targets), len(out_genes)), np.float32)
        observed = np.zeros((len(targets), len(out_genes)), bool)
        have = out_pos >= 0
        cols = out_pos[have]
        lfc[:, have] = np.where(mask[cols][None, :], lfc_net[:, cols], 0.0)
        observed[:, have] = mask[cols][None, :]
        path_out = a.out / f"effects_{ctx}.npz"
        np.savez_compressed(path_out, targets=np.array(targets), genes=np.array(out_genes), lfc=lfc,
                            observed=observed)
        manifest["contexts"][ctx] = {"controls": path, "controls_sha256": sha(path), "rows_drawn": int(rows.size),
                                     "genes_observed": int(observed[0].sum()), "pi_mean": float(pi.mean()),
                                     "lfc_abs_mean_observed": float(np.abs(lfc[observed]).mean()),
                                     "file": path_out.name, "sha256": sha(path_out)}
        print(ctx, manifest["contexts"][ctx], flush=True)
    (a.out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
