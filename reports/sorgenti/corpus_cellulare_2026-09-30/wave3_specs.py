"""Write the specs of the third ingestion wave (1/10, early morning) into jobs_colab/: human scPerturb screens of
single genes with integer counts, not yet ingested.

Every column name and control label below was read from the remote measurements (p1_r4/remote/scp_*.json); locators
and md5 come from urls_r4.json. Modalities are those the studies declare (scPerturb's perturbation_type and the
publications). A condition that changes the cells' baseline (a stimulation, a co-culture, a donor, a time point) is
a context of its own, through `context_col` or one unit per file, so no key mixes baselines. Left out, with the
reason: Adamson 2016 (controls are plasmid names; needs a declared label map), Papalexi pooled (labels `GENEg1`
without a separator), Wessels 2023 (pairs of Cas13 guides), the enhancer screens (Gasperini, Xie, Schraivogel), the
mouse screens, the drug screens and the ORF atlas.

    python wave3_specs.py          (refuses to write over an existing spec)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from wave2_specs import OUT, unit  # noqa: E402

SCP = "Zenodo 13350497 (scPerturb)"
LIC = "CC BY 4.0"

SPECS = {
    "j13_scp_ko_r1": [
        # melanoma cells in three conditions (Control, IFNγ, co-culture with T cells): three contexts
        unit("frangieh2021", "scp_FrangiehIzar2021_RNA", "h5csc_shards", "frangieh2021_melanoma_ko", "melanoma",
             "10x 3' v3", "KO", dict(target_col="perturbation", control_values=["control"], guides_col="guide_id",
                                     context_col="perturbation_2", published_depth="UMI_count"), SCP, LIC),
        # Calu-3, high MOI: several guides per cell are combinations and are never drawn
        unit("sunshine2023", "scp_SunshineHein2023", "h5csc_shards", "sunshine2023_calu3_ko", "Calu-3", "10x 3'",
             "KO", dict(target_col="perturbation", control_values=["control"], guides_col="guide_id",
                        library_col="gem_group", published_depth="UMI_count"), SCP, LIC),
        # THP-1, arrayed: one guide per well, the hashtag names the guide, so no library column
        unit("papalexi2021_arrayed", "scp_PapalexiSatija2021_eccite_arrayed_RNA", "h5csc_shards",
             "papalexi2021_thp1_arrayed_ko", "THP-1", "10x 3' (ECCITE)", "KO",
             dict(target_col="perturbation", control_values=["control"], guides_col="guide_id"), SCP, LIC)],
    "j14_scp_tcells_r1": [
        # primary T cells of two donors, with and without TCR stimulation: one context per sample
        unit("shifrut2018", "scp_ShifrutMarson2018", "h5rows", "shifrut2018_tcells_ko", "primary T cells", "10x",
             "KO", dict(target_col="target", control_values=["NonTarget"], guides_col="guide_id",
                        context_col="sample", donor_col="patient"), SCP, LIC),
        # Jurkat with and without TCR stimulation: one context each
        unit("datlinger2017", "scp_DatlingerBock2017", "h5rows", "datlinger2017_jurkat_ko", "Jurkat", "CROP-seq",
             "KO", dict(target_col="perturbation", control_values=["control"], library_col="replicate",
                        context_col="perturbation_2"), SCP, LIC),
        unit("datlinger2021", "scp_DatlingerBock2021", "h5rows", "datlinger2021_jurkat_ko", "Jurkat", "scifi-RNA-seq",
             "KO", dict(target_col="perturbation", control_values=["control"], library_col="sample",
                        context_col="perturbation_2"), SCP, LIC)],
    "j15_scp_k562_hek_r1": [
        # K562 knockouts of TFs: day 7, day 13 and high MOI are three contexts; intergenic cuts are the controls
        unit("dixit2016_d7", "scp_DixitRegev2016_K562_TFs_7_days", "h5csc_shards", "dixit2016_k562_ko", "K562 day 7",
             "10x (Perturb-seq)", "KO", dict(target_col="target", control_pattern="^INTERGENIC",
                                             guides_col="guide_id"), SCP, LIC),
        unit("dixit2016_d13", "scp_DixitRegev2016_K562_TFs_13_days", "h5csc_shards", "dixit2016_k562_ko",
             "K562 day 13", "10x (Perturb-seq)", "KO", dict(target_col="target", control_pattern="^INTERGENIC",
                                                            guides_col="guide_id"), SCP, LIC),
        unit("dixit2016_high_moi", "scp_DixitRegev2016_K562_TFs_High_MOI", "h5csc_shards", "dixit2016_k562_ko",
             "K562 high MOI", "10x (Perturb-seq)", "KO", dict(target_col="target", control_pattern="^INTERGENIC",
                                                              guides_col="guide_id"), SCP, LIC),
        # HEK293 CRISPRi
        unit("xu2023", "scp_XuCao2023", "h5csc_shards", "xu2023_hek293_crispri", "HEK293", "10x 3'", "CRISPRi",
             dict(target_col="target", control_values=["control"], guides_col="guide_id"), SCP, LIC)],
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
