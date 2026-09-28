"""The network's compact dataset and the leak-free training views built from it.

numpy and pandas at import; torch only inside `Phase` (data.py imports the writer on a machine without torch).

On disk (one new folder, written by data.py through `DatasetWriter`; the self-test writes a synthetic one):

    manifest.json         format, counts, sizes in bytes, options, input hashes, names of the basal rows
    axis.csv              the official gene axis (column `gene`)
    genes.csv             the stored response genes: gene, axis_index, n_families
    contexts.csv          context, family, group, se_factor, weight, modality, basal_row, row_start, row_stop
    targets.csv           target, axis_index, gene_index, in_panel, essential, chrom, tss, then p_* and x_* priors
    basal.npy             float32 [n_basal, n_axis]: CPM of each context's controls (NaN where unknown)
    raw.npy se.npy shrunk.npy          float16 [n_rows, n_genes]: ln fold change, its SE, the stage-98 shrunk effect
    row_context.npy row_target.npy     int32 [n_rows]
    row_ncells.npy                     float32 [n_rows]
    row_own.npy                        float32 [n_rows, 2]: raw and SE of the target's own gene (full axis)
    cis_indptr.npy cis_index.npy                          per target: stored-gene columns in its cis window
    partner_indptr.npy partner_index.npy partner_score.npy  per target: STRING partners among the targets

The rows of one context are contiguous. NaN means not measured, never zero (D-009).

Leakage (D-044, docs/GENERALIZZAZIONE.md). The dataset holds every context; a design is a set of visible rows.
`Phase` derives everything the network sees in training from its visible rows alone -- the centres, the gene
set, the family and partner profiles, the basal reference, the prior normalisation -- and `Phase.read` refuses
a row of the wrong kind (`LeakageError`): labels and profiles come only from visible rows, truth only from
invisible ones. The self-test (train.py --selftest) checks that the derived arrays and the training batches are
identical when every invisible row is overwritten.
"""
from __future__ import annotations

import json
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

FORMAT = "rete_contesti/1"
ARRAYS = ("raw", "se", "shrunk")
ROW_FILES = ("row_context", "row_target", "row_ncells", "row_own")
RELIABILITY = 100.0                 # n / (n + 100) on a row's cells, as `multisource.mix` in production
EFFECT_CLIP = 20.0
SE_RANGE = (1e-4, 1e4)
LOG1P_1 = float(np.log1p(1.0))       # the same thresholds as net.py
LOG1P_10 = float(np.log1p(10.0))
CONTEXT_COLUMNS = ("context", "family", "group", "se_factor", "weight", "modality", "basal_row", "row_start", "row_stop")
TARGET_COLUMNS = ("target", "axis_index", "gene_index", "in_panel", "essential", "chrom", "tss")


class LeakageError(RuntimeError):
    """A read that would let a held-out row reach training, or a training row pose as truth."""


def f16_effect(x: np.ndarray) -> np.ndarray:
    """ln fold changes to float16, clipped to +-20; NaN stays NaN."""
    return np.clip(np.asarray(x, dtype=np.float32), -EFFECT_CLIP, EFFECT_CLIP).astype(np.float16)


def f16_se(x: np.ndarray) -> np.ndarray:
    """SE to float16, clipped to [1e-4, 1e4]; not finite or not positive becomes NaN."""
    x = np.asarray(x, dtype=np.float32)
    ok = np.isfinite(x) & (x > 0)
    return np.where(ok, np.clip(np.where(ok, x, 1.0), *SE_RANGE), np.nan).astype(np.float16)


def quantile_ranks_np(x: np.ndarray) -> np.ndarray:
    """Tie-aware quantile ranks in [0, 1] along the last axis (the numpy twin of net.quantile_ranks)."""
    x = np.asarray(x, dtype=np.float64)
    n = x.shape[-1]
    flat = x.reshape(-1, n)
    out = np.empty(flat.shape, dtype=np.float64)
    for i, row in enumerate(flat):
        s = np.sort(row)
        lo = np.searchsorted(s, row, side="left")
        hi = np.searchsorted(s, row, side="right")
        out[i] = (lo + (hi - lo - 1) / 2.0) / max(n - 1, 1)
    return out.reshape(x.shape)


def impute_basal(cpm: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """log1p CPM with unknown entries set to the gene's median over the other basal rows (0 CPM when no row
    knows the gene), and the imputation flags. Controls only: no perturbation outcome enters."""
    cpm = np.asarray(cpm, dtype=np.float64)
    unknown = ~np.isfinite(cpm)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        med = np.nanmedian(np.where(unknown, np.nan, cpm), axis=0)
    med = np.where(np.isfinite(med), med, 0.0)
    filled = np.where(unknown, med[None, :], np.maximum(np.where(unknown, 0.0, cpm), 0.0))
    return np.log1p(filled).astype(np.float32), unknown


def basal_priors(cpm_sources: np.ndarray, target_axis: np.ndarray) -> pd.DataFrame:
    """Target priors from the source contexts' controls (no perturbation outcome): mean and SD over contexts of
    the target gene's log1p CPM, the share of contexts where it reaches 5 CPM, and whether it is on the axis."""
    cpm = np.asarray(cpm_sources, dtype=np.float64)
    ax = np.asarray(target_axis, dtype=np.int64)
    on = ax >= 0
    vals = np.full((ax.size, cpm.shape[0]), np.nan)
    vals[on] = cpm[:, ax[on]].T
    lv = np.log1p(np.where(np.isfinite(vals), np.maximum(vals, 0.0), np.nan))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        mean = np.nanmean(lv, axis=1)
        sd = np.nanstd(lv, axis=1)
        known = np.isfinite(vals).sum(axis=1)
        breadth = np.where(known > 0, (np.nan_to_num(vals, nan=-1.0) >= 5.0).sum(axis=1) / np.maximum(known, 1), np.nan)
    return pd.DataFrame({"p_expr_mean": mean, "p_expr_sd": sd, "p_expr_breadth": breadth,
                         "p_on_axis": on.astype(np.float64)})


def csr(lists: list, dtype=np.int32) -> tuple[np.ndarray, np.ndarray]:
    """A list of integer lists as (indptr int64, indices)."""
    indptr = np.zeros(len(lists) + 1, dtype=np.int64)
    indptr[1:] = np.cumsum([len(x) for x in lists])
    index = np.asarray([v for x in lists for v in x], dtype=dtype) if indptr[-1] else np.zeros(0, dtype=dtype)
    return indptr, index


def sha256_file(path: Path, limit: int | None = None) -> str | None:
    """SHA256 of a file's bytes; None when it is larger than `limit` bytes."""
    import hashlib
    path = Path(path)
    if limit is not None and path.stat().st_size > limit:
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class DatasetWriter:
    """Streams rows into float16 .npy memory maps, context by context; tables and manifest at `finish`.

    The output folder must not exist: a dataset is never overwritten."""

    def __init__(self, out: Path, n_rows: int, gene_axis_index: np.ndarray):
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=False)
        self.cols = np.asarray(gene_axis_index, dtype=np.int64)
        if self.cols.ndim != 1 or self.cols.size == 0 or np.unique(self.cols).size != self.cols.size:
            raise ValueError("gene_axis_index must be distinct axis columns")
        self.n_rows = int(n_rows)
        G = int(self.cols.size)
        self.arrays = {k: np.lib.format.open_memmap(self.out / f"{k}.npy", mode="w+", dtype=np.float16,
                                                    shape=(self.n_rows, G)) for k in ARRAYS}
        self.row_context = np.full(self.n_rows, -1, dtype=np.int32)
        self.row_target = np.full(self.n_rows, -1, dtype=np.int32)
        self.row_ncells = np.full(self.n_rows, np.nan, dtype=np.float32)
        self.row_own = np.full((self.n_rows, 2), np.nan, dtype=np.float32)
        self.pos = 0

    def add(self, context: int, targets: np.ndarray, n_cells: np.ndarray, raw: np.ndarray, se: np.ndarray,
            shrunk: np.ndarray, own_axis: np.ndarray) -> None:
        """One block of rows of one context: target indices, cells, full-axis arrays [n, n_axis], and each
        target's own axis column (-1 when the target gene is not on the axis)."""
        targets = np.asarray(targets, dtype=np.int64)
        n = targets.size
        if n == 0:
            return
        raw, se, shrunk = (np.asarray(a, dtype=np.float32) for a in (raw, se, shrunk))
        if raw.shape != se.shape or raw.shape != shrunk.shape or raw.shape[0] != n:
            raise ValueError("raw, se and shrunk must be [n_rows_in_block, n_axis]")
        if self.pos + n > self.n_rows:
            raise ValueError(f"more rows than announced ({self.n_rows})")
        sl = slice(self.pos, self.pos + n)
        self.arrays["raw"][sl] = f16_effect(raw[:, self.cols])
        self.arrays["se"][sl] = f16_se(se[:, self.cols])
        self.arrays["shrunk"][sl] = f16_effect(shrunk[:, self.cols])
        self.row_context[sl] = context
        self.row_target[sl] = targets
        self.row_ncells[sl] = np.asarray(n_cells, dtype=np.float32)
        own = np.asarray(own_axis, dtype=np.int64)
        idx = np.flatnonzero(own >= 0)
        self.row_own[self.pos + idx, 0] = raw[idx, own[idx]]
        self.row_own[self.pos + idx, 1] = se[idx, own[idx]]
        self.pos += n

    def finish(self, *, contexts: pd.DataFrame, targets: pd.DataFrame, genes: pd.DataFrame, axis: list,
               basal: np.ndarray, basal_names: list, cis: tuple, partners: tuple, manifest: dict) -> dict:
        """Write every table, flush the arrays, write manifest.json with the size of each file; returns it."""
        if self.pos != self.n_rows:
            raise ValueError(f"{self.pos} rows written, {self.n_rows} announced")
        for k in ARRAYS:
            self.arrays[k].flush()
        del self.arrays
        missing = [c for c in CONTEXT_COLUMNS if c not in contexts.columns]
        missing += [c for c in TARGET_COLUMNS if c not in targets.columns]
        if missing:
            raise ValueError(f"tables lack columns {missing}")
        np.save(self.out / "row_context.npy", self.row_context)
        np.save(self.out / "row_target.npy", self.row_target)
        np.save(self.out / "row_ncells.npy", self.row_ncells)
        np.save(self.out / "row_own.npy", self.row_own)
        np.save(self.out / "basal.npy", np.asarray(basal, dtype=np.float32))
        np.save(self.out / "cis_indptr.npy", np.asarray(cis[0], dtype=np.int64))
        np.save(self.out / "cis_index.npy", np.asarray(cis[1], dtype=np.int32))
        np.save(self.out / "partner_indptr.npy", np.asarray(partners[0], dtype=np.int64))
        np.save(self.out / "partner_index.npy", np.asarray(partners[1], dtype=np.int32))
        np.save(self.out / "partner_score.npy", np.asarray(partners[2], dtype=np.float32))
        contexts.to_csv(self.out / "contexts.csv", index=False)
        targets.to_csv(self.out / "targets.csv", index=False)
        genes.to_csv(self.out / "genes.csv", index=False)
        pd.DataFrame({"gene": list(axis)}).to_csv(self.out / "axis.csv", index=False)
        sizes = {p.name: p.stat().st_size for p in sorted(self.out.iterdir()) if p.is_file()}
        full = {"format": FORMAT, **manifest, "basal_names": list(basal_names),
                "counts": {"rows": self.n_rows, "genes": int(self.cols.size), "axis": len(axis),
                           "contexts": int(len(contexts)), "targets": int(len(targets)), "basal_rows": len(basal_names)},
                "bytes": sizes, "bytes_total_before_manifest": int(sum(sizes.values()))}
        with (self.out / "manifest.json").open("x", encoding="utf-8") as fh:
            json.dump(full, fh, indent=1, default=str)
        return full


def _read_table(path: Path, text=()) -> pd.DataFrame:
    # names such as NA must stay strings: only empty fields are missing; `text` columns are read as strings
    return pd.read_csv(path, keep_default_na=False, na_values=[""], dtype={c: str for c in text})


class Pool:
    """The dataset, read-only: tables in memory; the three arrays as memory maps (or arrays in the self-test)."""

    def __init__(self, arrays: dict, contexts: pd.DataFrame, targets: pd.DataFrame, genes: pd.DataFrame, axis: list,
                 rows: dict, basal: np.ndarray, basal_names: list, cis: tuple, partners: tuple, manifest: dict | None = None):
        self.arrays = arrays
        self.n_rows, self.G = (int(v) for v in arrays["raw"].shape)
        for k in ARRAYS:
            if tuple(arrays[k].shape) != (self.n_rows, self.G):
                raise ValueError(f"{k}: shape {arrays[k].shape}, expected {(self.n_rows, self.G)}")
        self.contexts = contexts.reset_index(drop=True)
        self.targets = targets.reset_index(drop=True)
        self.genes = genes.reset_index(drop=True)
        self.axis = [str(a) for a in axis]
        self.manifest = manifest or {}
        self.row_context = np.asarray(rows["row_context"], dtype=np.int64)
        self.row_target = np.asarray(rows["row_target"], dtype=np.int64)
        self.row_ncells = np.asarray(rows["row_ncells"], dtype=np.float64)
        self.row_own = np.asarray(rows["row_own"], dtype=np.float64)
        self.basal = np.asarray(basal, dtype=np.float32)
        self.basal_names = [str(b) for b in basal_names]
        self.cis_indptr = np.asarray(cis[0], dtype=np.int64)
        self.cis_index = np.asarray(cis[1], dtype=np.int64)
        self.partner_indptr = np.asarray(partners[0], dtype=np.int64)
        self.partner_index = np.asarray(partners[1], dtype=np.int64)
        self.partner_score = np.asarray(partners[2], dtype=np.float64)
        nT, nC = len(self.targets), len(self.contexts)
        if len(self.genes) != self.G:
            raise ValueError("genes.csv does not match the arrays")
        if self.basal.shape != (len(self.basal_names), len(self.axis)):
            raise ValueError("basal must be [n_basal, n_axis]")
        if self.cis_indptr.size != nT + 1 or self.partner_indptr.size != nT + 1:
            raise ValueError("cis and partner tables must have one entry per target")
        for k in ("row_context", "row_target", "row_ncells"):
            if np.asarray(rows[k]).shape != (self.n_rows,):
                raise ValueError(f"{k} must have one entry per row")
        if self.row_own.shape != (self.n_rows, 2):
            raise ValueError("row_own must be [n_rows, 2]")
        if (self.row_context < 0).any() or (self.row_context >= nC).any() or (self.row_target < 0).any() \
                or (self.row_target >= nT).any():
            raise ValueError("row tables point outside the context or target tables")
        self.genes_axis = self.genes["axis_index"].to_numpy(dtype=np.int64)
        self.target_names = self.targets["target"].astype(str).tolist()
        self.target_index = {t: i for i, t in enumerate(self.target_names)}
        if len(self.target_index) != nT:
            raise ValueError("duplicate targets")
        self.context_names = self.contexts["context"].astype(str).tolist()
        self.context_index = {c: i for i, c in enumerate(self.context_names)}
        self.basal_index = {b: i for i, b in enumerate(self.basal_names)}
        self.family_names = sorted(self.contexts["family"].astype(str).unique().tolist())
        fam_id = {f: i for i, f in enumerate(self.family_names)}
        self.ctx_family = np.array([fam_id[f] for f in self.contexts["family"].astype(str)], dtype=np.int64)
        self.ctx_group = self.contexts["group"].astype(str).to_numpy()
        self.ctx_basal = self.contexts["basal_row"].to_numpy(dtype=np.int64)
        self.ctx_se_factor = self.contexts["se_factor"].to_numpy(dtype=np.float64)
        self.ctx_weight = self.contexts["weight"].to_numpy(dtype=np.float64)
        self.ctx_modality = self.contexts["modality"].astype(str).to_numpy()
        self.ctx_rows = []
        for c, (a, b) in enumerate(zip(self.contexts["row_start"].astype(int), self.contexts["row_stop"].astype(int))):
            if not (0 <= a <= b <= self.n_rows) or (self.row_context[a:b] != c).any():
                raise ValueError(f"rows of context {self.context_names[c]} are not the contiguous block [{a}, {b})")
            self.ctx_rows.append(np.arange(a, b, dtype=np.int64))
        if sum(r.size for r in self.ctx_rows) != self.n_rows:
            raise ValueError("some rows belong to no context block")
        if (self.ctx_basal < 0).any() or (self.ctx_basal >= len(self.basal_names)).any():
            raise ValueError("basal_row outside basal.npy")
        self.tgt_axis = self.targets["axis_index"].to_numpy(dtype=np.int64)
        self.tgt_gene = self.targets["gene_index"].to_numpy(dtype=np.int64)
        self.tgt_panel = self.targets["in_panel"].astype(str).str.lower().isin(["true", "1", "1.0"]).to_numpy()
        self.tgt_essential = self.targets["essential"].astype(str).str.lower().isin(["true", "1", "1.0"]).to_numpy()
        self.tgt_chrom = self.targets["chrom"].astype(str).to_numpy()
        self.tgt_tss = pd.to_numeric(self.targets["tss"], errors="coerce").to_numpy(dtype=np.float64)
        self.prior_cols = [c for c in self.targets.columns if c.startswith(("p_", "x_"))]
        self.prior_raw = (self.targets[self.prior_cols].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=np.float64)
                          if self.prior_cols else np.zeros((nT, 0)))
        self.logcpm, self.imputed = impute_basal(self.basal)
        self.gene_cpm = np.where(np.isfinite(self.basal), np.maximum(self.basal, 0.0),
                                 np.expm1(self.logcpm))[:, self.genes_axis].astype(np.float32)

    @classmethod
    def from_dir(cls, path, *, mmap: bool = True) -> "Pool":
        path = Path(path)
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("format") != FORMAT:
            raise ValueError(f"{path}: format {manifest.get('format')!r}, expected {FORMAT!r}")
        arrays = {k: np.load(path / f"{k}.npy", mmap_mode="r" if mmap else None) for k in ARRAYS}
        rows = {k: np.load(path / f"{k}.npy") for k in ROW_FILES}
        cis = (np.load(path / "cis_indptr.npy"), np.load(path / "cis_index.npy"))
        partners = (np.load(path / "partner_indptr.npy"), np.load(path / "partner_index.npy"),
                    np.load(path / "partner_score.npy"))
        axis = _read_table(path / "axis.csv", ("gene",))["gene"].astype(str).tolist()
        contexts = _read_table(path / "contexts.csv", ("context", "family", "group", "modality"))
        targets = _read_table(path / "targets.csv", ("target", "chrom"))
        genes = _read_table(path / "genes.csv", ("gene",))
        return cls(arrays, contexts, targets, genes, axis, rows, np.load(path / "basal.npy"),
                   manifest["basal_names"], cis, partners, manifest)

    def exclusion_mask(self, targets: np.ndarray) -> np.ndarray:
        """[B, G] True on each target's own gene and on its cis-window genes: out of the loss, of the inputs m
        and q, and of the predictions (the cis head is added by the benches, as in gated_bench.py)."""
        targets = np.asarray(targets, dtype=np.int64)
        mask = np.zeros((targets.size, self.G), dtype=bool)
        own = self.tgt_gene[targets]
        ok = np.flatnonzero(own >= 0)
        mask[ok, own[ok]] = True
        ip, ix = self.cis_indptr, self.cis_index
        for i, t in enumerate(targets):
            cols = ix[ip[t]:ip[t + 1]]
            if cols.size:
                mask[i, cols] = True
        return mask


@dataclass
class RowSpec:
    """Rows to feed the network: a basal row and a family per row (family -1: a context known only by its
    controls, such as A/B/C), a target, and for dataset rows their row ids and context ids."""
    basal: np.ndarray
    family: np.ndarray
    target: np.ndarray
    row: np.ndarray | None = None
    context: np.ndarray | None = None

    def __len__(self) -> int:
        return int(self.target.size)

    def take(self, sel) -> "RowSpec":
        return RowSpec(self.basal[sel], self.family[sel], self.target[sel],
                       None if self.row is None else self.row[sel], None if self.context is None else self.context[sel])


@dataclass
class PhaseOptions:
    tau2: float = 0.01              # added to k * SE^2 in the loss weight 1 / (k SE^2 + tau2)
    min_frac: float = 0.5           # a family estimates a gene when its visible rows have it this often
    min_families: int = 2           # genes fewer visible families estimate are out of loss and prediction (t23 ablation)
    gene_weight: str = "context"    # "context": x / (1 + x), x = 0.05 CPM of the row's context; "flat": 1
    q_own_family: bool = False      # regime T: partners' profiles may come from the row's own family
    max_partners: int = 16
    strong_boost: float = 0.0       # > 0: rows in the top quartile of significant genes of their context weigh 1 + boost
    block: int = 1024


class Phase:
    """One training view: the visible rows, and everything derived from them alone.

    `train_rows` are the rows of the loss and of every derived quantity. Held-out rows (test or validation)
    are invisible; they are read only as truth."""

    def __init__(self, pool: Pool, train_rows, opts: PhaseOptions | None = None, device: str = "cpu", log=print):
        self.pool, self.opts, self.log = pool, (opts or PhaseOptions()), log
        self.device_name = str(device)
        rows = np.unique(np.asarray(train_rows, dtype=np.int64))
        if rows.size == 0:
            raise ValueError("no training rows")
        self.visible = np.zeros(pool.n_rows, dtype=bool)
        self.visible[rows] = True
        self.train_rows = rows
        self.contexts = np.unique(pool.row_context[rows])
        self.families = np.unique(pool.ctx_family[self.contexts])
        self.F = int(self.families.size)
        self.slot = np.full(len(pool.family_names), -1, dtype=np.int64)
        self.slot[self.families] = np.arange(self.F)
        self.seen_target = np.zeros(len(pool.target_names), dtype=bool)
        self.seen_target[pool.row_target[rows]] = True
        self._centres()
        self._profiles()
        self._partners()
        self._reference()
        self._priors()
        self._to_device()
        self.log(f"phase: {rows.size} visible rows in {self.contexts.size} contexts, {self.F} families "
                 f"({', '.join(pool.family_names[f] for f in self.families)}); {int(self.R.sum())} of {pool.G} genes "
                 f"estimated by >= {self.need_families} families; profiles {self.P.shape[0]} (family, target) rows, "
                 f"partner profiles {self.Q.shape[0]}")

    # ---- guarded reads
    def read(self, key: str, rows, purpose: str) -> np.ndarray:
        """float32 rows of raw/se/shrunk. purpose "train": visible rows only; "truth": invisible rows only."""
        rows = np.asarray(rows, dtype=np.int64)
        if purpose == "train":
            if not self.visible[rows].all():
                raise LeakageError(f"{int((~self.visible[rows]).sum())} invisible rows requested for training")
        elif purpose == "truth":
            if self.visible[rows].any():
                raise LeakageError(f"{int(self.visible[rows].sum())} visible rows requested as truth")
        else:
            raise ValueError(f"unknown purpose {purpose!r}")
        order = np.argsort(rows, kind="stable")
        out = np.empty((rows.size, self.pool.G), dtype=np.float32)
        out[order] = np.asarray(self.pool.arrays[key][rows[order]], dtype=np.float32)
        return out

    def visible_rows_of(self, c: int) -> np.ndarray:
        r = self.pool.ctx_rows[c]
        return r[self.visible[r]]

    # ---- derived from visible rows
    def _centres(self) -> None:
        """Per visible context, the mean raw and shrunk effect over its visible rows (the line's common response,
        removed from labels and inputs as gamma 1 does in production); the gene set R; row strengths."""
        pool, G, blk = self.pool, self.pool.G, self.opts.block
        self.mu_raw, self.mu_sh = {}, {}
        self.row_strength = np.zeros(pool.n_rows, dtype=np.float32)
        fam_frac = np.zeros((self.F, G))
        for c in self.contexts:
            rows = self.visible_rows_of(c)
            s_raw, n_raw, s_sh, n_sh = (np.zeros(G) for _ in range(4))
            for b in range(0, rows.size, blk):
                r = rows[b:b + blk]
                raw, se, sh = (self.read(k, r, "train") for k in ARRAYS)
                ok = np.isfinite(raw) & np.isfinite(se) & (se > 0)
                s_raw += np.where(ok, raw, 0.0).sum(axis=0, dtype=np.float64)
                n_raw += ok.sum(axis=0)
                oks = np.isfinite(sh)
                s_sh += np.where(oks, sh, 0.0).sum(axis=0, dtype=np.float64)
                n_sh += oks.sum(axis=0)
                with np.errstate(divide="ignore", invalid="ignore"):
                    z = np.abs(np.where(ok, raw / np.where(ok, se, 1.0), 0.0))
                self.row_strength[r] = (z >= 3).sum(axis=1)
            self.mu_raw[c] = np.divide(s_raw, n_raw, out=np.zeros(G), where=n_raw > 0).astype(np.float32)
            self.mu_sh[c] = np.divide(s_sh, n_sh, out=np.zeros(G), where=n_sh > 0).astype(np.float32)
            f = self.slot[pool.ctx_family[c]]
            fam_frac[f] = np.maximum(fam_frac[f], n_raw / max(rows.size, 1))
        self.need_families = int(min(self.opts.min_families, self.F))
        self.n_fam_gene = (fam_frac >= self.opts.min_frac).sum(axis=0)
        self.R = self.n_fam_gene >= self.need_families
        self.row_boost = np.ones(pool.n_rows, dtype=np.float32)
        if self.opts.strong_boost > 0:
            for c in self.contexts:
                rows = self.visible_rows_of(c)
                q75 = np.quantile(self.row_strength[rows], 0.75)
                self.row_boost[rows] = np.where(self.row_strength[rows] >= q75, 1.0 + self.opts.strong_boost, 1.0)

    def _profiles(self) -> None:
        """P: per (visible family, target) the reliability-weighted mean of the centred shrunk effect over the
        family's visible contexts (context weight x n / (n + 100)); PW its total weight; PD the weighted mean
        knockdown depth of the target's own gene (-raw)."""
        pool, G, blk = self.pool, self.pool.G, self.opts.block
        nT = len(pool.target_names)
        self.pf_row = np.full((self.F, nT), -1, dtype=np.int64)
        fam_ctx, fam_tg = [], []
        for f in self.families:
            ctxs = [c for c in self.contexts if pool.ctx_family[c] == f]
            fam_ctx.append(ctxs)
            fam_tg.append(np.unique(np.concatenate([pool.row_target[self.visible_rows_of(c)] for c in ctxs])))
        total = int(sum(t.size for t in fam_tg))
        self.P = np.empty((total, G), dtype=np.float16)
        self.PW = np.zeros(total, dtype=np.float32)
        self.PD = np.full(total, np.nan, dtype=np.float32)
        start = 0
        for fs, (ctxs, tg) in enumerate(zip(fam_ctx, fam_tg)):
            local = np.full(nT, -1, dtype=np.int64)
            local[tg] = np.arange(tg.size)
            num = np.zeros((tg.size, G), dtype=np.float32)
            den = np.zeros((tg.size, G), dtype=np.float32)
            wsum, dnum, dden = np.zeros(tg.size), np.zeros(tg.size), np.zeros(tg.size)
            for c in ctxs:
                rows = self.visible_rows_of(c)
                for b in range(0, rows.size, blk):
                    r = rows[b:b + blk]
                    sh = self.read("shrunk", r, "train") - self.mu_sh[c][None, :]
                    ok = np.isfinite(sh)
                    n = pool.row_ncells[r]
                    rel = np.where(np.isfinite(n) & (n > 0), n / (n + RELIABILITY), 0.0)
                    wt = (pool.ctx_weight[c] * rel).astype(np.float32)
                    li = local[pool.row_target[r]]            # distinct within a context
                    num[li] += wt[:, None] * np.where(ok, sh, 0.0)
                    den[li] += wt[:, None] * ok
                    wsum[li] += wt
                    own = pool.row_own[r]
                    okd = np.isfinite(own[:, 0]) & np.isfinite(own[:, 1]) & (own[:, 1] > 0)
                    dnum[li] += np.where(okd, wt * -np.where(okd, own[:, 0], 0.0), 0.0)
                    dden[li] += np.where(okd, wt, 0.0)
            prof = np.full(num.shape, np.nan, dtype=np.float32)
            np.divide(num, den, out=prof, where=den > 0)
            self.P[start:start + tg.size] = prof.astype(np.float16)
            self.PW[start:start + tg.size] = wsum
            self.PD[start:start + tg.size] = np.where(dden > 0, dnum / np.maximum(dden, 1e-12), np.nan)
            self.pf_row[fs, tg] = start + np.arange(tg.size)
            start += tg.size
            del num, den, prof

    def _partners(self) -> None:
        """Q: per (visible family, target) the mean of its STRING partners' family profiles, each partner's own
        gene left out (priors.partner_effects does the same); QW the partners' mean weight. Only partners with
        visible rows enter, so held-out targets are never partners."""
        pool, G = self.pool, self.pool.G
        nT, K = len(pool.target_names), self.opts.max_partners
        ip, ix = pool.partner_indptr, pool.partner_index
        self.qf_row = np.full((self.F, nT), -1, dtype=np.int64)
        per_family = []
        for fs in range(self.F):
            have = self.pf_row[fs] >= 0
            tlist, plist = [], []
            for t in range(nT):
                ps = [int(p) for p in ix[ip[t]:ip[t + 1]] if have[p] and p != t][:K]
                if ps:
                    tlist.append(t)
                    plist.append(ps)
            per_family.append((tlist, plist))
        total = int(sum(len(t) for t, _ in per_family))
        self.Q = np.empty((total, G), dtype=np.float16)
        self.QW = np.zeros(total, dtype=np.float32)
        start, blk = 0, 128
        for fs, (tlist, plist) in enumerate(per_family):
            for b in range(0, len(tlist), blk):
                ts, ps = tlist[b:b + blk], plist[b:b + blk]
                width = max(len(p) for p in ps)
                idx = np.full((len(ts), width), -1, dtype=np.int64)
                for i, p in enumerate(ps):
                    idx[i, :len(p)] = self.pf_row[fs, p]
                vals = self.P[np.clip(idx, 0, None)].astype(np.float32)          # [b, width, G]
                valid = np.isfinite(vals) & (idx >= 0)[:, :, None]
                own = np.full(idx.shape, -1, dtype=np.int64)
                for i, p in enumerate(ps):
                    own[i, :len(p)] = pool.tgt_gene[p]
                ii, kk = np.nonzero(own >= 0)
                valid[ii, kk, own[ii, kk]] = False
                cnt = valid.sum(axis=1)
                q = np.full((len(ts), G), np.nan, dtype=np.float32)
                np.divide(np.where(valid, vals, 0.0).sum(axis=1), cnt, out=q, where=cnt > 0)
                self.Q[start:start + len(ts)] = q.astype(np.float16)
                w = np.where(idx >= 0, self.PW[np.clip(idx, 0, None)], 0.0)
                self.QW[start:start + len(ts)] = w.sum(axis=1) / np.maximum((idx >= 0).sum(axis=1), 1)
                self.qf_row[fs, ts] = start + np.arange(len(ts))
                start += len(ts)

    def _reference(self) -> None:
        """The training-average control profile (mean log1p CPM over each visible family's contexts, then over
        families) and its features: the blind row (a context that looks exactly like the average, drank 0, as the
        blind gates of gated.py), the reference rank of the drank channel, and the rank of each family's mean
        profile (rbar), the reference of a row's transferred profile."""
        pool = self.pool
        lc = pool.logcpm.astype(np.float64)
        fam_lc = np.zeros((self.F, lc.shape[1]))
        for fs, f in enumerate(self.families):
            b = np.unique(pool.ctx_basal[[c for c in self.contexts if pool.ctx_family[c] == f]])
            fam_lc[fs] = lc[b].mean(axis=0)
        self.rbar = quantile_ranks_np(fam_lc).astype(np.float32)
        ref_lc = fam_lc.mean(axis=0)
        self.ref_rank = quantile_ranks_np(ref_lc[None, :])[0].astype(np.float32)
        zeros = np.zeros_like(ref_lc)
        self.blind_row = np.stack([ref_lc / 5.0, self.ref_rank, ref_lc >= LOG1P_1, ref_lc >= LOG1P_10, zeros, zeros],
                                  axis=-1).astype(np.float32)
        if self.opts.gene_weight == "context":
            x = 0.05 * pool.gene_cpm
            self.gw = (x / (1.0 + x)).astype(np.float32)
        elif self.opts.gene_weight == "flat":
            self.gw = np.ones_like(pool.gene_cpm)
        else:
            raise ValueError(f"gene_weight {self.opts.gene_weight!r}")

    def _priors(self) -> None:
        """Target priors z-scored over the targets with visible rows; an indicator column for every prior that is
        missing somewhere in the table (the choice of columns does not depend on the phase)."""
        X = self.pool.prior_raw
        miss = ~np.isfinite(X)
        seen = self.seen_target
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            mu = np.nanmean(np.where(miss, np.nan, X)[seen], axis=0) if seen.any() else np.zeros(X.shape[1])
            sd = np.nanstd(np.where(miss, np.nan, X)[seen], axis=0) if seen.any() else np.ones(X.shape[1])
        mu = np.where(np.isfinite(mu), mu, 0.0)
        sd = np.where(np.isfinite(sd) & (sd > 0), sd, 1.0)
        Z = np.where(miss, 0.0, (np.where(miss, 0.0, X) - mu) / sd)
        cols = miss.any(axis=0)
        self.prior_z = np.concatenate([Z, miss[:, cols].astype(np.float64)], axis=1).astype(np.float32)

    def _to_device(self) -> None:
        import torch
        d = torch.device(self.device_name)
        self.device = d
        self.t_P = torch.from_numpy(self.P).to(d)
        self.t_Q = torch.from_numpy(self.Q).to(d)
        self.t_R = torch.from_numpy(self.R).to(d)
        self.t_logcpm = torch.from_numpy(self.pool.logcpm).to(d)
        self.t_imputed = torch.from_numpy(self.pool.imputed.astype(np.float32)).to(d)
        self.t_blind = torch.from_numpy(self.blind_row).to(d)
        self.consts = {"genes_axis": torch.from_numpy(self.pool.genes_axis).to(d),
                       "rbar": torch.from_numpy(self.rbar).to(d),
                       "ref_rank": torch.from_numpy(self.ref_rank).to(d)}

    # ---- what a training step or a prediction reads
    @property
    def n_priors(self) -> int:
        return int(self.prior_z.shape[1])

    @property
    def blind_index(self) -> int:
        return len(self.pool.basal_names)

    def features(self, jitter_sd: float = 0.0, generator=None):
        """[n_basal + 1, n_axis, 6]: every basal row's features (its controls jittered in training), then the
        blind row, the features of the training-average control profile."""
        import torch
        from net import context_features, platform_jitter
        lc = platform_jitter(self.t_logcpm, jitter_sd, generator)
        return torch.cat([context_features(lc, self.t_imputed, self.consts["ref_rank"]), self.t_blind.unsqueeze(0)])

    def spec_rows(self, rows) -> RowSpec:
        rows = np.asarray(rows, dtype=np.int64)
        ctx = self.pool.row_context[rows]
        return RowSpec(self.pool.ctx_basal[ctx], self.pool.ctx_family[ctx], self.pool.row_target[rows], rows, ctx)

    def spec_basal(self, basal_name: str, targets, family: int = -1) -> RowSpec:
        """Rows of a context known only by its controls (A/B/C, or D/E/F later): no family, no labels."""
        b = self.pool.basal_index[basal_name]
        t = np.asarray(targets, dtype=np.int64)
        return RowSpec(np.full(t.size, b, dtype=np.int64), np.full(t.size, family, dtype=np.int64), t)

    def _allowed(self, family: np.ndarray, own_ok: bool) -> np.ndarray:
        """[B, F] family slots a row may draw profiles from: never its own family, unless own_ok."""
        allowed = np.ones((family.size, self.F), dtype=bool)
        if not own_ok:
            slot = np.where(family >= 0, self.slot[np.clip(family, 0, None)], -1)
            i = np.flatnonzero(slot >= 0)
            allowed[i, slot[i]] = False
        return allowed

    def _mix(self, table, idx: np.ndarray, w: np.ndarray):
        """Weighted mean over family slots of rows of `table` (float16 on the device): (profile, ok)."""
        import torch
        B, G = idx.shape[0], self.pool.G
        num = torch.zeros(B, G, device=self.device)
        den = torch.zeros(B, G, device=self.device)
        if table.shape[0] == 0:
            return num, den > 0
        ti = torch.from_numpy(idx).to(self.device)
        tw = torch.from_numpy(w.astype(np.float32)).to(self.device)
        for f in range(idx.shape[1]):
            v = ti[:, f] >= 0
            if not bool((w[:, f] > 0).any()):
                continue
            vals = table[ti[:, f].clamp(min=0)].float()
            fin = torch.isfinite(vals) & v.unsqueeze(1)
            wf = tw[:, f].unsqueeze(1) * fin.float()
            num = num + wf * torch.where(fin, vals, torch.zeros_like(vals))
            den = den + wf
        ok = den > 0
        return torch.where(ok, num / den.clamp(min=1e-12), torch.zeros_like(num)), ok

    @staticmethod
    def _summary(x, ok, has, n_fam, n_genes):
        import torch
        okf = ok.float()
        cnt = okf.sum(dim=1)
        rms = torch.sqrt((x * x * okf).sum(dim=1) / cnt.clamp(min=1.0))
        lrms = torch.where(has, (torch.log(rms + 1e-4) + 4.0) / 4.0, torch.zeros_like(rms))
        return torch.stack([has.float(), n_fam, cnt / max(n_genes, 1), lrms], dim=1)

    def batch(self, spec: RowSpec, *, labels: str | None = None, feat: str = "true", swap_basal: int | None = None,
              drop_m: float = 0.0, drop_q: float = 0.0, depth: str = "ref", depth_drop: float = 0.5,
              q_own_family: bool | None = None, centre: dict | None = None, rng=None) -> dict:
        """The network's inputs for `spec`, as tensors on the device.

        labels: None; "train" (visible rows, centred by the visible centres, weights 1 / (k SE^2 + tau2) times
        the gene weight); "truth" (invisible rows, centred by `centre` {context: [G]} when given, else by 0).
        feat: "true", "blind" (the training-average row) or "swap" (basal row `swap_basal`).
        drop_m / drop_q: in training, the share of rows whose m / q is withheld (the target seen as unmeasured).
        depth: "train" uses the row's own knockdown depth (replaced by the family reference with probability
        depth_drop); "ref" always the reference over the families m comes from.
        """
        import torch
        pool, d, B = self.pool, self.device, len(spec)
        tgt = spec.target
        own_q = self.opts.q_own_family if q_own_family is None else q_own_family
        allowed_m = self._allowed(spec.family, False)
        allowed_q = self._allowed(spec.family, own_q)
        idx_m = self.pf_row[:, tgt].T.copy()
        idx_m[~allowed_m] = -1
        idx_q = self.qf_row[:, tgt].T.copy()
        idx_q[~allowed_q] = -1
        dropped_m = np.zeros(B, dtype=bool)
        if rng is not None and drop_m > 0:
            dropped_m = rng.random(B) < drop_m
            idx_m[dropped_m] = -1
        if rng is not None and drop_q > 0:
            idx_q[rng.random(B) < drop_q] = -1
        w_m = np.where(idx_m >= 0, self.PW[np.clip(idx_m, 0, None)] if self.PW.size else 0.0, 0.0).astype(np.float32)
        w_q = np.where(idx_q >= 0, self.QW[np.clip(idx_q, 0, None)] if self.QW.size else 0.0, 0.0).astype(np.float32)
        excl = pool.exclusion_mask(tgt)
        t_excl = torch.from_numpy(excl).to(d)
        keep = self.t_R.unsqueeze(0) & ~t_excl
        m, m_ok = self._mix(self.t_P, idx_m, w_m)
        q, q_ok = self._mix(self.t_Q, idx_q, w_q)
        m_ok, q_ok = m_ok & keep, q_ok & keep
        m = torch.where(m_ok, m, torch.zeros_like(m))
        q = torch.where(q_ok, q, torch.zeros_like(q))
        sm, sq = w_m.sum(axis=1), w_q.sum(axis=1)
        omega = np.divide(w_m, sm[:, None], out=np.zeros_like(w_m), where=sm[:, None] > 0)
        n_genes = int(self.R.sum())
        Fn = max(self.F, 1)
        msum = self._summary(m, m_ok, torch.from_numpy(sm > 0).to(d),
                             torch.from_numpy(((w_m > 0).sum(axis=1) / Fn).astype(np.float32)).to(d), n_genes)
        qsum = self._summary(q, q_ok, torch.from_numpy(sq > 0).to(d),
                             torch.from_numpy(((w_q > 0).sum(axis=1) / Fn).astype(np.float32)).to(d), n_genes)
        # knockdown depth: the family reference, or the row's own measurement in training
        pd_ = np.where(idx_m >= 0, self.PD[np.clip(idx_m, 0, None)] if self.PD.size else np.nan, np.nan)
        wd = np.where(np.isfinite(pd_), w_m, 0.0)
        ref_depth = np.divide(np.where(np.isfinite(pd_), pd_ * wd, 0.0).sum(axis=1), wd.sum(axis=1),
                              out=np.full(B, np.nan), where=wd.sum(axis=1) > 0)
        dep = ref_depth
        if depth == "train" and spec.row is not None:
            own = pool.row_own[spec.row]
            okd = np.isfinite(own[:, 0]) & np.isfinite(own[:, 1]) & (own[:, 1] > 0)
            if rng is not None and depth_drop > 0:
                okd &= rng.random(B) >= depth_drop
            dep = np.where(okd, -np.where(okd, own[:, 0], 0.0), ref_depth)
        dep_f = np.stack([np.where(np.isfinite(dep), np.clip(np.nan_to_num(dep), -1.0, 6.0) / 3.0, 0.0),
                          np.isfinite(dep).astype(np.float64)], axis=1).astype(np.float32)
        if feat == "true":
            row_feat = spec.basal
        elif feat == "blind":
            row_feat = np.full(B, self.blind_index, dtype=np.int64)
        elif feat == "swap":
            if swap_basal is None:
                raise ValueError("swap needs swap_basal")
            row_feat = np.full(B, int(swap_basal), dtype=np.int64)
        else:
            raise ValueError(f"feat {feat!r}")
        emb = np.where(self.seen_target[tgt] & ~dropped_m, tgt, -1)   # a target shown as unmeasured has no embedding
        out = {"m": m, "m_ok": m_ok, "q": q, "q_ok": q_ok, "msum": msum, "qsum": qsum, "excl": t_excl,
               "omega": torch.from_numpy(omega).to(d),
               "row_feat": torch.from_numpy(np.asarray(row_feat, dtype=np.int64)).to(d),
               "tgt_axis": torch.from_numpy(pool.tgt_axis[tgt]).to(d),
               "tgt_gene": torch.from_numpy(pool.tgt_gene[tgt]).to(d),
               "tgt_emb": torch.from_numpy(emb.astype(np.int64)).to(d),
               "priors": torch.from_numpy(self.prior_z[tgt]).to(d),
               "depth": torch.from_numpy(dep_f).to(d)}
        if labels is None:
            return out
        if spec.row is None:
            raise ValueError("labels need dataset rows")
        purpose = "train" if labels == "train" else "truth"
        if labels not in ("train", "truth"):
            raise ValueError(f"labels {labels!r}")
        raw = self.read("raw", spec.row, purpose)
        se = self.read("se", spec.row, purpose)
        k = pool.ctx_se_factor[spec.context]
        usable = np.isfinite(raw) & np.isfinite(se) & (se > 0) & self.R[None, :] & ~excl
        if labels == "train":
            mu = np.stack([self.mu_raw[c] for c in spec.context])
        elif centre is not None:
            mu = np.stack([centre[c] for c in spec.context])
        else:
            mu = np.zeros_like(raw)
        w = np.zeros(raw.shape, dtype=np.float32)
        den = k[:, None] * np.where(usable, se, 1.0) ** 2 + self.opts.tau2
        np.divide(self.gw[spec.basal], den, out=w, where=usable)
        if labels == "train":
            w *= self.row_boost[spec.row][:, None]
        y = np.where(usable, raw - mu, 0.0).astype(np.float32)
        out["y"] = torch.from_numpy(y).to(d)
        out["w"] = torch.from_numpy(w).to(d)
        return out

    def truth_centres(self, rows) -> dict:
        """{context: [G]} the mean raw effect over the given invisible rows of each context (truth-side centring
        of validation or test rows, like the scorer's zero at the context's own mean response)."""
        rows = np.asarray(rows, dtype=np.int64)
        out = {}
        for c in np.unique(self.pool.row_context[rows]):
            r = rows[self.pool.row_context[rows] == c]
            raw, se = self.read("raw", r, "truth"), self.read("se", r, "truth")
            ok = np.isfinite(raw) & np.isfinite(se) & (se > 0)
            n = ok.sum(axis=0)
            out[int(c)] = np.divide(np.where(ok, raw, 0.0).sum(axis=0), n, out=np.zeros(self.pool.G), where=n > 0).astype(np.float32)
        return out
