This repo contains Seurat objects, differential expression analysis results, and pathway gene lists for the manuscript "Systematic reconstruction of molecular pathway signatures using scalable single-cell perturbation screens"
List of files:

1. Seurat_object_IFNB_Perturb_seq.rds:  Seurat object of the Perturb-seq data for Interferon-beta pathway
2. Seurat_object_IFNG_Perturb_seq.rds:  Seurat object of the Perturb-seq data for Interferon-gamma pathway
3. Seurat_object_TNFA_Perturb_seq.rds:  Seurat object of the Perturb-seq data for TNF-alpha pathway
4. Seurat_object_TGFB1_Perturb_seq.rds: Seurat object of the Perturb-seq data for TGF-beta1 pathway
5. Seurat_object_INS_Perturb_seq.rds:   Seurat object of the Perturb-seq data for insulin pathway
6. Pathway_genelist.rds:                The pathway gene lists from MultiCCA analysis
7. Pathway_Exclusive_genelist.rds:      The pathway exclusive gene lists generated from Pathway_genelist.rds
8. HClust_Pathway_celltype_specific_genelist.rds:     The cell-line specific pathway gene lists from hierarchical clustering analysis independently done on each cell line
9. DE_results_all_pathway.zip:          The DE test results for all the regulators, cell lines, and pathways (from Mixscale weighted DE test.)
10. Bulk_RNAseq_Seurat_object_IFNG_and_TGFB_stim.rds: Seurat object for the bulk RNA-seq data for interferon-gamma and TGF-beta stimulation experiments
11. Parse_Guide_Capture_Protocol.pdf:   The guide RNA capture protocol developed for Parse Evercode Whole Transcriptome kit
