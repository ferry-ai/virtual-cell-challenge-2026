"""Self-test of the context encoder and of its integration in the network: synthetic data, CPU, nothing kept.

    python train_emb.py --selftest       every check (needs net.py, pool.py, train.py of rete_contesti_2026-09-27)
    python pretrain.py --selftest        the encoder checks only (1-6)

The world (make_world). Every context has a latent state s in R^2: 14 CRISPRi contexts c0..c13 in 12 families
(f10: two conditions of one group; f11: two lines of one lab, the held-out pair c12 and c13, far apart in s), the
basal-only A, B, C, and 122 external contexts in two studies. Basal log expression is mu_g + L_g . s plus a
per-context, per-gene deviation (SD 0.3), silent below 0.8. Profiles are Poisson counts: 4 cell subsets per
CRISPRi context and for A, B, C (platform flex: a per-gene bias, 5 % of the genes unmeasured); 3 plates per
context of study extA (3'); 1 bulk profile per context of study extB (another per-gene bias). Two external
contexts are the held-out lines under other names (extA_LINE12 with the state of c12, extB_LINE13 with that of
c13): the line lists must catch them.

Responses (the network dataset, pool.py format: 300 targets, 360 axis genes, 320 stored). Planted: the effect of
target t in context c is exp(0.7 s_c1 + 0.7 a_t s_c2) theta_t, with a_t = +-1 a target property the network sees
as a prior (x_sens): the amplitude, target by target, is set by the latent state, which a context's controls show
only through many genes at once. Null: amplitude 1; the latent state still shapes the basal profiles. The
network holds out c12 and c13 (family f11); the encoder is pre-trained without them and without their aliases.

Checks, one line each; exit 1 when one fails:
 1 corpus round trip: both argument forms read back identical counts and tables;
 2 exclusions: exactly the held-out pair and its two external aliases leave; a missing --require context and a
   kept --expect-excluded context fail loudly;
 3 encoder leakage canary: with the excluded profiles overwritten by noise, genes, statistics, validation split,
   trained weights and every non-excluded embedding stay identical to the bit (one CPU thread);
 4 the pre-trained encoder recovers the latent state: a linear map fitted on the training contexts' embeddings
   predicts s on the validation and excluded contexts with mean R2 >= 0.5;
 5 the PCA baseline writes the same format and recovers the latent state too (mean R2 >= 0.5);
 6 consistency: the profiles of one context lie together (within/between spread < 0.3);
 7 default behaviour: the patched classes without embeddings train and predict exactly as train.py's own;
 8 fail loudly: an embedding file without c13, and an encoder that trained on a held-out context, are refused
   before training;
 9 embedding table: the blind row is 0 and is the weighted mean of the visible contexts; changing the held-out
   contexts' embeddings changes their rows only, not the standardisation constants;
10-11 planted, per held-out line: the network beats blind, swap, emb_blind and emb_swap (each paired skill gain
   with its interval above 0 and >= 0.02);
12 planted E2: the predicted difference between the two held-out lines correlates with the observed one (mean
   > 0.1, interval above 0, above the permutations' 97.5 %); blind and transfer predict no difference;
13 blind and swap with embeddings: the blind predictions of the two lines are identical; c12's rows with c13's
   features and embedding equal c13's predictions; emb_swap changes the prediction;
14-15 null, per held-out line: no gain over blind or emb_blind beyond noise (<= 2.5 bootstrap SD + 0.005), and
   no loss of more than 0.05 skill against the transfer;
16 fine-tuning: a short run trains the offsets, leaves the pre-trained weights untouched, predicts finite
   values and keeps the blind predictions of the two lines identical;
17 compare.py recomputes train.py's contrasts (net against blind, swap, emb_blind, emb_swap) from the saved
   predictions to 1e-6.
The planted world is built so that the embedding *can* help: a failure there means the code or the optimisation
is wrong. The null world checks that it does not help by a defect (a leak, a mis-built control).
"""
from __future__ import annotations

import dataclasses
import json
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import torch

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import corpus as CO  # noqa: E402
import pca_baseline  # noqa: E402
import pretrain  # noqa: E402

A_GENES, STORED, N_TARGETS = 360, 320, 300
HELD = ("c12", "c13")
POISON = {"c12", "c13", "extA_LINE12", "extB_LINE13"}
ENC_ARGS = ["--device", "cpu", "--d-emb", "8", "--d-hidden", "64", "--dropout", "0", "--batch-contexts", "32",
            "--lr", "3e-3", "--mask-borrow", "0.2", "--platform-sd", "0.2", "--eval-profiles", "400"]
SMALL = ["--device", "cpu", "--steps", "1500", "--eval-every", "50", "--patience", "8", "--batch", "64",
         "--lr", "3e-3", "--d-gene", "16", "--d-target", "16", "--d-context", "4", "--d-hidden", "64",
         "--k-gate", "8", "--k-inter", "8", "--dropout", "0", "--platform-sd", "0", "--val-rows", "600",
         "--q-drop", "0.1", "--m-drop", "0.1"]


def fmt(x, spec: str = "+.3f") -> str:
    return "None" if x is None else format(x, spec)


# ---------------------------------------------------------------- the synthetic world

def make_world(seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    A = A_GENES
    fam = [f"f{i}" for i in range(10)] + ["f10", "f10", "f11", "f11"]
    grp = [f"f{i}" for i in range(10)] + ["f10", "f10", "f11a", "f11b"]
    line = [f"LINE{i}" for i in range(10)] + ["LINE10", "LINE10", "LINE12", "LINE13"]
    S = rng.normal(0.0, 1.0, (14, 2))
    S[12] = (0.9, 1.1)
    S[13] = (-0.9, -1.0)
    ctx = [{"name": f"c{i}", "family": fam[i], "group": grp[i], "study": f"lab_{fam[i]}", "source": "crispri",
            "platform": "p3", "kind": "cells_subset", "n": 4, "line": line[i], "s": S[i].copy(), "net": True}
           for i in range(14)]
    for name in ("A", "B", "C"):
        ctx.append({"name": name, "family": "vcc", "group": "vcc", "study": "vcc", "source": "vcc", "platform": "flex",
                    "kind": "cells_subset", "n": 4, "line": "", "s": rng.normal(0.0, 1.0, 2), "net": False})
    ext = []
    for j in range(60):
        ext.append({"name": f"extA_L{j:03d}", "family": f"extA_L{j:03d}", "study": "extA", "source": "ext",
                    "platform": "p3", "kind": "pool", "n": 3, "line": f"L{j:03d}", "s": rng.normal(0.0, 1.0, 2)})
        ext.append({"name": f"extB_M{j:03d}", "family": f"extB_M{j:03d}", "study": "extB", "source": "ext",
                    "platform": "bulk", "kind": "bulk", "n": 1, "line": f"M{j:03d}", "s": rng.normal(0.0, 1.0, 2)})
    ext.append({"name": "extA_LINE12", "family": "extA_LINE12", "study": "extA", "source": "ext", "platform": "p3",
                "kind": "pool", "n": 3, "line": "LINE12", "s": S[12].copy()})
    ext.append({"name": "extB_LINE13", "family": "extB_LINE13", "study": "extB", "source": "ext", "platform": "bulk",
                "kind": "bulk", "n": 1, "line": "LINE13", "s": S[13].copy()})
    mu = rng.uniform(0.3, 6.0, A)
    L = rng.normal(0.0, 0.8, (A, 2))
    bias = {"p3": np.zeros(A), "flex": rng.normal(0.0, 0.5, A), "bulk": rng.normal(0.0, 0.4, A)}
    missing = {"p3": np.zeros(A, dtype=bool), "flex": rng.random(A) < 0.05, "bulk": np.zeros(A, dtype=bool)}
    for c in ctx + ext:
        lam = mu + L @ c["s"] + rng.normal(0.0, 0.3, A)
        c["lam"] = np.where(lam < 0.8, 0.0, lam)
    return {"ctx": ctx, "ext": ext, "bias": bias, "missing": missing}


def corpus_tables(world: dict, contexts: list, seed: int):
    """(counts float32 [N, A], library, meta) of the profiles of `contexts`."""
    counts, library, rows = [], [], []
    for k, c in enumerate(contexts):
        rng = np.random.default_rng([seed, k])
        expected = np.expm1(c["lam"]) * np.exp(world["bias"][c["platform"]])
        for j in range(c["n"]):
            e = expected * np.exp(rng.normal(0.0, 0.1, expected.size)) if c["kind"] == "pool" else expected
            lib = 1e6 if c["kind"] == "bulk" else 2e5
            x = rng.poisson(lib * e / e.sum()).astype(np.float32)
            x[world["missing"][c["platform"]]] = np.nan
            counts.append(x)
            library.append(float(np.nansum(x)) * 1.25)
            rows.append({"profile_id": f"{c['name']}_p{j}", "source": c["source"], "context": c["name"],
                         "family": c["family"], "study": c["study"], "platform": c["platform"], "kind": c["kind"],
                         "n_cells": np.nan if c["kind"] == "bulk" else 400.0, "cell_line": c["line"]})
    return np.vstack(counts), np.asarray(library, dtype=np.float64), pd.DataFrame(rows)


def poisoned(tables, names: set, seed: int):
    counts, library, meta = tables
    rng = np.random.default_rng(seed)
    bad = meta["context"].isin(names).to_numpy()
    c = counts.copy()
    noise = rng.poisson(30.0, (int(bad.sum()), c.shape[1])).astype(np.float32)
    c[bad] = np.where(np.isfinite(c[bad]), noise, np.nan)
    lib = library.copy()
    lib[bad] = np.nansum(c[bad], axis=1) * 1.25
    return c, lib, meta


def save_corpus(target: Path, counts, library, meta) -> None:
    target = Path(target)
    if target.suffix == ".npz":
        target.parent.mkdir(parents=True, exist_ok=True)
        npz, table = target, target.with_suffix(".csv")
    else:
        target.mkdir(parents=True, exist_ok=False)
        npz, table = target / "profiles.npz", target / "meta.csv"
    with open(npz, "xb") as fh:
        np.savez_compressed(fh, counts=counts.astype(np.float32), library=library.astype(np.float64),
                            profile_id=meta["profile_id"].to_numpy(dtype=str))
    meta.to_csv(table, index=False)


def data_args(ours, ext, required: list) -> list:
    return ["--corpus", str(ours), "--corpus", str(ext), "--reference-corpora", "1", "--exclude-families", "f11",
            "--exclude-lines", "LINE12,LINE13", "--require", ",".join(required), "--expect-excluded", "c12,c13",
            "--n-genes", "0", "--min-measured", "0.5", "--min-mean-cpm", "0", "--val-frac", "0.1", "--seed", "0"]


def r2_latent(world: dict, names: list, E: np.ndarray, train: list, test: list) -> np.ndarray:
    """R2 per latent dimension on `test` of a linear map from the embeddings fitted on `train`."""
    S = {c["name"]: c["s"] for c in world["ctx"] + world["ext"]}
    pos = {n: i for i, n in enumerate(names)}
    Xtr = np.c_[E[[pos[n] for n in train]], np.ones(len(train))]
    coef = np.linalg.lstsq(Xtr, np.stack([S[n] for n in train]), rcond=None)[0]
    Yte = np.stack([S[n] for n in test])
    pred = np.c_[E[[pos[n] for n in test]], np.ones(len(test))] @ coef
    return 1.0 - ((pred - Yte) ** 2).sum(axis=0) / ((Yte - Yte.mean(axis=0)) ** 2).sum(axis=0)


def write_network(out: Path, world: dict, planted: bool, seed: int, P) -> None:
    """The network dataset of the world (pool.py format), as train.synthetic builds its own."""
    rng = np.random.default_rng(seed)
    A, GS, T = A_GENES, STORED, N_TARGETS
    axis = [f"g{i:03d}" for i in range(A)]
    net = [c for c in world["ctx"] if c["net"]]
    abc = [c for c in world["ctx"] if not c["net"]]
    n_ctx = len(net)
    basal_names = [c["name"] for c in net + abc]
    basal = np.vstack([np.expm1(c["lam"]) for c in net + abc]).astype(np.float32)
    basal[0, 5] = np.nan                                   # an unknown control value: imputed, flagged
    t_axis = np.r_[np.arange(T - 10), np.full(10, -1)]
    tnames = axis[:T - 10] + [f"x{i}" for i in range(10)]
    theta = np.zeros((T, A))
    nz = rng.random((T, A)) < 0.15
    theta[nz] = rng.normal(0.0, 0.7, int(nz.sum()))
    on = np.flatnonzero(t_axis >= 0)
    theta[on, t_axis[on]] = -2.0
    sens = np.where(rng.random(T) < 0.5, -1.0, 1.0)
    S = np.stack([c["s"] for c in net])
    amp = np.exp(0.7 * S[:, [0]] + 0.7 * S[:, [1]] * sens[None, :]) if planted else np.ones((n_ctx, T))
    template = rng.normal(0.0, 0.05, (n_ctx, A))
    se_factor = np.array([1.0] * 10 + [2.0, 2.0, 1.0, 1.0])
    weight = np.array([1.0] * 10 + [0.5, 0.5, 1.0, 1.0])
    shared = rng.random(T) < 0.9
    measured = [rng.random(T) < 0.85 for _ in range(n_ctx - 2)] + [shared, shared]
    n_rows = int(sum(m.sum() for m in measured))
    genes_axis = np.arange(GS)
    w = P.DatasetWriter(out, n_rows, genes_axis)
    ctx_rows, pos, fin_frac = [], 0, np.zeros((n_ctx, A))
    for i in range(n_ctx):
        tg = np.flatnonzero(measured[i])
        n = tg.size
        signal = amp[i, tg][:, None] * theta[tg] + template[i][None, :]
        se = rng.uniform(0.08, 0.3, (n, A))
        raw = signal + rng.normal(0.0, 1.0, (n, A)) * se * np.sqrt(se_factor[i])
        silent = basal[i] == 0
        raw[:, silent] = np.nan
        se[:, silent] = np.nan
        z2 = (raw / se) ** 2
        shrunk = raw * z2 / (z2 + 4.0)
        raw, se, shrunk = (x.astype(np.float32) for x in (raw, se, shrunk))
        w.add(i, tg, rng.uniform(60, 400, n), raw, se, shrunk, t_axis[tg])
        ctx_rows.append((pos, pos + n))
        pos += n
        fin_frac[i] = np.isfinite(raw).mean(axis=0)
    fams = [c["family"] for c in net]
    fam_frac = np.array([fin_frac[[i for i in range(n_ctx) if fams[i] == f]].max(axis=0) for f in sorted(set(fams))])
    contexts = pd.DataFrame({"context": [c["name"] for c in net], "family": fams, "group": [c["group"] for c in net],
                             "se_factor": se_factor, "weight": weight, "modality": "crispri",
                             "basal_row": np.arange(n_ctx), "row_start": [a for a, _ in ctx_rows],
                             "row_stop": [b for _, b in ctx_rows]})
    tss = np.where(t_axis >= 0, t_axis * 3000.0, np.nan)
    targets = pd.DataFrame({"target": tnames, "axis_index": t_axis, "gene_index": np.where(t_axis < GS, t_axis, -1),
                            "in_panel": np.arange(T) < 20, "essential": (np.arange(T) >= 20) & (np.arange(T) < 30),
                            "chrom": np.where(t_axis >= 0, "1", ""), "tss": tss})
    targets = pd.concat([targets, P.basal_priors(basal[:n_ctx], t_axis)], axis=1)
    targets["x_sens"] = sens
    cis_lists = [[int(j) for j in (t_axis[t] - 1, t_axis[t] + 1) if 0 <= j < GS] if t_axis[t] >= 0 else []
                 for t in range(T)]
    part = [set() for _ in range(T)]
    for t in range(T):
        for p in rng.choice(T, size=3, replace=False):
            if p != t:
                part[t].add(int(p))
                part[int(p)].add(t)
    scores, plist = {}, []
    for t in range(T):
        ps = sorted(part[t])
        sc = {p: scores.setdefault((min(t, p), max(t, p)), float(rng.integers(700, 1000))) for p in ps}
        plist.append(sorted(ps, key=lambda p: (-sc[p], p)))
    targets["p_string_deg"] = np.log1p([len(p) for p in plist])
    p_ip, p_ix = P.csr(plist)
    p_sc = np.array([scores[(min(t, p), max(t, p))] for t in range(T) for p in plist[t]], dtype=np.float32)
    genes = pd.DataFrame({"gene": [axis[i] for i in genes_axis], "axis_index": genes_axis,
                          "n_families": (fam_frac[:, genes_axis] >= 0.5).sum(axis=0)})
    w.finish(contexts=contexts, targets=targets, genes=genes, axis=axis, basal=basal, basal_names=basal_names,
             cis=P.csr(cis_lists), partners=(p_ip, p_ix, p_sc),
             manifest={"stage": "encoder_contesto_2026-09-28/selftest_emb.py", "planted": planted, "seed": seed})


# ---------------------------------------------------------------- the checks

def main(network: bool = True) -> int:
    results, logs = [], []

    def check(name: str, ok: bool, detail: str) -> None:
        results.append(bool(ok))
        print(f"{'PASS' if ok else 'FAIL'} {name}: {detail}", flush=True)

    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    quiet = CO.Logger(quiet=True)
    logs.append(quiet)
    st: dict = {}
    # ignore_cleanup_errors: on Windows a memory-mapped file cannot be deleted while it is still open
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpname:
        tmp = Path(tmpname)

        def encoder_part() -> None:
            world = make_world(7)
            st["world"] = world
            ours, ext = corpus_tables(world, world["ctx"], 101), corpus_tables(world, world["ext"], 202)
            paths = {"ours": tmp / "ours", "ext": tmp / "ext" / "ext.npz", "ours_p": tmp / "ours_p",
                     "ext_p": tmp / "ext_p" / "ext.npz"}
            save_corpus(paths["ours"], *ours)
            save_corpus(paths["ext"], *ext)
            save_corpus(paths["ours_p"], *poisoned(ours, POISON, 9))
            save_corpus(paths["ext_p"], *poisoned(ext, POISON, 9))
            st["paths"] = paths
            required = [c["name"] for c in world["ctx"]]

            cs = CO.open_corpora([paths["ours"], paths["ext"]])
            want = pd.concat([ours[2], ext[2]], ignore_index=True)
            same_counts = np.array_equal(cs.read(0)[0], ours[0], equal_nan=True) and \
                np.array_equal(cs.read(1)[0], ext[0], equal_nan=True)
            same_meta = all(cs.meta[c].tolist() == want[c].tolist() for c in ("profile_id", "context", "family", "kind",
                                                                              "platform", "cell_line")) and \
                np.allclose(cs.meta["n_cells"].to_numpy(dtype=float), want["n_cells"].to_numpy(dtype=float),
                            equal_nan=True)
            check("corpus round trip", same_counts and same_meta and cs.n_axis == A_GENES,
                  f"{len(cs.meta)} profiles in 2 corpora (a folder, an .npz with its .csv), {cs.n_axis} genes: counts "
                  f"{'identical' if same_counts else 'DIFFER'}, tables {'identical' if same_meta else 'DIFFER'}")

            base = data_args(paths["ours"], paths["ext"], required)
            a_short = pretrain.build_parser().parse_args(base + ENC_ARGS + ["--steps", "40", "--eval-every", "20"])
            prep = CO.prepare(a_short, quiet)
            status = dict(zip(prep.contexts, prep.context_status()))
            excl = {c for c, s in status.items() if s == "excluded"}
            partial = {c for c, s in status.items() if s == "partial"}
            refused = []
            for extra, token in ((["--require", "c0,nowhere"], "nowhere"), (["--expect-excluded", "c11"], "c11")):
                try:
                    CO.prepare(pretrain.build_parser().parse_args(base + ENC_ARGS + extra), quiet)
                    refused.append(False)
                except ValueError as exc:
                    refused.append(token in str(exc))
            check("exclusions", excl == POISON and not partial and all(refused),
                  f"excluded contexts {sorted(excl)} (want {sorted(POISON)}), partly excluded {sorted(partial)}; "
                  f"missing --require and kept --expect-excluded refused: {refused}")

            a_pois = pretrain.build_parser().parse_args(data_args(paths["ours_p"], paths["ext_p"], required)
                                                        + ENC_ARGS + ["--steps", "40", "--eval-every", "20"])
            prep_p = CO.prepare(a_pois, quiet)
            same_prep = (np.array_equal(prep.genes, prep_p.genes) and np.array_equal(prep.mu, prep_p.mu)
                         and np.array_equal(prep.sd, prep_p.sd) and list(prep.split) == list(prep_p.split)
                         and np.array_equal(prep.train_ctx_weight, prep_p.train_ctx_weight)
                         and prep.platforms == prep_p.platforms)
            threads = torch.get_num_threads()
            torch.set_num_threads(1)                  # one thread: no reduction-order differences
            try:
                ma = pretrain.train_encoder(prep, a_short, quiet)[0]
                mb = pretrain.train_encoder(prep_p, a_pois, quiet)[0]
            finally:
                torch.set_num_threads(threads)
            sa, sb = ma.state_dict(), mb.state_dict()
            same_w = list(sa) == list(sb) and all(torch.equal(sa[k], sb[k]) for k in sa)
            kept = np.flatnonzero(prep.split != "excluded")
            cpu = torch.device("cpu")
            same_e = np.array_equal(pretrain.embed_profiles(ma, prep, cpu, kept),
                                    pretrain.embed_profiles(mb, prep_p, cpu, kept))
            differs = not np.array_equal(prep.z[prep.excluded_rows], prep_p.z[prep_p.excluded_rows], equal_nan=True)
            check("encoder leakage canary", same_prep and same_w and same_e and differs,
                  f"{prep.excluded_rows.size} excluded profiles overwritten with noise ({'they differ' if differs else 'NOT changed'}): "
                  f"genes, statistics, split and weights {'identical' if same_prep else 'DIFFER'}; trained weights "
                  f"{'identical' if same_w else 'DIFFER'}; embeddings of {kept.size} other profiles "
                  f"{'identical' if same_e else 'DIFFER'}")

            enc_dir = tmp / "enc"
            r = pretrain.run(base + ENC_ARGS + ["--steps", "600", "--eval-every", "50", "--patience", "6",
                                                "--out", str(enc_dir)], log=quiet)
            emb = CO.read_embeddings(enc_dir / "context_embeddings.npz")
            train_n = [n for n in emb["names"] if emb["status"][n] == "train"]
            test_n = [n for n in emb["names"] if emb["status"][n] in ("val", "excluded")]
            r2 = r2_latent(world, emb["names"], emb["E"], train_n, test_n)
            rec = r["manifest"]["reconstruction"]
            check("latent state recovered by the encoder", bool(np.mean(r2) >= 0.5),
                  f"R2 {np.round(r2, 3).tolist()} on {len(test_n)} validation and excluded contexts (map fitted on "
                  f"{len(train_n)}; needs mean >= 0.5); masked-gene R2 against the mean: validation "
                  f"{fmt((rec.get('val') or {}).get('r2_vs_mean'), '.3f')}, excluded "
                  f"{fmt((rec.get('excluded') or {}).get('r2_vs_mean'), '.3f')}")
            st["enc_dir"], st["emb"] = enc_dir, emb

            pca_dir = tmp / "pca"
            rp = pca_baseline.run(base + ["--d-emb", "8", "--eval-profiles", "400", "--out", str(pca_dir)], log=quiet)
            embp = CO.read_embeddings(pca_dir / "context_embeddings.npz")
            r2p = r2_latent(world, embp["names"], embp["E"], train_n, test_n)
            same_fmt = embp["names"] == emb["names"] and embp["E"].shape == emb["E"].shape and \
                embp["status"] == emb["status"]
            recp = rp["manifest"]["reconstruction"]
            check("PCA baseline", same_fmt and bool(np.mean(r2p) >= 0.5),
                  f"same contexts, dimension and status as the encoder: {same_fmt}; R2 {np.round(r2p, 3).tolist()}; "
                  f"masked-gene R2 against the mean on validation {fmt((recp.get('val') or {}).get('r2_vs_mean'), '.3f')}")

            geo = (r["manifest"]["geometry"] or {}).get("all") or {}
            ratio = geo.get("ratio")
            check("consistency", ratio is not None and ratio < 0.3,
                  f"within-context over between-context spread {fmt(ratio, '.4f')} over {geo.get('contexts')} "
                  f"contexts with two or more profiles (needs < 0.3)")

        def network_part() -> None:
            import train_emb as TE
            T, P = TE.T, TE.P
            qlog = T.Logger(quiet=True)
            logs.append(qlog)
            world, enc_dir, emb = st["world"], st["enc_dir"], st["emb"]
            planted_dir, null_dir = tmp / "net_planted", tmp / "net_null"
            write_network(planted_dir, world, True, 11, P)
            write_network(null_dir, world, False, 11, P)
            pool, pool0 = P.Pool.from_dir(planted_dir), P.Pool.from_dir(null_dir)
            emb_file = enc_dir / "context_embeddings.npz"

            def net_args(data, out, extra):
                return TE.build_parser().parse_args(SMALL + ["--data", str(data), "--out", str(out),
                                                             "--hold-out", ",".join(HELD)] + extra)

            args_d = net_args(planted_dir, tmp / "unused_d", ["--seed", "3"])
            design = T.make_design(pool, args_d, qlog)
            tcfg = T.train_config(args_d)
            opts = P.PhaseOptions()
            rows12 = design["test_rows"][pool.context_index["c12"]]
            preds, kinds = [], []
            threads = torch.get_num_threads()
            torch.set_num_threads(1)
            try:
                for patched in (False, True):
                    if patched:
                        TE.install(None)
                    try:
                        ph = P.Phase(pool, design["train_rows"], opts, "cpu", qlog)
                        mdl, _, _, _ = T.fit(ph, T.net_config(args_d, pool, ph), tcfg, steps=30, val=None, log=qlog)
                        preds.append(T.predict(ph, mdl, ph.spec_rows(rows12))[0])
                        kinds.append((type(ph).__name__, type(mdl).__name__))
                    finally:
                        TE.uninstall()
            finally:
                torch.set_num_threads(threads)
            check("default behaviour unchanged", np.array_equal(preds[0], preds[1], equal_nan=True)
                  and kinds == [("Phase", "PerturbNet"), ("EmbPhase", "EmbPerturbNet")],
                  f"train.py's classes {kinds[0]} and the patched ones without embeddings {kinds[1]}: 30 steps from "
                  f"seed 3 give {'identical' if np.array_equal(preds[0], preds[1], equal_nan=True) else 'DIFFERENT'} "
                  f"predictions")

            miss_dir, seen_dir = tmp / "emb_missing", tmp / "emb_seen"
            miss_dir.mkdir()
            seen_dir.mkdir()
            keep_i = [i for i, n in enumerate(emb["names"]) if n != "c13"]
            with open(miss_dir / "context_embeddings.npz", "xb") as fh:
                np.savez_compressed(fh, contexts=np.array([emb["names"][i] for i in keep_i]),
                                    embeddings=emb["E"][keep_i].astype(np.float32))
            shutil.copy2(emb_file, seen_dir / "context_embeddings.npz")
            man = json.loads((enc_dir / "manifest.json").read_text(encoding="utf-8"))
            man["contexts"]["excluded"] = []
            (seen_dir / "manifest.json").write_text(json.dumps(man), encoding="utf-8")
            refused = []
            for folder, token in ((miss_dir, "c13"), (seen_dir, "held-out")):
                try:
                    TE.make_settings(net_args(planted_dir, tmp / "unused_m",
                                              ["--context-embeddings", str(folder / "context_embeddings.npz")]),
                                     pool, qlog)
                    refused.append(False)
                except SystemExit as exc:
                    refused.append(token in str(exc))
            check("fail loudly", all(refused),
                  f"refused before training: an embedding file without c13 {refused[0]}; an encoder that trained on "
                  f"the held-out lines {refused[1]}")

            args_p = net_args(planted_dir, tmp / "run_planted", ["--context-embeddings", str(emb_file)])
            settings = TE.make_settings(args_p, pool, qlog)
            design = T.make_design(pool, args_p, qlog)
            TE.install(settings)
            try:
                ph = P.Phase(pool, design["train_rows"], opts, "cpu", qlog)
                tab = ph.consts["ctx_emb"].cpu().numpy()
                vis = ph.consts["emb_visible"]
                wv = np.asarray(ph.consts["emb_visible_weights"])
                blind0 = bool(np.all(tab[-1] == 0.0)) and \
                    bool(np.allclose((wv[:, None] * tab[vis]).sum(axis=0), 0.0, atol=1e-5))
                rng = np.random.default_rng(3)
                moved = dict(settings.table)
                for n in HELD:
                    moved[n] = rng.normal(0.0, 9.0, settings.dim)
                TE.install(dataclasses.replace(settings, table=moved))
                ph2 = P.Phase(pool, design["train_rows"], opts, "cpu", qlog)
                tab2 = ph2.consts["ctx_emb"].cpu().numpy()
                held_rows = [int(pool.ctx_basal[pool.context_index[n]]) for n in HELD]
                same_const = bool(torch.equal(ph.consts["emb_center"], ph2.consts["emb_center"])) and \
                    ph.consts["emb_scale"] == ph2.consts["emb_scale"] and np.array_equal(tab[vis], tab2[vis])
                changed = not np.array_equal(tab[held_rows], tab2[held_rows])
            finally:
                TE.uninstall()
            check("embedding table", blind0 and same_const and changed,
                  f"blind row 0 and the weighted mean of the {len(vis)} visible contexts: {blind0}; new embeddings for "
                  f"the held-out lines change their rows ({changed}), not the constants ({same_const})")

            res = TE.run_with(settings, args_p, pool, log=qlog)
            for c in HELD:
                d = res["results"]["contexts"][c]
                ok_all, parts = True, []
                for other in ("blind", "swap", "emb_blind", "emb_swap"):
                    s = d["contrasts"][f"net-{other}"]["all"]["skill"]
                    ok = s["mean"] is not None and s["ci95"][0] is not None and s["ci95"][0] > 0 and s["mean"] >= 0.02
                    ok_all = ok_all and ok
                    parts.append(f"{other} {fmt(s['mean'])} ({fmt(s['ci95'][0])}..{fmt(s['ci95'][1])})")
                check(f"planted {c}: net beats blind, swap, emb_blind and emb_swap", ok_all,
                      f"skill net {fmt(d['arms']['net']['skill'], '.3f')}; paired gains " + "; ".join(parts)
                      + f" over {d['targets']} targets (each: interval above 0 and >= 0.02)")
            e2 = res["results"]["e2"].get(f"{HELD[0]}-{HELD[1]}", {})
            en = e2.get("net", {})
            zero_ok = bool(e2.get("blind", {}).get("predicted_difference_is_zero")) and \
                bool(e2.get("transfer", {}).get("predicted_difference_is_zero"))
            e2_ok = (en.get("mean") is not None and en["mean"] > 0.1 and en.get("perm_q975") is not None
                     and en["mean"] > en["perm_q975"] and en["ci95"][0] is not None and en["ci95"][0] > 0 and zero_ok)
            check("planted E2", e2_ok,
                  f"mean correlation {fmt(en.get('mean'))} (CI {en.get('ci95')}), permutation q97.5 "
                  f"{fmt(en.get('perm_q975'))}; emb_blind {fmt(e2.get('emb_blind', {}).get('mean'))}; blind and "
                  f"transfer predict no difference: {zero_ok}")

            phase, model = res["phase"], res["model"]
            spec = {c: phase.spec_rows(res["design"]["test_rows"][pool.context_index[c]]) for c in HELD}
            b13 = int(pool.ctx_basal[pool.context_index[HELD[1]]])
            bl = {c: T.predict(phase, model, spec[c], feat="blind")[0] for c in HELD}
            tr = {c: T.predict(phase, model, spec[c])[0] for c in HELD}
            sw12 = T.predict(phase, model, spec[HELD[0]], feat="swap", swap_basal=b13)[0]
            with phase.override("swap", b13):
                es12 = T.predict(phase, model, spec[HELD[0]])[0]
            same_t = np.array_equal(spec[HELD[0]].target, spec[HELD[1]].target)
            sem = (same_t and np.allclose(bl[HELD[0]], bl[HELD[1]], atol=1e-6, equal_nan=True)
                   and np.allclose(sw12, tr[HELD[1]], atol=1e-6, equal_nan=True)
                   and not np.allclose(es12, tr[HELD[0]], atol=1e-4, equal_nan=True)
                   and not np.allclose(tr[HELD[0]], tr[HELD[1]], atol=1e-3, equal_nan=True))
            check("blind and swap with embeddings", sem,
                  "blind gives the two lines identical predictions; c12's rows with c13's controls and embedding equal "
                  "c13's predictions; c13's embedding alone changes c12's predictions; true c12 and c13 differ")

            args_n = net_args(null_dir, tmp / "run_null", ["--context-embeddings", str(emb_file)])
            res0 = TE.run_with(TE.make_settings(args_n, pool0, qlog), args_n, pool0, log=qlog)
            for c in HELD:
                d = res0["results"]["contexts"][c]
                ok_all, parts = True, []
                for other in ("blind", "emb_blind"):
                    s = d["contrasts"][f"net-{other}"]["all"]["skill"]
                    bound = 2.5 * (s["sd"] or 0.0) + 0.005
                    ok_all = ok_all and s["mean"] is not None and s["mean"] <= bound
                    parts.append(f"net-{other} {fmt(s['mean'], '+.4f')} <= {bound:.4f}")
                sn, stt = d["arms"]["net"]["skill"], d["arms"]["transfer"]["skill"]
                ok_all = ok_all and sn is not None and stt is not None and sn - stt >= -0.05
                check(f"null {c}: no gain from the context beyond noise, not worse than the transfer", ok_all,
                      "; ".join(parts) + f" (2.5 bootstrap SD + 0.005); skill net {fmt(sn, '.3f')}, transfer "
                      f"{fmt(stt, '.3f')} (tolerance 0.05)")

            args_f = net_args(planted_dir, tmp / "run_ft",
                              ["--finetune-encoder", str(enc_dir), "--finetune-corpus", str(st["paths"]["ours"]),
                               "--finetune-corpus", str(st["paths"]["ext"]), "--steps", "60", "--eval-every", "30",
                               "--val-family", "none"])
            sf = TE.make_settings(args_f, pool, qlog)
            rf = TE.run_with(sf, args_f, pool, log=qlog)
            mf = rf["model"]
            moved_w = any(float(p.detach().abs().sum()) > 0 for p in mf.ctx_encoder.deltas)
            base_sd = mf.ctx_encoder.base.state_dict()
            frozen = all(torch.equal(base_sd[k].cpu(), v.cpu()) for k, v in sf.finetune["state_dict"].items())
            finite = all(rf["results"]["contexts"][c]["arms"]["net"]["skill"] is not None for c in HELD)
            phf = rf["phase"]
            fb = {c: T.predict(phf, mf, phf.spec_rows(rf["design"]["test_rows"][pool.context_index[c]]),
                               feat="blind")[0] for c in HELD}
            same_blind = np.allclose(fb[HELD[0]], fb[HELD[1]], atol=1e-6, equal_nan=True)
            check("fine-tuning", moved_w and frozen and finite and same_blind,
                  f"offsets trained {moved_w}; pre-trained weights untouched {frozen}; finite skills {finite}; blind "
                  f"identical for the two lines {same_blind}; trainable parameters "
                  f"{(rf['emb_config'].get('parameters') or {}).get('total')}")

            import compare as CMP
            run = CMP.load_run(tmp / "run_planted")
            diffs = []
            for c in HELD:
                m = CMP.run_metrics(run, pool, c)
                for other in ("blind", "swap", "emb_blind", "emb_swap"):
                    want = res["results"]["contexts"][c]["contrasts"][f"net-{other}"]["all"]["skill"]["mean"]
                    got = CMP.contrast_mean(m, "net", other)
                    diffs.append(abs(got - want) if got is not None and want is not None else float("inf"))
            check("compare.py agrees with train.py", max(diffs) <= 1e-6,
                  f"largest difference {max(diffs):.2e} over {len(diffs)} contrasts of the planted run")

        def guarded(name: str, fn) -> bool:
            try:
                fn()
                return True
            except (Exception, SystemExit) as exc:          # a crash is a failure, reported with its traceback
                results.append(False)
                print(f"FAIL {name} crashed: {type(exc).__name__}: {exc}", flush=True)
                traceback.print_exc()
                return False

        ok = guarded("encoder checks", encoder_part)
        if network:
            if ok:
                guarded("network checks", network_part)
            else:
                check("network checks", False, "not run: the encoder checks crashed")
    n_fail = results.count(False)
    if n_fail:
        for lg in logs:
            print("\n".join(lg.lines[-40:]))
    print(f"selftest: {len(results) - n_fail} passed, {n_fail} failed", flush=True)
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
