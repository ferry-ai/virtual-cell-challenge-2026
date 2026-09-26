I successfully identified three human single-cell CRISPR screens and one mouse screen released in 2025-2026 meeting the criteria using web searches.

**measured**: I used the `search_web` tool to look for single-cell CRISPR screens (Perturb-seq, CRISPRi/ko) released in 2025 or 2026 with >= 1,000 targets, excluding datasets already listed in the prompt context (e.g., Mixscale, GSE314342, GSE337988, X-Atlas).

**measured**: I found the following four datasets through search summaries:

1. **VIPerturb-seq / GuEST-List** (Bradu et al., *bioRxiv* preprint 2026)
- Cell line(s): HEK293 and K562 (pilot experiments)
- Number of targets: >18,000 human genes
- Readout: Whole transcriptome (scRNA-seq)
- Accession/URL: https://doi.org/10.64898/2026.02.12.705613
- Source sentence: "contains approximately 57,000 constructs targeting over 18,000 human genes" (**unverified** exact wording on primary page)

2. **KOLF2.1J Perturbation Cell Atlas** (Nourreddine et al., *Nature Biotechnology* July 2026)
- Cell line(s): KOLF2.1J (human iPSCs)
- Number of targets: 11,692 genes
- Readout: Whole transcriptome (transcriptional phenotypes)
- Accession/URL: https://doi.org/10.1038/s41587-026-03199-w (raw data on figshare: 10.25452/figshare.plus.27261219.v1)
- Source sentence: "mapping transcriptional phenotypes and fitness effects associated with 11,692 perturbed genes" (**unverified** exact wording on primary page)

3. **Genome-scale single-cell CRISPRi map of trans gene regulation** (Feng et al., *Cell Genomics* Feb 2026)
- Cell line(s): 34 human iPSC lines
- Number of targets: 7,226 genes
- Readout: Whole transcriptome (scRNA-seq)
- Accession/URL: https://doi.org/10.1016/j.xgen.2025.101076
- Source sentence: "utilized over 20,000 guide RNAs to target 7,226 genes" (**unverified** exact wording on primary page)

4. **Metabolic CRISPR screen in T cells** (Pretto et al., *Nature Metabolism* March 2025)
- Cell line(s): Mouse CD8+ T cells (*in vivo*)
- Number of targets: >2,000 metabolic genes
- Readout: Whole transcriptome (single-cell transcriptomics)
- Accession/URL: https://doi.org/10.1038/s42255-025-01233-w
- Source sentence: "CRISPR screen of more than 2,000 metabolic genes in CD8+ T cells" (**unverified** exact wording on primary page)

**inferred**: The exact wording of the source sentences might differ slightly on the primary pages because search engines often synthesize or extract text snippets from abstracts.

What I did not do or could not verify:
- I did not run any shell commands or try to bypass paywalls to directly open the primary papers.
- I could not confirm the exact sentences on the primary pages, relying entirely on the search engine summaries.

Open questions for Claude1:
- Do you want to include *in vivo* mouse screens like the *Elovl1* screen (Dataset 4), or screens targeting non-coding regions (I found a 2026 HT29 colorectal cancer screen targeting 12,117 enhancer regions)?
- Are pilot datasets like those in the VIPerturb-seq preprint sufficient for the team's model training?
