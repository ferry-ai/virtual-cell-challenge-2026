"""Build the arms of the K562 panel bench (R-REV action 4): the effects files the Colab job scores.

The protocol, the arms and the rule are in RISULTATI.md, fixed at 18:10 on 29 September 2026 before
this code. Every arm is an unmodified stage-100 run on a recipe with the single context ``k562``;
nothing of K562 enters a source or the share (the cis prior, K562 targets outside the panel, is the
declared context leak common to every arm). In order:

1. **The share without K562.** ``share_k562.npy`` (reports/trasferimento/quota_condivisa_2026-09-27/r1/:
   universes CD4 and HCT116, panel targets excluded; float32 on the official axis) becomes
   ``quota_senza_k562.csv`` (gene, share, written with %.9g so it reads back to the same float32)
   and ``esclusione_senza_k562.csv`` (share > 0 -> 1, else 0), in ``--share-dir``. A file already
   there is reused only if it holds exactly the bytes the conversion writes; otherwise refused.
2. **Stage 100 per recipe**, as a subprocess through the rehearsal's ``misura.py`` (peak memory and
   times appended to ``<data-out>/tempi.jsonl``), into ``<data-out>/<arm>/``, with ``--targets-csv``
   the panel. The recipe run is written first to ``<data-out>/ricette_usate/<arm>.json``: the template
   of ``ricette/`` with two paths replaced when this build writes elsewhere than the templates name
   (``gene_share.path`` -> ``--share-dir``, ``match_detectable`` -> ``<data-out>/t22``); the manifest
   lists each replacement. C1 (``t22``) runs first: C2 and E2 match its detectable genes.
3. **Derived recipes**, from measured scales:
   - C3 ``t22s``: C1 at 1.576 x s(C2), s(C2) being C2's ``gene_share_scale`` (stage 100's manifest);
   - E2 ``exclrs``: E1 plus ``basal`` and ``match_detectable`` to C1: the exclusion rescaled to C1's
     median count of detectable genes on K562's control CPM, cis head included on both sides.
4. **R-B on K562's CPM** with the rehearsal's own functions (``n_det``, ``solve``, ``cis_head``,
   ``split_effects`` and ``Cpm``, imported unchanged from reports/invii/prova_generale_2026-09-28/
   diagnostica.py): the one amplitude s at which the median count of detectable genes of t22's
   official effects (today's panel, its cis head outside the scale) on K562's CPM equals the mean over
   A/B/C at 1.576 (the rehearsal measured 257.67). That is R-B as registered ("sugli effetti del t22
   del pannello di oggi"). R-C, the same with C1's own effects (no K562 source), is reported beside
   it. The arm RB (C1 at amplitude s) is built only if s is more than 10% from 3.152.
5. **Coverage** of the bench targets (panel targets with at least ``--min-cells`` cells whose gene
   the K562 cells measure: stage 73's rule, read from stage 71's groups.csv and var.csv) by the
   three sources of each cache, and by C1 (stage 100's ``targets_missing``).
6. Each ``effects_k562.npz`` is copied as ``<arm>.npz`` into ``--drive-out``; ``manifest.json``
   (arm -> sha256, recipe, scales, R-B, share hashes, coverage) is written there LAST, since the job
   waits for it, and a copy beside the arms in ``--data-out``.

Refuses a ``--data-out`` that is not empty and a ``--drive-out`` holding a manifest or an arm file.
Stage 100 peaked at about 590 MB on t22's three contexts (rehearsal, 28/09); here one context runs at
a time, one process at a time.

    scripts/py.cmd reports/generatore_e_banchi/banco_k562_pannello_2026-09-29/build_arms.py ^
        --k562-meta "G:/Il mio Drive/vcc2026/data/processed/k562_gwps_sc/x002" ^
        --data-out <data_root>/processed/banco_k562_pannello_2026-09-29 ^
        --drive-out "G:/Il mio Drive/vcc2026/data/processed/banco_k562_pannello_2026-09-29"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))

from vcc2026 import config  # noqa: E402

DATA_ROOT = config.paths().data_root
CTX = "k562"
SOURCES = ("cd4_mix", "orion_hct116", "orion_hek293t")
AMP_T22 = 1.576
AMP_A2 = 3.152
RB_TOLERANCE = 0.10                    # RB is built only if R-B is more than 10% from 3.152
SHARE_NPY = REPO / "reports/trasferimento/quota_condivisa_2026-09-27/r1/share_k562.npy"
SHARE_CSV, EXCL_CSV = "quota_senza_k562.csv", "esclusione_senza_k562.csv"
DEFAULT_SHARE_DIR = HERE / "quota"
DEFAULT_DATA_OUT = DATA_ROOT / "processed/banco_k562_pannello_2026-09-29"
DIAGNOSTICA = REPO / "reports/invii/prova_generale_2026-09-28"
MISURA = DIAGNOSTICA / "misura.py"
STAGE100 = REPO / "scripts/100_build_context_effects.py"
# (arm, bench role, template in ricette/ or None when derived here, cache key), in build order
ARMS = [("t22", "C1", "t22.json", "r5"), ("t23", "C2", "t23.json", "r5"), ("t22s", "C3", None, "r5"),
        ("gate", "T26", "gate.json", "r5"), ("excl", "E1", "excl.json", "r5"), ("exclrs", "E2", None, "r5"),
        ("t22h", "A1", "t22h.json", "r5"), ("t22d", "A2", "t22d.json", "r5"), ("t22r9", "D1", "t22r9.json", "r9")]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj, *, exclusive: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x" if exclusive else "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(obj, indent=2, ensure_ascii=False, default=str) + "\n")


# --- 1. the share ---------------------------------------------------------------------------------

def share_texts(share: np.ndarray, axis: np.ndarray) -> tuple[str, str]:
    """The two CSVs as text: the share (%.9g reads back to the same float32) and its 0/1 exclusion."""
    share = np.asarray(share)
    if share.shape != axis.shape or not np.isfinite(share).all() or (share < 0).any() or (share > 1).any():
        raise SystemExit(f"the share must hold one value in [0, 1] per gene of the {axis.size}-gene axis")
    frac = pd.DataFrame({"gene": axis, "share": share}).to_csv(index=False, float_format="%.9g", lineterminator="\n")
    excl = pd.DataFrame({"gene": axis, "share": (share > 0).astype(np.int64)}).to_csv(index=False, lineterminator="\n")
    return frac, excl


def convert_share(npy: Path, axis: np.ndarray, out_dir: Path) -> dict:
    """Write (or verify) the share CSV and its 0/1 exclusion in ``out_dir``; returns their record."""
    share = np.load(npy)
    texts = dict(zip((SHARE_CSV, EXCL_CSV), share_texts(share, axis)))
    out_dir.mkdir(parents=True, exist_ok=True)
    record = {"npy": str(npy), "npy_sha256": sha256(npy), "genes": int(share.size),
              "genes_zero": int((share == 0).sum()), "genes_one": int((share == 1).sum()),
              "median": float(np.median(share)), "files": {}}
    for name, text in texts.items():
        path = out_dir / name
        data = text.encode("utf-8")
        if path.exists():
            if path.read_bytes() != data:
                raise SystemExit(f"{path} exists and differs from the conversion of {npy}; refusing to use or replace it")
            reused = True
        else:
            with open(path, "xb") as fh:
                fh.write(data)
            reused = False
        record["files"][name] = {"path": str(path), "sha256": sha256(path), "reused": reused}
    back = pd.read_csv(out_dir / SHARE_CSV)["share"].to_numpy(dtype=np.float64)
    record["csv_reads_back_to_the_float32"] = bool(np.array_equal(back.astype(np.float32), share.astype(np.float32)))
    return record


# --- 2-3. recipes and stage 100 ----------------------------------------------------------------------

def materialise(template: dict, *, share_dir: Path, data_out: Path) -> tuple[dict, list[dict]]:
    """The recipe as run: ``template`` with its share path and its detectable reference pointed at
    this build's files when they are not where the template names them. Returns (recipe, replacements)."""
    recipe = json.loads(json.dumps(template))
    changes = []
    spec = recipe.get("gene_share")
    if spec is not None:
        named = config.repo_file(spec["path"])
        actual = share_dir / Path(spec["path"]).name
        if named.resolve() != actual.resolve():
            changes.append({"key": "gene_share.path", "template": spec["path"], "used": str(actual)})
            spec["path"] = str(actual)
        if spec.get("match_detectable"):
            named_ref = DATA_ROOT / spec["match_detectable"]
            actual_ref = data_out / Path(spec["match_detectable"]).name
            if named_ref.resolve() != actual_ref.resolve():
                changes.append({"key": "gene_share.match_detectable", "template": spec["match_detectable"],
                                "used": str(actual_ref)})
                spec["match_detectable"] = str(actual_ref)
    return recipe, changes


def derived_t22s(c1: dict, scale: float) -> dict:
    r = json.loads(json.dumps(c1))
    r["name"] = "banco_k562_t22s"
    r["contexts"][CTX]["amplitude"] = AMP_T22 * scale
    r["why"] = (f"C3, the amplitude control of C2 (V2): C1 at 1.576 x s(C2) = 1.576 x {scale:.6g}, s(C2) being C2's "
                "gene_share_scale in its stage-100 manifest. Written by build_arms.py from that measured scale. Cache r5.")
    return r


def derived_exclrs(e1: dict) -> dict:
    r = json.loads(json.dumps(e1))
    r["name"] = "banco_k562_exclrs"
    r["gene_share"]["basal"] = "processed/basal_sources_2026-09-26.csv"
    r["gene_share"]["match_detectable"] = "processed/banco_k562_pannello_2026-09-29/t22"
    r["why"] = ("E2, the exclusion with the detectable genes recovered: E1 scaled back to C1's median count of detectable "
                "genes on K562's control CPM, cis head included on both sides (stage 100's gene_share with "
                "match_detectable). Written by build_arms.py. Cache r5.")
    return r


def derived_rb(c1: dict, s: float) -> dict:
    r = json.loads(json.dumps(c1))
    r["name"] = "banco_k562_rb"
    r["contexts"][CTX]["amplitude"] = float(s)
    r["why"] = (f"RB: C1 at the amplitude of rule R-B on K562's CPM, {s:.6g} (more than 10% from 3.152). "
                "Written by build_arms.py. Cache r5.")
    return r


def run_stage100(arm: str, recipe_path: Path, cache: Path, out: Path, targets_csv: Path, coords: Path,
                 log: Path) -> dict:
    """Stage 100 in a child process, measured by misura.py; returns its manifest's k562 entry and more."""
    cmd = [sys.executable, str(MISURA), "--log", str(log), "--label", f"banco_k562 {arm}", "--disk-path", str(out.parent),
           "--", str(STAGE100), "--recipe", str(recipe_path), "--cache", str(cache), "--out", str(out),
           "--targets-csv", str(targets_csv), "--coords", str(coords)]
    env = dict(os.environ, PYTHONPATH=str(REPO / "src"), PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    print(f"--- stage 100: {arm} ({cache.name})", flush=True)
    code = subprocess.run(cmd, cwd=REPO, env=env).returncode
    if code != 0:
        raise SystemExit(f"stage 100 failed for {arm} (exit {code}); see {log}")
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    measured = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
    return {"stage100_manifest_sha256": sha256(out / "manifest.json"), "context": man["contexts"][CTX],
            "cache_check": man.get("cache_check"), "gene_share": man.get("gene_share"),
            "expression_gate": man.get("expression_gate"), "cis_prior_ln_by_bin": (man.get("cis") or {}).get("prior_ln_by_bin"),
            "peak_rss_bytes": measured.get("peak_rss_bytes"), "seconds": measured.get("seconds")}


# --- 4. R-B ------------------------------------------------------------------------------------------

def diagnostica():
    """The rehearsal's diagnostica.py, imported unchanged (it puts its own folder on sys.path)."""
    if str(DIAGNOSTICA) not in sys.path:
        sys.path.insert(0, str(DIAGNOSTICA))
    import diagnostica as dg

    return dg


def amplitude_rules(c1_dir: Path, c1_recipe: dict, reference: Path, reference_recipe: Path, cpm_ref: Path,
                    basal: Path, coords: Path, axis: np.ndarray) -> dict:
    """R-B (t22's official effects) and R-C (C1's own effects) on K562's CPM, with diagnostica.py's code.

    As in its `section_amplitude`: E is (lfc - cis head) / amplitude, the target is the mean over
    the reference contexts of N_det at their amplitude on their CPM (``--cpm-ref``, A/B/C), and a new
    context without a mapping is scored with the first reference context's E."""
    dg = diagnostica()
    ref_recipe = json.loads(reference_recipe.read_text(encoding="utf-8"))
    ref_man = json.loads((reference / "manifest.json").read_text(encoding="utf-8"))
    ref_ctx = list(ref_man["contexts"])
    panel = dg.load_effects(reference, ref_ctx[0])["targets"]
    K_ref, cis_ref = dg.cis_head(panel, axis, ref_recipe.get("cis"), coords)
    amp_ref = {c: float(ref_recipe["contexts"][c].get("amplitude", 1.0)) for c in ref_ctx}
    cpm_abc = dg.Cpm(axis, None, cpm_ref)
    cpm_k = dg.Cpm(axis, None, basal)
    E_first, per_ref, identical = None, {}, True
    for c in ref_ctx:
        E = dg.split_effects(reference, c, K_ref, amp_ref[c])
        if E_first is None:
            E_first = E
        else:
            identical &= bool(np.array_equal(E_first, E))
        gate, thr = cpm_abc.gate_threshold(c)
        per_ref[c] = dg.n_det(E[:, gate], K_ref.dense(gate), amp_ref[c], thr[gate])
        del E
    target = float(np.mean(list(per_ref.values())))
    gate_k, thr_k = cpm_k.gate_threshold(CTX)
    E_rb, K_rb, t_rb = E_first[:, gate_k], K_ref.dense(gate_k), thr_k[gate_k]
    rb = dg.solve(lambda s: dg.n_det(E_rb, K_rb, s, t_rb), target, AMP_T22)
    del E_first, E_rb, K_rb

    c1_panel = dg.load_effects(c1_dir, CTX)["targets"]
    K_c1, cis_c1 = dg.cis_head(c1_panel, axis, c1_recipe.get("cis"), coords)
    E_c1 = dg.split_effects(c1_dir, CTX, K_c1, float(c1_recipe["contexts"][CTX]["amplitude"]))[:, gate_k]
    K_c1g = K_c1.dense(gate_k)
    rc = dg.solve(lambda s: dg.n_det(E_c1, K_c1g, s, t_rb), target, AMP_T22)
    n_det_c1 = dg.n_det(E_c1, K_c1g, AMP_T22, t_rb)
    s = float(rb["s"])
    return {"rule": "R-B of reports/invii/prova_generale_2026-09-28/RISULTATI.md on K562's control CPM",
            "reference_effects": str(reference), "reference_contexts": ref_ctx, "reference_amplitudes": amp_ref,
            "reference_effects_identical_across_contexts": identical,
            "reference_n_det": {"per_context": per_ref, "mean": target, "rehearsal_measured_mean": 257.6666666666667},
            "cpm_reference": str(cpm_ref), "cpm_k562": f"{basal} (column {CTX})",
            "genes_gated_k562": int(gate_k.sum()), "cis_reference": cis_ref, "cis_c1": cis_c1,
            "R-B": rb, "R-C_with_C1_effects": rc, "C1_n_det_at_1.576": n_det_c1,
            "value": s, "multiplier_of_1.576": s / AMP_T22,
            "distance_from_3.152": abs(s - AMP_A2) / AMP_A2,
            "build_rb": bool(abs(s - AMP_A2) > RB_TOLERANCE * AMP_A2),
            "P5_within_2.84_3.47": bool(2.84 <= s <= 3.47)}


# --- 5. coverage -------------------------------------------------------------------------------------

def bench_targets(k562_meta: Path, min_cells: int) -> list[str]:
    """Stage 73's targets: panel genes with at least ``min_cells`` selected cells, measured by the cells."""
    groups = pd.read_csv(k562_meta / "groups.csv")
    names = set(pd.read_csv(k562_meta / "var.csv")["gene_name"].astype(str))
    counts = groups[groups.in_panel].groupby(groups["gene"].astype(str))["n_selected"].sum()
    return sorted(t for t, n in counts.items() if n >= min_cells and t in names)


def coverage(targets: list[str], caches: dict, missing_by_arm: dict) -> dict:
    out = {"bench_targets": len(targets), "rule": "stage 73: >= min_cells cells and the target gene measured"}
    for key, cache in caches.items():
        have = {}
        for src in SOURCES:
            with np.load(cache / f"{src}.npz", allow_pickle=False) as z:
                have[src] = set(z["targets"].astype(str))
        n_by = np.array([sum(t in have[s] for s in SOURCES) for t in targets])
        out[key] = {"cache": str(cache), "by_source": {s: sum(t in have[s] for t in targets) for s in SOURCES},
                    "by_at_least_one": int((n_by >= 1).sum()), "by_all_three": int((n_by == 3).sum()),
                    "by_none": sorted(t for t, n in zip(targets, n_by) if n == 0)}
    out["no_source_per_stage100"] = {arm: sorted(set(m) & set(targets)) for arm, m in missing_by_arm.items()}
    return out


def k562_axis_summary(npz: Path, measured: np.ndarray, gate: np.ndarray, thr: np.ndarray, rows: np.ndarray) -> dict:
    """Over the bench targets: median genes moved among those K562's cells measure (the bench's axis on
    the official one), and median detectable genes (|lfc| above 4/sqrt(400 mu), >= 5 CPM), cis included."""
    with np.load(npz, allow_pickle=False) as z:
        lfc = z["lfc"][rows]
    return {"genes_nonzero_on_k562_measured_median": float(np.median((lfc[:, measured] != 0).sum(axis=1))),
            "detectable_median": float(np.median((np.abs(lfc[:, gate]) > thr[gate][None, :]).sum(axis=1)))}


# --- main --------------------------------------------------------------------------------------------

def refuse_existing(data_out: Path, drive_out: Path, arms: list[str]) -> None:
    if data_out.exists() and any(data_out.iterdir()):
        raise SystemExit(f"{data_out} is not empty; a build goes to a new --data-out")
    taken = [p.name for p in [drive_out / "manifest.json", *(drive_out / f"{a}.npz" for a in arms)] if p.exists()]
    if taken:
        raise SystemExit(f"{drive_out} already holds {taken}; a build goes to a new --drive-out")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-out", type=Path, default=DEFAULT_DATA_OUT)
    ap.add_argument("--drive-out", type=Path, required=True, help="the folder the Colab job reads ($IN)")
    ap.add_argument("--k562-meta", type=Path, required=True, help="stage 71's folder (groups.csv, var.csv)")
    ap.add_argument("--share-dir", type=Path, default=DEFAULT_SHARE_DIR)
    ap.add_argument("--cache", type=Path, default=DATA_ROOT / "processed/multisource_2026-09-23_r5")
    ap.add_argument("--cache-r9", type=Path, default=DATA_ROOT / "processed/multisource_2026-09-27_r9")
    ap.add_argument("--targets-csv", type=Path, default=DATA_ROOT / "raw/controls/pert_counts.csv")
    ap.add_argument("--coords", type=Path, default=DATA_ROOT / "external/annotation/gene_coordinates_gencode_v50.tsv")
    ap.add_argument("--basal", type=Path, default=DATA_ROOT / "processed/basal_sources_2026-09-26.csv")
    ap.add_argument("--reference-effects", type=Path, default=DATA_ROOT / "processed/effects_t22_2026-09-26")
    ap.add_argument("--reference-recipe", type=Path, default=REPO / "configs/recipes/t22.json")
    ap.add_argument("--cpm-ref", type=Path, default=DATA_ROOT / "interim/basal_cpm_by_context.csv")
    ap.add_argument("--min-cells", type=int, default=40)
    args = ap.parse_args()
    started = datetime.now(timezone.utc).isoformat()
    all_arms = [a for a, *_ in ARMS] + ["rb"]
    refuse_existing(args.data_out, args.drive_out, all_arms)
    from vcc2026.genes import official_axis

    axis = np.asarray(official_axis().symbols)
    share_record = convert_share(SHARE_NPY, axis, args.share_dir)
    print(f"share: {share_record['genes_zero']} genes at 0 (npy sha256 {share_record['npy_sha256'][:12]})", flush=True)
    args.data_out.mkdir(parents=True, exist_ok=True)
    log = args.data_out / "tempi.jsonl"
    caches = {"r5": args.cache, "r9": args.cache_r9}
    templates = {a: json.loads((HERE / "ricette" / t).read_text(encoding="utf-8")) for a, _, t, _ in ARMS if t}
    arms, used = {}, {}

    def build(arm: str, role: str, recipe: dict, template_file: str | None, cache_key: str, extra: dict | None = None):
        run, changes = materialise(recipe, share_dir=args.share_dir, data_out=args.data_out)
        path = args.data_out / "ricette_usate" / f"{arm}.json"
        write_json(path, run)
        res = run_stage100(arm, path, caches[cache_key], args.data_out / arm, args.targets_csv, args.coords, log)
        used[arm] = run
        arms[arm] = {"role": role, "template": None if template_file is None else f"ricette/{template_file}",
                     "template_sha256": None if template_file is None else sha256(HERE / "ricette" / template_file),
                     "recipe_used": run, "recipe_used_sha256": sha256(path), "replacements": changes,
                     "cache": cache_key, "amplitude": run["contexts"][CTX]["amplitude"], **(extra or {}), **res}
        print(f"    {arm}: amplitude {arms[arm]['amplitude']:.6g}, gene_share_scale "
              f"{res['context'].get('gene_share_scale')}, peak {(res['peak_rss_bytes'] or 0) / 2**20:.0f} MiB", flush=True)

    for arm, role, template_file, cache_key in ARMS:
        if arm == "t22s":
            s_c2 = float(arms["t23"]["context"]["gene_share_scale"])
            build(arm, role, derived_t22s(templates["t22"], s_c2), None, cache_key, {"scale_from_C2": s_c2})
        elif arm == "exclrs":
            build(arm, role, derived_exclrs(templates["excl"]), None, cache_key)
        else:
            build(arm, role, templates[arm], template_file, cache_key)

    rules = amplitude_rules(args.data_out / "t22", used["t22"], args.reference_effects, args.reference_recipe,
                            args.cpm_ref, args.basal, args.coords, axis)
    print(f"R-B on K562 CPM: {rules['value']:.4f} (x{rules['multiplier_of_1.576']:.3f} of 1.576; "
          f"{rules['distance_from_3.152']:.1%} from 3.152; R-C with C1's effects {rules['R-C_with_C1_effects']['s']:.4f})",
          flush=True)
    if rules["build_rb"]:
        build("rb", "RB", derived_rb(templates["t22"], rules["value"]), None, "r5", {"from_rule": "R-B"})

    targets = bench_targets(args.k562_meta, args.min_cells)
    with np.load(args.data_out / "t22" / f"effects_{CTX}.npz", allow_pickle=False) as z:
        panel = list(z["targets"].astype(str))
    outside = [t for t in targets if t not in panel]
    if outside:
        raise SystemExit(f"{len(outside)} bench targets are not in the panel of {args.targets_csv}: {outside[:5]}")
    rows = np.array([panel.index(t) for t in targets])
    measured = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)[CTX].notna().to_numpy()
    gate_k, thr_k = diagnostica().Cpm(axis, None, args.basal).gate_threshold(CTX)
    for arm in arms:
        arms[arm]["k562_axis_bench_targets"] = k562_axis_summary(args.data_out / arm / f"effects_{CTX}.npz",
                                                                 measured, gate_k, thr_k, rows)
    cover = coverage(targets, caches, {a: arms[a]["context"]["targets_missing"] for a in arms})

    args.drive_out.mkdir(parents=True, exist_ok=True)
    for arm in arms:
        src = args.data_out / arm / f"effects_{CTX}.npz"
        dst = args.drive_out / f"{arm}.npz"
        shutil.copyfile(src, dst)
        arms[arm]["npz_sha256"] = sha256(src)
        if sha256(dst) != arms[arm]["npz_sha256"]:
            raise SystemExit(f"{dst}: the copy differs from {src}")
        arms[arm]["npz"] = dst.name
    manifest = {"script": "reports/generatore_e_banchi/banco_k562_pannello_2026-09-29/build_arms.py",
                "protocol": "reports/generatore_e_banchi/banco_k562_pannello_2026-09-29/RISULTATI.md (18:10, 29/09)",
                "started_utc": started, "written_utc": datetime.now(timezone.utc).isoformat(), "argv": sys.argv,
                "data_out": str(args.data_out), "context_key": CTX, "sources": list(SOURCES),
                "caches": {k: str(v) for k, v in caches.items()}, "targets_csv": str(args.targets_csv),
                "targets_csv_sha256": sha256(args.targets_csv), "share": share_record, "amplitude_rules": rules,
                "coverage": cover, "bench_targets": targets, "arms": arms,
                "arms_for_the_job": [a for a in all_arms if a in arms],
                "not_a_score": "effects only; nothing here is scored or uploaded"}
    write_json(args.data_out / "manifest.json", manifest)
    write_json(args.drive_out / "manifest.json", manifest)      # last: the job waits for it
    print(f"wrote {len(arms)} arms to {args.drive_out}; manifest last", flush=True)


if __name__ == "__main__":
    main()
