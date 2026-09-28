# VIPerturb-seq (Bradu et al. 2026, Zenodo 18460279, CC BY 4.0): read the filtered genome-wide Seurat object
# and print its structure, so the per-target sums can be written next. Private kernel; no data kept.
options(timeout = 7200)
url <- "https://zenodo.org/records/18460279/files/genome_wide_filtered.rds?download=1"
dest <- "/kaggle/temp/gw.rds"
dir.create("/kaggle/temp", showWarnings = FALSE)
t0 <- Sys.time()
download.file(url, dest, mode = "wb", quiet = TRUE)
cat("downloaded", file.info(dest)$size, "bytes in", format(Sys.time() - t0), "\n")
for (p in c("Matrix", "SeuratObject")) if (!requireNamespace(p, quietly = TRUE)) install.packages(p, repos = "https://cloud.r-project.org")
suppressPackageStartupMessages({library(Matrix); library(SeuratObject)})
obj <- readRDS(dest)
cat("class:", class(obj), "\n")
print(obj)
cat("assays:", paste(Assays(obj), collapse = ", "), "\n")
md <- obj[[]]
cat("cells:", nrow(md), " metadata columns:", paste(colnames(md), collapse = ", "), "\n")
print(head(md, 5))
for (cn in colnames(md)) {
  v <- md[[cn]]
  if (is.character(v) || is.factor(v)) {
    u <- unique(as.character(v))
    cat(sprintf("column %s: %d distinct, e.g. %s\n", cn, length(u), paste(head(u, 6), collapse = " | ")))
  }
}
a <- DefaultAssay(obj)
lay <- tryCatch(Layers(obj[[a]]), error = function(e) "no Layers()")
cat("default assay:", a, " layers:", paste(lay, collapse = ", "), "\n")
m <- tryCatch(LayerData(obj, assay = a, layer = "counts"), error = function(e) tryCatch(GetAssayData(obj, slot = "counts"), error = function(e2) NULL))
if (!is.null(m)) {
  cat("counts:", class(m), nrow(m), "genes x", ncol(m), "cells; nnz", length(m@x), "; integer:", all(m@x == round(m@x)), "\n")
  cat("first genes:", paste(head(rownames(m), 10), collapse = ", "), "\n")
}
cat("done in", format(Sys.time() - t0), "\n")
