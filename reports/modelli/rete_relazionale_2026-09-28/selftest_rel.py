"""Self-test of the relational network on CPU: synthetic data in a temporary folder, nothing kept; exit 1 on a failure.

    python selftest_rel.py                (or: python train_rel.py --selftest)

Two synthetic worlds in the network's dataset format (pool.DatasetWriter), with r1's layout: 10 contexts in 8
families (f6: two conditions of one group; f7: two lines of one lab), 360 axis genes of which 320 stored, 340
targets (10 on the axis but not stored, 10 off it), random STRING partners, cis windows of +-1 axis position.
* relational: 240 stored genes in 8 modules of 30, each gene with a loading of random sign; knocking down a target
  whose gene is in module k moves module k (response c_k L[g_t, k] L[:, k]); each basal row has a module activity
  v[c, k] added to the log CPM of the module's genes, and the module's response in context c is scaled by
  gamma[c, k] = exp(0.6 tanh(v[c, k] / 0.8)); plus a sparse idiosyncratic response and the knockdown (-2);
* null: r1's null world (sparse random responses, no module, no context interaction).

Checks (DISEGNO.md; map §3.4):
1. init identity: at step 0 a RelNet predicts A m + A_q q (to 1e-6); with random parameters the blind row has
   gamma = 1 exactly and norel equals the model with every relational parameter at 0;
2. leak canary: with every invisible row overwritten (train.poisoned), the cards, omega, the card-neighbour table,
   Qc, a training batch and every arm of the test predictions are identical, for an E and a J design; no hidden
   J target is ever a card neighbour;
3. qc against a plain loop, and the card-neighbour table against a brute-force search;
4. planted world, a test of what the code can learn: with relaxed penalties (RELAX: theta0 1e-5, theta_k 1e-4,
   w_self and W_p 1e-5) rel0 beats blind and swap on both held-out lines (E1), and its predicted difference between
   the two lines correlates with the observed one (E2: mean > 0.1, above the 97.5th permutation percentile, interval
   above 0); in J, with --val-m as-train (validation rows without m, as the J test rows and the J training rows),
   rel0 beats r1's network (none) and the partners arm, and cardnb beats partners. The same E design with the
   registered penalties, and J with train.py's validation (--val-m keep), are printed as INFO lines (not checks),
   with the scale of the basal module activity a: what the registered defaults do in this world;
5. null world: rel0 does not beat blind beyond noise and loses at most 0.05 skill to the transfer;
6. two CPU trainings from the same seed (one thread) give bit-identical predictions;
7. parity: train_rel.py --arch r1 --eval-every 250 --no-eval-step0 reproduces train.py's run bit for bit
   (predictions, metrics.json, history, final weights), with the same design and test targets; train.py's names
   are restored after the run.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

import relnet as RN
import relphase as RP
import net as N  # noqa: E402
import pool as P  # noqa: E402
import train as T  # noqa: E402
import train_rel as TR

SMALL = ["--device", "cpu", "--steps", "1500", "--batch", "64", "--lr", "3e-3", "--d-gene", "16", "--d-target", "16",
         "--d-context", "4", "--d-hidden", "64", "--k-gate", "8", "--k-inter", "8", "--dropout", "0",
         "--platform-sd", "0", "--val-rows", "600", "--q-drop", "0.1"]
REL = ["--rel-k", "10", "--rel-nb", "8", "--rel-omega-top", "30"]
E_DESIGN = ["--hold-out", "c8,c9", "--m-drop", "0.1"]
J_DESIGN = ["--regime", "J", "--hold-out", "c8", "--n-test", "40", "--cis-group-bp", "1000"]
RELAX = ["--lam-theta0", "1e-5", "--lam-theta", "1e-4", "--lam-self", "1e-5", "--lam-prior", "1e-5"]


# ---------------------------------------------------------------- synthetic worlds

def synthetic_rel(out: Path, *, world: str, seed: int) -> dict:
    """See the module docstring; the layout and the writer calls are train.synthetic's."""
    rng = np.random.default_rng(seed)
    A, GS, n_ctx, nT, n_mod = 360, 320, 10, 340, 8
    axis = [f"g{i:03d}" for i in range(A)]
    names = [f"c{i}" for i in range(n_ctx)]
    family = ["f0", "f1", "f2", "f3", "f4", "f5", "f6", "f6", "f7", "f7"]
    group = ["f0", "f1", "f2", "f3", "f4", "f5", "f6", "f6", "f7a", "f7b"]
    se_factor = np.array([1, 1, 1, 1, 1, 1, 2, 2, 1, 1], dtype=float)
    weight = np.array([1, 1, 1, 1, 1, 1, 0.5, 0.5, 1, 1], dtype=float)
    basal_names = names + ["A", "B", "C"]
    nb = len(basal_names)
    module = np.full(A, -1, dtype=np.int64)
    members = rng.permutation(GS)[:240]
    module[members] = np.arange(240) % n_mod
    L = np.zeros((A, n_mod))
    L[members, module[members]] = rng.choice([-1.0, 1.0], 240) * rng.uniform(0.6, 1.2, 240)
    v = rng.normal(0.0, 0.8, (nb, n_mod))
    mu = rng.uniform(0.3, 6.0, A)
    load = rng.normal(0.0, 0.9, (A, 2))
    vv = rng.normal(0.0, 1.0, (nb, 2))
    modact = np.where(module[None, :] >= 0, v[:, np.clip(module, 0, None)], 0.0)
    logc = mu[None, :] + vv @ load.T + modact + rng.normal(0.0, 0.25, (nb, A))
    logc = np.where(logc < 0.8, 0.0, logc)
    cpm = np.expm1(logc)
    basal = cpm.astype(np.float32)
    basal[0, 5] = np.nan
    t_axis = np.r_[np.arange(330), np.full(10, -1)]
    tnames = axis[:330] + [f"x{i}" for i in range(10)]
    on = np.flatnonzero(t_axis >= 0)
    t_mod = np.full(nT, -1, dtype=np.int64)
    stored_on = on[t_axis[on] < GS]
    t_mod[stored_on] = module[t_axis[stored_on]]
    theta_mod = np.zeros((nT, A))
    theta_idio = np.zeros((nT, A))
    gamma = np.ones((n_ctx, n_mod))
    if world == "relational":
        c_k = rng.choice([-1.5, 1.5], n_mod)
        for t in np.flatnonzero(t_mod >= 0):
            k = t_mod[t]
            theta_mod[t] = c_k[k] * L[t_axis[t], k] * L[:, k]
        nz = rng.random((nT, A)) < 0.08
        theta_idio[nz] = rng.normal(0.0, 0.35, int(nz.sum()))
        gamma = np.exp(0.6 * np.tanh(v[:n_ctx] / 0.8))
    elif world == "null":
        nz = rng.random((nT, A)) < 0.15
        theta_idio[nz] = rng.normal(0.0, 0.7, int(nz.sum()))
    else:
        raise ValueError(world)
    theta_idio[on, t_axis[on]] = -2.0
    theta_mod[on, t_axis[on]] = 0.0
    template = rng.normal(0.0, 0.05, (n_ctx, A))
    shared = rng.random(nT) < 0.9
    measured = [rng.random(nT) < 0.85 for _ in range(8)] + [shared, shared]
    n_rows = int(sum(m.sum() for m in measured))
    genes_axis = np.arange(GS)
    w = P.DatasetWriter(out, n_rows, genes_axis)
    ctx_rows, pos, fin_frac = [], 0, np.zeros((n_ctx, A))
    for c in range(n_ctx):
        tg = np.flatnonzero(measured[c])
        n = tg.size
        gk = np.where(t_mod[tg] >= 0, gamma[c, np.clip(t_mod[tg], 0, None)], 1.0)
        signal = gk[:, None] * theta_mod[tg] + theta_idio[tg] + template[c][None, :]
        se = rng.uniform(0.08, 0.3, (n, A))
        raw = signal + rng.normal(0.0, 1.0, (n, A)) * se * np.sqrt(se_factor[c])
        silent = cpm[c] == 0
        raw[:, silent] = np.nan
        se[:, silent] = np.nan
        z2 = (raw / se) ** 2
        shrunk = raw * z2 / (z2 + 4.0)
        raw, se, shrunk = (x.astype(np.float32) for x in (raw, se, shrunk))
        w.add(c, tg, rng.uniform(60, 400, n), raw, se, shrunk, t_axis[tg])
        ctx_rows.append((pos, pos + n))
        pos += n
        fin_frac[c] = np.isfinite(raw).mean(axis=0)
    fam_ids = sorted(set(family))
    fam_frac = np.array([fin_frac[[i for i in range(n_ctx) if family[i] == f]].max(axis=0) for f in fam_ids])
    contexts = pd.DataFrame({"context": names, "family": family, "group": group, "se_factor": se_factor,
                             "weight": weight, "modality": "crispri", "basal_row": np.arange(n_ctx),
                             "row_start": [a for a, _ in ctx_rows], "row_stop": [b for _, b in ctx_rows]})
    tss = np.where(t_axis >= 0, t_axis * 3000.0, np.nan)
    targets = pd.DataFrame({"target": tnames, "axis_index": t_axis, "gene_index": np.where(t_axis < GS, t_axis, -1),
                            "in_panel": np.arange(nT) < 20, "essential": (np.arange(nT) >= 20) & (np.arange(nT) < 30),
                            "chrom": np.where(t_axis >= 0, "1", ""), "tss": tss})
    targets = pd.concat([targets, P.basal_priors(basal[:n_ctx], t_axis)], axis=1)
    cis_lists = [[int(j) for j in (t_axis[t] - 1, t_axis[t] + 1) if 0 <= j < GS] if 0 <= t_axis[t] else []
                 for t in range(nT)]
    part = [set() for _ in range(nT)]
    for t in range(nT):
        for p in rng.choice(nT, size=3, replace=False):
            if p != t:
                part[t].add(int(p))
                part[int(p)].add(t)
    scores, plist = {}, []
    for t in range(nT):
        ps = sorted(part[t])
        sc = {p: scores.setdefault((min(t, p), max(t, p)), float(rng.integers(700, 1000))) for p in ps}
        plist.append(sorted(ps, key=lambda p: (-sc[p], p)))
    targets["p_string_deg"] = np.log1p([len(p) for p in plist])
    p_ip, p_ix = P.csr(plist)
    p_sc = np.array([scores[(min(t, p), max(t, p))] for t in range(nT) for p in plist[t]], dtype=np.float32)
    genes = pd.DataFrame({"gene": [axis[i] for i in genes_axis], "axis_index": genes_axis,
                          "n_families": (fam_frac[:, genes_axis] >= 0.5).sum(axis=0)})
    manifest = w.finish(contexts=contexts, targets=targets, genes=genes, axis=axis, basal=basal,
                        basal_names=basal_names, cis=P.csr(cis_lists), partners=(p_ip, p_ix, p_sc),
                        manifest={"stage": "selftest_rel.py synthetic", "world": world, "seed": seed})
    return {"manifest": manifest, "module": module, "t_mod": t_mod}


# ---------------------------------------------------------------- helpers

def parse(extra: list):
    return TR.build_parser().parse_args(extra)


def fmt(x, spec: str = "+.4f") -> str:
    return "None" if x is None else format(x, spec)


def read_arm(folder: Path, ctx: str, pool, key: str = "net", prefix: str = "pred_") -> tuple[list, np.ndarray]:
    with np.load(Path(folder) / f"{prefix}{ctx}.npz", allow_pickle=False) as z:
        return [str(s) for s in z["targets"]], np.asarray(z[key], dtype=np.float32)[:, pool.genes_axis]


def paired_contrast(res: dict, pool, ctx: str, arms: dict, pairs: list, tau2: float) -> dict:
    """train.effect_diagnostics of the given arms on one truth context of a run (ARM_PAIRS set for the call)."""
    phase, design = res["phase"], res["design"]
    c = pool.context_index[ctx]
    rows = design["test_rows"][c]
    spec = phase.spec_rows(rows)
    truth, se = phase.read("raw", rows, "truth"), phase.read("se", rows, "truth")
    keep = phase.R[None, :] & ~pool.exclusion_mask(spec.target)
    gw = phase.gw[pool.ctx_basal[c]]
    drop = pool.tgt_gene[design["test_targets"]]
    drop = drop[drop >= 0]
    old = T.ARM_PAIRS
    T.ARM_PAIRS = pairs
    try:
        return T.effect_diagnostics(truth, se, arms, gw, float(pool.ctx_se_factor[c]), tau2, keep, drop,
                                    np.random.default_rng([0, 3]))
    finally:
        T.ARM_PAIRS = old


def randomise(model: RN.RelNet, seed: int, scale: float = 0.3) -> None:
    g = torch.Generator().manual_seed(seed)
    with torch.no_grad():
        for n, p in model.named_parameters():
            if n in ("log_amp", "log_amp_q"):
                continue
            p.copy_(torch.randn(p.shape, generator=g) * scale)


def direct_qc(pool, phase, rows: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """qc recomputed row by row with plain loops (the reference for RelPhase.batch)."""
    G, nb = pool.G, phase.rel.nb
    out, ok_out = np.zeros((rows.size, G)), np.zeros((rows.size, G), dtype=bool)
    excl = pool.exclusion_mask(pool.row_target[rows])
    ip, ix = phase.card_indptr, phase.card_index
    for i, r in enumerate(rows):
        t, own_fam = pool.row_target[r], pool.ctx_family[pool.row_context[r]]
        num, den = np.zeros(G), np.zeros(G)
        for fs, f in enumerate(phase.families):
            if f == own_fam:
                continue
            ps = [int(p) for p in ix[ip[t]:ip[t + 1]] if phase.pf_row[fs, p] >= 0 and p != t][:nb]
            if not ps:
                continue
            fn, cnt = np.zeros(G), np.zeros(G)
            for p in ps:
                prof = phase.P[phase.pf_row[fs, p]].astype(np.float64)
                ok = np.isfinite(prof)
                if pool.tgt_gene[p] >= 0:
                    ok[pool.tgt_gene[p]] = False
                fn += np.where(ok, prof, 0.0)
                cnt += ok
            qf = np.where(cnt > 0, fn / np.where(cnt > 0, cnt, 1.0), np.nan).astype(np.float32).astype(np.float16)
            qf = qf.astype(np.float64)
            W = float(np.mean([phase.PW[phase.pf_row[fs, p]] for p in ps]))
            okq = np.isfinite(qf)
            num += W * np.where(okq, qf, 0.0)
            den += W * okq
        keep = phase.R & ~excl[i] & (den > 0)
        out[i] = np.where(keep, num / np.where(den > 0, den, 1.0), 0.0)
        ok_out[i] = keep
    return out, ok_out


def table_mismatches(pool, phase) -> tuple[int, int, float]:
    """(targets checked, targets whose neighbour list differs beyond near-ties, largest similarity gap of a
    difference) against a brute-force search: seen targets with a card, not itself, TSS farther than cis_bp."""
    nb, bp = phase.rel.nb, phase.rel.cis_bp
    cand_all = np.flatnonzero(phase.seen_target & phase.card_ok)
    bad, worst, n = 0, 0.0, 0
    for t in np.flatnonzero(phase.card_ok):
        c = cand_all[cand_all != t]
        if np.isfinite(pool.tgt_tss[t]):
            near = np.isfinite(pool.tgt_tss[c]) & (pool.tgt_chrom[c] == pool.tgt_chrom[t]) \
                & (np.abs(np.nan_to_num(pool.tgt_tss[c]) - pool.tgt_tss[t]) <= bp)
            c = c[~near]
        sims = (phase.card[c].astype(np.float64) @ phase.card[t].astype(np.float64))
        want = c[np.lexsort((c, -sims))][:nb]
        got = phase.card_index[phase.card_indptr[t]:phase.card_indptr[t + 1]]
        n += 1
        if not np.array_equal(want, got):
            s = dict(zip(c.tolist(), sims.tolist()))
            diff = set(want.tolist()) ^ set(got.tolist())
            boundary = s[int(want[-1])] if want.size else 0.0
            gap = max(abs(s[x] - boundary) for x in diff) if diff else 0.0
            if gap > 1e-5 or len(got) != len(want):
                bad += 1
            worst = max(worst, gap)
    return n, bad, worst


# ---------------------------------------------------------------- the checks

def main(tmp_root: str | None = None) -> int:
    results = []
    t_start = time.time()

    def check(name: str, ok: bool, detail: str) -> None:
        results.append(bool(ok))
        print(f"{'PASS' if ok else 'FAIL'} {name}: {detail}  [{time.time() - t_start:.0f} s]", flush=True)

    def info(name: str, ok: bool, detail: str) -> None:
        print(f"INFO ({'would pass' if ok else 'would fail'}; not a check) {name}: {detail}  "
              f"[{time.time() - t_start:.0f} s]", flush=True)

    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    quiet = T.Logger(quiet=True)
    with tempfile.TemporaryDirectory(dir=tmp_root, ignore_cleanup_errors=True) as tmp:
        tmp = Path(tmp)
        synthetic_rel(tmp / "rel", world="relational", seed=11)
        pool = P.Pool.from_dir(tmp / "rel")
        args_e = parse(SMALL + REL + E_DESIGN + ["--data", str(tmp / "rel"), "--out", str(tmp / "unused")])
        args_j = parse(SMALL + REL + J_DESIGN + ["--data", str(tmp / "rel"), "--out", str(tmp / "unused")])
        settings = RN.settings_from_args(args_e)
        opts = P.PhaseOptions()
        design_e = T.make_design(pool, args_e, quiet)
        design_j = T.make_design(pool, args_j, quiet)
        tcfg = T.train_config(args_e)

        # 1. init identity, blind and norel semantics
        ph = RP.RelPhase(pool, design_e["train_rows"], opts, "cpu", quiet, rel=settings)
        c8 = pool.context_index["c8"]
        spec8 = ph.spec_rows(design_e["test_rows"][c8])
        model = RN.build_model(ph, RN.rel_config(args_e, pool, ph))
        cal = T.calibrate(ph, tcfg, np.random.default_rng(0))
        model.set_amplitude(cal["amplitude"], cal["amplitude_q"])
        pred, m, q = T.predict(ph, model, spec8)
        want = cal["amplitude"] * np.nan_to_num(m) + cal["amplitude_q"] * np.nan_to_num(q)
        fin = np.isfinite(pred)
        keep = ph.R[None, :] & ~pool.exclusion_mask(spec8.target)
        d0 = float(np.max(np.abs(pred[fin] - want[fin])))
        randomise(model, 1)
        blind_r = T.predict(ph, model, spec8, feat="blind")[0]
        with torch.no_grad():
            saved = {n: p.detach().clone() for n, p in model.named_parameters()}
            model.theta0.zero_()
            model.theta.zero_()
        blind_0 = T.predict(ph, model, spec8, feat="blind")[0]
        with torch.no_grad():
            for n, p in model.named_parameters():
                p.copy_(saved[n])
        with model.relational_off():
            norel = T.predict(ph, model, spec8)[0]
        with torch.no_grad():
            for n in ("a_c", "theta0", "theta", "w_self", "W_p"):
                getattr(model, n).zero_()
        zeroed = T.predict(ph, model, spec8)[0]
        true_r = pred
        ok1 = (np.array_equal(fin, keep) and d0 <= 1e-6 and np.array_equal(blind_r, blind_0, equal_nan=True)
               and np.allclose(norel, zeroed, atol=1e-7, equal_nan=True))
        n_par = N.count_parameters(model)
        check("1 init identity", ok1,
              f"step-0 prediction vs A m + A_q q: max |diff| {d0:.2e} on {int(fin.sum())} entries (predicted exactly "
              f"on R minus own gene and cis window: {np.array_equal(fin, keep)}); random parameters: blind with theta "
              f"= blind with theta 0 (gamma 1): {np.array_equal(blind_r, blind_0, equal_nan=True)}; norel = relational "
              f"parameters at 0: {np.allclose(norel, zeroed, atol=1e-7, equal_nan=True)}; parameters "
              f"{n_par['total']} {n_par['by_block']}")
        del true_r

        # 2. leak canary, E and J
        for label, design, args_x in (("E", design_e, args_e), ("J", design_j, args_j)):
            tr = design["train_rows"]
            invisible = np.setdiff1d(np.arange(pool.n_rows), tr)
            ph_a = RP.RelPhase(pool, tr, opts, "cpu", quiet, rel=RN.settings_from_args(args_x))
            ph_b = RP.RelPhase(T.poisoned(pool, invisible, 5), tr, opts, "cpu", quiet, rel=RN.settings_from_args(args_x))
            names = ["R", "P", "PW", "Q", "QW", "prior_z", "blind_row", "rho0", "omega_mod", "card", "card_ok",
                     "card_indptr", "card_index", "Qc", "QcW", "qcf_row", "card_rows", "card_row_weight"]
            same = [np.array_equal(getattr(ph_a, k), getattr(ph_b, k), equal_nan=True) for k in names]
            sample = np.sort(np.random.default_rng(1).choice(tr, 128, replace=False))
            ba = ph_a.batch(ph_a.spec_rows(sample), labels="train", drop_m=0.3, drop_q=0.3, depth="train",
                            rng=np.random.default_rng(9))
            bb = ph_b.batch(ph_b.spec_rows(sample), labels="train", drop_m=0.3, drop_q=0.3, depth="train",
                            rng=np.random.default_rng(9))
            batch_same = set(ba) == set(bb) and all(torch.equal(ba[k], bb[k]) for k in ba)
            arms_same, n_arms = True, 0
            fixed_cal = {"amplitude": 0.5, "amplitude_q": 0.1}
            for c, rows in design["test_rows"].items():
                ma = RN.build_model(ph_a, RN.rel_config(args_x, pool, ph_a))
                mb = RN.build_model(ph_b, RN.rel_config(args_x, pool, ph_b))
                randomise(ma, 2)
                randomise(mb, 2)
                sw = design["swap"].get(c)
                sw = None if sw is None else int(pool.ctx_basal[sw])
                aa, _, _ = RN.rel_predict_arms(ph_a, ma, ph_a.spec_rows(rows), sw, fixed_cal)
                ab, _, _ = RN.rel_predict_arms(ph_b, mb, ph_b.spec_rows(rows), sw, fixed_cal)
                arms_same &= set(aa) == set(ab) and all(np.array_equal(aa[k], ab[k], equal_nan=True) for k in aa)
                n_arms = len(aa)
            hidden_nb = int(np.isin(ph_a.card_index, design["hidden_targets"]).sum()) if design["hidden_targets"].size else 0
            ok2 = all(same) and batch_same and arms_same and hidden_nb == 0
            check(f"2 leak canary {label}", ok2,
                  f"{invisible.size} invisible rows overwritten: {sum(same)}/{len(same)} derived arrays identical "
                  f"(cards, omega, neighbour table, Qc among them); training batch {batch_same}; {n_arms} arms of the "
                  f"test predictions identical {arms_same}; hidden targets {design['hidden_targets'].size}, "
                  f"as card neighbours {hidden_nb}")

        # 3. qc against a plain loop; the neighbour table against brute force
        rows_chk = np.r_[design_e["test_rows"][c8][:15], pool.ctx_rows[pool.context_index["c6"]][:10],
                         pool.ctx_rows[pool.context_index["c0"]][:5]]
        b = ph.batch(ph.spec_rows(rows_chk), labels=None)
        want_q, want_ok = direct_qc(pool, ph, rows_chk)
        got_q, got_ok = b["qc"].numpy(), b["qc_ok"].numpy()
        close = np.allclose(got_q, want_q, rtol=5e-3, atol=2e-3) and np.array_equal(got_ok, want_ok)
        n_t, bad, worst = table_mismatches(pool, ph)
        check("3 qc and neighbour table", close and bad == 0 and got_ok.any(),
              f"{rows_chk.size} rows (held-out, two-context family, one-context family): qc matches a plain loop (max "
              f"abs diff {float(np.max(np.abs(got_q - want_q))):.2e}, {int(got_ok.sum())} entries); neighbour lists of "
              f"{n_t} targets vs brute force: {bad} differ beyond near-ties (largest gap {worst:.1e})")

        # 4. planted world: capacity (relaxed penalties in E, J validation as the J test rows), then the registered
        #    defaults as information
        def e_readout(res, gate: bool, tag: str) -> None:
            ctx = res["results"]["contexts"]
            for cname in ("c8", "c9"):
                d = ctx[cname]
                parts, ok = [], True
                for other in ("blind", "swap"):
                    st = d["contrasts"][f"net-{other}"]["all"]["skill"]
                    ok &= st["mean"] is not None and st["ci95"][0] > 0
                    parts.append(f"net-{other} {fmt(st['mean'])} ({fmt(st['ci95'][0])}..{fmt(st['ci95'][1])})")
                a = d["arms"]
                extra = ", ".join(f"{k} {fmt(a[k]['skill'], '.3f')}" for k in ("net", "blind", "swap", "transfer",
                                                                                 "norel", "tperm", "cardnb") if k in a)
                (check if gate else info)(f"4 planted E1 {cname}{tag}: rel0 beats blind and swap", ok,
                                          "; ".join(parts) + f"; skills {extra}")
            e2 = res["results"]["e2"].get("c8-c9", {})
            en = e2.get("net", {})
            zero_ok = bool(e2.get("blind", {}).get("predicted_difference_is_zero"))
            ok = en.get("mean") is not None and en["mean"] > 0.1 and en.get("perm_q975") is not None \
                and en["mean"] > en["perm_q975"] and en["ci95"][0] > 0 and zero_ok
            (check if gate else info)(f"4 planted E2{tag}: predicted difference between the two held-out lines", ok,
                                      f"mean correlation {fmt(en.get('mean'), '.3f')} (CI "
                                      f"{[round(x, 3) for x in en.get('ci95', [])]}), permutation q97.5 "
                                      f"{fmt(en.get('perm_q975'), '.3f')}; blind predicts no difference: {zero_ok}")
            learned = res["rel_config"]["learned"]
            print(f"     learned{tag}: " + json.dumps({k: (round(v, 3) if isinstance(v, float) else v)
                                                      for k, v in learned.items() if v is not None})
                  + f"; best step {res['rel_config']['validation']['best_step']}", flush=True)

        res_e = TR.run(parse(SMALL + REL + E_DESIGN + RELAX + ["--data", str(tmp / "rel"), "--out", str(tmp / "e_rel0")]),
                       pool=pool, log=quiet)
        e_readout(res_e, True, " (relaxed penalties)")
        res_ed = TR.run(parse(SMALL + REL + E_DESIGN + ["--data", str(tmp / "rel"), "--out", str(tmp / "e_rel0_def")]),
                        pool=pool, log=quiet)
        e_readout(res_ed, False, " (registered penalties)")
        phd = res_ed["phase"]
        with torch.no_grad():
            feats = phd.features(0.0, None)[:, pool.genes_axis, 4]
            act = (feats @ phd.t_omega_mod).numpy()
        vis_b = np.unique(pool.ctx_basal[phd.contexts])
        print(f"     scale: basal module activity a, SD over the {vis_b.size} visible contexts, median over modules "
              f"{float(np.median(act[vis_b].std(axis=0))):.3f} (a slope theta moves log gamma by about 0.5 x theta x "
              f"that); penalties theta0 {args_e.lam_theta0:g}, theta_k {args_e.lam_theta:g}", flush=True)

        def j_run(tag: str, extra: list):
            return TR.run(parse(SMALL + REL + J_DESIGN + extra + ["--data", str(tmp / "rel"), "--out", str(tmp / tag)]),
                          pool=pool, log=quiet)

        res_jr = j_run("j_rel0", ["--val-m", "as-train"])
        res_jn = j_run("j_none", ["--val-m", "as-train", "--arch", "r1"])
        tr_, rel0 = read_arm(tmp / "j_rel0", "c8", pool)
        tn_, none = read_arm(tmp / "j_none", "c8", pool)
        dj = paired_contrast(res_jr, pool, "c8", {"rel0": rel0, "none": none}, [("rel0", "none")], args_j.tau2)
        st = dj["contrasts"]["rel0-none"]["all"]["skill"]
        ok_none = tr_ == tn_ and st["mean"] is not None and st["ci95"][0] > 0
        mj = res_jr["results"]["contexts"]["c8"]
        sp = mj["contrasts"]["net-partners"]["all"]["skill"]
        sc = mj["contrasts"]["cardnb-partners"]["all"]["skill"]
        ok_p = sp["mean"] is not None and sp["ci95"][0] > 0
        ok_c = sc["mean"] is not None and sc["ci95"][0] > 0
        a = mj["arms"]
        check("4 planted J (--val-m as-train): rel0 beats none and partners; cardnb beats partners",
              ok_none and ok_p and ok_c,
              f"{mj['targets']} hidden test targets; rel0-none {fmt(st['mean'])} ({fmt(st['ci95'][0])}..{fmt(st['ci95'][1])}); "
              f"rel0-partners {fmt(sp['mean'])} ({fmt(sp['ci95'][0])}..{fmt(sp['ci95'][1])}); cardnb-partners "
              f"{fmt(sc['mean'])} ({fmt(sc['ci95'][0])}..{fmt(sc['ci95'][1])}); skills rel0 {fmt(a['net']['skill'], '.3f')}, "
              f"none {fmt(res_jn['results']['contexts']['c8']['arms']['net']['skill'], '.3f')}, partners "
              f"{fmt(a['partners']['skill'], '.3f')}, cardnb {fmt(a['cardnb']['skill'], '.3f')}, tperm "
              f"{fmt(a['tperm']['skill'], '.3f')}, norel {fmt(a['norel']['skill'], '.3f')}; best steps rel0 "
              f"{res_jr['rel_config']['validation']['best_step']}, none {res_jn['rel_config']['validation']['best_step']}")
        res_jk = j_run("j_rel0_keep", [])
        ak = res_jk["results"]["contexts"]["c8"]["arms"]
        info("4 planted J with train.py's validation (--val-m keep, as registered)",
             res_jk["rel_config"]["validation"]["best_step"] > 0,
             f"best step {res_jk['rel_config']['validation']['best_step']} (refit {res_jk['rel_config']['final_steps']} "
             f"steps); skills rel0 {fmt(ak['net']['skill'], '.3f')}, cardnb {fmt(ak['cardnb']['skill'], '.3f')}, partners "
             f"{fmt(ak['partners']['skill'], '.3f')}: in J training withholds m from every row, the validation rows keep "
             f"it, and the calibrated start wins")

        # 5. null world
        synthetic_rel(tmp / "null", world="null", seed=11)
        pool0 = P.Pool.from_dir(tmp / "null")
        res0 = TR.run(parse(SMALL + REL + E_DESIGN + ["--data", str(tmp / "null"), "--out", str(tmp / "n_rel0")]),
                      pool=pool0, log=quiet)
        for cname in ("c8", "c9"):
            d = res0["results"]["contexts"][cname]
            st = d["contrasts"]["net-blind"]["all"]["skill"]
            bound = 2.5 * (st["sd"] or 0.0) + 0.005
            sn, stt = d["arms"]["net"]["skill"], d["arms"]["transfer"]["skill"]
            ok = st["mean"] is not None and st["mean"] <= bound and sn is not None and stt is not None and sn - stt >= -0.05
            check(f"5 null {cname}: no gain over blind beyond noise, no loss > 0.05 against the transfer", ok,
                  f"net-blind {fmt(st['mean'])} <= {bound:.4f}; skill net {fmt(sn, '.3f')}, transfer {fmt(stt, '.3f')}, "
                  f"blind {fmt(d['arms']['blind']['skill'], '.3f')}")

        # 6. determinism on CPU
        threads = torch.get_num_threads()
        torch.set_num_threads(1)
        runs = []
        args_d = parse(SMALL + REL + E_DESIGN + ["--data", str(tmp / "rel"), "--out", str(tmp / "unused"), "--seed", "3"])
        for _ in range(2):
            phd = RP.RelPhase(pool, design_e["train_rows"], opts, "cpu", quiet, rel=RN.settings_from_args(args_d))
            mdl, _, _, _ = RN.fit_rel(phd, RN.rel_config(args_d, pool, phd), T.train_config(args_d), steps=40, val=None,
                                      log=quiet, lam=RN.lambdas(args_d))
            runs.append(T.predict(phd, mdl, phd.spec_rows(design_e["test_rows"][c8]))[0])
        check("6 determinism on CPU", np.array_equal(runs[0], runs[1], equal_nan=True),
              "two rel0 trainings from seed 3, one thread, give bit-identical predictions")

        # 7. parity with train.py for --arch r1
        base = SMALL + E_DESIGN + ["--data", str(tmp / "rel"), "--steps", "300", "--eval-every", "250", "--patience", "8"]
        a_tr = T.build_parser().parse_args(base + ["--out", str(tmp / "p_train")])
        a_rl = parse(base + ["--out", str(tmp / "p_rel"), "--arch", "r1", "--no-eval-step0"])
        da, db = T.make_design(pool, a_tr, quiet), T.make_design(pool, a_rl, quiet)
        design_same = all(np.array_equal(da[k], db[k]) for k in ("test_targets", "train_rows", "hidden_targets")) \
            and all(np.array_equal(da["test_rows"][c], db["test_rows"][c]) for c in da["test_rows"]) \
            and np.array_equal(da["val"]["val_rows"], db["val"]["val_rows"]) and da["swap"] == db["swap"]
        r_tr = T.run_design(a_tr, pool=pool, log=quiet)
        r_rl = TR.run(a_rl, pool=pool, log=quiet)
        restored = RN.installed_is_original()
        preds_same = True
        for cname in ("c8", "c9"):
            with np.load(tmp / "p_train" / f"pred_{cname}.npz") as za, np.load(tmp / "p_rel" / f"pred_{cname}.npz") as zb:
                preds_same &= all(np.array_equal(za[k], zb[k], equal_nan=True) for k in ("net", "blind", "swap",
                                                                                          "transfer", "partners"))
        metrics_same = (tmp / "p_train" / "metrics.json").read_text() == (tmp / "p_rel" / "metrics.json").read_text()
        hist_same = (tmp / "p_train" / "history.csv").read_text() == (tmp / "p_rel" / "history.csv").read_text()
        sa, sb = r_tr["model"].state_dict(), r_rl["model"].state_dict()
        weights_same = set(sa) == set(sb) and all(torch.equal(sa[k], sb[k]) for k in sa)
        tt_same = (tmp / "p_train" / "test_targets.txt").read_text() == (tmp / "p_rel" / "test_targets.txt").read_text()
        torch.set_num_threads(threads)
        check("7 parity with train.py (--arch r1 --eval-every 250 --no-eval-step0)",
              design_same and preds_same and metrics_same and hist_same and weights_same and tt_same and restored,
              f"design {design_same}, test targets {tt_same}, predictions {preds_same}, metrics.json {metrics_same}, "
              f"history {hist_same}, final weights {weights_same} (best step {r_tr['config']['validation']['best_step']}, "
              f"refit {r_tr['config']['final_steps']} steps); train.py's names restored {restored}")
    n_fail = results.count(False)
    if n_fail:
        print("\n".join(quiet.lines[-60:]))
    print(f"selftest_rel: {len(results) - n_fail} passed, {n_fail} failed ({time.time() - t_start:.0f} s)", flush=True)
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
