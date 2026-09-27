"""Per-(target, pool) raw-count sums from a local single-cell h5ad (CSR by cell), in the format of kolf_sums.

For single-cell screens that are stored by cell and compressed, so they cannot be read by byte ranges and have
to be downloaded (on Colab or Kaggle when they do not fit here): GSE345058 (A549, Cas9 knockout of 1,000 genes),
Southard et al. 2025 (CRISPRa), VIPerturb-seq after conversion. Streams the raw-count matrix row block by row
block, assigns every cell to a group (target, pool) with pool = code of --pool-col modulo 8 (like the project's
other sources), and writes `sums.npz` with the keys `reports/universo_kolf_2026-09-27/kolf_sums.py` merge writes
(`sums` groups x official-axis genes, NaN for axis genes absent from the file; `target`, `pool`, `n_cells`,
`total_counts` = each group's summed counts over ALL genes of the file; `genes`, `file_columns`,
`missing_genes`, `url`), so one estimation step serves every source. Controls become the target `NTC`.

    python h5ad_sums.py --h5ad FILE --layer layers/raw_counts --target-col Perturbation \
        --control-col Condition --control-value Nontargeting --pool-col Lane --out DIR/sums.npz
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import h5py
import numpy as np
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))


def strings(ds) -> np.ndarray:
    return np.asarray([v.decode() if isinstance(v, bytes) else str(v) for v in ds[:]], dtype=object)


def column(obs: h5py.Group, name: str) -> np.ndarray:
    """An obs column as strings (categorical or plain)."""
    node = obs[name]
    if isinstance(node, h5py.Group):          # anndata categorical
        cats = strings(node["categories"])
        return cats[node["codes"][:].astype(np.int64)]
    return strings(node)


def index_name(group: h5py.Group) -> str:
    """The dataframe's index column, as anndata declares it in the group's `_index` attribute."""
    name = group.attrs.get("_index", "_index")
    return name.decode() if isinstance(name, bytes) else str(name)


def inspect(path: Path) -> None:
    """Print what a run needs to choose its options: layers, obs and var columns, the index names."""
    with h5py.File(path, "r") as f:
        print("top-level:", list(f.keys()))
        for key in ("X", "layers"):
            if key in f:
                node = f[key]
                items = [key] if not isinstance(node, h5py.Group) or "encoding-type" in node.attrs else \
                    [f"{key}/{k}" for k in node.keys()]
                for item in items:
                    attrs = dict(f[item].attrs)
                    print(f"  {item}: {attrs.get('encoding-type', type(f[item]).__name__)} shape {attrs.get('shape')}")
        for frame in ("obs", "var"):
            g = f[frame]
            print(f"{frame}: index '{index_name(g)}', columns {list(g.keys())}")
            for name in g.keys():
                try:
                    values = column(g, name)
                except Exception as err:            # noqa: BLE001 - a report, not a pipeline
                    print(f"    {name}: unreadable ({err})")
                    continue
                uniq = np.unique(values.astype(str))
                print(f"    {name}: {values.size} values, {uniq.size} distinct, e.g. {uniq[:6].tolist()}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--h5ad", type=Path, required=True)
    ap.add_argument("--inspect", action="store_true", help="print layers and obs/var columns, then stop")
    ap.add_argument("--layer", default="layers/raw_counts", help="path of the raw-count CSR group, or X")
    ap.add_argument("--target-col")
    ap.add_argument("--control-col", default=None, help="column marking controls (default: --target-col)")
    ap.add_argument("--control-value", action="append", help="value(s) marking a control cell")
    ap.add_argument("--pool-col", help="batch-like column; pool = its category code modulo 8")
    ap.add_argument("--var-symbols", default=None,
                    help="var column with gene symbols (default: the var index anndata declares)")
    ap.add_argument("--axis", type=Path, default=None, help="one-column CSV of the official axis (default: vcc2026)")
    ap.add_argument("--rows-per-block", type=int, default=20000)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    if args.inspect:
        inspect(args.h5ad)
        return
    missing = [n for n in ("target_col", "control_value", "pool_col", "out") if not getattr(args, n)]
    if missing:
        raise SystemExit(f"missing options: {missing}")
    if args.out.exists():
        raise SystemExit(f"{args.out} exists")
    t0 = time.time()
    if args.axis is not None:
        axis = np.loadtxt(args.axis, dtype=str, skiprows=1, delimiter=",")
    else:
        from vcc2026.genes import official_axis
        axis = np.asarray(official_axis().symbols)
    with h5py.File(args.h5ad, "r") as f:
        obs = f["obs"]
        target = column(obs, args.target_col)
        ctrl = np.isin(column(obs, args.control_col or args.target_col), args.control_value)
        target = np.where(ctrl, "NTC", target)
        pool_codes = obs[args.pool_col]["codes"][:].astype(np.int64) if isinstance(obs[args.pool_col], h5py.Group) \
            else np.unique(column(obs, args.pool_col), return_inverse=True)[1]
        pool = pool_codes % 8
        keys, group_of_cell = np.unique(np.char.add(target.astype(str), np.char.add("|", pool.astype(str))),
                                        return_inverse=True)
        g_target = np.asarray([k.rsplit("|", 1)[0] for k in keys], dtype=str)
        g_pool = np.asarray([int(k.rsplit("|", 1)[1]) for k in keys], dtype=np.int8)
        n_cells = np.bincount(group_of_cell, minlength=len(keys))
        symbols = column(f["var"], args.var_symbols or index_name(f["var"]))
        lookup = {}
        for i, s in enumerate(symbols):
            lookup.setdefault(str(s), i)
        file_columns = np.array([lookup.get(g, -1) for g in axis], dtype=np.int64)
        mapped = np.flatnonzero(file_columns >= 0)
        layer = f[args.layer]
        if layer.attrs.get("encoding-type") != "csr_matrix":
            raise SystemExit(f"{args.layer} is not a CSR matrix")
        n_rows, n_cols = (int(x) for x in layer.attrs["shape"])
        if n_rows != target.size:
            raise SystemExit("obs and matrix rows differ")
        indptr = layer["indptr"][:].astype(np.int64)
        take = file_columns[mapped]
        acc = np.zeros((len(keys), mapped.size), dtype=np.float64)
        totals = np.zeros(len(keys), dtype=np.float64)
        for a in range(0, n_rows, args.rows_per_block):
            b = min(n_rows, a + args.rows_per_block)
            lo, hi = int(indptr[a]), int(indptr[b])
            data = layer["data"][lo:hi].astype(np.float64)
            idx = layer["indices"][lo:hi].astype(np.int64)
            block = sp.csr_matrix((data, idx, indptr[a:b + 1] - lo), shape=(b - a, n_cols))
            groups = sp.csr_matrix((np.ones(b - a), (group_of_cell[a:b], np.arange(b - a))), shape=(len(keys), b - a))
            totals += np.asarray(groups @ block.sum(axis=1)).ravel()
            acc += (groups @ block[:, take]).toarray()
            print(f"[{time.time() - t0:7.0f}s] rows {b}/{n_rows}", flush=True)
    sums = np.full((len(keys), axis.size), np.nan, dtype=np.float32, order="F")   # as kolf_sums' merge
    sums[:, mapped] = acc.astype(np.float32)
    table = dict(sums=sums, target=g_target, pool=g_pool, n_cells=n_cells, total_counts=totals, genes=axis,
                 file_columns=file_columns, missing_genes=axis[file_columns < 0], url=str(args.h5ad),
                 groups_sha256=hashlib.sha256(json.dumps([keys.tolist(), n_cells.tolist()]).encode()).hexdigest())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.out.with_name(args.out.name + ".part.npz")
    np.savez(tmp, **table)
    tmp.rename(args.out)
    print(f"groups {len(keys)} (targets {len(set(g_target)) - 1} + NTC); axis genes in the file {mapped.size}; "
          f"cells {n_rows}; controls {int(ctrl.sum())}; {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
