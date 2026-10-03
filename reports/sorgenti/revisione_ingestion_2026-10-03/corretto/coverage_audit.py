"""Coverage audit of the (expanded) cell corpus: which line groups really teach each target, after exclusions.

The unit of independent support is the **line group** of R-LEAD P1 (every study, state, donor and clone of a line):
cells, files, donors, studies and contexts of one group never add support. Two steps:

    collect  shards (obs only, never X) or sample manifests -> label_counts.csv + exclusions.csv
             per (study, context, modality, published label): cells before and after the label-level and obs-level
             exclusions (duplicate cell keys, declared republications, keys without enough controls, depth and genes
             below half the 1st percentile of the key's own controls: a proxy of the prepass QC, which stays the
             authority for a training)
    audit    label_counts.csv -> counts by source/group/study/modality/target/control pool, the sparse target by
             line-group matrix, and the histogram of targets taught by 1, 2, 3, 4+ training groups, for all
             modalities and for CRISPRi alone, computed AFTER the frozen holdout group and the globally hidden
             target fold are removed (same sha256 fold rule and salt as R-LEAD's splits.py)

Aliases are reconciled before counting (declared alias map, then the R-LEAD key table: Ensembl ID, else SYM:<symbol>),
so one gene under two spellings is one target; a context without a line-group rule is never silently a new group.

    python coverage_audit.py collect --shards <dir with *.h5ad, recursive> --out <new dir>
    python coverage_audit.py audit --counts <label_counts.csv> [...] --line-groups line_groups_expanded_v1.json \
        --holdout-group H1 --hidden-fold 0 --n-folds 5 [--axis gene_names.csv] [--target-keys target_keys.json] \
        [--aliases aliases.json] --out <new dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parents[3]
SALT = "r-lead-2026-10-02"                     # reports/modelli/risposta_contesto_2026-10-02/splits.py
SEP = re.compile(r"[|_,;+\s]")                 # reports/modelli/rete_cellulare_2026-10-03/cell_data.py
UNLABELLED = {"UNASSIGNED", "MISSING", "NO_METADATA", "", "nan", "<NA>", "None"}
CONTROL = "NTC"
COLUMNS = ["study", "context", "modality", "target", "target_id", "control_kind"]


# ------------------------------------------------------------------------------------ rules shared with R-LEAD

def unit_hash(key: str, salt: str = SALT) -> float:
    """Uniform number in [0, 1) from sha256(salt:key): the function of R-LEAD's splits.py, copied."""
    h = hashlib.sha256(f"{salt}:{key}".encode("utf-8")).hexdigest()
    return int(h[:15], 16) / 16 ** 15


def target_fold(key: str, n_folds: int, salt: str = SALT) -> int:
    if n_folds < 2:
        raise ValueError("n_folds >= 2")
    return min(int(unit_hash(key, salt + ":fold") * n_folds), n_folds - 1)


def group_of(study: str, context: str, rules: dict) -> str | None:
    """Line group of a (study, context) as cell_data.group_of resolves it (exact context, then the longest study
    prefix), but with no fallback: None means no rule, and the caller decides (never a silent new group)."""
    g = (rules.get("contexts") or {}).get(context)
    if g:
        return g
    for prefix, grp in sorted((rules.get("study_prefixes") or {}).items(), key=lambda kv: -len(kv[0])):
        if study.startswith(prefix):
            return grp
    return None


def parse_label(label: str, axis: set | None, aliases: dict) -> tuple[str, tuple]:
    """(kind, symbols): 'single', 'combined' or 'unresolved', after the alias map. With an axis the rule is
    cell_data.parse_label (tokens that are axis genes); without one a label is single unless it joins several
    names with `+`, `|`, `,` or `;`."""
    label = aliases.get(label, label)
    if axis is None:
        parts = sorted({aliases.get(t, t) for t in re.split(r"[|,;+]", label) if t.strip()})
        if not parts:
            return "unresolved", ()
        return ("single" if len(parts) == 1 else "combined"), tuple(parts)
    if label in axis:
        return "single", (label,)
    found = sorted({aliases.get(t, t) for t in SEP.split(label) if aliases.get(t, t) in axis})
    if not found:
        return "unresolved", ()
    return ("single" if len(found) == 1 else "combined"), tuple(found)


def key_of(symbol: str, target_id: str, target_keys: dict) -> str:
    """Reconciled target key: the Ensembl ID the source records, else the R-LEAD key table, else SYM:<symbol>."""
    tid = str(target_id or "")
    if tid.startswith("ENSG"):
        return tid.split(".")[0]
    return target_keys.get(symbol) or f"SYM:{symbol}"


# ------------------------------------------------------------------------------------ collect

def count_cells(cells: pd.DataFrame, min_controls: int = 30, republications: dict | None = None,
                seen: set | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One row per cell (cell_key, study, context, modality, target, control_kind and, when present, target_id,
    depth_on_file_axis, n_genes_detected) -> (label counts, exclusions by reason).

    `seen` carries the cell keys of earlier calls, so a cell published in two shards or two datasets counts once."""
    c = cells.copy()
    for col in COLUMNS:
        if col not in c:
            c[col] = ""
        c[col] = c[col].astype(str)
    rep = republications or {}
    present = set(c["study"])
    c["reason"] = ""
    is_rep = c["study"].isin([s for s, canon in rep.items() if canon in present]).to_numpy()
    c.loc[is_rep, "reason"] = "republication"
    c["study"] = [rep.get(s, s) if not r else s for s, r in zip(c["study"], is_rep)]
    seen = set() if seen is None else seen
    dup = np.zeros(len(c), bool)
    for i, k in enumerate(c["cell_key"].astype(str)):
        if k in seen:
            dup[i] = True
        else:
            seen.add(k)
    c.loc[dup & (c["reason"] == ""), "reason"] = "duplicate_cell"
    c["is_control"] = (c["control_kind"] == CONTROL) | (c["target"] == CONTROL)
    c["key"] = c["study"] + "|" + c["context"]
    live = c["reason"] == ""
    n_ctrl = c[live & c["is_control"]].groupby("key").size()
    few = ~c["key"].map(n_ctrl).fillna(0).ge(min_controls)
    c.loc[live & few.to_numpy(), "reason"] = "key_without_controls"
    for col, why in (("depth_on_file_axis", "depth_below_floor"), ("n_genes_detected", "genes_below_floor")):
        if col not in c:
            continue
        v = pd.to_numeric(c[col], errors="coerce")
        ctrl = c["is_control"] & (c["reason"] == "")
        floor = 0.5 * v[ctrl].groupby(c.loc[ctrl, "key"]).quantile(0.01)
        low = (v < c["key"].map(floor)).fillna(False).to_numpy()
        c.loc[low & (c["reason"] == "").to_numpy(), "reason"] = why
    c["admitted"] = c["reason"] == ""
    counts = (c.groupby(COLUMNS, dropna=False)
              .agg(n_cells=("admitted", "size"), n_admitted=("admitted", "sum")).reset_index())
    excl = (c[~c["admitted"]].groupby(["study", "context", "reason"]).size().rename("cells").reset_index())
    return counts, excl


def read_obs(path: Path) -> pd.DataFrame:
    """The obs columns the audit needs from one contract shard, with h5py alone (X is never opened)."""
    import h5py  # noqa: PLC0415
    sys.path.insert(0, str(REPO / "reports/sorgenti/corpus_cellulare_2026-09-30"))
    from adapters import _h5_column  # noqa: PLC0415
    names = ["cell_key"] + COLUMNS + ["depth_on_file_axis", "n_genes_detected"]
    with h5py.File(path, "r") as f:
        cols = {n: _h5_column(f["obs"], n) for n in names}
    return pd.DataFrame({n: v for n, v in cols.items() if v is not None})


def collect(shards: list[Path], min_controls: int, republications: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Label counts of a set of shards. The obs of every shard are concatenated in memory before counting (about
    half a GB per million cells as text), so controls, floors and duplicates are judged over the whole set: run it
    per group of datasets on a runtime with enough RAM, then give all the label_counts.csv to `audit`."""
    frames = [read_obs(p) for p in shards]            # obs only: a few MB per shard
    cells = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["cell_key"] + COLUMNS)
    return count_cells(cells, min_controls, republications)


# ------------------------------------------------------------------------------------ audit

def audit(counts: pd.DataFrame, rules: dict, holdout_groups=(), hidden_fold: int | None = None, n_folds: int = 5,
          salt: str = SALT, min_cells: int = 10, axis: set | None = None, aliases: dict | None = None,
          target_keys: dict | None = None, allow_unmapped: bool = False) -> dict:
    """Tables of the audit, as DataFrames and a summary. `counts` has COLUMNS + n_cells, n_admitted."""
    aliases, target_keys = aliases or {}, target_keys or {}
    related = rules.get("related") or {}
    held = set(holdout_groups)
    held |= {r for g in holdout_groups for r in related.get(g, [])}
    t = counts.copy()
    for col in COLUMNS:
        t[col] = t[col].fillna("").astype(str)
    t["group"] = [group_of(s, c, rules) for s, c in zip(t["study"], t["context"])]
    unmapped = t[t["group"].isna()][["study", "context"]].drop_duplicates()
    if len(unmapped) and not allow_unmapped:
        raise ValueError(f"contexts without a line-group rule: {unmapped.to_dict('records')[:10]}")
    t["group"] = [g if g is not None else f"UNMAPPED:{s}|{c}" for g, s, c in zip(t["group"], t["study"], t["context"])]
    t["is_control"] = (t["control_kind"] == CONTROL) | (t["target"] == CONTROL)
    kind, key, symbol = [], [], []
    for label, tid, ctrl, ck in zip(t["target"], t["target_id"], t["is_control"], t["control_kind"]):
        if ctrl:
            k, syms = "control", ()
        elif ck == "UNASSIGNED" or label in UNLABELLED:
            k, syms = "unassigned", ()
        else:
            k, syms = parse_label(label, axis, aliases)
        kind.append(k)
        symbol.append(syms[0] if k == "single" else "+".join(syms))
        key.append(key_of(syms[0], tid, target_keys) if k == "single" else "")
    t["label_kind"], t["target_key"], t["symbol"] = kind, key, symbol
    # Reconcile across the entire input before assigning any fold. A source that omits
    # target_id must not give the same gene a second SYM key and a different fold.
    canonical = defaultdict(set)
    for sym, target_key, label_kind in zip(symbol, key, kind):
        if label_kind == "single" and target_key.startswith("ENSG"):
            canonical[sym].add(target_key)
    for sym, target_key in target_keys.items():
        if str(target_key).startswith("ENSG"):
            canonical[aliases.get(sym, sym)].add(str(target_key).split(".")[0])
    conflicts = {sym: sorted(ids) for sym, ids in canonical.items() if len(ids) > 1}
    if conflicts:
        raise ValueError(f"conflicting target identities: {conflicts}")
    t["target_key"] = [next(iter(canonical[sym])) if k == "single" and canonical.get(sym) else target_key
                       for sym, target_key, k in zip(symbol, key, kind)]
    single = t["label_kind"] == "single"
    t["hidden"] = [bool(k) and hidden_fold is not None and target_fold(k, n_folds, salt) == int(hidden_fold)
                   for k in t["target_key"]]
    t["held_out"] = t["group"].isin(held)
    t["role"] = np.where(t["is_control"], "control", np.where(~single, t["label_kind"],
                         np.where(t["held_out"], "held_out_group", np.where(t["hidden"], "hidden_target", "train"))))
    by_source = (t.groupby(["study", "group", "context", "modality", "role"])
                 .agg(labels=("target", "nunique"), n_cells=("n_cells", "sum"), n_admitted=("n_admitted", "sum"))
                 .reset_index())
    pools = (t[t["is_control"]].groupby(["study", "group", "context", "modality"])
             .agg(control_cells=("n_cells", "sum"), control_cells_admitted=("n_admitted", "sum")).reset_index())
    train = t[t["role"] == "train"]
    taught = train[train["n_admitted"] > 0]      # a label with no admitted cell (republication, QC) is no source
    matrix = (taught.groupby(["target_key", "group", "modality"])
              .agg(symbols=("symbol", lambda s: ";".join(sorted(set(s)))), studies=("study", "nunique"),
                   contexts=("context", "nunique"), n_cells=("n_cells", "sum"), n_admitted=("n_admitted", "sum"))
              .reset_index())
    matrix["supports"] = matrix["n_admitted"] >= min_cells
    hist, support = {}, {}
    for name, sel in (("all_modalities", matrix), ("CRISPRi", matrix[matrix["modality"] == "CRISPRi"])):
        cells = sel.groupby(["target_key", "group"])["n_admitted"].sum()       # modalities pooled inside a group
        groups = cells[cells >= min_cells].reset_index().groupby("target_key")["group"].nunique()
        support[name] = groups
        c = Counter(min(int(n), 4) for n in groups)
        hist[name] = {"1": c.get(1, 0), "2": c.get(2, 0), "3": c.get(3, 0), "4+": c.get(4, 0),
                      "targets": int(len(groups))}
    hist_df = pd.DataFrame([{"selection": k, **v} for k, v in hist.items()])
    summary = {"holdout_groups": sorted(holdout_groups), "held_with_related": sorted(held),
               "hidden_fold": hidden_fold, "n_folds": n_folds, "salt": salt, "min_cells": min_cells,
               "support_unit": "line group (R-LEAD P1); cells, files, donors, studies and contexts never add support",
               "key_reconciliation": {"axis": axis is not None, "aliases": len(aliases),
                                      "target_keys": len(target_keys),
                                      "keys_by_kind": dict(Counter("ensembl" if k.startswith("ENSG") else "symbol"
                                                                   for k in set(train["target_key"])))},
               "training_groups": sorted(set(train["group"])),
               "unmapped_contexts": unmapped.to_dict("records"),
               "cells": {"total": int(t["n_cells"].sum()), "admitted": int(t["n_admitted"].sum()),
                         "by_role_admitted": {r: int(v) for r, v in t.groupby("role")["n_admitted"].sum().items()}},
               "histogram_targets_by_training_groups": hist}
    return {"by_source": by_source, "control_pools": pools, "target_by_group": matrix, "histogram": hist_df,
            "labels": t, "support": support, "summary": summary}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--shards", type=Path, nargs="+", required=True, help="folders searched recursively for *.h5ad")
    c.add_argument("--glob", default="*.h5ad")
    c.add_argument("--min-controls", type=int, default=30)
    c.add_argument("--republications", type=Path, help="JSON {republished study: canonical study}")
    c.add_argument("--out", type=Path, required=True)
    a = sub.add_parser("audit")
    a.add_argument("--counts", type=Path, nargs="+", required=True)
    a.add_argument("--line-groups", type=Path, required=True)
    a.add_argument("--holdout-group", action="append", default=[])
    a.add_argument("--hidden-fold", type=int)
    a.add_argument("--n-folds", type=int, default=5)
    a.add_argument("--salt", default=SALT)
    a.add_argument("--min-cells", type=int, default=10)
    a.add_argument("--axis", type=Path, help="gene_names.csv of the official axis")
    a.add_argument("--aliases", type=Path, help="JSON {old symbol: current symbol}")
    a.add_argument("--target-keys", type=Path, help="R-LEAD target_keys.json {symbol: Ensembl ID}")
    a.add_argument("--allow-unmapped", action="store_true")
    a.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        sys.exit(f"refusing: {args.out} exists")
    load = lambda f: json.loads(f.read_text(encoding="utf-8")) if f else {}  # noqa: E731
    if args.cmd == "collect":
        shards = sorted(q for d in args.shards for q in d.rglob(args.glob))
        counts, excl = collect(shards, args.min_controls, load(args.republications))
        args.out.mkdir(parents=True)
        counts.to_csv(args.out / "label_counts.csv", index=False)
        excl.to_csv(args.out / "exclusions.csv", index=False)
        (args.out / "collect.json").write_text(json.dumps(
            {"shards": [str(s) for s in shards], "cells": int(counts["n_cells"].sum()),
             "admitted": int(counts["n_admitted"].sum()), "min_controls": args.min_controls}, indent=1),
            encoding="utf-8")
        print(f"{len(shards)} shards, {int(counts['n_cells'].sum())} cells -> {args.out}")
        return
    counts = pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False) for f in args.counts], ignore_index=True)
    for col in ("n_cells", "n_admitted"):
        counts[col] = counts[col].astype(int)
    axis = None
    if args.axis:
        axis = {l.strip().split(",")[0] for l in args.axis.read_text(encoding="utf-8").splitlines()[1:] if l.strip()}
    res = audit(counts, load(args.line_groups), args.holdout_group, args.hidden_fold, args.n_folds, args.salt,
                args.min_cells, axis, load(args.aliases), load(args.target_keys), args.allow_unmapped)
    args.out.mkdir(parents=True)
    for name in ("by_source", "control_pools", "target_by_group", "histogram"):
        res[name].to_csv(args.out / f"{name}.csv", index=False)
    (args.out / "summary.json").write_text(json.dumps(res["summary"], indent=1), encoding="utf-8")
    print(json.dumps(res["summary"]["histogram_targets_by_training_groups"]))


if __name__ == "__main__":
    main()
