"""The chain of the t30 submission, re-read offline from the receipts and the files on disk: entry, receipt, model,
effects, generation, package, official members, registered rule. It never calls the site and never submits.

Checks (each one true/false in the output, with the values compared):
- receipt: entry id, model name, bytes and md5 flag of `submit_t30_raw.json` against the status and the packaging;
- model and selector: sha256 of model.pt and selector_final.json against the export manifest and the registration;
- effects: sha256 of the exported effects files on disk against the export manifest; the t25 effects regenerated on
  4/10 against the sha256 of the t25 submission's own stage-100 manifest;
- generation: the stage-45 arguments of t30 against t25's (only the effects files and the run id may differ; options
  absent from the older manifest must be at their inactive default); the per-block diagnostics of t30 against t25's,
  on the blocks of the uncorrected targets (w = 0), read in two parts: the compositional shift, a deterministic
  function of the effects (profile parity, required), and the count statistics, which also depend on the random stream
  (cell parity, reported as a finding: stage 45 draws every block from one stream, so a changed block moves the noise
  of the blocks after it). Block statistics, not a bit-for-bit comparison: the t25 cells are no longer on disk;
- package: stage 48 reads the file stage 45 wrote; the package on disk has the size and the sampled sha256 recorded;
- score: the six published scaled members, their mean against score_avg, member by member against t25 and t28, the
  contribution of each member to the difference of the means, and the registered rule on the unrounded difference.

    .\\scripts\\py.cmd reports/modelli/diagnosi_t30_2026-10-04/chain_t30.py --out <new json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from vcc2026.manifest import file_fingerprint

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DATA = Path(os.environ.get("VCC2026_DATA_ROOT", "C:/Users/ferra/vcc2026-data"))
TRIAL = REPO / "reports/invii/trial_2026-10-04"
REG = REPO / "reports/invii/prediction_t30_2026-10-04/prediction.json"
HYB = REPO / "reports/modelli/ibrido_selettivo_2026-10-04"
EXPORT = DATA / "processed/ibrido_selettivo_2026-10-04/export_abc_r2"
ENTRY = "lDMSYUZU5cFYHcRqI0lq"
STATUS = {"t30": TRIAL / f"status_{ENTRY}.json",
          "t25": REPO / "reports/invii/trial_2026-09-27/status_ekxW6wo83Csum25pkddl.json",
          "t28": REPO / "reports/invii/trial_2026-09-29/status_ZvrYZ4UazadAyuq4AsDB_20260929T2305.json"}
MEMBERS = {"score_pds": "pds_cosine", "score_mse": "expr_mse_unbiased_capped_norm", "score_nmae": "de_wilcoxon_lfc_nmae",
           "score_fid": "de_wilcoxon_direction_fidelity_yield_raw", "score_reach": "de_wilcoxon_direction_reach_raw",
           "score_jac": "de_wilcoxon_sig_jaccard"}
THRESHOLD = 0.005
INACTIVE = {"gene_dispersion_scale": 1.0, "depth_bins": False}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(8 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load(path: Path):
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-16"):
        try:
            return json.loads(raw.decode(enc))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise SystemExit(f"cannot read {path}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    st = {k: load(v) for k, v in STATUS.items()}
    reg = load(REG)
    raw = load(TRIAL / "submit_t30_raw.json")
    started = load(TRIAL / "submit_t30_started.json")
    finished = load(TRIAL / "submit_t30_finished.json")
    pack = load(TRIAL / "t30_packaging.json")
    m45, m48 = load(TRIAL / "t30_manifest_45_generate_prediction.json"), load(TRIAL / "t30_manifest_48_package_prediction.json")
    exp = load(TRIAL / "t30_effects_manifest.json")
    regen = load(TRIAL / "t25_regen_effects_manifest.json")
    m45_t25 = load(REPO / "reports/invii/trial_2026-09-27/t25_manifest_45_generate_prediction.json")
    checks = {}

    checks["receipt"] = {
        "entry_matches_status": raw["entry_id"] == st["t30"]["entry_id"] == ENTRY,
        "model_name_matches_status": raw["model_name"] == st["t30"]["model_name"] == started["model_name"],
        "md5_verified_by_server": bool(raw["md5_verified"]),
        "bytes_uploaded": raw["bytes_uploaded"], "package_archive_bytes": pack["package"]["archive_bytes"],
        "bytes_match_package": raw["bytes_uploaded"] == pack["package"]["archive_bytes"] == started["bytes"],
        "upload_exit_code": finished["exit_code"], "status": st["t30"]["status"], "is_terminal": st["t30"]["is_terminal"],
        "panel_and_anchors_equal_t25_t28": len({(s["panel_id"], s["anchor_version"]) for s in st.values()}) == 1,
        "panel_id": st["t30"]["panel_id"], "anchor_version": st["t30"]["anchor_version"]}

    model = DATA / "processed/ibrido_selettivo_2026-10-04/out_train_hepg2_model_r1/train/ibrido/model.pt"
    selector = HYB / "esito/selector_final_r1/selector_final.json"
    model_sha, sel_sha = sha(model), sha(selector)
    checks["model_and_selector"] = {
        "model_sha256": model_sha, "model_matches_export_manifest": model_sha == exp["inputs"]["model"],
        "model_named_in_registration": model_sha in reg["candidate"]["R"],
        "selector_sha256": sel_sha, "selector_matches_export_manifest": sel_sha == exp["inputs"]["selector"],
        "selector_named_in_registration": sel_sha in reg["candidate"]["w"],
        "exported_state": exp["model"]["exported"], "anchor_sources": exp["anchors"]["sources"],
        "held_group_of_the_network": exp["anchors"]["held"],
        "exporter_sha256_now": sha(HYB / "export_abc.py"),
        "exporter_named_in_registration": sha(HYB / "export_abc.py") in reg["candidate"]["exporter"],
        "exporter_note": "the registration names the exporter before its gene-index reading fix (INVIO_T30.md)"}

    eff = {}
    for c in "ABC":
        f = EXPORT / f"effects_{c}.npz"
        on_disk = sha(f)
        eff[c] = {"sha256": on_disk, "matches_export_manifest": on_disk == exp["contexts"][c]["outputs"][f"effects_{c}.npz"],
                  "named_in_stage45_arguments": any(str(x).replace("\\", "/").endswith(f"export_abc_r2/effects_{c}.npz")
                                                    for x in m45["config"]["effects"]),
                  "parity_w0_equal_t25": exp["contexts"][c]["parity_w0_equal_t25"],
                  "t25_regenerated_sha256": regen["contexts"][c]["sha256"],
                  "t25_input_of_export": exp["inputs"][f"effects_{c}"]}
    t25_original = load(REPO / "reports/invii/trial_2026-09-27/t25_manifest_45_generate_prediction.json")
    checks["effects"] = {"contexts": eff,
                         "corrected_targets": exp["corrected_targets"], "not_corrected": exp["not_corrected"],
                         "note": ("stage 45 does not record the sha256 of the effects files it reads, only their paths: "
                                  "the link effects -> cells rests on the paths and on the files not having changed "
                                  "since (mtime before the generation start)"),
                         "effects_mtime_before_generation": all(
                             file_fingerprint(EXPORT / f"effects_{c}.npz", full=False)["mtime_utc"] < m45["started_utc"]
                             for c in "ABC"),
                         "t25_original_effects_paths": t25_original["config"]["effects"]}

    c30, c25 = dict(m45["config"]), dict(m45_t25["config"])
    diff = {k: (c25.get(k, "<absent>"), c30.get(k, "<absent>")) for k in sorted(set(c30) | set(c25))
            if c30.get(k, "<absent>") != c25.get(k, "<absent>")}
    allowed = {"run_id", "effects"}
    unexpected = {k: v for k, v in diff.items() if k not in allowed and not (v[0] == "<absent>" and INACTIVE.get(k) == v[1])}
    b30 = pd.DataFrame(load(TRIAL / "t30_generation_diagnostics.json")["per_block"]).set_index(["context", "target"])
    b25 = pd.DataFrame(load(REPO / "reports/invii/trial_2026-09-27/t25_generation_diagnostics.json")["per_block"]
                       ).set_index(["context", "target"])
    b25 = b25.loc[b30.index]
    same = (b30 == b25).all(axis=1)
    same_profile = b30["compositional_shift_log2"] == b25["compositional_shift_log2"]
    rel_nnz = (b30["nnz"] - b25["nnz"]).abs() / b25["nnz"]
    blocks = {}
    for c in "ABC":
        t = pd.read_csv(HYB / f"esito/export_abc_r2/targets_{c}.csv").set_index("symbol")
        w0 = t.index[t["w"] == 0]
        moved = t.index[t["w"] > 0]
        order = list(b30.loc[c].index)
        first_moved = min(order.index(s) for s in moved)
        blocks[c] = {"targets_w0": int(len(w0)),
                     "w0_profile_identical_to_t25": int(same_profile.loc[c].reindex(w0).sum()),
                     "w0_blocks_identical_to_t25": int(same.loc[c].reindex(w0).sum()),
                     "w0_blocks_before_the_first_corrected_block": int(sum(order.index(s) < first_moved for s in w0))
                     if c == "A" else 0,
                     "w0_median_relative_nnz_difference": float(rel_nnz.loc[c].reindex(w0).median()),
                     "targets_corrected": int(len(moved)),
                     "corrected_profile_identical_to_t25": int(same_profile.loc[c].reindex(moved).sum()),
                     "corrected_blocks_identical_to_t25": int(same.loc[c].reindex(moved).sum()),
                     "corrected_median_relative_nnz_difference": float(rel_nnz.loc[c].reindex(moved).median())}
    checks["generation"] = {
        "seed_t30": m45["seed"], "seed_t25": m45_t25["seed"], "trial_t30": c30["trial"], "trial_t25": c25["trial"],
        "argument_differences": diff, "unexpected_argument_differences": unexpected,
        "arguments_equal_but_effects": not unexpected and m45["seed"] == m45_t25["seed"],
        "controls_equal": all(m45["inputs"][f"controls:{c}"]["sha256"] == m45_t25["inputs"][f"controls:{c}"]["sha256"]
                              for c in "ABC"),
        "per_block_parity": blocks,
        "w0_profile_parity_through_generator": all(v["targets_w0"] == v["w0_profile_identical_to_t25"]
                                                   for v in blocks.values()),
        "w0_cells_identical_through_generator": all(v["targets_w0"] == v["w0_blocks_identical_to_t25"]
                                                    for v in blocks.values()),
        "finding": ("the cells of the uncorrected targets are not those of t25: one random stream runs through all the "
                    "blocks, so t30 - t25 carries a change of noise realization on every block after the first "
                    "corrected one, besides the correction; the only measured pair of seeds is t24 - t22 = +0.0016"),
        "block_fields_compared": list(b30.columns)}

    vcc = DATA / "artifacts/t30pack/prediction.vcc"
    fp = file_fingerprint(vcc) if vcc.exists() else {"exists": False}
    checks["package"] = {
        "stage48_reads_stage45_output": m48["inputs"]["prediction"]["sha256"] == m45["outputs"]["prediction"]["sha256"],
        "package_on_disk": fp.get("exists", False), "bytes_on_disk": fp.get("bytes"),
        "sampled_sha256_on_disk": fp.get("sha256"),
        "matches_stage48_manifest": fp.get("sha256") == m48["outputs"]["vcc"]["sha256"]
        and fp.get("bytes") == m48["outputs"]["vcc"]["bytes"],
        "validation": {k: pack["package"]["validation"][k] for k in ("n_obs", "n_vars", "all_integer", "n_nonfinite",
                                                                     "cells_per_context", "n_targets_per_context")}}

    scaled = {t: {m: float(s[m]) for m in MEMBERS} for t, s in st.items()}
    rawm = {t: {r: float(s[r]) for r in MEMBERS.values()} for t, s in st.items()}
    mean6 = {t: sum(v.values()) / 6 for t, v in scaled.items()}
    delta = st["t30"]["score_avg"] - reg["references"]["t25"]
    branch = "a" if delta >= THRESHOLD else "c" if delta <= -THRESHOLD else "b"
    lower = reg["references"]["t25"] - THRESHOLD
    checks["score"] = {
        "score_avg": {t: s["score_avg"] for t, s in st.items()}, "mean_of_six": mean6,
        "mean_matches_score_avg": {t: abs(mean6[t] - st[t]["score_avg"]) < 1e-12 for t in st},
        "scaled": scaled, "raw": rawm,
        "t30_minus_t25": {m: scaled["t30"][m] - scaled["t25"][m] for m in MEMBERS},
        "t30_minus_t28": {m: scaled["t30"][m] - scaled["t28"][m] for m in MEMBERS},
        "contribution_to_mean_vs_t25": {m: (scaled["t30"][m] - scaled["t25"][m]) / 6 for m in MEMBERS},
        "contribution_to_mean_vs_t28": {m: (scaled["t30"][m] - scaled["t28"][m]) / 6 for m in MEMBERS},
        "raw_t30_minus_t25": {r: rawm["t30"][r] - rawm["t25"][r] for r in MEMBERS.values()},
        "raw_t30_minus_t28": {r: rawm["t30"][r] - rawm["t28"][r] for r in MEMBERS.values()},
        "rule": {"reference_t25_registered": reg["references"]["t25"],
                 "reference_equals_t25_status": reg["references"]["t25"] == st["t25"]["score_avg"],
                 "delta_unrounded": delta, "threshold": THRESHOLD, "lower_bound_score": lower,
                 "score_minus_lower_bound": st["t30"]["score_avg"] - lower, "branch": branch,
                 "rounded_to_4_digits_would_be_ambiguous": round(st["t30"]["score_avg"], 4) == round(lower, 4),
                 "inside_registered_band": reg["expected"]["score_avg_band"][0] <= st["t30"]["score_avg"]
                 <= reg["expected"]["score_avg_band"][1]},
        "per_context_members": "not published in the status: none is reconstructed"}

    flat_ok = {
        "receipt": all(checks["receipt"][k] for k in ("entry_matches_status", "model_name_matches_status",
                                                      "md5_verified_by_server", "bytes_match_package",
                                                      "panel_and_anchors_equal_t25_t28")),
        "model_and_selector": all(checks["model_and_selector"][k] for k in (
            "model_matches_export_manifest", "model_named_in_registration", "selector_matches_export_manifest",
            "selector_named_in_registration")),
        "effects": all(v["matches_export_manifest"] and v["named_in_stage45_arguments"] and v["parity_w0_equal_t25"]
                       and v["t25_regenerated_sha256"] == eff["A"]["t25_regenerated_sha256"] for v in eff.values())
        and checks["effects"]["effects_mtime_before_generation"],
        "generation": checks["generation"]["arguments_equal_but_effects"] and checks["generation"]["controls_equal"]
        and checks["generation"]["w0_profile_parity_through_generator"],
        "generation_w0_cells_identical_to_t25": checks["generation"]["w0_cells_identical_through_generator"],
        "package": checks["package"]["stage48_reads_stage45_output"] and bool(checks["package"]["matches_stage48_manifest"]),
        "score": all(checks["score"]["mean_matches_score_avg"].values())
        and checks["score"]["rule"]["reference_equals_t25_status"]}
    out = {"written_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "entry_id": ENTRY,
           "passed": flat_ok, "checks": checks,
           "note": "offline re-read of receipts and files; no call to the site; not a new score"}
    a.out.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"passed": flat_ok, "branch": branch, "delta": delta,
                      "per_block": checks["generation"]["per_block_parity"],
                      "unexpected": unexpected}, default=str))


if __name__ == "__main__":
    main()
