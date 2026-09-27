# Ricerca di antigravity: dati multi-contesto (solo risultati di ricerca)

Rapporto integrale di antigravity (base di lancio, run `20260927-141048-v2-multictx-scout`, sola lettura, solo ricerca web, brief `v2-agy-multictx-scout.md`), copiato il 27 settembre senza modifiche. Le affermazioni vengono da estratti dei risultati di ricerca: la verifica sulle pagine primarie è in `verifica_grok.md`.

I found one confirmed public Perturb-seq dataset from 2026 measuring CRISPRi knockdowns in three cell lines, and identified several promising but unconfirmed leads from recent predictive modeling challenges.

### What I did and what I found
I executed web searches using the `search_web` tool for recent (2022-2026) single-cell CRISPR screens across multiple cell lines, excluding the team's already known datasets (Replogle, Nadig, Feng, Marson, X-Atlas, Mixscale). (**measured** from search query histories).
I discovered a recent pooled multi-cell line screen (VIPerturb-seq) and several 2026 computational challenges built on large, multi-cell line perturbation datasets. (**measured**)

### Confirmed Datasets
**VIPerturb-seq**
1. **Name/Author/Year**: VIPerturb-seq, Alexandra Bradu et al., 2026. **Accession/URL**: Zenodo (https://doi.org/10.5281/zenodo.18460279). (**measured**)
2. **Cell types/lines**: K562, HEK293, HAP1. (**measured**) **Shared perturbed genes**: A genome-wide library (and an mTOR regulators pilot), though the exact numerical overlap of guides successfully analyzed across all three lines is not explicitly stated in the search results. (**inferred**)
3. **Perturbation**: CRISPRi. **Readout**: single-cell RNA-seq (transcriptome via 10x Genomics Flex). (**measured**)
4. **Public data**: Yes, provided as Seurat `.rds` objects. (**measured**) **License**: not stated. **Size**: not stated. (**measured**)
5. **Certainty**: I am certain this dataset exists and is public. (**inferred**) **What to check**: A person should download the Zenodo repository, check the `genome_wide_manifest.txt`, and inspect the Seurat objects to verify the exact number of shared knockdown targets that passed quality control across the three cell lines. (**inferred**)

### Unconfirmed Leads
*   **Virtual Cell Challenge 2026 (Arc Institute)**: Involves a Perturb-seq (CRISPRi, 10x Flex scRNA-seq) dataset on 6 held-out cell lines from different tissues, with 300 knockdown targets per context. *Reason unconfirmed*: It is unclear if the post-perturbation ground-truth data is fully public, as the search indicates participants are only provided with basal state profiles for zero-shot prediction testing (URL: https://virtualcellchallenge.org/). (**measured/inferred**)
*   **"Echoes of Silenced Genes" Competition (Myllia Biotechnology, 2026)**: A Kaggle competition predicting human cancer cell line responses to CRISPRi CROP-seq perturbations. *Reason unconfirmed*: The dataset merges public atlases with a proprietary perturbation dataset; the specific cell lines, number of shared genes, and whether the proprietary processed data are fully open outside the competition are not stated (URL: https://www.kaggle.com/competitions/echoes-of-silenced-genes/overview). (**measured/inferred**)
*   **HyperMapDB (2026)**: A computational resource matrix of 18 cell lines × 19,036 perturbations. *Reason unconfirmed*: The framework "translates existing perturbation atlases," making it unverified whether this contains novel multi-cell line experimental screens or just computationally integrates already known datasets like Replogle and Orion (URL: https://doi.org/10.1101/2026.04.26.691475). (**measured/inferred**)
*   **scPerturb / PerturBase (2022-2024)**: Comprehensive databases harmonizing existing datasets (e.g., scPerturb has 44 datasets, 8,000 shared CRISPR perturbations). *Reason unconfirmed*: It is unverified if there is a single underlying novel primary screen inside these databases meeting the strict "same genes across many lines" criteria that is not already on your excluded list (URLs: https://scperturb.org, http://www.perturbase.cn/). (**measured/inferred**)

### What I did not do or could not verify, and open questions for Claude1
*   I did not execute any shell commands, run code, or view/modify local files, to strictly maintain the requested read-only state. (**measured**)
*   I could not verify the exact numerical count of overlapping perturbed genes in the VIPerturb-seq dataset or the specific cancer cell lines in the Kaggle competition because the web search summaries omitted these granular details. (**measured**)
*   **Open question for Claude1**: Does the research team want to participate in or request the full ground-truth data from the 2026 Arc Institute Virtual Cell Challenge, given it perfectly matches their experimental requirements (CRISPRi across 6 unseen lines)?
*   **Open question for Claude1**: Are large, harmonized databases (like scPerturb) useful for the team if they integrate distinct older screens into a single analytical space, even if they aren't derived from a single unified multi-cell line experiment?
