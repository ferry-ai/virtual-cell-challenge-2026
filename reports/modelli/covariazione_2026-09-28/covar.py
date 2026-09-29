"""Action 6 of R-REV, as registered in RISULTATI.md of this folder (28/09, 19:56): is gene-gene co-variation more
conserved across lines than single-target effects ("mappa", M1 against M2), and does co-variation learned in other
lines predict a new line's knockdown response ("uso", M3a)? The library behind run_parte_a.py, run_parte_b.py and
combine.py; every threshold of the registered rule is a constant below and `decide` applies them.

Pure numpy and pandas (scipy only for a faster eigensolver when present, h5py only in `ntc_*`): no torch and no
repository import, so a Kaggle kernel can ship this file alone.

Notation (RISULTATI.md, "Preparazione" and "Misure"):
- y_c(t, g): effect of target t on gene g in context c, on G* (the genes stored in r2 with CPM >= 20 in the controls
  of GSTAR_BASAL); the target's own gene and its 5 kb cis window are masked, like every unmeasured entry.
- Preparation of a set of targets in one context (`prepare`): centre each gene over the targets, divide by its
  standard deviation, set masked entries to 0, scale each target's profile to unit norm (u), then remove the first k
  right singular vectors of that matrix (`project`). k = 3 is primary; 0, 1 and 10 are reported.
- M1: K = gene x gene Pearson correlation over the targets of one half; Q_cov = mean of Mantel(K_c^H1, K_d^H2) and
  Mantel(K_c^H2, K_d^H1); ceiling C_cov(c) = Mantel(K_c^H1, K_c^H2); null = mean over permutations of gene labels
  within 20 expression bins; rho_cov = (Q - N) / sqrt((C_c - N_c)(C_d - N_d)).
- M2: Q_eff = mean per-target cosine; null = mean over permutations of targets within strata (deciles of significant
  genes x essential); rho_eff = (Q_eff - N_eff) / mean_t sqrt(r_c(t) r_d(t)), r = signal share of the profile from
  the calibrated SE. D = rho_cov - rho_eff, with a delete-a-block jackknife over 20 target blocks shared by M1 and M2.
- M3a (`m3a_context`): for a held-out context h, relation route -beta_s(x, .), effect route mean_s z_s(t, .), in-line
  ceiling -beta_h(x, .), combined route; specific skill = cosine minus its within-strata permutation expectation.
  The test targets' rows never enter a mean, a standard deviation or a beta, in any context (D-044).

Implementation choices the registered text leaves open are marked "choice:" where they are made; the lead declares
them. The main ones: the preparation (centre, SD, top-k axes) is computed per pair on the pair's pool P; the
reliability r is computed on the same projected profile as the cosine (exactly the registered formula at k = 0);
the jackknife keeps the preparation fixed and uses the exact permutation expectation as null in each replicate
(the point estimate uses the registered Monte Carlo nulls, and the exact values are reported beside them).

    scripts/py.cmd reports/modelli/covariazione_2026-09-28/selftest_covar.py
"""
from __future__ import annotations

import hashlib
import itertools
import json
import sys
import time
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------------------------------------------
# Registered constants (RISULTATI.md). Do not change after the registration.
# ---------------------------------------------------------------------------------------------------------------
CPM_MIN = 20.0
GSTAR_BASAL = ("k562", "rpe1", "cd4_Rest", "orion_hct116", "orion_hek293t", "kolf", "viperturb", "A", "B", "C")
GSTAR_EXPECTED = 2887
Z_SIG = 3.0                     # |raw / SE| >= 3 ...
MIN_SIG_GENES = 30              # ... on at least 30 genes of G*: "rispondente"
CIS_BP = 5000
K_LIST = (0, 1, 3, 10)
K_MAIN = 3
K_JACK = (3, 0)                 # D at k = 3 (rule) and the same at k = 0 (reported)
SEEDS = (0, 1, 2)               # W7
N_BLOCKS = 20
N_EXPR_BINS = 20
N_GENE_PERM = 100
N_TARGET_PERM = 200
N_BOOT = 1000
N_DECILES = 10
MIN_SHARED_RESPONSIVE = 200     # W6
Z95 = 1.959963984540054

W1_CEILING_MIN = 0.05
W1_SQRT_R_MIN = 0.20
W1_MIN_CONTEXTS = 4
W3_KAPPA_RANGE = (0.5, 2.0)
W4_MAX_DIFF = 0.10
W4_SIGNAL_SHARE = 0.5
MAP_YES_D_MEDIAN = 0.10
MAP_YES_MIN_POSITIVE = 5
MAP_YES_NO_PAIR_BELOW = -0.05
MAP_YES_RHO_MEDIAN = 0.20
MAP_NO_D_MEDIAN = 0.0
MAP_NO_RHO_MEDIAN = 0.10
USE_YES_MIN = 4
USE_NO_MIN = 3
ADDS_MIN = 4

P9_CONTEXTS = ("k562", "cd4_Rest", "orion_hct116", "kolf", "viperturb")
SAME_LINE = (frozenset(("k562", "viperturb")),)
REPLACEMENTS = (("orion_hct116", "orion_hek293t"), ("k562", "rpe1"), ("cd4_Rest", "cd4_Stim48hr"))
REPLOGLE_CONTEXTS = ("k562", "k562ess", "rpe1")
HIPSCI_LINES = ("eipl_1", "eipl_3", "fiaj_1", "fiaj_3", "iudw_1", "iudw_4", "jejf_2", "jejf_3", "kolf_2", "kolf_3",
                "oikd_2", "oikd_5", "paab_3", "paab_4", "pipw_4", "pipw_5", "tolg_4", "tolg_6", "zapk_3")
HIPSCI_WEAK = ("fiaj_3", "tolg_4", "pipw_5", "oikd_2")
HIPSCI_SAME_DONOR = (("eipl_1", "eipl_3"), ("iudw_1", "iudw_4"), ("jejf_2", "jejf_3"), ("kolf_2", "kolf_3"),
                     ("paab_3", "paab_4"))


def p9_pairs() -> list[tuple[str, str]]:
    """The nine P9 pairs: other lab and other line, every pair of P9_CONTEXTS except k562 x viperturb."""
    return [(a, b) for a, b in itertools.combinations(P9_CONTEXTS, 2) if frozenset((a, b)) not in SAME_LINE]


def part_a_pairs() -> list[tuple[str, str, str]]:
    """(stratum, a, b) for every pair of Part A: P9, replications (one context replaced), S1, S1b, S2, S3, S5."""
    out = [("P9", a, b) for a, b in p9_pairs()]
    for old, new in REPLACEMENTS:
        out += [("REP", new if a == old else a, new if b == old else b) for a, b in p9_pairs() if old in (a, b)]
    out += [("S1", "k562", "k562ess"), ("S1b", "viperturb", "k562"),
            ("S2", "cd4_Rest", "cd4_Stim8hr"), ("S2", "cd4_Stim8hr", "cd4_Stim48hr"), ("S2", "cd4_Rest", "cd4_Stim48hr"),
            ("S3", "k562", "rpe1"), ("S3", "orion_hct116", "orion_hek293t")]
    out += [("S5", "a549", c) for c in P9_CONTEXTS]
    return out


def hipsci_pairs() -> list[tuple[str, str, str]]:
    """(stratum, line_a, line_b): S0 for the five same-donor pairs, S3 for the pairs of different donors, among the
    lines with strong silencing. Donor = the part of the name before '_' (interpretation, RISULTATI.md)."""
    strong = [x for x in HIPSCI_LINES if x not in HIPSCI_WEAK]
    same = {frozenset(p) for p in HIPSCI_SAME_DONOR}
    out = []
    for a, b in itertools.combinations(strong, 2):
        if frozenset((a, b)) in same:
            out.append(("S0", a, b))
        elif a.split("_")[0] != b.split("_")[0]:
            out.append(("S3", a, b))
    return out


# ---------------------------------------------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------------------------------------------
_T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - _T0:8.1f}s] {msg}", flush=True)


def _win_memory() -> tuple[float, float] | None:
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        c = PMC()
        c.cb = ctypes.sizeof(PMC)
        k32 = ctypes.WinDLL("kernel32")
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi")
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        if psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb):
            return c.PeakWorkingSetSize / 2 ** 20, c.PeakPagefileUsage / 2 ** 20
    except Exception:  # noqa: BLE001 -- a missing measure must not stop a run
        return None
    return None


def peak_rss_mb() -> float | None:
    """Peak resident memory of this process in MB (Linux: getrusage; Windows: peak working set)."""
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except ImportError:
        w = _win_memory()
        return None if w is None else round(w[0], 1)


def peak_private_mb() -> float | None:
    """Windows only: peak private commit (what grows the paging file), in MB."""
    w = _win_memory()
    return None if w is None else round(w[1], 1)


def sha256_file(path, limit: int | None = 200_000_000) -> str | None:
    path = Path(path)
    if limit is not None and path.stat().st_size > limit:
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rng_for(*keys) -> np.random.Generator:
    """A generator seeded from any mix of ints and strings, stable across runs and machines."""
    words = []
    for k in keys:
        if isinstance(k, (int, np.integer)):
            words.append(int(k) & 0xFFFFFFFF)
        else:
            words.append(int(hashlib.sha256(str(k).encode()).hexdigest()[:8], 16))
    return np.random.default_rng(words)


def rank_bins(x, nbins: int) -> np.ndarray:
    """Equal-count bins by rank (ties broken by position): labels 0..nbins-1."""
    x = np.asarray(x, dtype=np.float64)
    n = x.size
    if n == 0:
        return np.zeros(0, dtype=np.int64)
    r = np.empty(n, dtype=np.int64)
    r[np.argsort(np.nan_to_num(x, nan=-np.inf), kind="stable")] = np.arange(n)
    return (r * nbins // n).astype(np.int64)


def pair_strata(nsig_a, nsig_b, essential) -> np.ndarray:
    """Strata of a pair's targets: deciles of the mean number of significant genes in the two contexts x essential.
    choice: the registered "decili di geni significativi" is read on the mean over the two contexts."""
    return rank_bins((np.asarray(nsig_a, float) + np.asarray(nsig_b, float)) / 2.0, N_DECILES) * 2 \
        + np.asarray(essential, dtype=bool).astype(np.int64)


def stratified_halves(strata, rng) -> np.ndarray:
    """True for H1, False for H2: each stratum shuffled and dealt alternately, the first card alternating between
    strata so the halves differ by at most one target."""
    strata = np.asarray(strata)
    h1 = np.zeros(strata.size, dtype=bool)
    start = 0
    for s in np.unique(strata):
        idx = np.flatnonzero(strata == s)
        idx = idx[rng.permutation(idx.size)]
        h1[idx[start::2]] = True
        start = (start + idx.size) % 2
    return h1


def make_blocks(n: int, rng, nb: int = N_BLOCKS) -> np.ndarray:
    b = np.empty(n, dtype=np.int64)
    b[rng.permutation(n)] = np.arange(n) % nb
    return b


def jackknife_se(values) -> float:
    v = np.asarray(values, dtype=np.float64)
    v = v[np.isfinite(v)]
    if v.size < 2:
        return float("nan")
    return float(np.sqrt((v.size - 1) / v.size * np.sum((v - v.mean()) ** 2)))


def _read_table(path: Path, text=()) -> pd.DataFrame:
    return pd.read_csv(path, keep_default_na=False, na_values=[""], dtype={c: str for c in text})


def _bool_col(s: pd.Series) -> np.ndarray:
    return s.astype(str).str.lower().isin(["true", "1", "1.0"]).to_numpy()


# ---------------------------------------------------------------------------------------------------------------
# Genes, masks, readers
# ---------------------------------------------------------------------------------------------------------------
def select_gstar(basal, basal_names, genes_axis, names=GSTAR_BASAL, cpm_min=CPM_MIN) -> np.ndarray:
    """Stored-gene positions of G*: CPM >= cpm_min in the controls of every basal row in `names` (unknown fails).
    Controls only: no perturbation outcome enters (RISULTATI.md, "Geni")."""
    idx = [list(basal_names).index(n) for n in names]
    b = np.asarray(basal, dtype=np.float64)[idx][:, np.asarray(genes_axis, dtype=np.int64)]
    return np.flatnonzero(np.all(np.nan_to_num(b, nan=-1.0) >= cpm_min, axis=0))


def basal_logcpm(basal, row: int, axis_cols) -> np.ndarray:
    """log1p CPM of one basal row on the given axis columns; unknown entries take the gene's median over rows."""
    b = np.asarray(basal, dtype=np.float64)[:, np.asarray(axis_cols, dtype=np.int64)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        med = np.nanmedian(b, axis=0)
    v = b[row]
    v = np.where(np.isfinite(v), v, np.where(np.isfinite(med), med, 0.0))
    return np.log1p(np.maximum(v, 0.0))


@dataclass
class MaskCSR:
    """Per row, the masked column positions (own gene and cis window)."""
    indptr: np.ndarray
    index: np.ndarray
    ncols: int

    @classmethod
    def from_lists(cls, lists, ncols: int) -> "MaskCSR":
        indptr = np.zeros(len(lists) + 1, dtype=np.int64)
        indptr[1:] = np.cumsum([len(x) for x in lists])
        index = np.asarray([v for x in lists for v in x], dtype=np.int64) if indptr[-1] else np.zeros(0, np.int64)
        return cls(indptr, index, int(ncols))

    def take(self, rows) -> "MaskCSR":
        rows = np.asarray(rows, dtype=np.int64)
        return MaskCSR.from_lists([self.index[self.indptr[r]:self.indptr[r + 1]] for r in rows], self.ncols)

    def dense(self, rows=None, cols=None) -> np.ndarray:
        """bool [len(rows), len(cols)] (all rows / all columns when None)."""
        rows = np.arange(self.indptr.size - 1) if rows is None else np.asarray(rows, dtype=np.int64)
        if cols is None:
            lookup, width = np.arange(self.ncols), self.ncols
        else:
            cols = np.asarray(cols, dtype=np.int64)
            lookup = np.full(self.ncols, -1, dtype=np.int64)
            lookup[cols] = np.arange(cols.size)
            width = cols.size
        out = np.zeros((rows.size, width), dtype=bool)
        counts = self.indptr[rows + 1] - self.indptr[rows]
        if counts.sum() == 0:
            return out
        ri = np.repeat(np.arange(rows.size), counts)
        ci = np.concatenate([self.index[self.indptr[r]:self.indptr[r + 1]] for r in rows[counts > 0]])
        pos = lookup[ci]
        ok = pos >= 0
        out[ri[ok], pos[ok]] = True
        return out


R2_FORMAT = "rete_contesti/1"


class R2:
    """The network's r2 dataset (reports/modelli/rete_contesti_2026-09-27/pool.py format), read-only, numpy only:
    tables in memory; the three float16 arrays read by file offset, row run by row run, cut to the wanted columns
    at once (the minimal part of pool.Pool.from_dir and Pool.exclusion_mask, without torch)."""

    def __init__(self, path):
        p = Path(path)
        self.path = p
        self.manifest = json.loads((p / "manifest.json").read_text(encoding="utf-8"))
        if self.manifest.get("format") != R2_FORMAT:
            raise ValueError(f"{p}: format {self.manifest.get('format')!r}, expected {R2_FORMAT!r}")
        self.contexts = _read_table(p / "contexts.csv", ("context", "family", "group", "modality"))
        self.targets = _read_table(p / "targets.csv", ("target", "chrom"))
        self.genes = _read_table(p / "genes.csv", ("gene",))
        self.basal = np.load(p / "basal.npy")
        self.basal_names = [str(b) for b in self.manifest["basal_names"]]
        self.row_context = np.load(p / "row_context.npy").astype(np.int64)
        self.row_target = np.load(p / "row_target.npy").astype(np.int64)
        self.cis_indptr = np.load(p / "cis_indptr.npy").astype(np.int64)
        self.cis_index = np.load(p / "cis_index.npy").astype(np.int64)
        self.gene_names = self.genes["gene"].astype(str).to_numpy()
        self.genes_axis = self.genes["axis_index"].to_numpy(dtype=np.int64)
        self.G = int(self.gene_names.size)
        self.target_names = self.targets["target"].astype(str).to_numpy()
        self.tgt_gene = self.targets["gene_index"].to_numpy(dtype=np.int64)
        self.tgt_axis = self.targets["axis_index"].to_numpy(dtype=np.int64)
        self.tgt_panel = _bool_col(self.targets["in_panel"])
        self.tgt_essential = _bool_col(self.targets["essential"])
        self.ctx = {str(r["context"]): r for _, r in self.contexts.iterrows()}
        self._arrays: dict = {}

    def rows(self, ctx: str) -> np.ndarray:
        r = self.ctx[ctx]
        rows = np.arange(int(r["row_start"]), int(r["row_stop"]), dtype=np.int64)
        c = self.contexts.index[self.contexts["context"] == ctx][0]
        if (self.row_context[rows] != c).any():
            raise ValueError(f"rows of {ctx} are not contiguous")
        return rows

    def _header(self, key: str) -> tuple[int, tuple, np.dtype]:
        if key not in self._arrays:
            with open(self.path / f"{key}.npy", "rb") as fh:
                version = np.lib.format.read_magic(fh)
                shape, fortran, dtype = (np.lib.format.read_array_header_1_0(fh) if version == (1, 0)
                                         else np.lib.format.read_array_header_2_0(fh))
                if fortran or len(shape) != 2 or shape[1] != self.G:
                    raise ValueError(f"{key}.npy: shape {shape}, fortran {fortran}; expected [n, {self.G}] C order")
                self._arrays[key] = (fh.tell(), shape, np.dtype(dtype))
        return self._arrays[key]

    def read(self, key: str, rows, cols, block: int = 1024, dtype=np.float16) -> np.ndarray:
        """[len(rows), len(cols)] of one array, read with plain file reads of consecutive row runs (at most
        `block` rows per read): private memory stays at one run, and no mapping enters the working set."""
        offset, shape, dt = self._header(key)
        rows = np.asarray(rows, dtype=np.int64)
        cols = np.asarray(cols, dtype=np.int64)
        out = np.empty((rows.size, cols.size), dtype=dtype)
        rowbytes = shape[1] * dt.itemsize
        order = np.argsort(rows, kind="stable")
        srt = rows[order]
        with open(self.path / f"{key}.npy", "rb", buffering=0) as fh:
            i = 0
            while i < srt.size:
                j = i + 1
                while j < srt.size and j - i < block and srt[j] == srt[j - 1] + 1:
                    j += 1
                fh.seek(offset + int(srt[i]) * rowbytes)
                buf = np.frombuffer(fh.read((j - i) * rowbytes), dtype=dt).reshape(j - i, shape[1])
                out[order[i:j]] = buf[:, cols].astype(dtype, copy=False)
                i = j
        return out

    def masked_genes(self, t: int) -> np.ndarray:
        """Stored-gene positions masked for target t: its own gene and its cis window (pool.exclusion_mask)."""
        cis = self.cis_index[self.cis_indptr[t]:self.cis_indptr[t + 1]]
        own = self.tgt_gene[t]
        return np.concatenate([[own], cis]).astype(np.int64) if own >= 0 else cis

    def mask_csr(self, target_ids, cols) -> MaskCSR:
        """MaskCSR over positions in `cols` (stored-gene positions) for each target id."""
        lookup = np.full(self.G, -1, dtype=np.int64)
        cols = np.asarray(cols, dtype=np.int64)
        lookup[cols] = np.arange(cols.size)
        cache: dict = {}
        lists = []
        for t in np.asarray(target_ids, dtype=np.int64):
            if t not in cache:
                p = lookup[self.masked_genes(int(t))]
                cache[t] = np.unique(p[p >= 0])
            lists.append(cache[t])
        return MaskCSR.from_lists(lists, cols.size)

    def ctx_family(self, ctx: str) -> str:
        return str(self.ctx[ctx]["family"])

    def ctx_se_factor(self, ctx: str) -> float:
        return float(self.ctx[ctx]["se_factor"])

    def ctx_logcpm(self, ctx: str, cols) -> np.ndarray:
        return basal_logcpm(self.basal, int(self.ctx[ctx]["basal_row"]), self.genes_axis[np.asarray(cols, np.int64)])

    def small_file_hashes(self) -> dict:
        out = {}
        for f in sorted(self.path.iterdir()):
            if f.is_file():
                out[f.name] = {"bytes": f.stat().st_size, "sha256": sha256_file(f, limit=50_000_000)}
        return out


def chunk_files(folder: Path, prefix: str) -> list[str]:
    """A universe's chunk files in index order (copied from rete_contesti_2026-09-27/data.py): a numeric chunk is
    <prefix>_<chunk:03d>.npz, a string names the file, an empty chunk is a target without effects."""
    idx = pd.read_csv(folder / "index.csv", keep_default_na=False, na_values=[""], dtype={"target": str})
    idx = idx[idx["chunk"].notna() & (idx["chunk"].astype(str).str.strip() != "")].copy()
    if pd.api.types.is_numeric_dtype(idx["chunk"]):
        files = [f"{prefix}_{int(c):03d}.npz" for c in idx["chunk"]]
    else:
        files = idx["chunk"].astype(str).str.strip().tolist()
    return list(dict.fromkeys(files))


def read_universe(folder, prefix: str, axis_cols, keys=("raw", "se"), dtype=np.float16, drop_panel=True,
                  keep_targets=None) -> dict:
    """A stage-98 universe cut to `axis_cols` at once, one key of one shard at a time (peak ~ one shard key,
    about 45 MB). Returns {'targets': names, key: [n, len(axis_cols)] arrays, 'n_cells'}."""
    folder = Path(folder)
    idx = pd.read_csv(folder / "index.csv", keep_default_na=False, na_values=[""], dtype={"target": str})
    panel = set(idx.loc[_bool_col(idx["in_panel"]), "target"].astype(str)) if "in_panel" in idx.columns else set()
    axis_cols = np.asarray(axis_cols, dtype=np.int64)
    keep = None if keep_targets is None else set(map(str, keep_targets))
    names, cells, parts = [], [], {k: [] for k in keys}
    for f in chunk_files(folder, prefix):
        with np.load(folder / f, allow_pickle=False) as z:
            t = z["targets"].astype(str)
            sel = np.ones(t.size, dtype=bool)
            if drop_panel:
                sel &= ~np.isin(t, list(panel))
            if keep is not None:
                sel &= np.isin(t, list(keep))
            sel = np.flatnonzero(sel)
            for k in keys:
                a = z[k]
                parts[k].append(np.asarray(a[sel][:, axis_cols], dtype=dtype))
                del a
            names.append(t[sel])
            cells.append(np.asarray(z["n_cells"])[sel] if "n_cells" in z.files else np.full(sel.size, np.nan))
    out = {"targets": np.concatenate(names) if names else np.zeros(0, str),
           "n_cells": np.concatenate(cells) if cells else np.zeros(0)}
    for k in keys:
        out[k] = np.concatenate(parts[k]) if parts[k] else np.zeros((0, axis_cols.size), dtype=dtype)
    _, first = np.unique(out["targets"], return_index=True)
    if first.size != out["targets"].size:
        keep_idx = np.sort(first)
        for k in ["targets", "n_cells", *keys]:
            out[k] = out[k][keep_idx]
    return out


def load_coords(path) -> pd.DataFrame:
    """The gene coordinate table (symbol, chrom, tss), one row per symbol, as vcc2026.predictor_sc reads it."""
    frame = pd.read_csv(path, sep="\t", dtype={"symbol": str, "chrom": str})
    return frame.drop_duplicates("symbol").set_index("symbol")


def coord_mask(target_names, gene_names, coords: pd.DataFrame, bp: int = CIS_BP) -> MaskCSR:
    """MaskCSR over `gene_names`: each target's own gene and the genes whose TSS lies within bp of its TSS, the rule
    data.py used to build r2's cis tables (TSS - bp <= tss <= TSS + bp, same chromosome)."""
    gene_names = np.asarray(gene_names).astype(str)
    gpos = {g: i for i, g in enumerate(gene_names)}
    chrom = np.array([str(coords.at[g, "chrom"]) if g in coords.index else "" for g in gene_names], dtype=object)
    tss = np.array([float(coords.at[g, "tss"]) if g in coords.index else np.nan for g in gene_names])
    by = {}
    ok = np.isfinite(tss)
    for c in np.unique(chrom[ok]):
        idx = np.flatnonzero(ok & (chrom == c))
        idx = idx[np.argsort(tss[idx], kind="stable")]
        by[c] = (idx, tss[idx])
    lists = []
    for t in np.asarray(target_names).astype(str):
        m = [gpos[t]] if t in gpos else []
        if t in coords.index and np.isfinite(float(coords.at[t, "tss"])):
            c, x = str(coords.at[t, "chrom"]), float(coords.at[t, "tss"])
            if c in by:
                idx, pos = by[c]
                lo = np.searchsorted(pos, x - bp, side="left")
                hi = np.searchsorted(pos, x + bp, side="right")
                m += [int(j) for j in idx[lo:hi]]
        lists.append(np.unique(np.asarray(m, dtype=np.int64)))
    return MaskCSR.from_lists(lists, gene_names.size)


def n_significant(raw, se, mask: np.ndarray, z: float = Z_SIG, block: int = 2048) -> np.ndarray:
    """Per row, the genes with |raw / SE| >= z, both finite, SE > 0, outside the mask (own gene, cis window)."""
    n = raw.shape[0]
    out = np.zeros(n, dtype=np.int64)
    for i in range(0, n, block):
        r = np.asarray(raw[i:i + block], dtype=np.float32)
        s = np.asarray(se[i:i + block], dtype=np.float32)
        with np.errstate(invalid="ignore"):
            ok = np.isfinite(r) & np.isfinite(s) & (s > 0) & ~mask[i:i + block]
            out[i:i + block] = (ok & (np.abs(r) >= z * s)).sum(axis=1)
    return out


# ---------------------------------------------------------------------------------------------------------------
# Preparation
# ---------------------------------------------------------------------------------------------------------------
@dataclass
class Prep:
    u: np.ndarray            # [n, G] float32, unit rows (centred, standardised, masked -> 0)
    zn2: np.ndarray          # [n] squared norm of z before the unit scaling
    d2: np.ndarray | None    # [n, G] float32 (se / sd)^2, 0 where masked or unknown
    V: np.ndarray            # [G, kmax] leading right singular vectors of u
    mu: np.ndarray
    sd: np.ndarray


def nan_stats(y: np.ndarray, bad: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Column mean, SD (ddof 0) and count over the entries not flagged `bad`; y is modified: bad -> 0, centred."""
    y[bad] = 0.0
    cnt = (~bad).sum(axis=0).astype(np.float64)
    mu = np.divide(y.sum(axis=0, dtype=np.float64), cnt, out=np.zeros(y.shape[1]), where=cnt > 0)
    y -= mu.astype(np.float32)
    y[bad] = 0.0
    var = np.divide(np.einsum("ij,ij->j", y, y, dtype=np.float64), cnt, out=np.zeros(y.shape[1]), where=cnt > 0)
    return mu, np.sqrt(var), cnt


def top_axes(u: np.ndarray, kmax: int) -> np.ndarray:
    """[G, kmax] leading right singular vectors of u (eigenvectors of u'u), sign fixed for determinism."""
    G = u.shape[1]
    if min(kmax, G) <= 0:
        return np.zeros((G, 0), dtype=np.float32)
    return _top_from_gram(u.T @ u, kmax)


def prepare(raw, mask: np.ndarray, se=None, kmax: int = max(K_LIST)) -> Prep:
    """Centre each gene over the targets, standardise it, mask -> 0, unit rows; d2 from the SE; top axes."""
    y = np.array(raw, dtype=np.float32)
    with np.errstate(invalid="ignore"):
        bad = mask | ~np.isfinite(y)
    mu, sd, _ = nan_stats(y, bad)
    good = np.isfinite(sd) & (sd > 1e-12)
    inv = np.where(good, 1.0 / np.where(good, sd, 1.0), 0.0).astype(np.float32)
    y *= inv
    zn2 = np.einsum("ij,ij->i", y, y, dtype=np.float64)
    nrm = np.sqrt(zn2)
    y /= np.where(nrm > 0, nrm, 1.0).astype(np.float32)[:, None]
    d2 = None
    if se is not None:
        d2 = np.array(se, dtype=np.float32)
        d2 *= inv
        np.square(d2, out=d2)
        with np.errstate(invalid="ignore"):
            d2[bad | ~np.isfinite(d2)] = 0.0
    del bad
    return Prep(u=y, zn2=zn2, d2=d2, V=top_axes(y, kmax), mu=mu, sd=sd)


def project(u: np.ndarray, V: np.ndarray, k: int) -> np.ndarray:
    """u (I - V_k V_k'): the first k axes removed. k = 0 returns u itself (never modify the result in place)."""
    if k <= 0:
        return u
    Vk = V[:, :k]
    return u - (u @ Vk) @ Vk.T


def reliability(prep: Prep, Uk: np.ndarray, k: int, kappa, kfac: float) -> np.ndarray:
    """r(t) = max(0, 1 - kfac * sum_g kappa_g w_g (se/sd)^2 / ||z_k(t)||^2), the signal share of the projected profile.
    w_g = 1 - sum_{j<k} V_gj^2 is the projection's diagonal (the expected noise left after removing k axes); at k = 0
    this is the registered r_c(t) = max(0, 1 - kappa k_c sum_g (se/sd)^2 / ||z||^2).
    choice: computed on the same projected profile whose cosine it disattenuates."""
    if prep.d2 is None:
        raise ValueError("reliability needs the SE (prepare(..., se=...))")
    w = 1.0 - (prep.V[:, :k] ** 2).sum(axis=1) if k > 0 else np.ones(prep.V.shape[0])
    kap = np.broadcast_to(np.asarray(kappa, dtype=np.float64), w.shape)
    E = prep.zn2 * np.einsum("ij,ij->i", Uk, Uk, dtype=np.float64)
    N = float(kfac) * (prep.d2 @ (kap * w).astype(np.float32)).astype(np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(E > 0, 1.0 - N / np.where(E > 0, E, 1.0), 0.0)
    return np.clip(r, 0.0, 1.0)


def signal_share(raw, se, mask: np.ndarray, kappa, kfac: float) -> np.ndarray:
    """Per gene, 1 - mean_t(kfac kappa se^2) / mean_t(ytilde^2) over the unmasked, measured targets: the gene's
    signal share in this context (W4's declared fallback keeps the genes with share >= 0.5 in both contexts)."""
    y = np.array(raw, dtype=np.float32)
    s = np.array(se, dtype=np.float32)
    with np.errstate(invalid="ignore"):
        bad = mask | ~np.isfinite(y) | ~np.isfinite(s)
    _, sd, cnt = nan_stats(y, bad)
    del y
    s[bad] = 0.0
    noise = np.divide(np.einsum("ij,ij->j", s, s, dtype=np.float64), cnt, out=np.full(s.shape[1], np.nan),
                      where=cnt > 1)
    var = sd ** 2
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where((var > 0) & (cnt > 1), 1.0 - float(kfac) * np.asarray(kappa, dtype=np.float64) * noise / var,
                        np.nan)


# ---------------------------------------------------------------------------------------------------------------
# M1: gene x gene matrices and their comparison
# ---------------------------------------------------------------------------------------------------------------
def gram(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:
    X = np.ascontiguousarray(X, dtype=np.float32)
    return X.T @ X, X.sum(axis=0, dtype=np.float64), int(X.shape[0])


def corr_from_gram(M: np.ndarray, s: np.ndarray, n: int) -> np.ndarray:
    """Pearson correlation over rows from X'X, column sums and n; NaN rows/columns for genes without variance."""
    K = np.array(M, dtype=np.float32)
    if n < 2:
        K[:] = np.nan
        return K
    mean = (s / n).astype(np.float32)
    s32 = s.astype(np.float32)
    for i in range(0, K.shape[0], 512):
        K[i:i + 512] -= np.outer(mean[i:i + 512], s32)
    d = np.diag(K).astype(np.float64).copy()
    ok = d > 1e-10 * max(float(np.nanmax(d)) if d.size else 0.0, 1e-30)
    inv = np.where(ok, 1.0 / np.sqrt(np.where(ok, d, 1.0)), np.nan).astype(np.float32)
    K *= inv[:, None]
    K *= inv[None, :]
    return K


def corr_rows(X: np.ndarray) -> np.ndarray:
    return corr_from_gram(*gram(X))


def cross_corr(XA: np.ndarray, XB: np.ndarray) -> np.ndarray:
    """The noise-free gene x gene matrix of W4: corr_t(A_g, B_h) between two cell halves of the same targets,
    symmetrised. Its off-diagonal carries no within-pseudobulk noise, which the two halves do not share."""
    XA = np.asarray(XA, dtype=np.float32)
    XB = np.asarray(XB, dtype=np.float32)
    a = XA - XA.mean(axis=0, dtype=np.float64).astype(np.float32)
    b = XB - XB.mean(axis=0, dtype=np.float64).astype(np.float32)
    C = a.T @ b
    sa = np.sqrt(np.einsum("ij,ij->j", a, a, dtype=np.float64))
    sb = np.sqrt(np.einsum("ij,ij->j", b, b, dtype=np.float64))
    ok = (sa > 0) & (sb > 0)
    ia = np.where(ok, 1.0 / np.where(ok, sa, 1.0), np.nan).astype(np.float32)
    ib = np.where(ok, 1.0 / np.where(ok, sb, 1.0), np.nan).astype(np.float32)
    C *= ia[:, None]
    C *= ib[None, :]
    C += C.T.copy()
    C *= 0.5
    return C


def _dot64(A: np.ndarray, B: np.ndarray, rows: int = 256) -> float:
    """sum(A * B): BLAS dot products on row chunks (float32 within a chunk), accumulated in float64."""
    tot = 0.0
    for i in range(0, A.shape[0], rows):
        a, b = A[i:i + rows], B[i:i + rows]
        if a.dtype == np.float32 and b.dtype == np.float32 and a.flags.c_contiguous and b.flags.c_contiguous:
            tot += float(np.vdot(a.ravel(), b.ravel()))
        else:
            tot += float(np.einsum("ij,ij->", a, b, dtype=np.float64))
    return tot


class OffDiag:
    """Moments of a symmetric matrix's off-diagonal entries, which gene-label permutations leave unchanged."""

    def __init__(self, A: np.ndarray):
        G = A.shape[0]
        self.m = G * (G - 1)
        self.diag = np.diag(A).astype(np.float64).copy()
        s = float(A.sum(dtype=np.float64)) - self.diag.sum()
        ss = _dot64(A, A) - float((self.diag ** 2).sum())
        self.mean = s / self.m
        self.var = max(ss / self.m - self.mean ** 2, 0.0)


def valid_genes(*mats) -> np.ndarray:
    v = np.ones(mats[0].shape[0], dtype=bool)
    for A in mats:
        v &= np.isfinite(np.diag(A))
    return v


def _sub(A: np.ndarray, v: np.ndarray) -> np.ndarray:
    return A if v.all() else A[np.ix_(v, v)]


def mantel(A: np.ndarray, B: np.ndarray) -> float:
    """Pearson correlation of the off-diagonal entries of two gene x gene matrices, on the genes valid in both."""
    v = valid_genes(A, B)
    if v.sum() < 3:
        return float("nan")
    A, B = _sub(A, v), _sub(B, v)
    a, b = OffDiag(A), OffDiag(B)
    if a.var <= 0 or b.var <= 0:
        return float("nan")
    cross = _dot64(A, B) - float((a.diag * b.diag).sum())
    return (cross / a.m - a.mean * b.mean) / np.sqrt(a.var * b.var)


def _bins_on(bins: np.ndarray, v: np.ndarray) -> np.ndarray:
    return np.asarray(bins)[v]


def mantel_null_mc(A, B, bins, nperm: int, rng) -> tuple[float, float]:
    """Mean and SD of Mantel(A, B permuted) over `nperm` permutations of B's gene labels within expression bins."""
    v = valid_genes(A, B)
    A, B, bins = _sub(A, v), _sub(B, v), _bins_on(bins, v)
    a, b = OffDiag(A), OffDiag(B)
    if a.var <= 0 or b.var <= 0 or nperm <= 0:
        return float("nan"), float("nan")
    groups = [np.flatnonzero(bins == x) for x in np.unique(bins)]
    vals = np.empty(nperm)
    base = np.arange(A.shape[0])
    for p in range(nperm):
        pi = base.copy()
        for g in groups:
            pi[g] = g[rng.permutation(g.size)]
        Bp = B[np.ix_(pi, pi)]
        cross = _dot64(A, Bp) - float((a.diag * b.diag[pi]).sum())
        vals[p] = (cross / a.m - a.mean * b.mean) / np.sqrt(a.var * b.var)
        del Bp
    return float(vals.mean()), float(vals.std())


def mantel_null_exact(A, B, bins) -> float:
    """The exact expectation of Mantel(A, B permuted) over all permutations of B's gene labels within bins: the
    limit of mantel_null_mc (the off-diagonal moments are permutation-invariant, only the cross term moves)."""
    v = valid_genes(A, B)
    A, B, bins = _sub(A, v), _sub(B, v), _bins_on(bins, v)
    a, b = OffDiag(A), OffDiag(B)
    if a.var <= 0 or b.var <= 0:
        return float("nan")
    labels, inv = np.unique(bins, return_inverse=True)
    P = np.zeros((A.shape[0], labels.size), dtype=np.float32)
    P[np.arange(A.shape[0]), inv] = 1.0
    npb = P.sum(axis=0).astype(np.float64)

    def block_sums(X, dg):
        S = (P.T @ (X @ P)).astype(np.float64)
        S[np.diag_indices_from(S)] -= np.bincount(inv, weights=dg, minlength=labels.size)
        return S

    SA, SB = block_sums(A, a.diag), block_sums(B, b.diag)
    cnt = np.outer(npb, npb)
    cnt[np.diag_indices_from(cnt)] = npb * (npb - 1)
    Bbar = np.divide(SB, cnt, out=np.zeros_like(SB), where=cnt > 0)
    cross = float((SA * Bbar).sum())
    return (cross / a.m - a.mean * b.mean) / np.sqrt(a.var * b.var)


def rho_from(Q, NQ, Ca, Na, Cb, Nb) -> float:
    """(Q - N) / sqrt((C_a - N_a)(C_b - N_b)); NaN when a ceiling does not exceed its null."""
    ea, eb = Ca - Na, Cb - Nb
    if not (np.isfinite(ea) and np.isfinite(eb)) or ea <= 0 or eb <= 0:
        return float("nan")
    return float((Q - NQ) / np.sqrt(ea * eb))


# ---------------------------------------------------------------------------------------------------------------
# M2: per-target agreement and its target-permutation null
# ---------------------------------------------------------------------------------------------------------------
def unit_rows(X: np.ndarray, inplace: bool = False) -> np.ndarray:
    n = np.sqrt(np.einsum("ij,ij->i", X, X, dtype=np.float64))
    if inplace and X.dtype == np.float32:
        X /= np.where(n > 0, n, 1.0).astype(np.float32)[:, None]
        return X
    return (X / np.where(n > 0, n, 1.0)[:, None]).astype(np.float32)


def project_inplace(u: np.ndarray, V: np.ndarray, k: int, block: int = 2048) -> np.ndarray:
    """u <- u (I - V_k V_k'), in row blocks (no full-size temporary)."""
    if k > 0:
        Vk = V[:, :k]
        for i in range(0, u.shape[0], block):
            u[i:i + block] -= (u[i:i + block] @ Vk) @ Vk.T
    return u


class StrataCross:
    """Within each stratum, the matrix of cosines between the targets' profiles in context a and in context b: the
    diagonal is Q_eff's per-target cosine, the rest gives the target-permutation null (Monte Carlo and exact)."""

    def __init__(self, Ua_hat: np.ndarray, Ub_hat: np.ndarray, strata):
        strata = np.asarray(strata)
        self.n = strata.size
        self.groups = [np.flatnonzero(strata == s) for s in np.unique(strata)]
        self.S = [Ua_hat[g] @ Ub_hat[g].T for g in self.groups]
        self.cos = np.empty(self.n)
        for g, S in zip(self.groups, self.S):
            self.cos[g] = np.diag(S)

    def exact(self, keep: np.ndarray | None = None) -> float:
        tot, n = 0.0, 0
        for g, S in zip(self.groups, self.S):
            k = np.ones(g.size, dtype=bool) if keep is None else keep[g]
            ns = int(k.sum())
            if ns == 0:
                continue
            tot += float(S[np.ix_(k, k)].sum(dtype=np.float64)) / ns
            n += ns
        return tot / n if n else float("nan")

    def mc(self, nperm: int, rng) -> tuple[float, float]:
        vals = np.empty(nperm)
        for p in range(nperm):
            tot = 0.0
            for g, S in zip(self.groups, self.S):
                tot += float(S[np.arange(g.size), rng.permutation(g.size)].sum(dtype=np.float64))
            vals[p] = tot / self.n
        return float(vals.mean()), float(vals.std())


def fit_kappa(cos_ab, EA, NA, EB, NB, lo: float = 1e-3, hi: float = 1e3) -> tuple[float, str]:
    """kappa such that mean_t sqrt(r_A(t) r_B(t)) equals the observed mean cosine between two cell halves of the
    same targets (whose signal is the same), with r = max(0, 1 - kappa N / E). Bisection in log space."""
    target = float(np.mean(cos_ab))
    EA, NA, EB, NB = (np.asarray(x, dtype=np.float64) for x in (EA, NA, EB, NB))

    def f(k):
        ra = np.clip(1.0 - k * np.divide(NA, EA, out=np.full_like(NA, np.inf), where=EA > 0), 0.0, 1.0)
        rb = np.clip(1.0 - k * np.divide(NB, EB, out=np.full_like(NB, np.inf), where=EB > 0), 0.0, 1.0)
        return float(np.mean(np.sqrt(ra * rb))) - target

    if f(lo) < 0:
        return lo, "at lower bound: halves agree less than any kappa predicts"
    if f(hi) > 0:
        return hi, "at upper bound"
    a, b = np.log(lo), np.log(hi)
    for _ in range(200):
        m = 0.5 * (a + b)
        if f(np.exp(m)) > 0:
            a = m
        else:
            b = m
    return float(np.exp(0.5 * (a + b))), "ok"


# ---------------------------------------------------------------------------------------------------------------
# One pair: M1, M2, D, jackknife
# ---------------------------------------------------------------------------------------------------------------
@dataclass
class Side:
    """One context of a pair, on the pair's targets P (rows aligned across the two sides)."""
    name: str
    raw: np.ndarray            # [n, G] effects (float16 or float32)
    se: np.ndarray | None      # [n, G] or None (then M2 is skipped)
    kappa: np.ndarray          # [G] SE calibration (scalar broadcast allowed)
    kfac: float                # CD4 factor 2 between families, else 1
    logcpm: np.ndarray         # [G] basal log1p CPM, for the expression bins

    def cols(self, sel) -> "Side":
        sel = np.asarray(sel)
        kap = np.broadcast_to(np.asarray(self.kappa, dtype=np.float64), (self.raw.shape[1],))[sel]
        return Side(self.name, self.raw[:, sel], None if self.se is None else self.se[:, sel], kap, self.kfac,
                    np.asarray(self.logcpm)[sel])

    def rows(self, sel) -> "Side":
        sel = np.asarray(sel)
        return Side(self.name, self.raw[sel], None if self.se is None else self.se[sel], self.kappa, self.kfac,
                    self.logcpm)


def gsig_genes(a: Side, b: Side, mask: np.ndarray) -> np.ndarray:
    """W4's declared fallback gene set: the genes whose signal share is >= 0.5 in both contexts of the pair."""
    sa = signal_share(a.raw, a.se, mask, a.kappa, a.kfac)
    sb = signal_share(b.raw, b.se, mask, b.kappa, b.kfac)
    with np.errstate(invalid="ignore"):
        return np.flatnonzero((sa >= W4_SIGNAL_SHARE) & (sb >= W4_SIGNAL_SHARE))


class _Halves:
    """The gene x gene matrices of one seed (context a/b x half 1/2). With `subtract`, the Grams are kept and a
    jackknife replicate is Gram - Gram(block) (cheap for large halves); otherwise it is recomputed from the rows
    (less memory, for the laptop)."""

    def __init__(self, Ua, Ub, h1, blocks, subtract: bool):
        self.U = {"a": Ua, "b": Ub}
        self.rows = {1: np.flatnonzero(h1), 2: np.flatnonzero(~h1)}
        self.blocks = blocks
        self.subtract = subtract
        self.G = {}
        if subtract:
            for s in ("a", "b"):
                for h in (1, 2):
                    self.G[(s, h)] = gram(self.U[s][self.rows[h]])

    def K(self, s: str, h: int, j: int | None = None) -> np.ndarray:
        r = self.rows[h]
        if j is None:
            return corr_from_gram(*self.G[(s, h)]) if self.subtract else corr_rows(self.U[s][r])
        if self.subtract:
            M, sm, n = self.G[(s, h)]
            Mj, sj, nj = gram(self.U[s][r[self.blocks[r] == j]])
            return corr_from_gram(M - Mj, sm - sj, n - nj)
        return corr_rows(self.U[s][r[self.blocks[r] != j]])


def m1_stats(get, bins_q, bins_a, bins_b) -> dict:
    """Q_cov, the two ceilings and their exact nulls, holding at most three matrices at a time; get(s, h) -> K."""
    a1, b2 = get("a", 1), get("b", 2)
    Q1, NQ1 = mantel(a1, b2), mantel_null_exact(a1, b2, bins_q)
    a2 = get("a", 2)
    Ca, Na = mantel(a1, a2), mantel_null_exact(a1, a2, bins_a)
    del a1
    b1 = get("b", 1)
    Q2, NQ2 = mantel(a2, b1), mantel_null_exact(a2, b1, bins_q)
    del a2
    Cb, Nb = mantel(b1, b2), mantel_null_exact(b1, b2, bins_b)
    return {"Q_cov": 0.5 * (Q1 + Q2), "C_a": Ca, "C_b": Cb, "NQ_exact": 0.5 * (NQ1 + NQ2), "Na_exact": Na,
            "Nb_exact": Nb}


def analyse_pair(a: Side, b: Side, mask: np.ndarray, essential, nsig_a, nsig_b, *, pair: str, stratum: str,
                 gene_set: str = "gstar", subset: str = "all", k_list=K_LIST, jack_k=K_JACK, seeds=SEEDS,
                 n_gene_perm: int = N_GENE_PERM, n_target_perm: int = N_TARGET_PERM, subtract: bool = True,
                 targets=None) -> dict:
    """M1, M2 and D for one pair on its pool P (rows aligned). Returns lists of records: 'pairs' (one per k and
    seed), 'ceilings' (per context), 'nulls' (Monte Carlo against exact), 'per_target' (k = 0 and 3)."""
    n, G = a.raw.shape
    rec = {"pairs": [], "ceilings": [], "nulls": [], "per_target": []}
    kmax = max(k_list) if len(k_list) else 0
    pa = prepare(a.raw, mask, a.se, kmax)
    pb = prepare(b.raw, mask, b.se, kmax)
    strata = pair_strata(nsig_a, nsig_b, essential)
    bins_a = rank_bins(a.logcpm, N_EXPR_BINS)
    bins_b = rank_bins(b.logcpm, N_EXPR_BINS)
    bins_q = rank_bins((np.asarray(a.logcpm) + np.asarray(b.logcpm)) / 2.0, N_EXPR_BINS)
    do_m2 = a.se is not None and b.se is not None
    per_t = {}
    base = {"pair": pair, "stratum": stratum, "a": a.name, "b": b.name, "gene_set": gene_set, "subset": subset,
            "n_targets": n, "n_genes": G}
    for k in k_list:
        Ua, Ub = project(pa.u, pa.V, k), project(pb.u, pb.V, k)
        m2 = {}
        if do_m2:
            sc = StrataCross(unit_rows(Ua), unit_rows(Ub), strata)
            ra = reliability(pa, Ua, k, a.kappa, a.kfac)
            rb = reliability(pb, Ub, k, b.kappa, b.kfac)
            sq = np.sqrt(ra * rb)
            m2 = {"Q_eff": float(sc.cos.mean()), "N_eff_exact": sc.exact(), "mean_sqrt_rr": float(sq.mean()),
                  "mean_sqrt_r_a": float(np.sqrt(ra).mean()), "mean_sqrt_r_b": float(np.sqrt(rb).mean())}
            ess = np.asarray(essential, dtype=bool)
            for lab, sel in (("essential", ess), ("nonessential", ~ess)):
                m2[f"Q_eff_{lab}"] = float(sc.cos[sel].mean()) if sel.any() else float("nan")
                m2[f"n_{lab}"] = int(sel.sum())
            if k in (0, K_MAIN):
                per_t[k] = (sc.cos.copy(), sq.copy())
        for seed in seeds:
            rng = rng_for(seed, pair, gene_set, subset, k)
            h1 = stratified_halves(strata, rng)
            blocks = make_blocks(n, rng)
            hv = _Halves(Ua, Ub, h1, blocks, subtract)
            K4 = {(s, hh): hv.K(s, hh) for s in ("a", "b") for hh in (1, 2)}
            st = m1_stats(lambda s, hh: K4[(s, hh)], bins_q, bins_a, bins_b)
            nq1 = mantel_null_mc(K4[("a", 1)], K4[("b", 2)], bins_q, n_gene_perm, rng)
            nq2 = mantel_null_mc(K4[("a", 2)], K4[("b", 1)], bins_q, n_gene_perm, rng)
            na = mantel_null_mc(K4[("a", 1)], K4[("a", 2)], bins_a, n_gene_perm, rng)
            nb = mantel_null_mc(K4[("b", 1)], K4[("b", 2)], bins_b, n_gene_perm, rng)
            del K4
            NQ = 0.5 * (nq1[0] + nq2[0])
            row = {**base, "k": k, "seed": seed, "n_h1": int(h1.sum()), "n_h2": int((~h1).sum()), **st,
                   "NQ": NQ, "Na": na[0], "Nb": nb[0],
                   "rho_cov": rho_from(st["Q_cov"], NQ, st["C_a"], na[0], st["C_b"], nb[0]),
                   "rho_cov_exact": rho_from(st["Q_cov"], st["NQ_exact"], st["C_a"], st["Na_exact"], st["C_b"],
                                             st["Nb_exact"])}
            for lab, (m, s), ex in (("Q_h1a_h2b", nq1, None), ("Q_h2a_h1b", nq2, None), ("C_a", na, st["Na_exact"]),
                                    ("C_b", nb, st["Nb_exact"])):
                rec["nulls"].append({**base, "k": k, "seed": seed, "measure": "M1", "which": lab, "mc_mean": m,
                                     "mc_sd": s, "n_perm": n_gene_perm, "exact": ex})
            if do_m2:
                ne, ne_sd = sc.mc(n_target_perm, rng)
                row.update(m2)
                row["N_eff"] = ne
                row["rho_eff"] = (m2["Q_eff"] - ne) / m2["mean_sqrt_rr"] if m2["mean_sqrt_rr"] > 0 else float("nan")
                row["rho_eff_exact"] = ((m2["Q_eff"] - m2["N_eff_exact"]) / m2["mean_sqrt_rr"]
                                        if m2["mean_sqrt_rr"] > 0 else float("nan"))
                row["D"] = row["rho_cov"] - row["rho_eff"]
                rec["nulls"].append({**base, "k": k, "seed": seed, "measure": "M2", "which": "Q_eff", "mc_mean": ne,
                                     "mc_sd": ne_sd, "n_perm": n_target_perm, "exact": m2["N_eff_exact"]})
            if k in jack_k:
                jr = {"rho_cov": [], "rho_eff": [], "D": []}
                for j in range(N_BLOCKS):
                    sj = m1_stats(lambda s, hh: hv.K(s, hh, j), bins_q, bins_a, bins_b)
                    rc = rho_from(sj["Q_cov"], sj["NQ_exact"], sj["C_a"], sj["Na_exact"], sj["C_b"], sj["Nb_exact"])
                    jr["rho_cov"].append(rc)
                    if do_m2:
                        keep = blocks != j
                        den = float(sq[keep].mean())
                        r_e = (float(sc.cos[keep].mean()) - sc.exact(keep)) / den if den > 0 else float("nan")
                        jr["rho_eff"].append(r_e)
                        jr["D"].append(rc - r_e)
                for key, vals in jr.items():
                    if vals:
                        row[f"se_{key}"] = jackknife_se(vals)
                        row[f"jack_n_{key}"] = int(np.isfinite(vals).sum())
            rec["pairs"].append(row)
            for side, C, N, Nx, r in (("a", st["C_a"], na[0], st["Na_exact"], m2.get("mean_sqrt_r_a")),
                                      ("b", st["C_b"], nb[0], st["Nb_exact"], m2.get("mean_sqrt_r_b"))):
                rec["ceilings"].append({**base, "k": k, "seed": seed, "context": a.name if side == "a" else b.name,
                                        "C_cov": C, "N": N, "N_exact": Nx, "ceiling_minus_null": C - N,
                                        "mean_sqrt_r": r})
            del hv
        del Ua, Ub
    if do_m2 and targets is not None:
        for i, t in enumerate(np.asarray(targets)):
            r = {"pair": pair, "stratum": stratum, "gene_set": gene_set, "subset": subset, "target": t,
                 "essential": bool(np.asarray(essential)[i]), "nsig_a": int(nsig_a[i]), "nsig_b": int(nsig_b[i])}
            for k, (cs, sq) in per_t.items():
                r[f"cos_k{k}"] = float(cs[i])
                r[f"sqrt_rr_k{k}"] = float(sq[i])
            rec["per_target"].append(r)
    return rec


# ---------------------------------------------------------------------------------------------------------------
# W4 and W5 (Part B)
# ---------------------------------------------------------------------------------------------------------------
@dataclass
class SSide:
    """A context held as stored effects (float16 is fine) with per-row masks: rows are prepared on demand."""
    name: str
    raw: np.ndarray            # [n, G]
    masks: MaskCSR             # per row
    logcpm: np.ndarray         # [G]


@dataclass
class PrepStats:
    mu: np.ndarray
    inv: np.ndarray            # 1 / SD, 0 for genes without variance
    V: np.ndarray              # [G, kmax]


def _block_z(raw, masks: MaskCSR, rows, mu=None, inv=None) -> tuple[np.ndarray, np.ndarray]:
    y = np.array(raw[rows], dtype=np.float32)
    with np.errstate(invalid="ignore"):
        bad = masks.dense(rows) | ~np.isfinite(y)
    if mu is not None:
        y -= mu.astype(np.float32)
        y *= inv.astype(np.float32)
    y[bad] = 0.0
    return y, bad


def prepare_stats(s: SSide, kmax: int, block: int = 1024) -> PrepStats:
    """The same centre, SD and top axes as `prepare`, streamed over row blocks (peak: one block and a G x G
    matrix), for pairs too large to hold as float32 on the laptop."""
    n, G = s.raw.shape
    sm, ss, cnt = np.zeros(G), np.zeros(G), np.zeros(G)
    for i in range(0, n, block):
        y, bad = _block_z(s.raw, s.masks, np.arange(i, min(i + block, n)))
        sm += y.sum(axis=0, dtype=np.float64)
        ss += np.einsum("ij,ij->j", y, y, dtype=np.float64)
        cnt += (~bad).sum(axis=0)
    mu = np.divide(sm, cnt, out=np.zeros(G), where=cnt > 0)
    var = np.divide(ss, cnt, out=np.zeros(G), where=cnt > 0) - mu ** 2
    sd = np.sqrt(np.maximum(var, 0.0))
    good = sd > 1e-12
    inv = np.where(good, 1.0 / np.where(good, sd, 1.0), 0.0)
    V = np.zeros((G, 0), dtype=np.float32)
    if kmax > 0:
        M = np.zeros((G, G), dtype=np.float32)
        for i in range(0, n, block):
            u = unit_rows(_block_z(s.raw, s.masks, np.arange(i, min(i + block, n)), mu, inv)[0])
            M += u.T @ u
        V = _top_from_gram(M, kmax)
    return PrepStats(mu, inv, V)


def _top_from_gram(M: np.ndarray, kmax: int) -> np.ndarray:
    G = M.shape[0]
    kmax = int(min(kmax, G))
    M64 = M.astype(np.float64)
    del M
    try:
        from scipy.linalg import eigh
        _, V = eigh(M64.T, subset_by_index=[G - kmax, G - 1], overwrite_a=True)   # symmetric: .T is F-order
    except ImportError:
        _, V = np.linalg.eigh(M64)
        V = V[:, G - kmax:]
    V = V[:, ::-1]
    sgn = np.sign(V[np.abs(V).argmax(axis=0), np.arange(V.shape[1])])
    return (V * np.where(sgn == 0, 1.0, sgn)).astype(np.float32)


def u_rows(s: SSide, st: PrepStats, rows, k: int) -> np.ndarray:
    """Prepared rows (centred, standardised, masked -> 0, unit, first k axes removed) of a streamed side."""
    u = unit_rows(_block_z(s.raw, s.masks, np.asarray(rows), st.mu, st.inv)[0], inplace=True)
    return project_inplace(u, st.V, k)


def _m1_rho(Ka1, Ka2, Kb1, Kb2, bins_q, bins_a, bins_b, nperm, rng) -> dict:
    Q = 0.5 * (mantel(Ka1, Kb2) + mantel(Ka2, Kb1))
    Ca, Cb = mantel(Ka1, Ka2), mantel(Kb1, Kb2)
    NQ = 0.5 * (mantel_null_mc(Ka1, Kb2, bins_q, nperm, rng)[0] + mantel_null_mc(Ka2, Kb1, bins_q, nperm, rng)[0])
    Na = mantel_null_mc(Ka1, Ka2, bins_a, nperm, rng)[0]
    Nb = mantel_null_mc(Kb1, Kb2, bins_b, nperm, rng)[0]
    return {"Q_cov": Q, "C_a": Ca, "C_b": Cb, "NQ": NQ, "Na": Na, "Nb": Nb, "rho_cov": rho_from(Q, NQ, Ca, Na, Cb, Nb)}


def analyse_w4(half_a: SSide, half_b: SSide, ref: SSide, strata, *, k_list=(K_MAIN, 0), seeds=SEEDS,
               n_gene_perm=N_GENE_PERM) -> list[dict]:
    """W4: rho_cov(one cell half, ref) against rho_cov(cross-half matrix, ref), same targets, same H1/H2. The cross
    matrix corr_t(A_g, B_h) holds no within-pseudobulk noise covariance (the halves share no cells)."""
    kmax = max(k_list)
    sA, sB, sR = (prepare_stats(s, kmax) for s in (half_a, half_b, ref))
    bins_v = rank_bins(half_a.logcpm, N_EXPR_BINS)
    bins_r = rank_bins(ref.logcpm, N_EXPR_BINS)
    bins_q = rank_bins((np.asarray(half_a.logcpm) + np.asarray(ref.logcpm)) / 2.0, N_EXPR_BINS)
    out = []
    for k in k_list:
        for seed in seeds:
            rng = rng_for(seed, "w4", k)
            h1 = stratified_halves(strata, rng)
            r1, r2 = np.flatnonzero(h1), np.flatnonzero(~h1)
            KR1, KR2 = corr_rows(u_rows(ref, sR, r1, k)), corr_rows(u_rows(ref, sR, r2, k))
            row = {"pair": f"{half_a.name}+{half_b.name}|{ref.name}", "k": k, "seed": seed,
                   "n_targets": int(h1.size)}
            for lab in ("half_a", "half_b", "cross"):
                def K(r, lab=lab):
                    if lab == "half_a":
                        return corr_rows(u_rows(half_a, sA, r, k))
                    if lab == "half_b":
                        return corr_rows(u_rows(half_b, sB, r, k))
                    return cross_corr(u_rows(half_a, sA, r, k), u_rows(half_b, sB, r, k))
                K1, K2 = K(r1), K(r2)
                for key, v in _m1_rho(K1, K2, KR1, KR2, bins_q, bins_v, bins_r, n_gene_perm, rng).items():
                    row[f"{lab}_{key}"] = v
                del K1, K2
            row["diff_one_half_minus_cross"] = (0.5 * (row["half_a_rho_cov"] + row["half_b_rho_cov"])
                                                - row["cross_rho_cov"])
            out.append(row)
            del KR1, KR2
    return out


def ntc_pseudo_effects(path, gene_names, min_cells: int = 20) -> tuple[np.ndarray, np.ndarray]:
    """Non-targeting pseudo-effects of a Replogle bulk file, as se_calibrazione/se_ntc_check.py builds them: each
    non-targeting row with >= min_cells cells against the pooled rest, ln fraction ratio; columns in `gene_names`
    order (NaN where the file lacks the gene or its control fraction is below 1e-6). Returns (effects, n_cells)."""
    X, n, names = _ntc_rows(path, min_cells)
    tot = (X * n[:, None]).sum(axis=0)
    N = n.sum()
    frac = X / X.sum(axis=1, keepdims=True)
    eff = np.full((X.shape[0], len(gene_names)), np.nan, dtype=np.float32)
    col = pd.Index(names).get_indexer(np.asarray(gene_names).astype(str))
    have = col >= 0
    for i in range(X.shape[0]):
        cmu = (tot - X[i] * n[i]) / (N - n[i])
        cfrac = cmu / cmu.sum()
        ok = (cfrac >= 1e-6) & (X[i] > 0)
        e = np.log(np.maximum(frac[i], 1e-7)) - np.log(np.maximum(cfrac, 1e-7))
        e = np.where(ok, e, np.nan)
        eff[i, have] = e[col[have]]
    return eff, n


def _ntc_rows(path, min_cells: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    import h5py
    with h5py.File(path, "r") as f:
        labels = np.array([s.decode() if isinstance(s, bytes) else str(s) for s in f["obs/gene_transcript"][:]])
        rows = np.flatnonzero(np.array(["non-targeting" in lab for lab in labels]))
        parts = []                                    # contiguous row blocks: bounded memory on h5py reads
        for i in range(0, f["X"].shape[0], 512):
            sel = rows[(rows >= i) & (rows < i + 512)]
            if sel.size:
                parts.append(np.asarray(f["X"][i:i + 512], dtype=np.float64)[sel - i])
        X = np.concatenate(parts) if parts else np.zeros((0, f["X"].shape[1]))
        n = f["obs/num_cells_filtered"][:][rows].astype(np.float64)
        g = f["var/gene_name"]
        if np.issubdtype(g.dtype, np.integer) and "var/__categories/gene_name" in f:
            cats = np.array([s.decode() if isinstance(s, bytes) else str(s) for s in f["var/__categories/gene_name"][:]])
            names = cats[g[:]]
        else:
            names = np.array([s.decode() if isinstance(s, bytes) else str(s) for s in g[:]])
    good = np.isfinite(n) & (n >= min_cells)
    X, n = X[good], n[good]
    _, first = np.unique(names, return_index=True)
    keep = np.sort(first)
    return X[:, keep], n, names[keep]


NTC_BINS = (0, 0.01, 0.03, 0.1, 0.3, 1, 3, 10, 1e9)


def ntc_kappa(path, gene_names, phi: float = 0.2, n_rows: int = 200, seed: int = 0) -> tuple[np.ndarray, list]:
    """Per-gene SE calibration of a Replogle context: the ratio observed mean LFC^2 / predicted mean se^2 on
    non-targeting rows, per bin of control mean count per cell, exactly as se_calibrazione/se_ntc_check.py (same
    seed, rows, bins and phi); bins with fewer than 20 genes take the nearest valid bin. Genes the file lacks get 1."""
    X, n, names = _ntc_rows(path, 20)
    rng = np.random.default_rng(seed)
    obs, pred, mus = [], [], []
    for i in rng.choice(X.shape[0], size=min(n_rows, X.shape[0]), replace=False):
        m = np.ones(X.shape[0], dtype=bool)
        m[i] = False
        cmu = (X[m] * n[m, None]).sum(axis=0) / n[m].sum()
        cfrac = cmu / cmu.sum()
        nc = max(n[m].sum(), 1000.0)
        mu = X[i]
        frac = mu / mu.sum()
        ok = (cfrac >= 1e-6) & (mu > 0)
        eff = np.log(np.maximum(frac, 1e-7)) - np.log(np.maximum(cfrac, 1e-7))
        se2 = 1.0 / (n[i] * np.maximum(mu, 1e-3)) + phi / n[i] + 1.0 / (nc * np.maximum(cmu, 1e-3)) + phi / nc
        obs.append(np.where(ok, eff ** 2, np.nan))
        pred.append(np.where(ok, se2, np.nan))
        mus.append(cmu)
    O, P, M = np.array(obs), np.array(pred), np.array(mus).mean(axis=0)
    b = np.digitize(M, NTC_BINS) - 1
    table, ratio = [], {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        for k in range(len(NTC_BINS) - 1):
            g = b == k
            if g.sum() < 20:
                continue
            o, p = float(np.nanmean(O[:, g])), float(np.nanmean(P[:, g]))
            ratio[k] = o / p
            table.append({"bin": [NTC_BINS[k], NTC_BINS[k + 1]], "genes": int(g.sum()), "obs": o, "pred": p,
                          "ratio": o / p})
    valid = np.array(sorted(ratio))
    gene_bin = b
    kap_file = np.array([ratio[valid[np.abs(valid - x).argmin()]] for x in gene_bin])
    col = pd.Index(names).get_indexer(np.asarray(gene_names).astype(str))
    kappa = np.where(col >= 0, kap_file[np.maximum(col, 0)], 1.0)
    return kappa, table


def analyse_w5(ref: SSide, other: SSide, ntc: SSide, strata, *, k_list=(K_MAIN, 0), seeds=SEEDS) -> list[dict]:
    """W5: Q_cov(k562, d) - Q_cov(non-targeting pseudo-effects of k562, d), with a jackknife over 20 blocks that
    delete targets and non-targeting rows together. choice: k562's halves are subsampled to the size of the
    non-targeting halves, so both Q_cov compare matrices estimated from as many rows (the unmatched Q_cov of k562
    is reported too)."""
    kmax = max(k_list)
    sR, sD, sN = prepare_stats(ref, kmax), prepare_stats(other, kmax), prepare_stats(ntc, kmax)
    nN = ntc.raw.shape[0]
    out = []
    for k in k_list:
        for seed in seeds:
            rng = rng_for(seed, "w5", other.name, k)
            h1 = stratified_halves(strata, rng)
            r1, r2 = np.flatnonzero(h1), np.flatnonzero(~h1)
            perm = rng.permutation(nN)
            nA, nB = np.sort(perm[: nN // 2]), np.sort(perm[nN // 2:])
            m = min(nA.size, nB.size, r1.size, r2.size)
            s1, s2 = np.sort(rng.choice(r1, m, replace=False)), np.sort(rng.choice(r2, m, replace=False))
            blocks = make_blocks(h1.size, rng)
            nblocks = make_blocks(nN, rng)

            def qs(j=None, unmatched=False):
                kt = (lambda r: r) if j is None else (lambda r: r[blocks[r] != j])
                kn = (lambda r: r) if j is None else (lambda r: r[nblocks[r] != j])
                res = {}
                KD = corr_rows(u_rows(other, sD, kt(r2), k))
                res["Q_k1d2"] = mantel(corr_rows(u_rows(ref, sR, kt(s1), k)), KD)
                res["Q_nAd2"] = mantel(corr_rows(u_rows(ntc, sN, kn(nA), k)), KD)
                if unmatched:
                    res["Q_full_k1d2"] = mantel(corr_rows(u_rows(ref, sR, r1, k)), KD)
                del KD
                KD = corr_rows(u_rows(other, sD, kt(r1), k))
                res["Q_k2d1"] = mantel(corr_rows(u_rows(ref, sR, kt(s2), k)), KD)
                res["Q_nBd1"] = mantel(corr_rows(u_rows(ntc, sN, kn(nB), k)), KD)
                if unmatched:
                    res["Q_full_k2d1"] = mantel(corr_rows(u_rows(ref, sR, r2, k)), KD)
                del KD
                res["Q_ref"] = 0.5 * (res["Q_k1d2"] + res["Q_k2d1"])
                res["Q_ntc"] = 0.5 * (res["Q_nAd2"] + res["Q_nBd1"])
                res["diff"] = res["Q_ref"] - res["Q_ntc"]
                return res

            full = qs(unmatched=True)
            reps = [qs(j)["diff"] for j in range(N_BLOCKS)]
            out.append({"pair": f"{ref.name}|{other.name}", "k": k, "seed": seed, "n_targets": int(h1.size),
                        "n_ntc_rows": int(nN), "n_matched": int(m), **full,
                        "Q_ref_unmatched": 0.5 * (full["Q_full_k1d2"] + full["Q_full_k2d1"]),
                        "se_diff": jackknife_se(reps)})
    return out


# ---------------------------------------------------------------------------------------------------------------
# M3a
# ---------------------------------------------------------------------------------------------------------------
@dataclass
class Ctx:
    """One context's non-panel rows for M3a, on columns `cols` of which the first G are G*."""
    name: str
    tids: np.ndarray           # target id per row
    raw: np.ndarray            # [n, C] float16
    se: np.ndarray             # [n, C] float16
    masks: MaskCSR             # per row, over the C columns
    nsig: np.ndarray           # per row, on G*
    kappa: np.ndarray          # [C]
    kfac: float


def _col_stats(c: Ctx, rows, colsel) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Training mean and SD of `colsel` over `rows` (masked and unknown entries out), and z of those rows."""
    Y = np.asarray(c.raw[np.ix_(np.asarray(rows), np.asarray(colsel))], dtype=np.float32)
    with np.errstate(invalid="ignore"):
        bad = c.masks.dense(rows, colsel) | ~np.isfinite(Y)
    mu, sd, _ = nan_stats(Y, bad)
    good = np.isfinite(sd) & (sd > 1e-12)
    Y *= np.where(good, 1.0 / np.where(good, sd, 1.0), 0.0).astype(np.float32)
    return mu, sd, Y


def _z_rows(c: Ctx, rows, colsel, mu, sd) -> np.ndarray:
    Y = np.asarray(c.raw[np.ix_(np.asarray(rows), np.asarray(colsel))], dtype=np.float32)
    with np.errstate(invalid="ignore"):
        bad = c.masks.dense(rows, colsel) | ~np.isfinite(Y)
    good = np.isfinite(sd) & (sd > 1e-12)
    Y = (Y - mu.astype(np.float32)) * np.where(good, 1.0 / np.where(good, sd, 1.0), 0.0).astype(np.float32)
    Y[bad] = 0.0
    return Y


def signal_variance(c: Ctx, rows, cols, block: int = 512) -> np.ndarray:
    """Per column: mean squared deviation over `rows` minus the mean calibrated SE^2 (kfac kappa se^2), masked and
    unknown entries out: the signal variance of a target's own gene in a source (M3a eligibility)."""
    out = np.full(len(cols), np.nan)
    rows = np.asarray(rows)
    cols = np.asarray(cols)
    for i in range(0, cols.size, block):
        cs = cols[i:i + block]
        Y = np.asarray(c.raw[np.ix_(rows, cs)], dtype=np.float32)
        S = np.asarray(c.se[np.ix_(rows, cs)], dtype=np.float32)
        with np.errstate(invalid="ignore"):
            bad = c.masks.dense(rows, cs) | ~np.isfinite(Y) | ~np.isfinite(S)
        _, sd, cnt = nan_stats(Y, bad)
        S[bad] = 0.0
        noise = np.divide((S.astype(np.float64) ** 2).sum(axis=0), cnt, out=np.full(cs.size, np.nan), where=cnt > 1)
        out[i:i + cs.size] = np.where(cnt > 1, sd ** 2 - c.kfac * np.asarray(c.kappa)[cs] * noise, np.nan)
    return out


def _masked_cos_matrix(P: np.ndarray, T: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """C[i, j] = cos(P[j] restricted to valid[i], T[i]) where T is already 0 outside valid[i]."""
    dot = T @ P.T
    pn2 = valid.astype(np.float32) @ (P * P).T
    tn2 = np.einsum("ij,ij->i", T, T, dtype=np.float64)
    den = np.sqrt(np.maximum(pn2, 0.0) * tn2[:, None])
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(den > 0, dot / np.where(den > 0, den, 1.0), 0.0)


def route_skill(P: np.ndarray, T: np.ndarray, valid: np.ndarray, strata, rng, n_boot: int = N_BOOT) -> dict:
    """Specific skill of a route: per target cos(p(t), truth(t)) minus its exact expectation when targets are
    permuted within strata (mean over the stratum of cos(p(t'), truth(t)), t' = t included); bootstrap over targets."""
    strata = np.asarray(strata)
    cos = np.empty(T.shape[0])
    null = np.empty(T.shape[0])
    for s in np.unique(strata):
        g = np.flatnonzero(strata == s)
        C = _masked_cos_matrix(P[g], T[g], valid[g])
        cos[g] = np.diag(C)
        null[g] = C.mean(axis=1)
    d = cos - null
    boot = np.array([d[rng.integers(0, d.size, d.size)].mean() for _ in range(n_boot)]) if d.size else np.array([np.nan])
    return {"n": int(d.size), "mean_cos": float(cos.mean()) if d.size else np.nan,
            "mean_null": float(null.mean()) if d.size else np.nan, "delta": float(d.mean()) if d.size else np.nan,
            "lo": float(np.quantile(boot, 0.025)), "hi": float(np.quantile(boot, 0.975)), "per_target": d,
            "cos": cos, "null": null}


def m3a_context(h: str, data: dict, sources: list, *, G: int, xpos_of: dict, logcpm_h_x: dict, essential_of: dict,
                seeds=SEEDS, n_boot: int = N_BOOT, debug: dict | None = None) -> dict:
    """M3a for held-out context h (RISULTATI.md, "M3a, l'uso"). data[c] is a Ctx on columns [G* | extra] for h and
    every source; xpos_of[target id] is the column of the target's own gene (-1: not stored). Returns records.

    Test targets: a random half (per seed) of the eligible ones -- non-panel, responsive in h, own gene stored, with
    signal variance above 0 in every source (computed on the source rows of targets that are not candidates in h, so
    no candidate's outcome enters the choice). Training: every other non-panel target. The test targets' rows leave
    every mean, SD and beta, in h and in the sources; the effect route reads their source rows as input only."""
    H = data[h]
    rec = {"m3a": [], "m3a_targets": [], "counts": {}}
    cand = np.flatnonzero((H.nsig >= MIN_SIG_GENES) & np.array([xpos_of.get(int(t), -1) >= 0 for t in H.tids]))
    cand_t = H.tids[cand]
    xcols = np.array([xpos_of[int(t)] for t in cand_t], dtype=np.int64)
    sig = np.full((len(sources), cand.size), np.nan)
    for i, s in enumerate(sources):
        S = data[s]
        rows = np.flatnonzero(~np.isin(S.tids, cand_t))
        sig[i] = signal_variance(S, rows, xcols)
    with np.errstate(invalid="ignore"):
        elig = np.all(np.nan_to_num(sig, nan=-1.0) > 0, axis=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        xsig = np.nanmean(np.where(np.isfinite(sig), sig, np.nan), axis=0) if sig.size else np.zeros(0)
    rec["counts"] = {"h": h, "responsive_with_stored_gene": int(cand.size), "eligible": int(elig.sum())}
    el_rows, el_t, el_x, el_sig = cand[elig], cand_t[elig], xcols[elig], xsig[elig]
    gidx = np.arange(G)
    for seed in seeds:
        rng = rng_for(seed, "m3a", h)
        order = rng.permutation(el_rows.size)
        test = np.sort(order[: el_rows.size // 2])
        t_ids, t_rows, t_x = el_t[test], el_rows[test], el_x[test]
        m = t_ids.size
        if m < 2:
            continue
        ux, inv = np.unique(t_x, return_inverse=True)
        colsel = np.concatenate([gidx, ux[~np.isin(ux, gidx)]])
        xin = pd.Index(colsel).get_indexer(ux)          # position of each unique x within colsel
        rel_sum = np.zeros((m, G))
        rel_cnt = np.zeros(m)
        eff_sum = np.zeros((m, G))
        eff_cnt = np.zeros(m)
        beta_in = None
        truth = None
        for c in [h] + list(sources):
            C = data[c]
            train = np.flatnonzero(~np.isin(C.tids, t_ids))
            mu, sd, Z = _col_stats(C, train, colsel)
            Zx = Z[:, xin]
            num = Zx.T @ Z[:, :G]
            den = np.einsum("ij,ij->j", Zx, Zx, dtype=np.float64)
            beta = np.where(den[:, None] > 0, num / np.where(den > 0, den, 1.0)[:, None], np.nan)[inv]
            if debug is not None:
                debug.setdefault(seed, {})[c] = {"mu": mu.copy(), "sd": sd.copy(), "beta": beta.copy()}
            del Z, Zx, num
            if c == h:
                beta_in = -beta
                truth_rows = t_rows
                truth = _z_rows(C, truth_rows, gidx, mu[:G], sd[:G])
                raw_h = np.asarray(C.raw[truth_rows, :G], dtype=np.float32)
                valid = ~C.masks.dense(truth_rows, gidx) & np.isfinite(raw_h)
                del raw_h
                truth[~valid] = 0.0
            else:
                ok = np.isfinite(beta).all(axis=1)
                rel_sum[ok] -= beta[ok]
                rel_cnt[ok] += 1
                pos = {int(t): i for i, t in enumerate(C.tids)}
                have = np.array([pos.get(int(t), -1) for t in t_ids])
                hv = np.flatnonzero(have >= 0)
                if hv.size:
                    zt = _z_rows(C, have[hv], gidx, mu[:G], sd[:G])
                    eff_sum[hv] += zt
                    eff_cnt[hv] += 1
        with np.errstate(invalid="ignore", divide="ignore"):
            p_rel = rel_sum / np.where(rel_cnt > 0, rel_cnt, np.nan)[:, None]
            p_eff = eff_sum / np.where(eff_cnt > 0, eff_cnt, np.nan)[:, None]
        p_in = beta_in
        ess = np.array([bool(essential_of.get(int(t), False)) for t in t_ids])
        nsig_h = H.nsig[t_rows]
        lc = np.array([logcpm_h_x.get(int(t), np.nan) for t in t_ids])
        rel_strata = rank_bins(lc, N_DECILES) * N_DECILES + rank_bins(el_sig[test], N_DECILES)
        eff_strata = rank_bins(nsig_h, N_DECILES) * 2 + ess.astype(np.int64)
        routes = {}
        for name, P, strata in (("relation", p_rel, rel_strata), ("inline", p_in, rel_strata),
                                ("effect", p_eff, eff_strata)):
            ok = np.isfinite(P).all(axis=1)
            routes[name] = (ok, route_skill(np.nan_to_num(P[ok]).astype(np.float32), truth[ok], valid[ok],
                                            strata[ok], rng_for(seed, "boot", h, name), n_boot))
        both = routes["relation"][0] & routes["effect"][0]

        def unit_on_valid(P):
            Pm = np.where(valid, np.nan_to_num(P), 0.0)
            n = np.sqrt((Pm ** 2).sum(axis=1))
            return Pm / np.where(n > 0, n, 1.0)[:, None]

        p_comb = unit_on_valid(p_eff) + unit_on_valid(p_rel)
        comb = route_skill(p_comb[both].astype(np.float32), truth[both], valid[both], eff_strata[both],
                           rng_for(seed, "boot", h, "combined"), n_boot)
        eff_b = route_skill(np.nan_to_num(p_eff[both]).astype(np.float32), truth[both], valid[both], eff_strata[both],
                            rng_for(seed, "boot", h, "effect_on_both"), n_boot)
        gain_t = comb["per_target"] - eff_b["per_target"]
        grng = rng_for(seed, "boot", h, "gain")
        gboot = np.array([gain_t[grng.integers(0, gain_t.size, gain_t.size)].mean() for _ in range(n_boot)]) \
            if gain_t.size else np.array([np.nan])
        routes_out = {**{k: v[1] for k, v in routes.items()}, "combined": comb, "effect_on_both": eff_b,
                      "gain_combined_minus_effect": {"n": int(gain_t.size), "mean_cos": np.nan, "mean_null": np.nan,
                                                     "delta": float(gain_t.mean()) if gain_t.size else np.nan,
                                                     "lo": float(np.quantile(gboot, 0.025)),
                                                     "hi": float(np.quantile(gboot, 0.975))}}
        for name, r in routes_out.items():
            rec["m3a"].append({"h": h, "seed": seed, "route": name, "n_test": int(m), "n": r["n"],
                               "mean_cos": r["mean_cos"], "mean_null": r["mean_null"], "delta": r["delta"],
                               "lo": r["lo"], "hi": r["hi"], "sources": "|".join(sources)})
        for name in ("relation", "inline", "effect"):
            ok, r = routes[name]
            for t, cs, nl in zip(t_ids[ok], r["cos"], r["null"]):
                rec["m3a_targets"].append({"h": h, "seed": seed, "route": name, "target_id": int(t), "cos": float(cs),
                                           "null": float(nl)})
    return rec


# ---------------------------------------------------------------------------------------------------------------
# The registered rule
# ---------------------------------------------------------------------------------------------------------------
def _seed_mean(df: pd.DataFrame, keys: list, cols: list) -> pd.DataFrame:
    if not len(df):
        return pd.DataFrame(columns=[*keys, *cols])
    return df.groupby(keys, dropna=False)[cols].mean().reset_index()


def decide(pairs: pd.DataFrame, ceilings: pd.DataFrame, m3a: pd.DataFrame, *, kappa_pb: float | None,
           w4: pd.DataFrame | None, w5: pd.DataFrame | None, s0_pairs: pd.DataFrame | None,
           counts: pd.DataFrame) -> dict:
    """Apply the rule of RISULTATI.md ("Controlli di validità", "Regola"). Tables as written by run_parte_a.py
    (pairs, ceilings, m3a, counts) and run_parte_b.py (w4, w5, s0_pairs: the S0 pairs' rows of its pairs.csv).
    A missing Part B table leaves its check "pending" and the verdict provisional ("in attesa della parte B").

    Choices (declared): W1 per context = median over its P9 pairs of (C_cov - null) and of mean sqrt(r), k = 3,
    seed mean; a context that fails leaves every P9 pair and the M3a reading, the M3a sources stay as run; the counts
    5 of 9 and 4 of 5 stay absolute when contexts leave. W2 compares medians of rho_cov and of rho_eff at k = 3.
    W4 triggers on |mean(rho_cov one half A, B) - rho_cov cross| > 0.10, seed mean, k = 3. W5 needs every retained
    K562 pair of P9 to have diff - 1.96 SE > 0 (seed means). A pair's interval is the seed-mean D +- 1.96 x the
    seed-mean jackknife SE. Precedence: W1 or W2 failed -> inconclusive; W5 failed -> mappa no; W3 failed -> mappa
    pending (fase B)."""
    v: dict = {"checks": {}, "notes": []}
    cnt = counts[counts["stratum"] == "P9"] if "stratum" in counts.columns else counts
    w6_ok = {r["pair"]: bool(r["n_P"] >= MIN_SHARED_RESPONSIVE) for _, r in cnt.iterrows()}
    v["checks"]["W6"] = {"pairs_below_200": sorted(p for p, ok in w6_ok.items() if not ok)}
    # W4 decides the gene set of the "mappa" reading
    gene_set, w4_state = "gstar", "pending"
    if w4 is not None and len(w4):
        d = w4[w4["k"] == K_MAIN]["diff_one_half_minus_cross"].mean()
        # choice: a cross-half rho_cov that cannot be formed (its ceiling not above its null) counts as a difference
        w4_state = "triggered" if (not np.isfinite(d) or abs(d) > W4_MAX_DIFF) else "passed"
        gene_set = "gsig" if w4_state == "triggered" else "gstar"
        v["checks"]["W4"] = {"diff": float(d), "state": w4_state, "gene_set": gene_set}
    else:
        v["checks"]["W4"] = {"state": "pending", "gene_set": gene_set}
    p9 = pairs[(pairs["stratum"] == "P9") & (pairs["gene_set"] == gene_set) & (pairs["subset"] == "all")
               & (pairs["k"] == K_MAIN)].copy()
    p9 = p9[p9["pair"].map(lambda p: w6_ok.get(p, False)).astype(bool)]
    # W1
    ce = ceilings[(ceilings["stratum"] == "P9") & (ceilings["gene_set"] == gene_set) & (ceilings["subset"] == "all")
                  & (ceilings["k"] == K_MAIN)]
    ce = ce[ce["pair"].map(lambda p: w6_ok.get(p, False)).astype(bool)]
    cm = _seed_mean(ce, ["pair", "context"], ["ceiling_minus_null", "mean_sqrt_r"])
    w1 = {}
    for c in P9_CONTEXTS:
        sub = cm[cm["context"] == c]
        cmn, sr = float(sub["ceiling_minus_null"].median()) if len(sub) else np.nan, \
            float(sub["mean_sqrt_r"].median()) if len(sub) else np.nan
        w1[c] = {"ceiling_minus_null": cmn, "mean_sqrt_r": sr,
                 "pass": bool(np.isfinite(cmn) and np.isfinite(sr) and cmn >= W1_CEILING_MIN and sr >= W1_SQRT_R_MIN)}
    kept = [c for c in P9_CONTEXTS if w1[c]["pass"]]
    v["checks"]["W1"] = {"per_context": w1, "retained": kept, "pass": len(kept) >= W1_MIN_CONTEXTS}
    p9 = p9[p9["a"].isin(kept) & p9["b"].isin(kept)]
    # W7 and the per-pair intervals
    if len(p9):
        g = p9.groupby("pair")
        tab = pd.DataFrame({"D": g["D"].mean(), "se_D": g["se_D"].mean(), "rho_cov": g["rho_cov"].mean(),
                            "rho_eff": g["rho_eff"].mean(),
                            "all_seeds_positive": g["D"].apply(lambda s: bool((s > 0).all())),
                            "n_seeds": g["D"].size(), "a": g["a"].first(), "b": g["b"].first()})
    else:
        v["notes"].append("nessuna coppia P9 utilizzabile")
        tab = pd.DataFrame(columns=["D", "se_D", "rho_cov", "rho_eff", "all_seeds_positive", "n_seeds", "a", "b"],
                           index=pd.Index([], name="pair")).astype({"D": float, "se_D": float, "rho_cov": float,
                                                                   "rho_eff": float, "all_seeds_positive": bool})
    tab["lo"] = tab["D"] - Z95 * tab["se_D"]
    tab["hi"] = tab["D"] + Z95 * tab["se_D"]
    tab["positive"] = (tab["lo"] > 0) & tab["all_seeds_positive"]
    v["pairs"] = tab.reset_index().to_dict(orient="records")
    med_D = float(tab["D"].median()) if len(tab) else np.nan
    med_rho = float(tab["rho_cov"].median()) if len(tab) else np.nan
    loco = {}
    for c in kept:
        sub = tab[(tab["a"] != c) & (tab["b"] != c)]
        loco[c] = float(sub["D"].median()) if len(sub) else np.nan
    loco_ok = bool(np.isfinite(med_D) and all(np.isfinite(x) and np.sign(x) == np.sign(med_D) and x != 0
                                              for x in loco.values()))
    yes = (np.isfinite(med_D) and med_D >= MAP_YES_D_MEDIAN and int(tab["positive"].sum()) >= MAP_YES_MIN_POSITIVE
           and not bool((tab["hi"] < MAP_YES_NO_PAIR_BELOW).any()) and np.isfinite(med_rho)
           and med_rho >= MAP_YES_RHO_MEDIAN and loco_ok)
    no = (np.isfinite(med_D) and med_D <= MAP_NO_D_MEDIAN) or (np.isfinite(med_rho) and med_rho < MAP_NO_RHO_MEDIAN)
    mappa = "sì" if yes else ("no" if no else "inconclusiva")
    v["mappa_rule"] = {"median_D": med_D, "median_rho_cov": med_rho, "n_positive": int(tab["positive"].sum()),
                       "n_pairs": int(len(tab)), "pairs_hi_below_-0.05": int((tab["hi"] < MAP_YES_NO_PAIR_BELOW).sum()),
                       "leave_one_context_out_median_D": loco, "loco_sign_holds": loco_ok, "reading_before_W3_W5": mappa}
    # W5
    w5_state = "pending"
    if w5 is not None and len(w5):
        w = w5[w5["k"] == K_MAIN].groupby("pair")[["diff", "se_diff"]].mean()
        k562_pairs = [f"k562|{c}" for c in kept if c != "k562" and frozenset(("k562", c)) not in SAME_LINE]
        if "k562" not in kept:
            k562_pairs = []
        rows = {p: {"diff": float(w.loc[p, "diff"]), "lo": float(w.loc[p, "diff"] - Z95 * w.loc[p, "se_diff"])}
                for p in k562_pairs if p in w.index}
        missing = [p for p in k562_pairs if p not in w.index]
        ok = all(r["diff"] > 0 and r["lo"] > 0 for r in rows.values()) and not missing
        w5_state = "passed" if ok else "failed"
        v["checks"]["W5"] = {"per_pair": rows, "missing": missing, "state": w5_state}
    else:
        v["checks"]["W5"] = {"state": "pending"}
    # W3
    w3_state = "pending"
    if kappa_pb is not None and np.isfinite(kappa_pb):
        w3_state = "passed" if W3_KAPPA_RANGE[0] <= kappa_pb <= W3_KAPPA_RANGE[1] else "failed"
    v["checks"]["W3"] = {"kappa_pseudobulk": kappa_pb, "state": w3_state}
    if w5_state == "failed":
        mappa = "no"
        v["notes"].append("W5: la conservazione non supera quella delle guide non mirate: mappa no")
    elif w3_state == "failed":
        mappa = "inconclusiva"
        v["notes"].append("W3: kappa fuori da [0,5; 2]: la lettura mappa aspetta la fase B")
    v["mappa"] = mappa
    # W2
    w2_state = "pending"
    if s0_pairs is not None and len(s0_pairs):
        s1 = pairs[(pairs["stratum"] == "S1") & (pairs["gene_set"] == "gstar") & (pairs["subset"] == "all")
                   & (pairs["k"] == K_MAIN)]
        np_of = counts.set_index("pair")["n_P"]
        s1 = s1[s1["pair"].map(lambda p: bool(np_of.get(p, 0) >= MIN_SHARED_RESPONSIVE)).astype(bool)]
        s0 = s0_pairs[(s0_pairs["k"] == K_MAIN) & (s0_pairs["n_targets"] >= MIN_SHARED_RESPONSIVE)]
        ref = pd.concat([s0, s1], ignore_index=True)
        rm = ref.groupby("pair")[["rho_cov", "rho_eff"]].mean()
        p9g = pairs[(pairs["stratum"] == "P9") & (pairs["gene_set"] == "gstar") & (pairs["subset"] == "all")
                    & (pairs["k"] == K_MAIN)]
        p9g = p9g[p9g["pair"].map(lambda p: w6_ok.get(p, False)).astype(bool)].groupby("pair")[["rho_cov", "rho_eff"]].mean()
        m = {x: {"S0_S1": float(rm[x].median()) if len(rm) else np.nan, "P9": float(p9g[x].median())
                 if len(p9g) else np.nan} for x in ("rho_cov", "rho_eff")}
        ok = all(np.isfinite(m[x]["S0_S1"]) and np.isfinite(m[x]["P9"]) and m[x]["S0_S1"] > m[x]["P9"] for x in m)
        w2_state = "passed" if ok else "failed"
        v["checks"]["W2"] = {"medians": m, "n_reference_pairs": int(len(rm)), "state": w2_state}
    else:
        v["checks"]["W2"] = {"state": "pending"}
    # uso
    mm = m3a[m3a["h"].isin(kept)]
    per = {}
    for route in ("relation", "inline", "effect", "combined", "gain_combined_minus_effect"):
        sub = mm[mm["route"] == route].groupby("h")[["delta", "lo", "hi"]].mean()
        per[route] = sub.to_dict(orient="index")
    n_rel = sum(1 for r in per["relation"].values() if r["delta"] > 0 and r["lo"] > 0)
    n_in = sum(1 for r in per["inline"].values() if r["delta"] > 0 and r["lo"] > 0)
    bad_rel = sum(1 for r in per["relation"].values() if not r["lo"] > 0)
    bad_in = sum(1 for r in per["inline"].values() if not r["lo"] > 0)
    uso = "sì" if (n_rel >= USE_YES_MIN and n_in >= USE_YES_MIN) else \
        ("no" if (bad_rel >= USE_NO_MIN or bad_in >= USE_NO_MIN) else "inconclusiva")
    adds = sum(1 for r in per["gain_combined_minus_effect"].values() if r["lo"] > 0) >= ADDS_MIN
    v["uso"] = uso
    v["uso_rule"] = {"per_context": per, "relation_positive": n_rel, "inline_positive": n_in,
                     "relation_interval_touching_or_below_0": bad_rel, "inline_interval_touching_or_below_0": bad_in,
                     "combined_beats_effect_in_4_of_5": bool(adds)}
    # overall
    pend = [w for w, s in (("W2", w2_state), ("W3", w3_state), ("W4", w4_state), ("W5", w5_state)) if s == "pending"]
    if not v["checks"]["W1"]["pass"] or w2_state == "failed":
        overall = "inconclusivo"
    elif mappa == "sì" and uso == "sì":
        overall = "sì (provvisorio fino alla fase B)"
    elif mappa == "no" or uso == "no":
        overall = "no"
    else:
        overall = "inconclusivo"
    v["verdetto"] = overall
    v["aggiunge_al_trasferimento"] = bool(adds) if overall.startswith("sì") else None
    v["pending"] = pend
    if pend:
        v["notes"].append(f"controlli in attesa della parte B: {', '.join(pend)}; verdetto non definitivo")
    return v


def jsonable(x):
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        return None if not np.isfinite(x) else float(x)
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, np.ndarray):
        return jsonable(x.tolist())
    return x


def append_csv(path: Path, records: list) -> None:
    """Append records to a CSV (header on first write), so a run cut short keeps what it computed."""
    if not records:
        return
    df = pd.DataFrame(records)
    new = not Path(path).exists()
    if not new:
        cols = pd.read_csv(path, nrows=0).columns.tolist()
        extra = [c for c in df.columns if c not in cols]
        if extra:
            old = pd.read_csv(path)
            pd.concat([old, df], ignore_index=True).to_csv(path, index=False, float_format="%.6g")
            return
        df = df.reindex(columns=cols)
    df.to_csv(path, mode="a", header=new, index=False, float_format="%.6g")


if __name__ == "__main__":
    sys.exit("library: run selftest_covar.py, run_parte_a.py, run_parte_b.py or combine.py")
