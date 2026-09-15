"""Probe target-descriptor sources for unseen-gene (mode B) inputs.

Isolated path: writes only to --out and --cache. Does not touch the modular
benchmark, signatures, or source registry. Small public annotation files are
downloaded after a HEAD size check; files above --max-file-mb are recorded
and skipped.

    .\\scripts\\py.cmd scripts/56_probe_target_descriptors.py --out reports/encoder_inputs_2026-09-14
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

from vcc2026.config import paths as project_paths

ROOT = Path(__file__).resolve().parents[1]

# Declared sizes (STRING download page, 2026-09-14 fetch) used when HEAD
# omits Content-Length. The probe still records the live HEAD status.
CANDIDATES = {
    "hgnc_complete_set": {
        "url": "https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt",
        "license": "CC0 (HGNC license agreement)",
        "license_url": "https://www.genenames.org/about/license/",
        "family": "mapping",
        "max_mb": 25,
        "role": "symbol -> ENSG / UniProt / Entrez / locus_group",
    },
    "goa_human_gaf": {
        "url": "https://ftp.ebi.ac.uk/pub/databases/GO/goa/HUMAN/goa_human.gaf.gz",
        "license": "GO CC-BY-4.0; GOA README permits free redistribution with notice",
        "license_url": "https://geneontology.org/docs/go-citation-policy/",
        "family": "function",
        "max_mb": 20,
        "role": "GO annotations, one canonical protein per gene",
    },
    "goa_human_gpi": {
        "url": "https://ftp.ebi.ac.uk/pub/databases/GO/goa/HUMAN/goa_human.gpi.gz",
        "license": "same as GOA GAF",
        "license_url": "https://ftp.ebi.ac.uk/pub/databases/GO/goa/HUMAN/README",
        "family": "mapping",
        "max_mb": 5,
        "role": "gene-product metadata including xrefs",
    },
    "goslim_generic": {
        "url": "http://current.geneontology.org/ontology/subsets/goslim_generic.obo",
        "license": "CC-BY-4.0",
        "license_url": "https://geneontology.org/docs/go-citation-policy/",
        "family": "function",
        "max_mb": 5,
        "role": "compact GO subset for a fixed-width binary vector",
    },
    "go_basic_obo": {
        "url": "http://current.geneontology.org/ontology/go-basic.obo",
        "license": "CC-BY-4.0",
        "license_url": "https://geneontology.org/docs/go-citation-policy/",
        "family": "function",
        "max_mb": 40,
        "role": "is_a/part_of graph so slim membership can be propagated",
    },
    "string_protein_info": {
        "url": "https://stringdb-downloads.org/download/protein.info.v12.0/9606.protein.info.v12.0.txt.gz",
        "license": "CC-BY-4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "family": "relations",
        "max_mb": 8,
        "role": "human STRING v12 proteins; preferred_name is typically HGNC symbol",
        "declared_size": "1.9 MB (STRING download page, species=9606)",
    },
    "string_physical_links": {
        "url": "https://stringdb-downloads.org/download/protein.physical.links.v12.0/9606.protein.physical.links.v12.0.txt.gz",
        "license": "CC-BY-4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "family": "relations",
        "max_mb": 15,
        "role": "physical PPI only (not the coexpression-containing full network)",
        "declared_size": "8.5 MB (STRING download page, species=9606)",
    },
}

# gene2vec: HEAD reports ~23.6 MiB; a GET without size cap exceeded 40 MiB
# uncompressed. Not downloaded. Vectors exist at the URL below.

HEAD_ONLY = {
    "string_links_full_combined": {
        "url": "https://stringdb-downloads.org/download/protein.links.v12.0/9606.protein.links.v12.0.txt.gz",
        "declared_size": "79.3 MB",
        "why_skip": "above small-probe budget; includes coexpression channel",
        "license": "CC-BY-4.0",
    },
    "string_sequence_embeddings_prott5": {
        "url": "https://stringdb-downloads.org/download/protein.sequence.embeddings.v12.0/9606.protein.sequence.embeddings.v12.0.h5",
        "declared_size": "36.4 MB",
        "why_skip": "coverage equals STRING protein.info; download later if GO ablation wins",
        "license": "CC-BY-4.0; ProtT5 embeddings via SPACE",
    },
    "string_network_embeddings": {
        "url": "https://stringdb-downloads.org/download/protein.network.embeddings.v12.0/9606.protein.network.embeddings.v12.0.h5",
        "declared_size": "18.7 MB",
        "why_skip": "graph includes coexpression; keep out of mode-B rigorous set",
        "license": "CC-BY-4.0",
    },
    "esm2_t6_8M": {
        "url": "https://huggingface.co/facebook/esm2_t6_8M_UR50D/resolve/main/model.safetensors",
        "declared_size": "29.93 MB (HuggingFace file listing)",
        "why_skip": "weights exist (MIT); not needed to measure mapping coverage",
        "license": "MIT",
    },
    "reactome_uniprot2reactome": {
        "url": "https://reactome.org/download/current/UniProt2Reactome.txt",
        "declared_size": "41 MB uncompressed (directory listing 2026-06-19)",
        "why_skip": "larger than GOA; GO slim is the first functional source",
        "license": "CC0 for annotation/mapping files (Reactome license)",
    },
    "corum_human": {
        "url": "https://mips.helmholtz-muenchen.de/corum/download/humanComplexes.txt.zip",
        "declared_size": "unknown before HEAD",
        "why_skip": "CC-BY-NC-4.0 on the CORUM site; same NC concern as Orion",
        "license": "CC-BY-NC-4.0 (declared on CORUM homepage)",
    },
    "gene2vec": {
        "url": "https://raw.githubusercontent.com/jingcheng-du/Gene2vec/master/pre_trained_emb/gene2vec_dim_200_iter_9.txt",
        "declared_size": "HEAD 23,648,087 bytes; GET uncompressed exceeded 40 MiB, aborted",
        "why_skip": "not a small metadata file once decompressed; trained on GEO co-expression",
        "license": "paper states CC0 waiver for data",
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _head(client: httpx.Client, url: str) -> dict:
    rec = {"url": url, "method": "HEAD"}
    try:
        r = client.head(url)
        rec["status"] = r.status_code
        rec["content_length"] = r.headers.get("content-length")
        rec["content_type"] = r.headers.get("content-type")
        rec["final_url"] = str(r.url)
        if rec["content_length"] is not None:
            rec["bytes"] = int(rec["content_length"])
    except Exception as exc:
        rec["error"] = f"{type(exc).__name__}: {exc}"
    return rec


def _download(client: httpx.Client, url: str, dest: Path, max_bytes: int) -> dict:
    rec = {"url": url, "path": str(dest), "method": "GET"}
    try:
        with client.stream("GET", url) as r:
            rec["status"] = r.status_code
            rec["content_type"] = r.headers.get("content-type")
            rec["final_url"] = str(r.url)
            cl = r.headers.get("content-length")
            if cl is not None and int(cl) > max_bytes:
                rec["skipped"] = True
                rec["reason"] = f"content-length {cl} exceeds budget {max_bytes}"
                rec["bytes"] = int(cl)
                return rec
            r.raise_for_status()
            body = bytearray()
            for chunk in r.iter_bytes():
                body.extend(chunk)
                if len(body) > max_bytes:
                    rec["skipped"] = True
                    rec["reason"] = f"stream exceeded budget {max_bytes}"
                    rec["bytes"] = len(body)
                    return rec
        dest.write_bytes(body)
        rec["bytes"] = len(body)
        rec["sha256"] = _sha256(bytes(body))
        rec["skipped"] = False
    except Exception as exc:
        rec["error"] = f"{type(exc).__name__}: {exc}"
        rec["skipped"] = True
    return rec


def _open_maybe_gzip(path: Path):
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        return io.TextIOWrapper(gzip.GzipFile(fileobj=io.BytesIO(raw)), encoding="utf-8")
    return io.StringIO(raw.decode("utf-8", errors="replace"))


def load_official_lists(data_root: Path) -> dict:
    genes = pd.read_csv(data_root / "raw" / "controls" / "gene_names.csv")
    gene_col = genes.columns[0]
    axis = genes[gene_col].astype(str).tolist()
    perts = pd.read_csv(data_root / "raw" / "controls" / "pert_counts.csv")
    targets = perts["target_gene"].astype(str).tolist()
    inv = pd.read_csv(ROOT / "reports" / "data_audit" / "target_inventory.csv")
    return {
        "n_axis": len(axis),
        "n_axis_unique": len(set(axis)),
        "n_vcc_targets": len(targets),
        "n_vcc_unique": len(set(targets)),
        "vcc_on_axis": int(sum(t in set(axis) for t in targets)),
        "vcc_targets": targets,
        "axis_set": set(axis),
        "inventory": inv,
    }


def load_signature_targets(sig_dir: Path) -> dict:
    out = {}
    for name in ("k562_gwps", "k562_essential", "rpe1_essential"):
        p = sig_dir / f"{name}.rows.json"
        if not p.exists():
            out[name] = {"missing": True, "path": str(p)}
            continue
        rows = json.loads(p.read_text(encoding="utf-8"))
        targets = [r["target"] for r in rows]
        ensgs = [r.get("meta", {}).get("ensg", "") for r in rows]
        uniq = sorted(set(targets))
        ensg_by = defaultdict(set)
        for t, e in zip(targets, ensgs):
            if e and e != "non-targeting":
                ensg_by[t].add(e)
        multi = {t: sorted(v) for t, v in ensg_by.items() if len(v) > 1}
        out[name] = {
            "n_rows": len(rows),
            "n_unique_targets": len(uniq),
            "n_with_ensg": sum(1 for t in uniq if ensg_by[t]),
            "n_multi_ensg": len(multi),
            "targets": uniq,
            "ensg_by_target": {t: sorted(v)[0] for t, v in ensg_by.items() if len(v) == 1},
            "multi_ensg_examples": dict(list(multi.items())[:8]),
        }
    return out


def parse_hgnc(path: Path) -> dict:
    df = pd.read_csv(path, sep="\t", dtype=str, low_memory=False)
    df = df.fillna("")
    approved = {}
    alias_to = defaultdict(set)
    for _, row in df.iterrows():
        sym = row.get("symbol", "")
        if not sym:
            continue
        rec = {
            "hgnc_id": row.get("hgnc_id", ""),
            "symbol": sym,
            "name": row.get("name", ""),
            "locus_group": row.get("locus_group", ""),
            "locus_type": row.get("locus_type", ""),
            "status": row.get("status", ""),
            "ensembl_gene_id": row.get("ensembl_gene_id", ""),
            "entrez_id": row.get("entrez_id", ""),
            "uniprot_ids": [u for u in str(row.get("uniprot_ids", "")).split("|") if u],
        }
        approved[sym] = rec
        for field in ("alias_symbol", "prev_symbol"):
            raw = str(row.get(field, "")).strip().strip('"')
            if not raw:
                continue
            for a in raw.split("|"):
                a = a.strip()
                if a and a != sym:
                    alias_to[a].add(sym)
    return {"n_rows": int(len(df)), "approved": approved, "alias_to": alias_to, "columns": list(df.columns)}


def map_symbols(symbols, hgnc: dict) -> dict:
    approved = hgnc["approved"]
    alias_to = hgnc["alias_to"]
    rows = []
    for s in symbols:
        if s in approved:
            rec = dict(approved[s])
            rec.update(query=s, match="approved", n_alias_hits=1)
            rows.append(rec)
            continue
        hits = sorted(alias_to.get(s, ()))
        if len(hits) == 1:
            rec = dict(approved[hits[0]])
            rec.update(query=s, match="unique_alias_or_previous", n_alias_hits=1)
            rows.append(rec)
        elif len(hits) > 1:
            rows.append({
                "query": s, "match": "ambiguous_alias", "n_alias_hits": len(hits),
                "candidates": hits[:8], "ensembl_gene_id": "", "uniprot_ids": [],
                "locus_group": "",
            })
        else:
            rows.append({
                "query": s, "match": "unmapped", "n_alias_hits": 0,
                "ensembl_gene_id": "", "uniprot_ids": [], "locus_group": "",
            })
    n = len(symbols)
    return {
        "n": n,
        "approved": sum(r["match"] == "approved" for r in rows),
        "unique_alias": sum(r["match"] == "unique_alias_or_previous" for r in rows),
        "ambiguous": sum(r["match"] == "ambiguous_alias" for r in rows),
        "unmapped": sum(r["match"] == "unmapped" for r in rows),
        "with_ensg": sum(1 for r in rows if r.get("ensembl_gene_id")),
        "with_uniprot": sum(1 for r in rows if r.get("uniprot_ids")),
        "protein_coding": sum(1 for r in rows if r.get("locus_group") == "protein-coding gene"),
        "rows": rows,
    }


def parse_gaf(path: Path) -> dict:
    """Index GO terms by UniProt accession and by gene symbol (column 3)."""
    by_uniprot = defaultdict(lambda: {"P": set(), "F": set(), "C": set(), "evidence": set()})
    by_symbol = defaultdict(lambda: {"P": set(), "F": set(), "C": set()})
    n = 0
    n_not = 0
    evidence = defaultdict(int)
    version_line = ""
    with _open_maybe_gzip(path) as fh:
        for line in fh:
            if line.startswith("!"):
                if "gaf-version" in line or "Generated" in line or "date-generated" in line.lower() or "GO-version" in line:
                    version_line += line.strip() + " | "
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 15:
                continue
            n += 1
            qual = parts[3]
            if "NOT" in qual:
                n_not += 1
                continue
            uid, symbol, goid, eco, aspect = parts[1], parts[2], parts[4], parts[6], parts[8]
            evidence[eco] += 1
            if aspect in "PFC":
                by_uniprot[uid][aspect].add(goid)
                by_uniprot[uid]["evidence"].add(eco)
                if symbol:
                    by_symbol[symbol][aspect].add(goid)
    return {
        "n_annotation_rows": n,
        "n_not_rows": n_not,
        "n_uniprot": len(by_uniprot),
        "n_symbols": len(by_symbol),
        "evidence_counts": dict(sorted(evidence.items(), key=lambda kv: -kv[1])),
        "header": version_line.strip(" |"),
        "by_uniprot": by_uniprot,
        "by_symbol": by_symbol,
    }


def parse_slim(path: Path) -> list[str]:
    terms = []
    current = None
    obsolete = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip() == "[Term]":
            if current and not obsolete:
                terms.append(current)
            current, obsolete = None, False
        elif line.startswith("id: GO:"):
            current = line.split("id: ", 1)[1].strip()
        elif line.startswith("is_obsolete: true"):
            obsolete = True
    if current and not obsolete:
        terms.append(current)
    return terms


def parse_obo_parents(path: Path) -> dict[str, set[str]]:
    parents = defaultdict(set)
    current = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip() == "[Term]":
            current = None
        elif line.startswith("id: GO:"):
            current = line.split("id: ", 1)[1].strip()
        elif current and (line.startswith("is_a: GO:") or line.startswith("relationship: part_of GO:")):
            token = line.split("GO:", 1)[1]
            parents[current].add("GO:" + token.split()[0])
    return parents


def ancestors(term: str, parents: dict[str, set[str]], cache: dict) -> set[str]:
    if term in cache:
        return cache[term]
    seen = {term}
    stack = [term]
    while stack:
        t = stack.pop()
        for p in parents.get(t, ()):
            if p not in seen:
                seen.add(p)
                stack.append(p)
    cache[term] = seen
    return seen


def go_coverage_for_mapped(mapped_rows, gaf, slim_ids, parents) -> dict:
    slim = set(slim_ids)
    cache = {}
    n = 0
    n_any = 0
    n_bp = 0
    n_slim = 0
    n_slim_prop = 0
    n_iea_only = 0
    missing = []
    missing_slim = []
    experimental = {"EXP", "IDA", "IPI", "IMP", "IGI", "IEP", "HTP", "HDA", "HMP", "HGI", "HEP"}
    for rec in mapped_rows:
        n += 1
        terms = {"P": set(), "F": set(), "C": set()}
        evid = set()
        for uid in rec.get("uniprot_ids") or []:
            block = gaf["by_uniprot"].get(uid)
            if block:
                for asp in "PFC":
                    terms[asp] |= block[asp]
                evid |= block["evidence"]
        if not any(terms.values()):
            block = gaf["by_symbol"].get(rec.get("symbol") or rec["query"])
            if block:
                for asp in "PFC":
                    terms[asp] |= block[asp]
        if any(terms.values()):
            n_any += 1
        if terms["P"]:
            n_bp += 1
        direct = (terms["P"] | terms["F"] | terms["C"]) & slim
        if direct:
            n_slim += 1
        prop = set()
        if parents:
            for t in terms["P"] | terms["F"] | terms["C"]:
                prop |= ancestors(t, parents, cache) & slim
            if prop:
                n_slim_prop += 1
        else:
            prop = set()
        if evid and evid <= {"IEA"}:
            n_iea_only += 1
        if not any(terms.values()):
            missing.append(rec["query"])
        elif parents and not prop:
            missing_slim.append(rec["query"])
    return {
        "n": n,
        "with_any_go": n_any,
        "with_bp": n_bp,
        "with_direct_slim": n_slim,
        "with_propagated_slim": n_slim_prop if parents else None,
        "iea_only_among_annotated": n_iea_only,
        "experimental_codes_considered": sorted(experimental),
        "missing_examples": missing[:20],
        "n_missing": len(missing),
        "missing_slim_examples": missing_slim,
        "n_slim_terms": len(slim),
    }


def parse_string_info(path: Path) -> dict:
    names = {}
    n = 0
    with _open_maybe_gzip(path) as fh:
        header = fh.readline()
        for line in fh:
            n += 1
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            pid, pref = parts[0], parts[1]
            names.setdefault(pref, []).append(pid)
    return {"n_proteins": n, "preferred_to_ids": names, "header": header.strip()}


def parse_string_physical(path: Path, keep_ids: set[str]) -> dict:
    """Count physical edges among a set of STRING ids. Combined score is *1000."""
    deg = defaultdict(int)
    n = 0
    with _open_maybe_gzip(path) as fh:
        header = fh.readline()
        for line in fh:
            parts = line.split()
            if len(parts) < 3:
                continue
            a, b, score = parts[0], parts[1], int(float(parts[2]))
            n += 1
            if a in keep_ids:
                deg[a] += 1
            if b in keep_ids and b != a:
                deg[b] += 1
    return {"n_edges_file": n, "degree": dict(deg), "header": header.strip()}


def parse_gene2vec(path: Path) -> dict:
    genes = []
    dim = None
    with path.open(encoding="utf-8", errors="replace") as fh:
        first = fh.readline().strip().split()
        offset = 0
        if len(first) == 2 and first[0].isdigit():
            dim = int(first[1])
        else:
            genes.append(first[0])
            dim = len(first) - 1
            offset = 1
        for line in fh:
            parts = line.split()
            if not parts:
                continue
            genes.append(parts[0])
            if dim is None:
                dim = len(parts) - 1
    return {"n_genes": len(genes), "dim": dim, "genes": set(genes)}


def summarise_mapping(name: str, mapped: dict) -> dict:
    return {k: mapped[k] for k in mapped if k != "rows"}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=ROOT / "reports" / "encoder_inputs_2026-09-14")
    p.add_argument(
        "--cache",
        type=Path,
        default=None,
        help="Download cache; default data_root/interim/encoder_inputs_2026-09-14",
    )
    p.add_argument("--skip-download", action="store_true")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    data_root = project_paths().data_root
    cache = args.cache or (data_root / "interim" / "encoder_inputs_2026-09-14")
    cache.mkdir(parents=True, exist_ok=True)

    disk = shutil.disk_usage(data_root)
    hardware = {"disk_total": disk.total, "disk_free": disk.free, "data_root": str(data_root)}
    (args.out / "hardware.json").write_text(json.dumps(hardware, indent=2), encoding="utf-8")

    local = load_official_lists(data_root)
    vcc = local["vcc_targets"]
    inv = local["inventory"]
    basal = {
        "n_inventory_rows": int(len(inv)),
        "k562_gwps_true": int(inv["k562_gwps"].sum()) if "k562_gwps" in inv else None,
        "missing_all_local": int(inv["missing_all_local_sources"].sum()) if "missing_all_local_sources" in inv else None,
        "all_300_have_A_cpm": bool((inv["A_mean_cpm"] > 0).all()) if "A_mean_cpm" in inv else None,
        "n_below_1cpm_any_context": int(
            ((inv["A_mean_cpm"] < 1) | (inv["B_mean_cpm"] < 1) | (inv["C_mean_cpm"] < 1)).sum()
        ) if "A_mean_cpm" in inv else None,
        "n_below_5cpm_any_context": int(
            ((inv["A_mean_cpm"] < 5) | (inv["B_mean_cpm"] < 5) | (inv["C_mean_cpm"] < 5)).sum()
        ) if "A_mean_cpm" in inv else None,
    }
    sigs = load_signature_targets(data_root / "artifacts" / "e001" / "signatures")
    train_k562 = sigs.get("k562_gwps", {}).get("targets") or []

    cd4_path = ROOT / "reports" / "candidate_verification" / "annotations" / "cd4_design.csv"
    cd4 = {}
    if cd4_path.exists():
        d = pd.read_csv(cd4_path)
        genes = set(d["perturbed_gene_name"].astype(str))
        ids = dict(zip(d["perturbed_gene_name"].astype(str), d["perturbed_gene_id"].astype(str)))
        cd4 = {
            "n_library_genes": len(genes),
            "vcc_in_library": int(sum(t in genes for t in vcc)),
            "vcc_with_ensg_in_library": int(sum(t in ids and ids[t].startswith("ENSG") for t in vcc)),
        }

    local_report = {
        "retrieved_at": _now(),
        "official": {k: local[k] for k in local if k not in {"vcc_targets", "axis_set", "inventory"}},
        "basal_from_target_inventory": basal,
        "signatures": {k: {kk: vv for kk, vv in rec.items() if kk not in {"targets", "ensg_by_target"}} for k, rec in sigs.items()},
        "cd4_design": cd4,
        "existing_descriptor_bank": {
            "source": "src/vcc2026/benchmark/descriptors.py",
            "unseen_with_context_n_features_measured": 41,
            "unseen_without_context_n_features_measured": 4,
            "evidence": "reports/benchmark_2026-09-14/splits/new_context_unseen_target_k562_to_rpe1_seed2026.json",
            "response_codes_forbidden_for_unseen": True,
        },
    }
    (args.out / "local_inventory.json").write_text(json.dumps(local_report, indent=2), encoding="utf-8")

    heads = {"retrieved_at": _now(), "candidates": {}, "head_only": {}}
    downloads = {"retrieved_at": _now(), "files": {}}
    timeout = httpx.Timeout(60.0, connect=30.0)
    with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": "vcc2026-descriptor-probe"}) as client:
        for key, spec in CANDIDATES.items():
            heads["candidates"][key] = {**spec, **_head(client, spec["url"])}
        for key, spec in HEAD_ONLY.items():
            heads["head_only"][key] = {**spec, **_head(client, spec["url"])}
        (args.out / "remote_heads.json").write_text(json.dumps(heads, indent=2), encoding="utf-8")

        if not args.skip_download:
            for key, spec in CANDIDATES.items():
                dest = cache / key
                max_bytes = int(spec["max_mb"] * 1024 * 1024)
                rec = _download(client, spec["url"], dest, max_bytes)
                rec.update(family=spec["family"], role=spec["role"], license=spec["license"])
                downloads["files"][key] = rec
                print(key, rec.get("status"), rec.get("bytes"), rec.get("skipped"), rec.get("error", ""), flush=True)
        (args.out / "downloads.json").write_text(json.dumps(downloads, indent=2), encoding="utf-8")

    hgnc = None
    hgnc_path = cache / "hgnc_complete_set"
    coverage = {"retrieved_at": _now()}
    if hgnc_path.exists() and hgnc_path.stat().st_size > 0:
        hgnc = parse_hgnc(hgnc_path)
        vcc_map = map_symbols(vcc, hgnc)
        train_map = map_symbols(train_k562, hgnc) if train_k562 else None
        coverage["hgnc"] = {
            "n_approved_symbols": len(hgnc["approved"]),
            "n_columns": len(hgnc["columns"]),
            "columns": hgnc["columns"],
            "vcc300": summarise_mapping("vcc", vcc_map),
            "k562_gwps_unique_targets": summarise_mapping("train", train_map) if train_map else None,
        }
        unmapped_vcc = [r["query"] for r in vcc_map["rows"] if r["match"] in {"unmapped", "ambiguous_alias"}]
        coverage["hgnc"]["vcc300"]["unmapped_or_ambiguous"] = unmapped_vcc
        (args.out / "hgnc_vcc300_mapping.csv").write_text(
            pd.DataFrame([
                {
                    "query": r["query"],
                    "match": r["match"],
                    "symbol": r.get("symbol", ""),
                    "ensembl_gene_id": r.get("ensembl_gene_id", ""),
                    "uniprot_ids": "|".join(r.get("uniprot_ids") or []),
                    "locus_group": r.get("locus_group", ""),
                    "locus_type": r.get("locus_type", ""),
                }
                for r in vcc_map["rows"]
            ]).to_csv(index=False),
            encoding="utf-8",
        )
    else:
        coverage["hgnc"] = {"downloaded": False}

    gaf = None
    gaf_path = cache / "goa_human_gaf"
    slim_ids = []
    parents = {}
    slim_path = cache / "goslim_generic"
    obo_path = cache / "go_basic_obo"
    if slim_path.exists() and slim_path.stat().st_size > 0:
        slim_ids = parse_slim(slim_path)
        coverage["goslim"] = {"n_terms": len(slim_ids), "term_examples": slim_ids[:15]}
    if obo_path.exists() and obo_path.stat().st_size > 1000:
        parents = parse_obo_parents(obo_path)
        coverage["go_basic"] = {"n_terms_with_parents": len(parents)}
    if gaf_path.exists() and gaf_path.stat().st_size > 0 and hgnc is not None:
        gaf = parse_gaf(gaf_path)
        coverage["goa"] = {
            "n_annotation_rows": gaf["n_annotation_rows"],
            "n_not_rows": gaf["n_not_rows"],
            "n_uniprot": gaf["n_uniprot"],
            "n_symbols": gaf["n_symbols"],
            "evidence_counts": gaf["evidence_counts"],
            "header": gaf["header"],
            "vcc300": go_coverage_for_mapped(vcc_map["rows"], gaf, slim_ids, parents),
        }
        if train_k562:
            coverage["goa"]["k562_gwps_unique_targets"] = go_coverage_for_mapped(
                train_map["rows"], gaf, slim_ids, parents
            )

    info_path = cache / "string_protein_info"
    if info_path.exists() and info_path.stat().st_size > 0:
        sinfo = parse_string_info(info_path)
        vcc_hit = [t for t in vcc if t in sinfo["preferred_to_ids"]]
        multi = [t for t in vcc_hit if len(sinfo["preferred_to_ids"][t]) > 1]
        coverage["string_info"] = {
            "n_proteins": sinfo["n_proteins"],
            "vcc_preferred_name_hits": len(vcc_hit),
            "vcc_preferred_name_multi_id": len(multi),
            "vcc_miss_examples": [t for t in vcc if t not in sinfo["preferred_to_ids"]][:20],
            "k562_gwps_preferred_name_hits": int(sum(t in sinfo["preferred_to_ids"] for t in train_k562)) if train_k562 else None,
        }
        phys_path = cache / "string_physical_links"
        if phys_path.exists() and phys_path.stat().st_size > 0:
            keep = set()
            for t in vcc_hit:
                keep.update(sinfo["preferred_to_ids"][t])
            phys = parse_string_physical(phys_path, keep)
            degs = []
            for t in vcc_hit:
                degs.append(sum(phys["degree"].get(pid, 0) for pid in sinfo["preferred_to_ids"][t]))
            coverage["string_physical"] = {
                "n_edges_in_file": phys["n_edges_file"],
                "vcc_with_degree_gt0": int(sum(d > 0 for d in degs)),
                "median_degree_among_mapped": float(pd.Series(degs).median()) if degs else None,
            }

    g2v_path = cache / "gene2vec"
    if g2v_path.exists() and g2v_path.stat().st_size > 0:
        g2v = parse_gene2vec(g2v_path)
        coverage["gene2vec"] = {
            "n_genes": g2v["n_genes"],
            "dim": g2v["dim"],
            "vcc_hits": int(sum(t in g2v["genes"] for t in vcc)),
            "vcc_miss_examples": [t for t in vcc if t not in g2v["genes"]][:20],
            "k562_gwps_hits": int(sum(t in g2v["genes"] for t in train_k562)) if train_k562 else None,
            "training_note": "Du et al. 2019: 200-d from co-expression in 984 GEO datasets, not protein sequence",
        }

    replogle_vs_hgnc = {}
    if hgnc is not None and "ensg_by_target" in sigs.get("k562_gwps", {}):
        agree = disagree = missing = 0
        examples = []
        for t, e in sigs["k562_gwps"]["ensg_by_target"].items():
            rec = hgnc["approved"].get(t)
            if rec is None:
                missing += 1
                continue
            he = rec.get("ensembl_gene_id") or ""
            if not he:
                missing += 1
            elif he == e:
                agree += 1
            else:
                disagree += 1
                if len(examples) < 10:
                    examples.append({"symbol": t, "replogle": e, "hgnc": he})
        replogle_vs_hgnc = {
            "agree": agree, "disagree": disagree, "missing_or_no_hgnc_ensg": missing,
            "disagree_examples": examples,
        }
    coverage["replogle_ensg_vs_hgnc"] = replogle_vs_hgnc

    (args.out / "coverage.json").write_text(json.dumps(coverage, indent=2, default=str), encoding="utf-8")

    summary = {
        "retrieved_at": _now(),
        "claim_type": {
            "local_lists": "measured",
            "remote_heads": "verified_on_file_or_headers",
            "downloads": "verified_on_file" if not args.skip_download else "not_run",
            "coverage": "verified_on_file" if hgnc is not None else "not_run",
        },
        "vcc_targets": local_report["official"]["n_vcc_targets"],
        "vcc_on_official_axis": local_report["official"]["vcc_on_axis"],
        "hgnc": coverage.get("hgnc"),
        "goa_vcc": coverage.get("goa", {}).get("vcc300") if isinstance(coverage.get("goa"), dict) else None,
        "string_vcc": coverage.get("string_info"),
        "gene2vec_vcc": coverage.get("gene2vec"),
        "skipped_large": {k: {"declared_size": v["declared_size"], "why_skip": v["why_skip"]} for k, v in HEAD_ONLY.items()},
        "cache": str(cache),
        "out": str(args.out),
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print("wrote", args.out / "summary.json", flush=True)


if __name__ == "__main__":
    main()
