"""Write the specs of the second ingestion wave (1/10, night) into jobs_colab/.

Every column name and control label below was read from the remote measurements (p1_r4/remote/*.json and, for KOLF,
p1_r5/remote_kolf/*.json, read again with the corrected reader); locators, sizes and checksums come from urls_r4.json
and from those measurements. Modalities are those the studies declare (scPerturb's perturbation_type, the file names,
the publications): CRISPRi, CRISPRa or KO, never merged.

    python wave2_specs.py          (refuses to write over an existing spec)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "jobs_colab"
URLS = {x["id"]: x for x in json.loads((HERE / "urls_r4.json").read_text(encoding="utf-8"))}


def measured(rid):
    for d in (HERE / "p1_r5" / "remote_kolf", HERE / "p1_r4" / "remote"):
        f = d / f"{rid}.json"
        if f.is_file():
            return json.loads(f.read_text(encoding="utf-8")), f.relative_to(HERE).as_posix()
    raise SystemExit(f"no measurement for {rid}")


def unit(name, rid, adapter, study, context, chemistry, modality, kwargs, release, license_):
    m, where = measured(rid)
    u = URLS[rid]
    src = {"role": "counts h5ad", "locator": u["url"], "bytes": m["bytes"], "measured": where}
    if u.get("md5"):
        src["md5"] = u["md5"]
    shape = (m.get("layers", {}).get(kwargs.get("layer", "X")) or m["X"])["shape"]
    kw = {"path": u["url"], "study": study, "context": context, "chemistry": chemistry, "modality": modality,
          "axis_csv": "{AXIS}", "block": 20000, **kwargs}
    if adapter == "h5csc_shards":
        kw["work"] = "{WORK}/buckets_" + name
        kw.setdefault("cells_per_pass", 200000)
    return {"name": name, "adapter": adapter, "kwargs": kw,
            "source": {"id": rid, "release": release, "license": license_, "files": [src]},
            "expect": {"rows": [0, int(shape[0])]}}


SCP = "Zenodo 13350497 (scPerturb)"
KOLF = dict(target_col="gene_target", control_values=["NTC"], guides_col="gRNA", library_col="channel", layer="counts")
TIAN = dict(target_col="perturbation", control_values=["control"], guides_col="guide_id", library_col="batch")
SOUTHARD = dict(target_col="guide_target", control_values=["non"], guides_col="guide_identity", library_col="gem_group",
                published_depth="UMI_count", var_symbol_col="gene_name", feature_id_col="gene_id")

SPECS = {
    "j08_kolf_small_r1": [
        unit("kolf_chromatin", "kolf_KOLF_Chromatin_Modifiers_QC_Filtered", "h5csc_shards", "kolf_chromatin_modifiers",
             "KOLF2.1J iPSC", "MISSING", "CRISPRi", KOLF, "Figshare+ 27261219", "CC BY 4.0"),
        unit("kolf_metabolic", "kolf_KOLF_Metabolic_Enzymes_QC_Filtered", "h5csc_shards", "kolf_metabolic_enzymes",
             "KOLF2.1J iPSC", "MISSING", "CRISPRi", KOLF, "Figshare+ 27261219", "CC BY 4.0")],
    "j09_southard_r1": [
        unit("southard_rpe1", "southard_RPE1_CRISPRa_final_population", "h5rows", "southard_rpe1_crispra", "RPE1",
             "10x 3'", "CRISPRa", SOUTHARD, "Zenodo 15213619", "CC BY 4.0"),
        unit("southard_hs27", "southard_fibroblast_CRISPRa_final_pop", "h5rows", "southard_hs27_crispra",
             "Hs27 fibroblast", "10x 3'", "CRISPRa", SOUTHARD, "Zenodo 15200179", "CC BY 4.0")],
    "j10_a549_r1": [
        unit("a549_ko", "a549_GSE345058_SC_raw_normalized_counts", "h5rows", "a549_liu_hillsley2026", "A549", "MISSING",
             "KO", dict(target_col="Perturbation", control_values=["Nontargeting"], guides_col="sgRNA",
                        library_col="Lane", published_depth="total_counts", layer="raw_counts"), "GEO GSE345058",
             "GEO terms")],
    "j11_tian_norman_r1": [
        unit("tian2021_crispri", "scp_TianKampmann2021_CRISPRi", "h5csc_shards", "tian2021_crispri",
             "iPSC-induced neuron", "10x 3'", "CRISPRi", TIAN, SCP, "CC BY 4.0"),
        unit("tian2021_crispra", "scp_TianKampmann2021_CRISPRa", "h5csc_shards", "tian2021_crispra",
             "iPSC-induced neuron", "10x 3'", "CRISPRa", TIAN, SCP, "CC BY 4.0"),
        unit("tian2019_ipsc", "scp_TianKampmann2019_iPSC", "h5csc_shards", "tian2019_ipsc", "iPSC", "10x 3'",
             "CRISPRi", TIAN, SCP, "CC BY 4.0"),
        unit("tian2019_neuron", "scp_TianKampmann2019_day7neuron", "h5csc_shards", "tian2019_neuron_day7",
             "iPSC-induced neuron day 7", "10x 3'", "CRISPRi", TIAN, SCP, "CC BY 4.0"),
        unit("norman2019", "scp_NormanWeissman2019_filtered", "h5csc_shards", "norman2019_crispra", "K562", "10x 3'",
             "CRISPRa", dict(target_col="perturbation", control_values=["control"], guides_col="guide_id",
                             library_col="gemgroup", published_depth="UMI_count"), SCP, "CC BY 4.0")],
    "j12_kolf_strong_r1": [
        unit("kolf_strong", "kolf_KOLF_Strong_Perturbations", "h5csc_shards", "kolf_strong_perturbations",
             "KOLF2.1J iPSC", "MISSING", "CRISPRi", KOLF, "Figshare+ 27261219", "CC BY 4.0")],
}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for job, units in SPECS.items():
        path = OUT / f"{job}_spec.json"
        if path.exists():
            sys.exit(f"refusing: {path} exists")
        path.write_text(json.dumps({"job_id": job, "min_free_stage_bytes": 4 << 30, "units": units,
                                    "min_free_out_bytes": 0}, indent=1), encoding="utf-8")
        print(path.name, [(u["name"], u["expect"]["rows"][1]) for u in units])


if __name__ == "__main__":
    main()
