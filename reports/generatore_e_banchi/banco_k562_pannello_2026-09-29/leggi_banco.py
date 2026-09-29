"""Read the K562 panel bench (stage 73, three generator seeds) by the rule registered in RISULTATI.md.

The protocol and the rule were fixed at 18:10 on 29 September 2026, before this code; this file
implements them and says, where the text leaves a choice, which reading it takes (marked READING).

Inputs: the job folder (``bench.json`` and one ``per_pert_<arm>@s<S>.csv`` per arm and seed, long
format: perturbation, metric, value). Drive for desktop shows ':' in a file name as a space, so the
file of ``g0:t22_a1.0@s1`` may be ``per_pert_g0 t22_a1.0@s1.csv``; both spellings are read, and two
files for one arm are refused.

Per contrast X - Y, seed by seed: per-target raw differences for each member (pds, nmae, fidelity,
reach, jaccard), their NaN-aware mean over targets, and the mean of members on two scales, each
difference divided by (replicate - baseline) of that member: the official anchors
(reports/gara/anchors_2026-09-17/anchors.json) and the bench's own. The MSE member counts 0, as in
every submission (it is clipped), so the mean of members is the sum over five members divided by 6.
nMAE's anchors run downwards, so a worse (higher) nMAE lowers the mean. The estimate is the mean over
seeds; the 95% interval is a paired bootstrap over targets, 2,000 draws, the same draw for every seed
and member (READING: targets missing for a member in a draw are skipped, as in the NaN-aware mean);
beside it, the standard deviation between seeds (ddof 1).

Validity checks and rule (RISULTATI.md):
* V1, t23 as it is: on C2 - C1, pds up with the interval above 0; raw nMAE up and reach down, each
  with that sign in at least 2 seeds of 3. Failing, the outcome is "the bench contradicts the
  official" when an interval of one of those three members lies wholly on the side opposite the
  official sign (READING: any of the three, pds below 0, nMAE below 0, reach above 0), and
  "inconclusive by resolution" otherwise.
* V2, beyond amplitude: on C2 - C3, pds or reach with an interval excluding 0.
* V3, amplitude: on C1 - A1, the mean of members (official anchors) above 0 with its interval above 0.
* V4, t26 as it is: on T26 - C1, no member whose raw interval lies wholly beyond 0.005 from 0
  (READING: the five members of the mean; MSE is reported, not judged). ``identical_to_C1`` says
  whether T26 scored exactly as C1 in every seed: on the build of 29/09 its effects equal C1's on the
  bench's genes (all above 5 CPM in K562), so V4 and P4 then pass by construction, and P4_note says so.
* A candidate among E1, E2 (admitted when V1 and V2 pass) and A2, RB (admitted when V3 passes; RB
  only if it was built) passes when its mean of members (official anchors) minus C1 is above 0 with
  the interval above 0, above 0 in every seed, and more than twice the seed SD. The largest passing
  estimate wins; if the interval of the difference between the first two contains 0, the simpler of
  those two wins, in the order E1, E2, A2, RB (READING: RB after A2).
* V4 failing is written beside every choice. G1 and D1 are descriptive.

Writes, to new files: ``contrasti.csv`` (one row per contrast), ``esito.json`` (checks, readings of
P1-P5, candidates, winner) and ``bench_media_semi.json`` (each arm's raw members averaged over seeds,
under ``results.<arm>.raw``, the shape stage 84 reads).

    scripts/py.cmd reports/generatore_e_banchi/banco_k562_pannello_2026-09-29/leggi_banco.py ^
        --job-dir reports/generatore_e_banchi/banco_k562_pannello_2026-09-29/r1 ^
        --manifest reports/generatore_e_banchi/banco_k562_pannello_2026-09-29/r1/manifest.json
"""
from __future__ import annotations

import argparse
import json
import os
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ANCHORS = REPO / "reports/gara/anchors_2026-09-17/anchors.json"

MEMBERS = ["pds_cosine", "de_wilcoxon_lfc_nmae", "de_wilcoxon_direction_fidelity_yield_raw",
           "de_wilcoxon_direction_reach_raw", "de_wilcoxon_sig_jaccard"]
MSE = "expr_mse_unbiased_capped_norm"
SHORT = {"pds_cosine": "pds", "de_wilcoxon_lfc_nmae": "nmae", "de_wilcoxon_direction_fidelity_yield_raw": "fid",
         "de_wilcoxon_direction_reach_raw": "reach", "de_wilcoxon_sig_jaccard": "jac"}
N_MEMBERS = 6                       # the MSE member adds 0
ARMS = {"C1": "g0:t22_a1.0", "C2": "g0:t23_a1.0", "C3": "g0:t22s_a1.0", "T26": "g0:gate_a1.0",
        "E1": "g0:excl_a1.0", "E2": "g0:exclrs_a1.0", "A1": "g0:t22h_a1.0", "A2": "g0:t22d_a1.0",
        "RB": "g0:rb_a1.0", "G1": "g0d:t22_a1.0", "D1": "g0:t22r9_a1.0"}
SIMPLICITY = ["E1", "E2", "A2", "RB"]
V4_BAND = 0.005
N_BOOT = 2000
BOOT_SEED = 20260929


# --- inputs ------------------------------------------------------------------------------------------

def per_pert_file(names: set[str], key: str) -> str:
    """The file name of arm ``key`` among ``names``: ':' as written on Colab, or as Drive shows it."""
    spellings = {key.replace(":", c) for c in (":", " ", "_", "")}
    found = sorted(f"per_pert_{s}.csv" for s in spellings if f"per_pert_{s}.csv" in names)
    if not found:
        raise SystemExit(f"no per_pert file for {key!r}")
    if len(found) > 1:
        raise SystemExit(f"{key!r}: several files could be it, {found}; refusing to guess")
    return found[0]


def read_per_target(job: Path, key: str, names: set[str]) -> pd.DataFrame:
    frame = pd.read_csv(job / per_pert_file(names, key))
    return frame.pivot_table(index="perturbation", columns="metric", values="value", aggfunc="first", dropna=False)


def official_scales(path: Path) -> dict:
    anchors = json.loads(path.read_text(encoding="utf-8"))["anchors"]
    return {m: anchors[m]["replicate"] - anchors[m]["baseline"] for m in MEMBERS}


def local_scales(results: dict) -> dict:
    r, b = results["replicate"]["raw"], results["baseline"]["raw"]
    return {m: r[m] - b[m] for m in MEMBERS}


def seeds_in(results: dict, arm: str) -> list[int]:
    return sorted(int(k.rsplit("@s", 1)[1]) for k in results if k.rsplit("@s", 1)[0] == arm and "@s" in k)


# --- contrasts ---------------------------------------------------------------------------------------

class Tables:
    """Per-target raw members of every arm and seed, on one target index."""

    def __init__(self, job: Path, results: dict, arms: list[str], seeds: list[int]):
        names = set(os.listdir(job))
        self.seeds, self.results = seeds, results
        frames = {(a, s): read_per_target(job, f"{a}@s{s}", names) for a in arms for s in seeds}
        self.targets = sorted(set().union(*(f.index for f in frames.values())))
        self.values = {}
        for key, f in frames.items():
            f = f.reindex(self.targets)
            self.values[key] = np.stack([f[m].to_numpy(dtype=np.float64) if m in f else np.full(len(self.targets), np.nan)
                                         for m in MEMBERS])            # (members, targets)
        self.check = {}
        for (a, s), f in frames.items():
            reported = results[f"{a}@s{s}"]["raw"]
            diffs = [abs(float(np.nanmean(f[m])) - float(reported[m])) for m in MEMBERS
                     if m in f and reported.get(m) is not None and np.isfinite(np.nanmean(f[m]))]
            self.check[f"{a}@s{s}"] = max(diffs) if diffs else None

    def diff(self, x: str, y: str) -> np.ndarray:
        """(seeds, members, targets) raw X - Y."""
        return np.stack([self.values[(x, s)] - self.values[(y, s)] for s in self.seeds])

    def mse_diff(self, x: str, y: str) -> list:
        """X - Y of the MSE member's aggregate (bench.json), seed by seed: the per-target files hold
        ``expr_mse_unbiased_capped``, not the normalised aggregate, and the mean counts MSE as 0."""
        out = []
        for s in self.seeds:
            a, b = self.results[f"{x}@s{s}"]["raw"].get(MSE), self.results[f"{y}@s{s}"]["raw"].get(MSE)
            out.append(None if a is None or b is None else float(a - b))
        return out


def nanmean(a: np.ndarray, axis: int) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return np.nanmean(a, axis=axis)


def contrast(d: np.ndarray, off: dict, loc: dict, idx: np.ndarray) -> dict:
    """Estimates, seed values, seed SD and bootstrap intervals of one contrast ``d`` (seeds, members, targets)."""
    per_seed = nanmean(d, axis=2)                                  # (seeds, members), raw
    w_off = np.array([1.0 / off[m] for m in MEMBERS]) / N_MEMBERS
    w_loc = np.array([1.0 / loc[m] for m in MEMBERS]) / N_MEMBERS
    boot = nanmean(d[:, :, idx], axis=3).mean(axis=0)                # (members, draws): same draw for all seeds
    boot_off, boot_loc = (w_off[:, None] * boot).sum(axis=0), (w_loc[:, None] * boot).sum(axis=0)

    def ci(v):
        ok = np.isfinite(v)
        return [float(np.quantile(v[ok], 0.025)), float(np.quantile(v[ok], 0.975))] if ok.any() else [None, None]

    seed_off, seed_loc = per_seed @ w_off, per_seed @ w_loc
    sd = lambda v: float(np.std(v, ddof=1)) if len(v) > 1 else None  # noqa: E731
    out = {"targets": int(d.shape[2]), "seeds": d.shape[0], "bootstrap_draws": int(idx.shape[0]),
           "members": {}, "mean_official": float(seed_off.mean()), "mean_official_ci95": ci(boot_off),
           "mean_official_by_seed": seed_off.tolist(), "mean_official_seed_sd": sd(seed_off),
           "mean_local": float(seed_loc.mean()), "mean_local_ci95": ci(boot_loc),
           "mean_local_by_seed": seed_loc.tolist(), "mean_local_seed_sd": sd(seed_loc)}
    for j, m in enumerate(MEMBERS):
        out["members"][SHORT[m]] = {
            "raw": float(per_seed[:, j].mean()), "raw_ci95": ci(boot[j]), "raw_by_seed": per_seed[:, j].tolist(),
            "raw_seed_sd": sd(per_seed[:, j]), "official": float(per_seed[:, j].mean() / off[m]),
            "official_ci95": sorted(v / off[m] for v in ci(boot[j])) if None not in ci(boot[j]) else [None, None],
            "targets_with_value": int(np.isfinite(d[:, j, :]).any(axis=0).sum())}
    return out


# --- rule --------------------------------------------------------------------------------------------

def above(ci) -> bool:
    return ci[0] is not None and ci[0] > 0


def below(ci) -> bool:
    return ci[1] is not None and ci[1] < 0


def excludes_zero(ci) -> bool:
    return above(ci) or below(ci)


def v1(c: dict) -> dict:
    mem = c["members"]
    pds_ok = above(mem["pds"]["raw_ci95"])
    nmae_up = sum(v > 0 for v in mem["nmae"]["raw_by_seed"])
    reach_down = sum(v < 0 for v in mem["reach"]["raw_by_seed"])
    passed = bool(pds_ok and nmae_up >= 2 and reach_down >= 2)
    wrong = {"pds_interval_below_0": below(mem["pds"]["raw_ci95"]),
             "nmae_interval_below_0": below(mem["nmae"]["raw_ci95"]),
             "reach_interval_above_0": above(mem["reach"]["raw_ci95"])}
    outcome = "passa" if passed else ("il banco contraddice l'ufficiale" if any(wrong.values())
                                      else "non conclusivo per risoluzione")
    return {"passed": passed, "outcome": outcome, "pds_interval_above_0": pds_ok,
            "seeds_nmae_up": nmae_up, "seeds_reach_down": reach_down, "wrong_side": wrong}


def v2(c: dict) -> dict:
    pds, reach = excludes_zero(c["members"]["pds"]["raw_ci95"]), excludes_zero(c["members"]["reach"]["raw_ci95"])
    return {"passed": bool(pds or reach), "pds_interval_excludes_0": pds, "reach_interval_excludes_0": reach}


def v3(c: dict) -> dict:
    return {"passed": bool(c["mean_official"] > 0 and above(c["mean_official_ci95"])),
            "mean_official": c["mean_official"], "ci95": c["mean_official_ci95"]}


def v4(c: dict) -> dict:
    beyond = {m: bool((v["raw_ci95"][0] is not None and v["raw_ci95"][0] > V4_BAND)
                      or (v["raw_ci95"][1] is not None and v["raw_ci95"][1] < -V4_BAND))
              for m, v in c["members"].items()}
    return {"passed": not any(beyond.values()), "members_beyond_0.005": beyond}


def passes(c: dict) -> dict:
    by_seed = c["mean_official_by_seed"]
    sd = c["mean_official_seed_sd"]
    checks = {"positive_with_interval_above_0": bool(c["mean_official"] > 0 and above(c["mean_official_ci95"])),
              "positive_in_every_seed": bool(all(v > 0 for v in by_seed)),
              "above_twice_seed_sd": bool(sd is not None and c["mean_official"] > 2 * sd)}
    return {"passed": all(checks.values()), **checks}


def prediction(c: dict, member: str, sign: int) -> str:
    """READING of a registered prediction on one member: its interval on the predicted side confirms it,
    on the other side contradicts it, across 0 leaves it unresolved."""
    ci = c["members"][member]["raw_ci95"]
    if (above(ci) and sign > 0) or (below(ci) and sign < 0):
        return "confermata"
    if excludes_zero(ci):
        return "contraddetta"
    return "non risolta"


def decide(contrasts: dict, tables: Tables, off: dict, loc: dict, idx: np.ndarray, present: set, manifest: dict | None) -> dict:
    checks = {"V1": v1(contrasts["C2 - C1"]), "V2": v2(contrasts["C2 - C3"]), "V3": v3(contrasts["C1 - A1"]),
              "V4": v4(contrasts["T26 - C1"])}
    # Measured on the build of 29/09: every gene K562's cells measure is above 5 CPM, so T26's effects equal
    # C1's on the bench's genes and, with the same generator seeds, its scores too. Say so instead of
    # letting V4 and P4 read as measured.
    checks["V4"]["identical_to_C1"] = bool(all(
        np.array_equal(tables.values[(ARMS["T26"], s)], tables.values[(ARMS["C1"], s)], equal_nan=True)
        for s in tables.seeds))
    admit_e = checks["V1"]["passed"] and checks["V2"]["passed"]
    admit_a = checks["V3"]["passed"]
    candidates = {}
    for role in SIMPLICITY:
        if role not in present:
            candidates[role] = {"built": False}
            continue
        admitted = admit_e if role.startswith("E") else admit_a
        c = contrasts[f"{role} - C1"]
        candidates[role] = {"built": True, "admitted": admitted,
                            "admitted_by": "V1 and V2" if role.startswith("E") else "V3",
                            "mean_official": c["mean_official"], "ci95": c["mean_official_ci95"],
                            "by_seed": c["mean_official_by_seed"], "seed_sd": c["mean_official_seed_sd"],
                            **{k: v for k, v in passes(c).items()}}
        candidates[role]["passes_rule"] = bool(admitted and candidates[role]["passed"])
    winners = sorted((r for r, v in candidates.items() if v.get("passes_rule")),
                     key=lambda r: -candidates[r]["mean_official"])
    choice = {"passing": winners, "winner": None, "why": "nessun braccio passa: il prossimo invio non si sceglie su questo banco"}
    if len(winners) == 1:
        choice.update(winner=winners[0], why="il solo braccio che passa")
    elif len(winners) > 1:
        a, b = winners[:2]
        top = contrast(tables.diff(ARMS[a], ARMS[b]), off, loc, idx)
        contrasts[f"{a} - {b}"] = top
        if excludes_zero(top["mean_official_ci95"]):
            choice.update(winner=a, why=f"il Δ più grande, e l'intervallo di {a} - {b} esclude lo zero")
        else:
            simpler = min((a, b), key=SIMPLICITY.index)
            choice.update(winner=simpler, why=f"l'intervallo di {a} - {b} comprende lo zero: vince il più semplice")
        choice["top_two_contrast"] = {"contrast": f"{a} - {b}", "mean_official": top["mean_official"],
                                      "ci95": top["mean_official_ci95"]}
    if not checks["V4"]["passed"]:
        choice["v4_note"] = "V4 non passa: il banco vede nel t26 un effetto che l'ufficiale non ha visto (da dire accanto a ogni scelta)"
    if not admit_a:
        choice["amplitude_note"] = "V3 non passa: nessuna scelta d'ampiezza dal banco"
    if not admit_e:
        choice["exclusion_note"] = f"V1 {checks['V1']['outcome']}; V2 {'passa' if checks['V2']['passed'] else 'non passa'}: i bracci E si leggono solo in modo descrittivo"
    p = {"P1": prediction(contrasts["C2 - C1"], "pds", +1),
         "P2": {"nmae": prediction(contrasts["C3 - C1"], "nmae", +1), "reach": prediction(contrasts["C3 - C1"], "reach", +1)},
         "P3": {"reach": prediction(contrasts["E1 - C1"], "reach", -1), "jac": prediction(contrasts["E1 - C1"], "jac", -1)},
         "P4": "confermata" if not any(excludes_zero(v["raw_ci95"]) for v in contrasts["T26 - C1"]["members"].values())
               else "contraddetta"}
    if checks["V4"]["identical_to_C1"]:
        p["P4_note"] = ("T26 e C1 hanno gli stessi valori per bersaglio in ogni seme: V4 e P4 passano per costruzione "
                        "(la soglia a 5 CPM di K562 non tocca geni misurati dal banco), non per misura")
    if manifest is not None:
        s = manifest["amplitude_rules"]["value"]
        p["P5"] = {"R-B": s, "reading": "confermata" if 2.84 <= s <= 3.47 else "contraddetta"}
    return {"checks": checks, "candidates": candidates, "choice": choice, "predictions": p}


def seed_means(results: dict, arms: list[str], seeds: list[int]) -> dict:
    out = {}
    for a in arms:
        raw = {}
        for m in [*MEMBERS, MSE]:
            vals = [results[f"{a}@s{s}"]["raw"].get(m) for s in seeds]
            vals = [v for v in vals if v is not None]
            raw[m] = float(np.mean(vals)) if vals else None
        out[a] = {"raw": raw, "seeds": seeds, "raw_by_seed": {s: results[f"{a}@s{s}"]["raw"] for s in seeds}}
    for anchor in ("replicate", "baseline"):
        out[anchor] = {"raw": results[anchor]["raw"]}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--job-dir", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, default=None, help="default: --job-dir")
    ap.add_argument("--manifest", type=Path, default=None, help="build_arms.py's manifest.json (R-B for P5)")
    ap.add_argument("--anchors", type=Path, default=ANCHORS)
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    args = ap.parse_args()
    out = args.out_dir or args.job_dir
    targets_out = [out / "contrasti.csv", out / "esito.json", out / "bench_media_semi.json"]
    taken = [p.name for p in targets_out if p.exists()]
    if taken:
        raise SystemExit(f"{out} already holds {taken}; a reading goes to a new --out-dir")
    bench = json.loads((args.job_dir / "bench.json").read_text(encoding="utf-8"))
    results = bench["results"]
    present = {role for role, arm in ARMS.items() if seeds_in(results, arm)}
    need = {"C1", "C2", "C3", "T26", "E1", "E2", "A1", "A2"}
    if need - present:
        raise SystemExit(f"bench.json lacks arms {sorted(need - present)}")
    seeds = seeds_in(results, ARMS["C1"])
    for role in present:
        if seeds_in(results, ARMS[role]) != seeds:
            raise SystemExit(f"{ARMS[role]} was scored with seeds {seeds_in(results, ARMS[role])}, C1 with {seeds}")
    arms = [ARMS[r] for r in ARMS if r in present]
    tables = Tables(args.job_dir, results, arms, seeds)
    off, loc = official_scales(args.anchors), local_scales(results)
    idx = np.random.default_rng(BOOT_SEED).integers(0, len(tables.targets), size=(args.n_boot, len(tables.targets)))
    contrasts = {}
    for role in [r for r in ARMS if r in present and r != "C1"]:
        contrasts[f"{role} - C1"] = contrast(tables.diff(ARMS[role], ARMS["C1"]), off, loc, idx)
    contrasts["C2 - C3"] = contrast(tables.diff(ARMS["C2"], ARMS["C3"]), off, loc, idx)
    contrasts["C1 - A1"] = contrast(tables.diff(ARMS["C1"], ARMS["A1"]), off, loc, idx)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8")) if args.manifest else None
    verdict = decide(contrasts, tables, off, loc, idx, present, manifest)
    for name, c in contrasts.items():
        x, y = name.split(" - ")
        c["mse_norm_aggregate_by_seed"] = tables.mse_diff(ARMS[x], ARMS[y])

    rows = []
    for name, c in contrasts.items():
        row = {"contrast": name, "targets": c["targets"], "seeds": c["seeds"], "mean_official": c["mean_official"],
               "mean_official_ci95": c["mean_official_ci95"], "mean_official_seed_sd": c["mean_official_seed_sd"],
               "mean_official_by_seed": c["mean_official_by_seed"], "mean_local": c["mean_local"],
               "mean_local_ci95": c["mean_local_ci95"], "mean_local_seed_sd": c["mean_local_seed_sd"]}
        for m, v in c["members"].items():
            row.update({f"{m}_raw": v["raw"], f"{m}_raw_ci95": v["raw_ci95"], f"{m}_raw_by_seed": v["raw_by_seed"],
                        f"{m}_official": v["official"], f"{m}_targets": v["targets_with_value"]})
        row["mse_norm_aggregate_by_seed"] = c["mse_norm_aggregate_by_seed"]
        rows.append(row)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "contrasti.csv", "x", encoding="utf-8", newline="") as fh:
        pd.DataFrame(rows).to_csv(fh, index=False, lineterminator="\n")
    check = [v for v in tables.check.values() if v is not None]
    esito = {"script": "reports/generatore_e_banchi/banco_k562_pannello_2026-09-29/leggi_banco.py",
             "written_utc": datetime.now(timezone.utc).isoformat(), "job_dir": str(args.job_dir),
             "protocol": "RISULTATI.md, fixed at 18:10 on 29/09 before the code", "arms": {r: ARMS[r] for r in ARMS if r in present},
             "seeds": seeds, "targets": len(tables.targets), "bootstrap": {"draws": args.n_boot, "seed": BOOT_SEED},
             "anchors": {"official": str(args.anchors), "official_spans": off, "local_spans": loc},
             "aggregate_check_max_abs": max(check) if check else None, "aggregate_check": tables.check,
             **verdict, "contrasts": contrasts,
             "descriptive_only": ["G1 - C1", "D1 - C1"],
             "not_a_vcc_score": "local truth (K562, half A of each target), our generator and scorer; the official "
                                "anchors only weight differences, they are never applied to levels"}
    with open(out / "esito.json", "x", encoding="utf-8", newline="\n") as fh:
        json.dump(esito, fh, indent=2, ensure_ascii=False, default=float)
    media = {"script": esito["script"], "written_utc": esito["written_utc"], "job_dir": str(args.job_dir),
             "what": "each arm's raw members from bench.json, averaged over the generator seeds (stage 84 reads "
                     "results.<arm>.raw); replicate and baseline as scored once",
             "results": seed_means(results, arms, seeds)}
    with open(out / "bench_media_semi.json", "x", encoding="utf-8", newline="\n") as fh:
        json.dump(media, fh, indent=2, default=float)
    print(f"aggregate check: max |mean of per-target - reported| = {esito['aggregate_check_max_abs']}")
    fmt = lambda v: "NA" if v is None or not np.isfinite(v) else f"{v:+.4f}"  # noqa: E731
    for name, c in contrasts.items():
        lo, hi = c["mean_official_ci95"]
        print(f"{name:10s} mean (official) {fmt(c['mean_official'])} ({fmt(lo)}..{fmt(hi)}) seed sd "
              f"{fmt(c['mean_official_seed_sd'])}  " + " ".join(f"{m}={fmt(v['raw'])}" for m, v in c["members"].items()))
    print(json.dumps({k: verdict[k] for k in ("checks", "choice", "predictions")}, indent=1, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()
