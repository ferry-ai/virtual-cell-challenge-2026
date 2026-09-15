"""Freeze the table `gene symbol -> 140 GO slim bits + missing indicator`.

The join is the whole point, so it is written down and frozen rather than
recomputed at fit time:

    symbol -> HGNC (approved, else a *unique* alias or previous symbol)
           -> UniProt accession(s)
           -> GAF rows for those accessions, dropping NOT-qualified ones
           -> ancestral closure over is_a / part_of in go-basic.obo
           -> intersection with goslim_generic

A symbol whose HGNC match is ambiguous, or whose closure never meets the slim,
gets `missing = 1` and 140 zeros -- never a silent row of zeros that reads like
«annotated, and none of these apply». The four source files are hashed into the
manifest, because the table is only reproducible against those bytes.

Nothing here reads a perturbation response: that is what makes these descriptors
legal for a target excluded from every training response (mode B).

    scripts/py.cmd scripts/58_build_go_slim_table.py --out <artifacts>/g001
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config
from vcc2026.manifest import RunManifest

CACHE = Path("C:/Users/ferra/vcc2026-data/interim/encoder_inputs_2026-09-14")
SOURCES = {
    "hgnc_complete_set": CACHE / "hgnc_complete_set",
    "goa_human_gaf": CACHE / "goa_human_gaf",
    "goslim_generic": CACHE / "goslim_generic",
    "go_basic_obo": CACHE / "go_basic_obo",
}


def sha256(path: Path, block: int = 1 << 22) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(block):
            digest.update(chunk)
    return digest.hexdigest()


def read_slim_terms(path: Path) -> list[str]:
    terms, current = [], None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line == "[Term]":
            current = None
        elif line.startswith("id: GO:"):
            current = line.split("id: ", 1)[1].strip()
        elif line.startswith("is_obsolete: true"):
            current = None
        if current and current not in terms and line.startswith("id: GO:"):
            terms.append(current)
    return terms


def read_go_parents(path: Path) -> tuple[dict[str, set[str]], dict[str, str]]:
    """is_a and part_of parents, plus alt_id -> primary id."""
    parents: dict[str, set[str]] = defaultdict(set)
    alt_of: dict[str, str] = {}
    current = None
    obsolete = False
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.rstrip()
            if line == "[Term]":
                current, obsolete = None, False
            elif line.startswith("id: GO:"):
                current = line[4:].strip()
            elif line.startswith("is_obsolete: true"):
                obsolete = True
                if current:
                    parents.pop(current, None)
                current = None
            elif current and not obsolete:
                if line.startswith("alt_id: GO:"):
                    alt_of[line[8:].strip()] = current
                elif line.startswith("is_a: GO:"):
                    parents[current].add(line[6:].split("!")[0].strip())
                elif line.startswith("relationship: part_of GO:"):
                    parents[current].add(
                        line.split("part_of", 1)[1].split("!")[0].strip()
                    )
    return parents, alt_of


def ancestors(term: str, parents: dict[str, set[str]], cache: dict[str, set[str]]) -> set[str]:
    if term in cache:
        return cache[term]
    out = {term}
    stack = list(parents.get(term, ()))
    seen = set()
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        out.add(node)
        if node in cache:
            out |= cache[node]
            continue
        stack.extend(parents.get(node, ()))
    cache[term] = out
    return out


def hgnc_symbol_to_uniprot(path: Path) -> tuple[dict[str, list[str]], dict]:
    frame = pd.read_csv(path, sep="\t", dtype=str, low_memory=False)
    frame = frame[frame.status.fillna("") == "Approved"]
    approved: dict[str, list[str]] = {}
    for symbol, ids in zip(frame.symbol.fillna(""), frame.uniprot_ids.fillna("")):
        if symbol:
            approved[symbol] = [i for i in ids.split("|") if i]

    # An alias resolves only when it points at exactly one approved symbol, and
    # only when it is not itself an approved symbol of another gene.
    alias_hits: dict[str, set[str]] = defaultdict(set)
    for column in ("alias_symbol", "prev_symbol"):
        for symbol, raw in zip(frame.symbol.fillna(""), frame[column].fillna("")):
            for alias in (a for a in raw.split("|") if a):
                alias_hits[alias].add(symbol)
    alias_map = {
        alias: next(iter(targets))
        for alias, targets in alias_hits.items()
        if len(targets) == 1 and alias not in approved
    }
    stats = {
        "n_approved_symbols": len(approved),
        "n_unique_aliases": len(alias_map),
        "n_ambiguous_aliases": sum(1 for t in alias_hits.values() if len(t) > 1),
    }
    return approved, {"alias_map": alias_map, **stats}


def gaf_go_by_accession(path: Path) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    n_not = 0
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith("!"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 5:
                continue
            accession, qualifier, go_id = parts[1], parts[3], parts[4]
            if "NOT" in qualifier.split("|"):
                n_not += 1
                continue
            if go_id.startswith("GO:"):
                out[accession].add(go_id)
    out["__n_not_dropped__"] = n_not  # carried out, popped by the caller
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None,
                        help="directory for go_slim_table.npz; defaults to <artifacts>/g001")
    parser.add_argument("--symbols-from", type=Path, nargs="*", default=None,
                        help="signature directories whose targets must be covered")
    parser.add_argument("--allow-overwrite", action="store_true")
    args = parser.parse_args()

    out_dir = args.out or (config.paths().data_root / "artifacts" / "g001")
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / "go_slim_table.npz"
    if dest.exists() and not args.allow_overwrite:
        raise FileExistsError(f"{dest} exists; give a new --out (never overwrite)")

    missing_files = [k for k, p in SOURCES.items() if not p.exists()]
    if missing_files:
        raise SystemExit(f"missing cached sources: {missing_files}; run script 56 first")

    print("leggo HGNC", flush=True)
    approved, hgnc_stats = hgnc_symbol_to_uniprot(SOURCES["hgnc_complete_set"])
    alias_map = hgnc_stats.pop("alias_map")

    print("leggo il GAF", flush=True)
    go_by_acc = gaf_go_by_accession(SOURCES["goa_human_gaf"])
    n_not_dropped = go_by_acc.pop("__n_not_dropped__")

    print("leggo go-basic.obo", flush=True)
    parents, alt_of = read_go_parents(SOURCES["go_basic_obo"])
    slim_terms = read_slim_terms(SOURCES["goslim_generic"])
    slim_index = {term: i for i, term in enumerate(slim_terms)}
    print(f"  termini slim: {len(slim_terms)}", flush=True)

    # Which symbols to materialise: every perturbed target we have, plus the panel.
    wanted: set[str] = set()
    dirs = args.symbols_from or [
        config.paths().data_root / "artifacts" / "e001" / "signatures",
        config.paths().data_root / "artifacts" / "e003" / "signatures",
    ]
    for directory in dirs:
        for rows in Path(directory).glob("*.rows.json"):
            wanted |= {
                str(r["target"])
                for r in json.loads(rows.read_text(encoding="utf-8"))
            }
    panel_csv = config.paths().raw / "controls" / "pert_counts.csv"
    panel = set(pd.read_csv(panel_csv).target_gene.astype(str)) if panel_csv.exists() else set()
    wanted |= panel
    symbols = sorted(wanted)
    print(f"  simboli da annotare: {len(symbols)}", flush=True)

    cache: dict[str, set[str]] = {}
    bits = np.zeros((len(symbols), len(slim_terms)), dtype=bool)
    missing = np.ones(len(symbols), dtype=bool)
    resolution = []
    for i, symbol in enumerate(symbols):
        how, accessions = "approved", approved.get(symbol)
        if accessions is None:
            target = alias_map.get(symbol)
            if target is not None:
                how, accessions = f"alias->{target}", approved.get(target, [])
            else:
                how, accessions = "unmapped", []
        go_ids: set[str] = set()
        for accession in accessions:
            go_ids |= go_by_acc.get(accession, set())
        go_ids = {alt_of.get(g, g) for g in go_ids}
        closed: set[str] = set()
        for go_id in go_ids:
            closed |= ancestors(go_id, parents, cache)
        hit = [slim_index[t] for t in closed & slim_index.keys()]
        if hit:
            bits[i, hit] = True
            missing[i] = False
        resolution.append({
            "symbol": symbol, "how": how, "n_uniprot": len(accessions),
            "n_go_direct": len(go_ids), "n_slim_bits": len(hit),
        })

    np.savez_compressed(
        dest,
        symbols=np.asarray(symbols, dtype=object),
        bits=bits,
        missing=missing,
        slim_terms=np.asarray(slim_terms, dtype=object),
    )

    frame = pd.DataFrame(resolution)
    frame.to_csv(out_dir / "go_slim_resolution.csv", index=False)
    summary = {
        "n_symbols": len(symbols),
        "n_slim_terms": len(slim_terms),
        "n_with_slim": int((~missing).sum()),
        "n_missing": int(missing.sum()),
        "median_bits_when_present": float(
            np.median(bits[~missing].sum(axis=1)) if (~missing).any() else 0.0
        ),
        "resolution_counts": frame.how.str.split("->").str[0].value_counts().to_dict(),
        "panel": {
            "n_panel": len(panel),
            "n_panel_with_slim": int(sum(
                not missing[symbols.index(s)] for s in panel if s in wanted
            )),
        },
        "gaf": {"n_not_qualified_rows_dropped": n_not_dropped},
        "hgnc": hgnc_stats,
        "sources": {k: {"path": str(p), "bytes": p.stat().st_size, "sha256": sha256(p)}
                    for k, p in SOURCES.items()},
        "not_derived_from_perturbative_response": True,
    }
    (out_dir / "go_slim_summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )

    manifest = RunManifest(
        run_id=out_dir.name, stage="58_build_go_slim_table",
        config={k: str(v) for k, v in vars(args).items()},
    )
    for name, path in SOURCES.items():
        manifest.add_input(name, path)
    manifest.add_output("table", dest)
    manifest.metrics = {k: summary[k] for k in
                        ("n_symbols", "n_slim_terms", "n_with_slim", "n_missing")}
    manifest.note("No perturbation response is read here; the table is legal in mode B.")
    manifest.write(out_dir / "manifest_58_go_slim_table.json",
                   allow_overwrite=args.allow_overwrite)
    print(json.dumps(summary["resolution_counts"], indent=2))
    print(json.dumps({k: summary[k] for k in ("n_symbols", "n_with_slim", "n_missing")},
                     indent=2))
    print(f"-> {dest}")


if __name__ == "__main__":
    main()
