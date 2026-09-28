I answered point 4 for both datasets and most of the other points for VIPerturb-seq. For the 10x demo, points 1–3 and 5 are mostly unanswered: its page returned HTTP 429 on all three fetch attempts, and I could not read its technical-note PDF.

**What I did.** I read the source cards and made six web fetches and two web searches. I ran no shell commands and changed no files. One limit on the paper-derived facts: WebFetch passes each page through a small summarising model, so I did not read these sentences myself. Two of its answers contradict each other (see the library name below).

## Dataset A: VIPerturb-seq (bioRxiv 10.64898/2026.02.12.705613; Zenodo 18460279)

1. **Perturbation**
   - CRISPRi with the effector KRAB-dCas9-MeCP2 (**verified**, from the preprint's full text).
   - 57,050 sgRNAs, three per annotated human protein-coding gene, with non-targeting guides included (**verified**, preprint).
   - The number of non-targeting guides is not stated in what I extracted (**unverified**).
   - The library name is contradictory: one pass said "GuEST-List", another said the guides come from the "Dolcetto library" (**unverified** — open the Methods to settle it).
   - MOI 0.3–0.5 at 50x library coverage; median 14 cells per guide and 42 per targeted gene (**verified**, preprint).
   - The target list is probably `genome_wide_manifest.txt` (398.9 kB) on Zenodo, plus the Supplementary Tables of sequences. That this manifest *is* the target list is **unverified**; its contents are unread.
2. **Readout**
   - The genome-wide screen uses Flex v2 (Apex); the pilot and the vimentin screen use Flex v1. About 880,000 cell barcodes across two lanes (**verified**, preprint).
   - Guides are read with custom barcode probes, 238 left-hand and 240 right-hand sequences (**verified**).
   - The transcriptome probe set's name, version and gene count were not found in the text (**unverified**; card 4 at `reports/schede_sorgenti_2026-09-24/SCHEDE.md:104` also marks it to be verified).
   - Per-cell data exist only as Seurat `.rds` objects (**verified**, https://zenodo.org/records/18460279). Sizes:

     | File | Size |
     |---|---|
     | `genome_wide_binA.RDS` | 3.6 GB |
     | `genome_wide_binB.RDS` | 3.8 GB |
     | `genome_wide_binC.RDS` | 2.9 GB |
     | `genome_wide_filtered.rds` (6,724 perturbations passing QC) | 3.6 GB |
     | `multimodal_cell_line_mixing_pilot.rds` | 1.6 GB |
     | `vimentin_screen.rds` | 1.9 GB |
     | Total | 17.3 GB |

   - Reading them in Python needs an R conversion step (**inferred**).
3. **Overlap with a 3' dataset**
   - It is genome-wide over protein-coding genes in K562, so it should contain nearly all Replogle 2022 K562 genome-wide targets and the essential subset (**inferred**; not checked against a list).
   - The paper compares its perturbation "fingerprints" against reference fingerprints from Replogle's genome-wide dataset (GWPS) and from a "Flex-Plex dataset" (**verified**, preprint). That "Flex-Plex" means the 10x demo below is a guess (**unverified**).
4. **Licence:** CC-BY-4.0 (**verified**, Zenodo).
5. **Published Flex vs 3' comparison**
   - Median 15,100 UMIs and 5,300 detected genes per cell, "a median increase of 30% UMI/cell and 65% genes/cell" over GWPS, at about 25,000 reads per cell (**verified**, preprint).
   - Target knockdown was detected for 88% of perturbations (**verified**).
   - The fetches returned no correlation, sign-agreement or effect-size numbers between the same perturbations in the two assays (**verified absence in the extracted text**). I did not check figures or supplements.

## Dataset B: 10x "16-plex GEM-X Flex 1M human K562 CRISPR aggregate"

1. **Perturbation**
   - K562 stably expressing KRAB-dCas9, so CRISPRi; a pooled lentiviral library of lncRNA and protein-coding targets with about 6,903 sgRNAs (**verified** from search snippets of the dataset page and of technical note CG000814).
   - Card 12 (`SCHEDE.md:168`) splits this into 567 coding, 280 lncRNA and 177 non-targeting. `SCHEDE.md:30-31` says the "4,045 assigned" breakdown was wrong (**unverified**).
   - Library origin, target-list file and MOI: **not obtained**.
2. **Readout**
   - GEM-X Flex, 16 probe barcodes, split into 16 hybridisations then pooled over four GEM lanes; about 1.2 million cells; custom probes for sgRNAs and their targets spiked into the transcriptome probes (**verified**, search snippet of https://www.10xgenomics.com/datasets/16-plex_GEM-X_Flex_1M_human_K562_CRISPR_aggregate).
   - Chemistry is probably Flex v1, given Cell Ranger 9.0.0 (per the card) and that the technical note predates the v2 launch (**inferred**).
   - Probe-set version and gene count, file list, formats and sizes: **not obtained** (HTTP 429).
3. **Overlap with Replogle 2022:** unknown until the target list is retrieved. The lncRNA targets cannot overlap, because Replogle's screens target genes (**inferred**).
4. **Licence:** CC BY 4.0 per `SCHEDE.md:31` (**unverified by me**; the page was unreachable).
5. **Published Flex vs 3' comparison:** a search snippet says CG000814 includes "comparison metrics between GEM-X Flex and other assays for CRISPR screening" (**unverified**: that was a summary, and I could not open the PDF).

## Still unknown / questions for Claude1

- **Probe-set gene coverage for both datasets**, needed to map onto the 18,533-gene competition axis. Suggested next step: read the `features` of `genome_wide_filtered.rds` after download.
- **Dataset B's file list, sizes, target list and MOI**: retry the page later, or pull the page's JSON or the file listing from the 10x CDN.
- **CG000814 contents**: the PDF is cached at `C:\Users\ferra\.claude\projects\C--Users-ferra-OneDrive-Desktop-vcc2026\c8c5e9ed-46bc-49c9-bf97-97f64a202a35\tool-results\webfetch-1790288475227-m7lu48.pdf`. It could not be read here because `pdftoppm` is not installed; a `pypdf` text extraction would do it.
- **VIPerturb-seq details**: the library name ("GuEST-List" or "Dolcetto"), the non-targeting count, and whether "Flex-Plex" is the 10x demo.
- **Per-perturbation Flex vs 3' concordance**: I found no published number for effect size or sign agreement. Only depth figures are published (UMIs and detected genes per cell), so the team would have to compute concordance itself from VIPerturb-seq against Replogle's genome-wide dataset.

Sources: [VIPerturb-seq preprint](https://www.biorxiv.org/content/10.64898/2026.02.12.705613v1.full) · [Zenodo 18460279](https://zenodo.org/records/18460279) · [10x dataset page](https://www.10xgenomics.com/datasets/16-plex_GEM-X_Flex_1M_human_K562_CRISPR_aggregate) · [CG000814](https://cdn.10xgenomics.com/image/upload/v1744998417/support-documents/CG000814_TechnicalNote_CRISPR_Screening_with_GEM-X_Flex_Gene_Expression_RevA.pdf)
