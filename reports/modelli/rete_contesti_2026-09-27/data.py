"""Assemble the network's compact dataset from N genome-wide universes and the basal table (runs locally).

Reads the context registry (`contesti.csv`: context, universe, prefix, basal, family, group, se_factor, weight,
modality), each universe's stage-98 npz chunks through its index.csv, the basal CPM table, the gene coordinates,
the panel, the K562 essential screen and the STRING physical links; writes a NEW folder in the format documented
in pool.py: one float16 row per (context, target) for raw, se and shrunk on the stored genes, the tables, and
manifest.json with the size of every file.

Two passes over the chunks. The first reads `targets`, `n_cells` and `raw` only: it counts the rows and, per gene,
how often each context measures it. The stored genes are those that at least --min-families families measure in
at least --min-frac of their rows (the exclusion the t23 ablation supports, reports/trasferimento/ablazione_t23_2026-09-27/;
each training design narrows it again to its own training families). The second pass writes the rows.

Leakage (D-044). Nothing here turns a perturbation outcome into a feature: whether a universe has a finite value
for a gene is decided by its estimator from the controls and the size of each target group, not from the gene's
response; the priors come from controls, coordinates and STRING. The dataset holds every context; each design's
exclusions are applied by train.py (pool.Phase) to the visible rows. --exclude-targets also drops rows here, for a
dataset without them on disk.

    scripts/py.cmd reports/modelli/rete_contesti_2026-09-27/data.py --out C:/Users/ferra/vcc2026-data/processed/rete_contesti_r1
    scripts/py.cmd reports/modelli/rete_contesti_2026-09-27/data.py --out <new dir> --dry-run          (sizes only)
    scripts/py.cmd reports/modelli/rete_contesti_2026-09-27/data.py --out <new dir> --contexts k562,orion_hct116 --check-reader 20
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(HERE))

import pool as P  # noqa: E402
from vcc2026.config import paths  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402
from vcc2026.predictor_sc import load_coordinates  # noqa: E402

REGISTRY_COLUMNS = ("context", "universe", "prefix", "basal", "family", "group", "se_factor")
HASH_LIMIT = 200_000_000          # bytes; larger inputs are recorded by size only


def log(msg: str, t0=time.time()) -> None:
    print(f"[{time.time() - t0:8.1f}s] {msg}", flush=True)


def resolve(root: Path, value) -> Path:
    p = Path(str(value))
    return p if p.is_absolute() else root / p


def chunk_files(folder: Path, prefix: str) -> list[str]:
    """The universe's chunk files in index order, resolved as atlas_bench.Universe does: a numeric chunk is
    <prefix>_<chunk:03d>.npz (the CD4 conditions share one index), a string names the file; an empty chunk is a
    target without effects."""
    idx = pd.read_csv(folder / "index.csv", keep_default_na=False, na_values=[""], dtype={"target": str})
    idx = idx[idx["chunk"].notna() & (idx["chunk"].astype(str).str.strip() != "")].copy()
    if pd.api.types.is_numeric_dtype(idx["chunk"]):
        files = [f"{prefix}_{int(c):03d}.npz" for c in idx["chunk"]]
    else:
        files = idx["chunk"].astype(str).str.strip().tolist()
    return list(dict.fromkeys(files))


def string_tables(links: Path, info: Path, min_score: int) -> pd.DataFrame:
    """STRING edges as symbols (a, b, score >= min_score), both directions, the best score per pair; read as
    vcc2026.priors.partner_effects reads the same files (gzip without the extension)."""
    def gz(path: Path):
        with open(path, "rb") as fh:
            return "gzip" if fh.read(2) == b"\x1f\x8b" else None
    names = pd.read_csv(info, sep="\t", usecols=[0, 1], compression=gz(info))
    sym = dict(zip(names.iloc[:, 0].astype(str), names.iloc[:, 1].astype(str)))
    edges = pd.read_csv(links, sep=" ", compression=gz(links))
    edges = edges[edges["combined_score"] >= min_score]
    e = pd.DataFrame({"a": edges["protein1"].astype(str).map(sym), "b": edges["protein2"].astype(str).map(sym),
                      "score": edges["combined_score"].astype(float)}).dropna()
    e = e[e["a"] != e["b"]]
    both = pd.concat([e, e.rename(columns={"a": "b", "b": "a"})], ignore_index=True)
    return both.groupby(["a", "b"], as_index=False)["score"].max()


def near_counts(coords: pd.DataFrame, symbols: list, windows: tuple) -> dict:
    """For each symbol with coordinates, how many other coordinate genes have a TSS within each window (bp)."""
    chrom = coords["chrom"].astype(str)
    tss = pd.to_numeric(coords["tss"], errors="coerce")
    by = {}
    for c, sub in tss[tss.notna()].groupby(chrom[tss.notna()]):
        by[c] = np.sort(sub.to_numpy(dtype=np.float64))
    out = {w: np.full(len(symbols), np.nan) for w in windows}
    for i, s in enumerate(symbols):
        if s not in coords.index or not np.isfinite(tss.get(s, np.nan)):
            continue
        pos = by[str(coords.at[s, "chrom"])]
        for w in windows:
            n = np.searchsorted(pos, tss[s] + w, side="right") - np.searchsorted(pos, tss[s] - w, side="left")
            out[w][i] = n - 1
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True, help="new folder (refused if it exists)")
    ap.add_argument("--registry", type=Path, default=HERE / "contesti.csv")
    ap.add_argument("--contexts", default="", help="comma-separated subset of the registry (default: every row)")
    ap.add_argument("--data-root", type=Path, default=None, help="default: configs/config.yaml (VCC2026_DATA_ROOT)")
    ap.add_argument("--basal", default="processed/basal_sources_2026-09-27.csv")
    ap.add_argument("--extra-basal", default="A,B,C", help="basal columns kept as basal-only contexts")
    ap.add_argument("--coords", default="external/annotation/gene_coordinates_gencode_v50.tsv")
    ap.add_argument("--panel", default="raw/controls/pert_counts.csv")
    ap.add_argument("--essential", default="external/K562_essential_raw_bulk_01.h5ad")
    ap.add_argument("--string-links", default="interim/encoder_inputs_2026-09-14/string_physical_links")
    ap.add_argument("--string-info", default="interim/encoder_inputs_2026-09-14/string_protein_info")
    ap.add_argument("--string-min-score", type=int, default=700)
    ap.add_argument("--max-partners", type=int, default=32)
    ap.add_argument("--min-frac", type=float, default=0.5)
    ap.add_argument("--min-families", type=int, default=2)
    ap.add_argument("--cis-bp", type=int, default=5000, help="genes within this TSS distance of a target: out of its loss")
    ap.add_argument("--extra-targets", type=Path, default=None, help="targets to describe even without rows")
    ap.add_argument("--exclude-targets", type=Path, default=None, help="targets whose rows are not written")
    ap.add_argument("--target-features", type=Path, default=None, help="CSV: symbol, numeric columns (x_ priors)")
    ap.add_argument("--dry-run", action="store_true", help="first pass only: print the sizes, write nothing")
    ap.add_argument("--check-reader", type=int, default=0, help="rows per context checked against atlas_bench.Universe")
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists: a dataset is never overwritten")
    root = args.data_root or paths().data_root
    started = datetime.now(timezone.utc).isoformat()

    reg = pd.read_csv(args.registry, keep_default_na=False, na_values=[""], dtype=str)
    missing = [c for c in REGISTRY_COLUMNS if c not in reg.columns]
    if missing:
        raise SystemExit(f"{args.registry} lacks {missing}")
    reg["weight"] = reg["weight"] if "weight" in reg.columns else "1"
    reg["modality"] = reg["modality"] if "modality" in reg.columns else "crispri"
    if args.contexts:
        want = [c.strip() for c in args.contexts.split(",") if c.strip()]
        unknown = sorted(set(want) - set(reg["context"]))
        if unknown:
            raise SystemExit(f"contexts {unknown} are not in {args.registry}")
        reg = reg[reg["context"].isin(want)]
    reg = reg.reset_index(drop=True)
    if reg["context"].duplicated().any():
        raise SystemExit("duplicate contexts in the registry")
    folders = [resolve(root, u) for u in reg["universe"]]
    absent = [str(f) for f in folders if not (f / "index.csv").exists()]
    if absent:
        raise SystemExit(f"universes without index.csv: {absent}; choose --contexts")

    axis = [str(s) for s in official_axis().symbols]
    A = len(axis)
    col = {g: i for i, g in enumerate(axis)}
    basal_path = resolve(root, args.basal)
    table = pd.read_csv(basal_path, keep_default_na=False, na_values=[""], dtype={"gene_name": str})
    if table["gene_name"].duplicated().any():
        raise SystemExit(f"{basal_path}: duplicate gene names")
    table = table.set_index("gene_name").reindex(axis)
    extra_basal = [c.strip() for c in args.extra_basal.split(",") if c.strip()]
    basal_names = list(dict.fromkeys(list(reg["basal"]) + extra_basal))
    lacking = [c for c in basal_names if c not in table.columns]
    if lacking:
        raise SystemExit(f"{basal_path} lacks basal columns {lacking}")
    basal = np.vstack([pd.to_numeric(table[c], errors="coerce").to_numpy(dtype=np.float32) for c in basal_names])
    excluded: set = set()
    if args.exclude_targets:
        excluded = {s.strip() for s in args.exclude_targets.read_text(encoding="utf-8").splitlines() if s.strip()}
        log(f"{len(excluded)} targets excluded from every context")

    # ---- pass 1: rows and measured genes per context
    plan, fin_count, n_rows_ctx, target_set = [], [], [], set()
    for i, r in reg.iterrows():
        folder, prefix = folders[i], r["prefix"]
        files, seen, count, n_ctx_rows = chunk_files(folder, prefix), set(), np.zeros(A, dtype=np.int64), 0
        per_file = []
        for f in files:
            path = folder / f
            if not path.exists():
                raise SystemExit(f"{r['context']}: {path} is missing")
            with np.load(path, allow_pickle=False) as z:
                tg = z["targets"].astype(str)
                raw = z["raw"]
            if raw.shape != (tg.size, A):
                raise SystemExit(f"{path}: raw is {raw.shape}, expected ({tg.size}, {A})")
            keep = np.array([t not in excluded for t in tg], dtype=bool)
            dup = seen & set(tg[keep])
            if dup:
                raise SystemExit(f"{r['context']}: targets in two chunks, e.g. {sorted(dup)[:5]}")
            seen |= set(tg[keep])
            target_set |= set(tg[keep])
            count += np.isfinite(raw[keep]).sum(axis=0)
            n_ctx_rows += int(keep.sum())
            per_file.append((f, keep))
        plan.append(per_file)
        fin_count.append(count)
        n_rows_ctx.append(n_ctx_rows)
        log(f"pass 1 {r['context']}: {n_ctx_rows} rows in {len(files)} chunks")
    fams = sorted(set(reg["family"]))
    frac = np.vstack([fc / max(n, 1) for fc, n in zip(fin_count, n_rows_ctx)])
    fam_frac = np.vstack([frac[(reg["family"] == f).to_numpy()].max(axis=0) for f in fams])
    n_fam = (fam_frac >= args.min_frac).sum(axis=0)
    genes_axis = np.flatnonzero(n_fam >= min(args.min_families, len(fams))).astype(np.int64)
    n_rows = int(sum(n_rows_ctx))
    G = genes_axis.size
    planned = {"arrays": 3 * n_rows * G * 2, "row_tables": n_rows * (4 + 4 + 4 + 8),
               "basal": len(basal_names) * A * 4}
    log(f"stored genes: {G} of {A} (measured in >= {args.min_frac} of the rows of >= {args.min_families} families); "
        f"{n_rows} rows; planned bytes {planned} (total {sum(planned.values())})")
    if args.dry_run:
        return

    # ---- tables
    extra = []
    if args.extra_targets:
        extra = [s.strip() for s in args.extra_targets.read_text(encoding="utf-8").splitlines() if s.strip()]
        target_set |= set(extra)
    names = sorted(target_set)
    tindex = {t: i for i, t in enumerate(names)}
    t_axis = np.array([col.get(t, -1) for t in names], dtype=np.int64)
    gpos = np.full(A, -1, dtype=np.int64)
    gpos[genes_axis] = np.arange(G)
    t_gene = np.where(t_axis >= 0, gpos[np.clip(t_axis, 0, None)], -1)
    panel = set(pd.read_csv(resolve(root, args.panel)).iloc[:, 0].astype(str))
    ess_path = resolve(root, args.essential)
    essential, ess_note = set(), "not read"
    if ess_path.exists():
        import h5py
        with h5py.File(ess_path, "r") as fh:
            labels = [s.decode() for s in fh["obs/gene_transcript"][:]]
        essential = {lab.split("_")[1] for lab in labels if "non-targeting" not in lab}
        ess_note = f"{len(essential)} targets"
    else:
        log(f"{ess_path} not found: no target is flagged essential")
    coords = load_coordinates(resolve(root, args.coords))
    chrom = np.array([str(coords.at[t, "chrom"]) if t in coords.index else "" for t in names], dtype=object)
    tss = np.array([float(coords.at[t, "tss"]) if t in coords.index else np.nan for t in names], dtype=np.float64)
    targets = pd.DataFrame({"target": names, "axis_index": t_axis, "gene_index": t_gene,
                            "in_panel": [t in panel for t in names], "essential": [t in essential for t in names],
                            "chrom": chrom, "tss": tss})
    src_basal = np.vstack([basal[basal_names.index(b)] for b in dict.fromkeys(reg["basal"])])
    targets = pd.concat([targets, P.basal_priors(src_basal, t_axis)], axis=1)
    near = near_counts(coords, names, (5000, 20000))
    targets["p_cis5k"] = np.log1p(near[5000])
    targets["p_cis20k"] = np.log1p(near[20000])
    links, info = resolve(root, args.string_links), resolve(root, args.string_info)
    edges = string_tables(links, info, args.string_min_score)
    deg = edges.groupby("a")["b"].nunique()
    targets["p_string_deg"] = np.log1p(np.array([float(deg.get(t, 0)) for t in names]))
    known = set(tindex)
    inside = edges[edges["a"].isin(known) & edges["b"].isin(known)].sort_values(["a", "score", "b"],
                                                                                ascending=[True, False, True])
    plist, slist = [[] for _ in names], [[] for _ in names]
    for a, sub in inside.groupby("a", sort=False):
        top = sub.head(args.max_partners)
        plist[tindex[a]] = [tindex[b] for b in top["b"]]
        slist[tindex[a]] = top["score"].tolist()
    p_ip, p_ix = P.csr(plist)
    p_sc = np.array([s for x in slist for s in x], dtype=np.float32)
    if args.target_features:
        xf = pd.read_csv(args.target_features, keep_default_na=False, na_values=[""])
        xf = xf.set_index(xf.columns[0])
        xf.index = xf.index.astype(str)
        xf = xf[~xf.index.duplicated()].apply(pd.to_numeric, errors="coerce").reindex(names)
        xf.columns = [f"x_{c}" for c in xf.columns]
        targets = pd.concat([targets, xf.reset_index(drop=True)], axis=1)
    # cis windows on the stored genes
    g_chrom = np.array([str(coords.at[axis[g], "chrom"]) if axis[g] in coords.index else "" for g in genes_axis], dtype=object)
    g_tss = np.array([float(coords.at[axis[g], "tss"]) if axis[g] in coords.index else np.nan for g in genes_axis])
    by = {}
    okg = np.isfinite(g_tss)
    for c in np.unique(g_chrom[okg]):
        idx = np.flatnonzero(okg & (g_chrom == c))
        idx = idx[np.argsort(g_tss[idx], kind="stable")]
        by[c] = (idx, g_tss[idx])
    cis_lists = []
    for i, t in enumerate(names):
        if not np.isfinite(tss[i]) or chrom[i] not in by:
            cis_lists.append([])
            continue
        idx, pos = by[chrom[i]]
        lo = np.searchsorted(pos, tss[i] - args.cis_bp, side="left")
        hi = np.searchsorted(pos, tss[i] + args.cis_bp, side="right")
        cis_lists.append([int(j) for j in idx[lo:hi] if j != t_gene[i]])

    # ---- pass 2: the rows
    writer = P.DatasetWriter(args.out, n_rows, genes_axis)
    ctx_rows = []
    for i, r in reg.iterrows():
        start = writer.pos
        for f, keep in plan[i]:
            with np.load(folders[i] / f, allow_pickle=False) as z:
                tg = z["targets"].astype(str)[keep]
                raw, se, sh = (z[k][keep] for k in ("raw", "se", "shrunk"))
                n_cells = np.asarray(z["n_cells"], dtype=np.float64)[keep]
            ti = np.array([tindex[t] for t in tg], dtype=np.int64)
            writer.add(i, ti, n_cells, raw, se, sh, t_axis[ti])
        ctx_rows.append((start, writer.pos))
        log(f"pass 2 {r['context']}: rows {start}..{writer.pos}")
    contexts = pd.DataFrame({"context": reg["context"], "family": reg["family"], "group": reg["group"],
                             "se_factor": reg["se_factor"].astype(float), "weight": reg["weight"].astype(float),
                             "modality": reg["modality"], "basal_row": [basal_names.index(b) for b in reg["basal"]],
                             "row_start": [a for a, _ in ctx_rows], "row_stop": [b for _, b in ctx_rows],
                             "universe": reg["universe"], "prefix": reg["prefix"]})
    genes = pd.DataFrame({"gene": [axis[g] for g in genes_axis], "axis_index": genes_axis, "n_families": n_fam[genes_axis]})

    def provenance(path: Path) -> dict:
        path = Path(path)
        if not path.exists():
            return {"path": str(path), "exists": False}
        return {"path": str(path), "bytes": path.stat().st_size, "sha256": P.sha256_file(path, HASH_LIMIT)}

    manifest = {"stage": "rete_contesti_2026-09-27/data.py", "started_utc": started,
                "claim_type": "input dataset for the network; no perturbation outcome enters a feature (pool.py)",
                "registry": provenance(args.registry),
                "universes": {r["context"]: {"folder": str(folders[i]), "index": provenance(folders[i] / "index.csv"),
                                             "manifest": provenance(folders[i] / "manifest.json"),
                                             "rows": n_rows_ctx[i]} for i, r in reg.iterrows()},
                "basal": provenance(basal_path), "coords": provenance(resolve(root, args.coords)),
                "panel": provenance(resolve(root, args.panel)), "essential": {**provenance(ess_path), "read": ess_note},
                "string": {"links": provenance(links), "info": provenance(info), "min_score": args.string_min_score,
                           "edges_kept": int(len(edges))},
                "options": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
                "stored_genes_rule": {"min_frac": args.min_frac, "min_families": args.min_families, "families": fams,
                                      "stored": int(G)},
                "excluded_targets": len(excluded), "extra_targets": len(extra)}
    full = writer.finish(contexts=contexts, targets=targets, genes=genes, axis=axis, basal=basal,
                         basal_names=basal_names, cis=P.csr(cis_lists), partners=(p_ip, p_ix, p_sc), manifest=manifest)
    total = sum(p.stat().st_size for p in args.out.iterdir() if p.is_file())
    log(f"written {args.out}: {n_rows} rows x {G} genes; {total} bytes in all (manifest included); by file "
        f"{full['bytes']}")
    if args.check_reader > 0:
        check_reader(args.out, reg, folders, args.check_reader)


def check_reader(out: Path, reg: pd.DataFrame, folders: list, n: int) -> None:
    """Compare stored rows with atlas_bench.Universe.table, the reference reader, cast the same way."""
    sys.path.insert(0, str(REPO / "reports" / "trasferimento" / "atlante_2026-09-26"))
    from atlas_bench import Universe
    pool = P.Pool.from_dir(out)
    rng = np.random.default_rng(0)
    bad = 0
    for i, r in reg.iterrows():
        uni = Universe(r["prefix"], folders[i])
        rows = pool.ctx_rows[i]
        pick = np.sort(rng.choice(rows, size=min(n, rows.size), replace=False))
        tnames = [pool.target_names[pool.row_target[j]] for j in pick]
        tab = uni.table(tnames)
        ix = tab.index()
        for j, t in zip(pick, tnames):
            k = ix.get(t)
            if k is None:
                bad += 1
                continue
            for key, arr, cast in (("raw", tab.raw, P.f16_effect), ("se", tab.se, P.f16_se),
                                   ("shrunk", tab.shrunk, P.f16_effect)):
                want = cast(arr[k][pool.genes_axis][None, :])[0]
                if not np.array_equal(np.asarray(pool.arrays[key][j]), want, equal_nan=True):
                    bad += 1
        log(f"check-reader {r['context']}: {pick.size} rows compared")
    log(f"check-reader: {bad} mismatches")
    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
