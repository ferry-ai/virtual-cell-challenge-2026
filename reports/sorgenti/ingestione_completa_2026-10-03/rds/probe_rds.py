"""Kaggle kernel: what is inside the RDS files of Mixscale (Zenodo 14518762), VIPerturb (Zenodo 18460279) and DLD-1 (GEO).

The columns of their cell metadata are not known yet, and the conversion spec cannot be written without them. This
kernel installs R (base, Matrix, jsonlite: no Seurat), reads from Zenodo the smallest Seurat object of Mixscale, the
filtered genome-wide object of VIPerturb, the cell table of the low-MOI processed object of DLD-1 (GSE337988, whose
counts are in an HDF5 file read by probe_dld1.py) and the small text files, checks the md5 where one is published
(Zenodo; GEO publishes none), and writes for each
object a JSON with its structure: classes, slots, assays and layers with their shapes, whether the counts are whole
numbers, and every metadata column with its type and values. Nothing is converted. R reads each file in a process of
its own, with its peak memory recorded: the conversion jobs are sized on it.

Run as a Kaggle script kernel (push_script.py); nothing is passed on the command line.
"""
import hashlib, json, subprocess, time, urllib.request
from pathlib import Path

OUT, WORK = Path("/kaggle/working"), Path("/tmp/rds")
WORK.mkdir(parents=True, exist_ok=True)
GEO = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE337nnn/GSE337988/suppl/"
FILES = [                                                  # (Zenodo record or base URL, file, md5 or None, read with R)
    (GEO, "GSE337988_sublib2_samplesheet.csv.gz", None, False),
    (GEO, "GSE337988_pilot_samplesheet.csv.gz", None, False),
    (GEO, "GSE337988_NGS6475_Sample_Mapping_File_All.csv.gz", None, False),
    (GEO, "GSE337988_NGS6475_crispr_feature_barcode_MENGNTCUPDATE.csv.gz", None, False),
    (GEO, "GSE337988_sublib2_processed_objects_Low_se.rds", None, True),
    ("14518762", "A_readme.txt", "b05ff3d3117887faa4aaff1414030317", False),
    ("14518762", "Pathway_genelist.rds", "f107354d6d075364a3c94e34f1ff5134", True),
    ("14518762", "Seurat_object_TGFB_Perturb_seq.rds", "8e9b4d39a95ec5881a30be6a2df541d1", True),
    ("18460279", "genome_wide_manifest.txt", "c095c8f2d16136753c22ef5d9b30a22b", False),
    ("18460279", "genome_wide_filtered.rds", "ac52c41233fc7a5a5c3810e0a075007f", True),
    ("18460279", "genome_wide_binC.RDS", "af9e5908510f6765863d728f5ef18595", True),
]
R_SCRIPT = r'''
args <- commandArgs(trailingOnly = TRUE)
suppressWarnings(suppressMessages({library(Matrix); library(jsonlite)}))
summ_vec <- function(v) {
  out <- list(class = class(v)[1], n = length(v))
  if (is.factor(v)) v <- as.character(v)
  if (is.character(v) || is.logical(v)) {
    out$unique <- length(unique(v))
    if (out$unique <= 60) {
      t <- sort(table(v, useNA = "ifany"), decreasing = TRUE)
      nm <- names(t); nm[is.na(nm)] <- "<NA>"
      out$table <- as.list(setNames(as.integer(t), nm))
    } else out$head <- head(v, 8)
  } else if (is.numeric(v) && length(v)) {
    out$min <- min(v, na.rm = TRUE); out$max <- max(v, na.rm = TRUE); out$head <- head(v, 5)
    h <- head(v, 2000); out$integer_valued <- all(h == round(h), na.rm = TRUE)
  }
  out
}
summ <- function(x, depth) {
  cl <- class(x)[1]
  if (inherits(x, "data.frame"))
    return(list(class = cl, dim = dim(x), rownames_head = head(rownames(x), 3), columns = lapply(x, summ_vec)))
  if (cl %in% c("dgCMatrix", "dgTMatrix", "dgRMatrix") || inherits(x, "sparseMatrix")) {
    xs <- attr(x, "x"); s <- head(xs, 100000); dn <- attr(x, "Dimnames")
    return(list(class = cl, dim = attr(x, "Dim"), nnz = length(xs), integer_valued_sample = all(s == round(s)),
                max_sample = if (length(s)) max(s) else NA, rownames_head = head(dn[[1]], 5), colnames_head = head(dn[[2]], 3)))
  }
  if (is.matrix(x))
    return(list(class = cl, dim = dim(x), type = typeof(x), rownames_head = head(rownames(x), 5), colnames_head = head(colnames(x), 3)))
  if (isS4(x)) {
    a <- attributes(x); a$class <- NULL
    out <- list(class = cl, package = attr(class(x), "package"), slots = names(a))
    if (depth > 0) out$content <- lapply(a, summ, depth = depth - 1)
    return(out)
  }
  if (is.list(x)) {
    out <- list(class = cl, length = length(x), names = head(names(x), 40))
    if (depth > 0 && length(x) <= 40) out$content <- lapply(x, summ, depth = depth - 1)
    return(out)
  }
  if (is.atomic(x)) return(summ_vec(x))
  list(class = cl)
}
obj <- readRDS(args[1])
res <- list(file = basename(args[1]), bytes = file.size(args[1]), object_size_bytes = as.numeric(object.size(obj)),
            r_version = R.version.string, top = summ(obj, 5))
writeLines(toJSON(res, auto_unbox = TRUE, null = "null", na = "string", digits = NA, pretty = TRUE, force = TRUE), args[2])
cat("ok", basename(args[1]), "\n")
'''
doc, t0 = {"steps": {}}, time.time()


def sh(cmd, name, timeout=3600):
    t = time.time()
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    doc["steps"][name] = {"returncode": r.returncode, "seconds": round(time.time() - t, 1),
                          "tail": (r.stdout + r.stderr)[-1500:]}
    print(json.dumps({name: {k: doc["steps"][name][k] for k in ("returncode", "seconds")}}), flush=True)
    return r.returncode == 0


def fetch(record, name, md5):
    dest, h, n = WORK / name, hashlib.md5(), 0
    url = record + name if record.startswith("http") else f"https://zenodo.org/records/{record}/files/{name}?download=1"
    req = urllib.request.Request(url, headers={"User-Agent": "vcc2026-ingestione/1"})
    t = time.time()
    with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as fh:
        for block in iter(lambda: r.read(8 << 20), b""):
            fh.write(block)
            h.update(block)
            n += len(block)
    got = {"record": record, "bytes": n, "md5": h.hexdigest(), "md5_published": md5,
           "md5_ok": None if md5 is None else h.hexdigest() == md5,
           "seconds": round(time.time() - t, 1), "mb_per_s": round(n / 1e6 / max(time.time() - t, 0.01), 1)}
    print(json.dumps({name: got}), flush=True)
    return dest, got


sh("apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq r-base-core r-cran-matrix r-cran-jsonlite", "apt")
sh("Rscript --version", "r_version")
(OUT / "rds_inspect.R").write_text(R_SCRIPT)
doc["files"] = {}
for record, name, md5, is_rds in FILES:
    try:
        dest, got = fetch(record, name, md5)
    except Exception as err:
        doc["files"][name] = {"error": f"{type(err).__name__}: {err}"}
        continue
    doc["files"][name] = got
    if got["md5_ok"] is False:
        continue
    if not is_rds:
        (OUT / name).write_bytes(dest.read_bytes())
    else:
        ok = sh(f"/usr/bin/time -v Rscript {OUT / 'rds_inspect.R'} {dest} {OUT / (name + '.structure.json')}", f"inspect_{name}", 7200)
        tail = doc["steps"][f"inspect_{name}"]["tail"]
        rss = [l for l in tail.splitlines() if "Maximum resident set size" in l]
        got["inspected"], got["max_rss_kb"] = ok, int(rss[0].rsplit(":", 1)[1]) if rss else None
    dest.unlink()
doc["seconds"] = round(time.time() - t0, 1)
(OUT / "rds_probe.json").write_text(json.dumps(doc, indent=1))
print(json.dumps({"files": {k: {a: v.get(a) for a in ("md5_ok", "inspected", "max_rss_kb", "error")} for k, v in doc["files"].items()},
                  "seconds": doc["seconds"]}), flush=True)
