"""Bench v2: effects in, paired multi-seed scores out. Independent of how the effects were produced.

Why (CP-0065): the one-seed bench with about 32 predicted cells per target had a noise on a paired gain of 0.007-0.045
per line, as large as the gains it was used to decide on; and its generator drew every block of an arm from one random
stream, so two arms differing on one target drew different noise on every later target.

What changes against hybrid_lanes.py laneB / diag_lanes.py (same scorer, same truth, same local scale):
- any number of arms, each a stage-100 style npz (targets, genes, lfc in ln, observed) on the line's targets;
- `--n-pred` predicted cells per target (default 400, the submission's), not half of the real cells;
- `--gen-seeds K` generator seeds (default 5); every arm is scored once per seed;
- one random stream per (seed, target), derived from the target's name: two arms draw the same random numbers on a
  target, so an unchanged target gives the same cells in both arms (common random numbers) and the order of the
  targets does not matter;
- `--emission t25` (Poisson around the pooled profile, effects x 1) or `--emission t28` (effects x 1.5 and the
  per-gene Gamma-Poisson dispersion of stage 45's --gene-dispersion, fitted once on the control pool);
- `--pair A:B` declares the paired differences to report: per seed, avg(A) - avg(B), then mean, standard deviation
  (n - 1) and whether it is resolved (|mean| > 2 sd / sqrt(K)), on the six members, on the five without JAC and on
  each member; raw members and the scale's denominators are kept in bench.json.
The truth half, the replicate, the baseline and the control pool stay on `--seed` (the bench seed), as before.

Parity: an arm named twice under two names gives identical cells at every seed; `--check-identical A:B` makes the run
fail if it does not. Writes bench/ (scaled_local.csv, bench.json, per_pert_*.csv), paired.json, run.json.
Not VCC scores: local anchors on a half-depth truth; compare arms, not leaderboards.

    py bench_v2.py --real <real_cells.npz> --targets <targets.json> --arm base=<a.npz> --arm cand=<b.npz> \
        --pair cand:base --out <new dir> [--n-pred 400] [--gen-seeds 5] [--emission t25|t28] [--seed 2026]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zlib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy.sparse as sp

MEMBERS = {"PDS": "pds_cosine", "MSE": "expr_mse_unbiased_capped_norm", "NMAE": "de_wilcoxon_lfc_nmae",
           "FID": "de_wilcoxon_direction_fidelity_yield_raw", "REACH": "de_wilcoxon_direction_reach_raw",
           "JAC": "de_wilcoxon_sig_jaccard"}
NO_JAC = [m for m in MEMBERS if m != "JAC"]
EMISSIONS = {"t25": {"scale": 1.0, "gene_dispersion": False}, "t28": {"scale": 1.5, "gene_dispersion": True}}
GEN_SEED = 20260912
F32 = np.float32


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(8 << 20), b""):
            h.update(b)
    return h.hexdigest()


def block_rng(gen_seed: int, k: int, target: str) -> np.random.Generator:
    """The stream of one (seed, target) block: the same for every arm, whatever the order of the targets."""
    return np.random.default_rng([gen_seed, k, zlib.crc32(target.encode("utf-8"))])


def load_arm(path: Path, labels: list, genes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(lfc [targets, genes] float32 with 0 off the mask, observed bool) of an npz on the bench's targets and genes;
    a target or gene the file lacks is unobserved."""
    with np.load(path, allow_pickle=False) as z:
        t_pos = {str(t): i for i, t in enumerate(z["targets"])}
        g_pos = {str(g): i for i, g in enumerate(z["genes"])}
        lfc_in, obs_in = z["lfc"], z["observed"]
    gi = np.array([g_pos.get(str(g), -1) for g in genes], np.int64)
    lfc = np.zeros((len(labels), genes.size), F32)
    obs = np.zeros((len(labels), genes.size), bool)
    for i, t in enumerate(labels):
        j = t_pos.get(t)
        if j is None:
            continue
        row, mask = lfc_in[j], obs_in[j]
        ok = gi >= 0
        o = np.zeros(genes.size, bool)
        o[ok] = mask[gi[ok]] & np.isfinite(row[gi[ok]])
        v = np.zeros(genes.size, F32)
        v[ok] = np.nan_to_num(row[gi[ok]], nan=0.0)
        lfc[i], obs[i] = np.where(o, v, 0.0), o
    return lfc, obs


def stats(v) -> dict:
    v = np.asarray(v, float)
    sd = float(v.std(ddof=1)) if v.size > 1 else float("nan")
    return {"mean": float(v.mean()), "sd": sd, "values": [float(x) for x in v],
            "resolved": bool(abs(v.mean()) > 2 * sd / np.sqrt(v.size)) if v.size > 1 else False}


def paired(results: dict, pairs: list, seeds: int) -> dict:
    """Per declared pair, the per-seed differences of the scaled members and of their means."""
    def member(arm, k, m):
        return float(results[f"{arm}@s{k}"]["scaled_local"][MEMBERS[m]])

    out = {}
    for a, b in pairs:
        d = {m: np.array([member(a, k, m) - member(b, k, m) for k in range(seeds)]) for m in MEMBERS}
        out[f"{a}:{b}"] = {"six": stats(np.mean([d[m] for m in MEMBERS], axis=0)),
                           "without_JAC": stats(np.mean([d[m] for m in NO_JAC], axis=0)),
                           "members": {m: stats(d[m]) for m in MEMBERS},
                           "raw_members": {m: stats([results[f"{a}@s{k}"]["raw"][MEMBERS[m]]
                                                     - results[f"{b}@s{k}"]["raw"][MEMBERS[m]] for k in range(seeds)])
                                           for m in MEMBERS}}
    return out


def generate(basal, lfc, obs, libs, labels, n_pred, gen_seed, k, ch, phi):
    from vcc2026.inference import trial01_cells
    blocks = []
    for i, t in enumerate(labels):
        cells, _ = trial01_cells(basal, lfc[i], obs[i], libs, n_pred, block_rng(gen_seed, k, t),
                                 max_stored_per_cell=ch.max_stored_per_cell,
                                 max_counts_per_cell=ch.max_counts_per_cell, overdispersion=phi)
        blocks.append(cells)
    return sp.vstack(blocks).tocsr()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--real", type=Path, required=True)
    p.add_argument("--targets", type=Path, required=True)
    p.add_argument("--arm", action="append", required=True, metavar="NAME=NPZ")
    p.add_argument("--pair", action="append", default=[], metavar="A:B")
    p.add_argument("--check-identical", action="append", default=[], metavar="A:B")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--n-pred", type=int, default=400)
    p.add_argument("--gen-seeds", type=int, default=5)
    p.add_argument("--gen-seed", type=int, default=GEN_SEED)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--emission", choices=sorted(EMISSIONS), default="t25")
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    arms = dict(x.split("=", 1) for x in a.arm)
    if len(arms) != len(a.arm):
        raise SystemExit("an arm name is given twice")
    pairs = [tuple(x.split(":", 1)) for x in a.pair]
    same = [tuple(x.split(":", 1)) for x in a.check_identical]
    for x, y in pairs + same:
        if x not in arms or y not in arms:
            raise SystemExit(f"pair {x}:{y} names an arm that is not given")
    from vcc2026.bench import Bench
    from vcc2026.config import challenge
    from vcc2026.sampling import fit_gene_dispersion
    z = np.load(a.real, allow_pickle=False)
    x = sp.csr_matrix((z["data"], z["indices"], z["indptr"]), shape=tuple(z["shape"]))
    lab, genes = z["labels"].astype(str), z["genes"].astype(str)
    targets = [t for t in json.loads(a.targets.read_text(encoding="utf-8")) if (lab == t["symbol"]).sum() >= 4]
    labels = [t["symbol"] for t in targets]
    ctrl_rows = np.flatnonzero(lab == "non-targeting")
    a.out.mkdir(parents=True)
    bench = Bench(x, {t: np.flatnonzero(lab == t) for t in labels}, ctrl_rows, genes, a.out / "bench", seed=a.seed)
    bench.anchors()
    ctrl = x[ctrl_rows]
    basal = np.asarray(ctrl.sum(0), dtype=np.float64).ravel()
    libs = np.asarray(ctrl.sum(1)).ravel().astype(np.int64)
    em = EMISSIONS[a.emission]
    phi = None
    if em["gene_dispersion"]:
        detected = np.bincount(ctrl.indices[ctrl.data > 0], minlength=ctrl.shape[1])
        phi = fit_gene_dispersion(basal, libs, 1.0 - detected / ctrl.shape[0], seed=a.seed)
    ch = challenge()
    effects = {name: load_arm(Path(path), labels, genes) for name, path in arms.items()}
    pred_labels = np.concatenate([np.full(a.n_pred, t) for t in labels])
    identical = {}
    for k in range(a.gen_seeds):
        kept = {}
        for name, (lfc, obs) in effects.items():
            mat = generate(basal, lfc * F32(em["scale"]), obs, libs, labels, a.n_pred, a.gen_seed, k, ch, phi)
            if any(name in pr for pr in same):
                kept[name] = mat
            bench.score(f"{name}@s{k}", mat, pred_labels, {"observed_share": float(obs.mean()), "seed_index": k})
        for u, v in same:
            identical[f"{u}:{v}@s{k}"] = bool((kept[u] != kept[v]).nnz == 0)
    bench.finish(dict(stage="bench v2", targets=labels, genes=int(genes.size), real=str(a.real),
                      real_sha256=sha(a.real), seed=a.seed, gen_seed=a.gen_seed, gen_seeds=a.gen_seeds,
                      n_pred=a.n_pred, emission={"name": a.emission, **em,
                                                 "phi_median": float(np.median(phi)) if phi is not None else None},
                      arms={n: {"path": str(pth), "sha256": sha(Path(pth))} for n, pth in arms.items()},
                      generator="trial-01 path, one stream per (seed, target) shared by every arm",
                      identical=identical))
    out = {"written_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "n_pred": a.n_pred,
           "gen_seeds": a.gen_seeds, "emission": a.emission, "pairs": paired(bench.results, pairs, a.gen_seeds),
           "identical": identical,
           "note": "paired differences at the same generator seed, local scale; not VCC scores"}
    (a.out / "paired.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    (a.out / "run.json").write_text(json.dumps({"arguments": {k: str(v) for k, v in vars(a).items()},
                                                "code_sha256": sha(Path(__file__))}, indent=1), encoding="utf-8")
    if not all(identical.values()):
        raise SystemExit(f"identical arms gave different cells: {identical}")
    print(json.dumps({pr: {"six": (round(v["six"]["mean"], 4), round(v["six"]["sd"], 4), v["six"]["resolved"]),
                           "PDS": (round(v["members"]["PDS"]["mean"], 4), round(v["members"]["PDS"]["sd"], 4))}
                      for pr, v in out["pairs"].items()}))


if __name__ == "__main__":
    main()
