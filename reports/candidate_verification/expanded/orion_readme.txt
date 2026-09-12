---
license: cc-by-nc-sa-4.0

configs:
- config_name: default
  data_files:
  - split: HCT116
    path: "data/HCT116*.parquet"
  - split: HEK293T
    path: "data/HEK293T*.parquet"
- config_name: gene_metadata
  data_files: metadata/gene_metadata.parquet
---

# X-Atlas/Orion 

X-Atlas: Orion edition (X-Atlas/Orion) is a Perturb-seq atlas containing two genome-wide Fix-Cryopreserve-ScRNAseq (FiCS) Perturb-seq screens that target all human 
protein-coding genes (n = 18,903 genes). The dataset is comprised of eight million HCT116 and HEK293T cells, each deeply sequenced to a median of 16,000 unique molecular 
identifiers (UMIs) per cell. The median on-target knockdown efficiency is 75.4% in HCT116 cells and 51.5% in HEK293T cells, with a median of at least 140 cells per 
perturbation. Through the release of X-Atlas/Orion, we highlight the potential of FiCS Perturb-seq to address current scalability and variability challenges in data 
generation, advance foundation model development that incorporates gene-dosage effects, and accelerate biological discoveries.

**Preprint**: [X-Atlas/Orion: Genome-wide Perturb-seq Datasets via a Scalable Fix-Cryopreserve Platform for Training Dose-Dependent Biological Foundation Models](https://www.biorxiv.org/content/10.1101/2025.06.11.659105v1)
<br>
**Processed h5ads and other metadata**: https://doi.org/10.25452/figshare.plus.29190726

<img src="https://pbs.twimg.com/media/Gt6v0cfXkAAUCkc?format=jpg&name=large" width="1024" height="1024">

## Tutorial
```python
from datasets import load_dataset

# load the entire dataset in streaming mode
ds = load_dataset("Xaira-Therapeutics/X-Atlas-Orion", streaming=True)
# load only hct116
hct116_ds = load_dataset("Xaira-Therapeutics/X-Atlas-Orion", streaming=True, split="HCT116")
# load only hek293t
hek293t_ds = load_dataset("Xaira-Therapeutics/X-Atlas-Orion", streaming=True, split="HEK293T")
```

## Dataset

The dataset contains the following information:

| **name**         | **description**     |
|------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `gene_token_id`  | gene identifiers corresponding to genes with non-zero expression in each cell. to be used with `gene_expression`. <br> `metadata/gene_metadata.parquet` contains the mapping from  `gene_token_id` to Ensembl ID and official gene symbol |
| `gene_expression`  | raw counts for genes with non-zero expression. to be used with `gene_token_id`                                                                            |
| `cell_barcode` | 10X-generated cell barcode. the suffix `-1` is replaced with `-<SAMPLE>`                                                                                      |
| `sample`   | GEM batch                                                                                                                                                         |
| `num_features`    | number of guides                                                                                                                                           |
| `guide_target`     | guide identity                                                                                                                                            |
| `gene_target`       | gene targeted by guide                                                                                                                                   |
| `n_genes_by_counts`     | number of genes with non-zero counts                                                                                                                 |
| `total_counts`       | total UMIs                                                                                                                                              |
| `total_counts_mt`      | total UMIs from MT genes                                                                                                                              |
| `pct_counts_mt`      | % UMIs from MT genes                                                                                                                                    |
| `pass_guide_filter`      | boolean if cells contains two guides from the same guide pair                                                                                       |

## Gene metadata

All samples were aligned to the 10x Genomics GRCh38 2024-A pre-built reference genome ([human reference (GRCh38) - 2024-A](https://www.10xgenomics.com/support/software/cell-ranger/downloads#reference-downloads)). Official gene symbols and ensembl IDs were extracted from the `genes.gtf` file.

```python
# load metadata containing mappings to gene tokens and names
gene_metadata = load_dataset("Xaira-Therapeutics/X-Atlas-Orion","gene_metadata")
```

| name   | description                                                                                                 |
|---------------|------------------------------------------------------------------------------------------------------|
| `ensembl_id` | Ensembl ID                                                                                            |
| `gene_name`  | official gene symbol                                                                                  |
| `gene_token_id`    | gene identifiers corresponding to genes with non-zero expression in each cell. to be used with `gene_token_id` in the dataset |

## Citation
```
@article{huang2025xatlasorion,
  title={X-Atlas/Orion: Genome-wide Perturb-seq Datasets via a Scalable Fix-Cryopreserve Platform for Training Dose-Dependent Biological Foundation Models},
  author={Huang, Ann C and Hsieh, Tsung-Han S and Zhu, Jiang and Michuda, Jackson and Teng, Ashton and Kim, Soohong and Rumsey, Elizabeth M and Lam, Sharon K and Anigbogu, Ikenna and Wright, Philip and Ameen, Mohamed and You, Kwontae and Graves, Christopher J and Kim, Hyunsung John and Litterman, Adam J and Sit, Rene V  and Blocker, Alex and Chu, Ci},
  journal={bioRxiv},
  year={2025},
  url={https://www.biorxiv.org/content/10.1101/2025.06.11.659105v1}
}
```