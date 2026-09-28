"""Basal-profile corpora for the context encoder: format, reading, exclusions, genes, normalisation (numpy, pandas).

pretrain.py adds torch; pca_baseline.py and compare.py run without it.

The format. The lead writes it: one corpus per source group, and a data condition is a list of corpora.

    profiles.npz  counts   float32 [N, A]  counts on the official gene axis (A = 18,533: the rows of the network
                                            dataset's axis.csv, in that order), NaN where the source does not
                                            measure the gene (not measured is never 0, D-009)
                  library  float64 [N]     the profile's total counts over all the genes of its source
                  optional: profile_id [N] (checked against meta.csv), genes [A] (checked against --axis)
    meta.csv      one row per profile, in the order of the arrays:
                  profile_id, source, context, family, study, platform, kind, n_cells
                  kind: cells_subset (pseudobulk of a random subset of control cells), pool, donor, guide, bulk.
                  Read when present: cell_line, cell_type, tissue (the line lists of an exclusion are matched
                  against them as well as against context), treatment (recorded only).

A corpus argument is a folder holding profiles.npz and meta.csv, or an .npz file whose table sits beside it
(<stem>.csv, <stem>_meta.csv, <stem>.meta.csv, or meta.csv in the same folder).

The names.
* context: the unit that gets one embedding (the mean over its profiles) and whose profiles the consistency term
  pulls together. Use the network dataset's names for its contexts and for A, B, C (or map them with
  train_emb.py --emb-map). Two sources describe the same context only if they use the same name, case included.
* family, study: units that leave together (exclusions; --val-unit study).
* platform: the decoder's nuisance input (flex, 3prime, bulk, ...).

Order of operations (prepare): read the tables; drop profiles of other kinds or with too few cells; apply the
exclusions -- contexts, families, studies, cell-line names; PRESETS holds the explicit lists of the designs --
before anything is computed; check --require and --expect-excluded; draw the validation units among the contexts
that are neither excluded nor required; choose the genes on the reference corpora; compute CPM (over the genes
each profile measures, or over its library), then log1p or within-profile ranks, then standardise with the
training profiles' statistics. Excluded profiles never enter gene choice, statistics, validation or training;
they are read again only to be embedded (a held-out context needs its embedding) and for the reconstruction
report.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.lib import format as npy_format

EMB_FORMAT = "context_embeddings/1"
META_COLUMNS = ("profile_id", "source", "context", "family", "study", "platform", "kind", "n_cells")
TEXT_COLUMNS = ("profile_id", "source", "context", "family", "study", "platform", "kind", "cell_line", "cell_type",
                "tissue", "treatment")
KINDS = ("cells_subset", "pool", "donor", "guide", "bulk")
MATCH_FIELDS = ("context", "cell_line", "cell_type", "tissue")
HASH_LIMIT = 4_000_000_000          # bytes; larger files are recorded by size only
SD_FLOOR = {"log": 0.1, "rank": 0.01}
Z_CLIP = 10.0

# The explicit exclusion lists of the designs (DISEGNO.md §8). A name is upper-cased and reduced to letters and
# digits; a pattern of four or more characters matches inside a field ("HCT116" matches "orion_hct116" and
# "HCT 116"), a shorter one only a whole field or one of its words ("CD4" matches "cd4_Rest" and "CD4-positive,
# alpha-beta T cell", not "CD40LG"). Fields: context, and cell_line, cell_type, tissue when the table has them.
PRESETS = {
    "k562": {
        "families": ["k562"],
        "lines": ["K562"],
        "why": "K562 from every source and platform (Replogle, VIPerturb-seq Flex, DepMap, Tahoe, scBaseCount)"},
    "orion": {
        "families": ["orion"],
        "lines": ["HCT116", "HEK293", "293T", "293FT", "HEKTE", "HEK"],
        "why": "the Orion family: HCT116 and HEK293T, with HEK293 and its derivatives"},
    "cd4": {
        "families": ["cd4"],
        "lines": ["CD4", "CD4POSITIVE", "TCELL", "THELPER", "TREG", "TH1", "TH2", "TH17", "PBMC",
                  "PERIPHERALBLOODMONONUCLEAR", "WHOLEBLOOD", "LYMPHOCYTE", "LYMPHNODE", "THYMUS", "THYMOCYTE",
                  "SPLEEN", "TONSIL",
                  "JURKAT", "HUT78", "HUT102", "MOLT4", "MOLT3", "CCRFCEM", "CEM", "SUPT1", "HPBALL", "CUTLL1",
                  "LOUCY", "DND41", "KOPTK1", "RPMI8402", "ALLSIL", "KARPAS45", "MYLA", "HH"],
        "why": "CD4 T cells: every T cell, the blood and lymphoid samples that contain them, T-lineage lines"},
    "ipsc": {
        "families": ["kolf", "hipsci"],
        "lines": ["KOLF", "HIPSCI", "HPSI", "IPSC", "IPS", "HIPS", "ESC", "HESC", "EMBRYONICSTEM", "PLURIPOTENT",
                  "H1", "H9", "WTC11", "WA01", "WA09"],
        "why": "pluripotent stem cells: KOLF2.1J, the HipSci lines, other iPS and ES lines"},
}


# ---------------------------------------------------------------- small helpers

class Logger:
    """Prints and appends to a file; `quiet` keeps the lines in memory only (the self-test)."""

    def __init__(self, path: Path | None = None, quiet: bool = False):
        self.fh = open(path, "x", encoding="utf-8") if path is not None else None
        self.quiet, self.lines, self.t0 = quiet, [], time.time()

    def __call__(self, msg: str) -> None:
        line = f"[{time.time() - self.t0:8.1f}s] {msg}"
        self.lines.append(line)
        if not self.quiet:
            print(line, flush=True)
        if self.fh is not None:
            self.fh.write(line + "\n")
            self.fh.flush()

    def close(self) -> None:
        if self.fh is not None:
            self.fh.close()
            self.fh = None


def split_list(text) -> list[str]:
    """Comma-separated names (or a list of such strings) as a list, blanks dropped."""
    if text is None:
        return []
    if isinstance(text, (list, tuple)):
        out = []
        for t in text:
            out += split_list(t)
        return out
    return [s.strip() for s in str(text).split(",") if s.strip()]


def norm_name(s) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(s).upper())


def match_line(value, patterns: list[str]) -> str | None:
    """The first pattern (normalised) that matches a field value, or None; see PRESETS."""
    v = norm_name(value)
    if not v:
        return None
    words = {norm_name(w) for w in re.split(r"[^0-9A-Za-z]+", str(value)) if w}
    for p in patterns:
        if p == v or p in words or (len(p) >= 4 and p in v):
            return p
    return None


def jsonable(x):
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return jsonable(x.tolist())
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, (np.floating, float)):
        v = float(x)
        return v if math.isfinite(v) else None
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, Path):
        return str(x)
    return x


def write_json(path: Path, obj) -> None:
    with Path(path).open("x", encoding="utf-8") as fh:
        json.dump(jsonable(obj), fh, indent=1)


def sha256_file(path: Path, limit: int | None = HASH_LIMIT) -> str | None:
    path = Path(path)
    if limit is not None and path.stat().st_size > limit:
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def provenance(path: Path) -> dict:
    path = Path(path)
    if not path.exists():
        return {"path": str(path), "exists": False}
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def read_axis(path: Path) -> list[str]:
    return pd.read_csv(path, keep_default_na=False, na_values=[""], dtype={"gene": str})["gene"].astype(str).tolist()


# ---------------------------------------------------------------- reading

def resolve_corpus(arg) -> tuple[Path, Path]:
    """(profiles .npz, meta table) of a corpus argument."""
    p = Path(arg)
    if p.is_dir():
        npz, meta = p / "profiles.npz", p / "meta.csv"
    else:
        npz = p
        cands = [p.with_suffix(".csv"), p.with_name(p.stem + "_meta.csv"), p.with_name(p.stem + ".meta.csv"),
                 p.parent / "meta.csv"]
        meta = next((c for c in cands if c.exists()), cands[0])
    if not npz.exists():
        raise FileNotFoundError(f"corpus {arg}: {npz} does not exist")
    if not meta.exists():
        raise FileNotFoundError(f"corpus {arg}: no table beside {npz} (profiles.npz with meta.csv, or <stem>.csv)")
    return npz, meta


def read_meta(path: Path) -> pd.DataFrame:
    head = pd.read_csv(path, nrows=0)
    dtypes = {c: str for c in head.columns if c in TEXT_COLUMNS}
    df = pd.read_csv(path, keep_default_na=False, na_values=[""], dtype=dtypes)
    missing = [c for c in META_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path}: columns {missing} are missing (need {list(META_COLUMNS)})")
    for c in TEXT_COLUMNS:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str).str.strip()
    df["n_cells"] = pd.to_numeric(df["n_cells"], errors="coerce")
    bad = sorted(set(df["kind"]) - set(KINDS))
    if bad:
        raise ValueError(f"{path}: unknown kinds {bad} (allowed {list(KINDS)})")
    if (df["context"] == "").any():
        raise ValueError(f"{path}: {int((df['context'] == '').sum())} profiles without a context")
    return df


def npz_shapes(path: Path) -> dict:
    """{array name: shape} of an .npz without reading the arrays."""
    out = {}
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            if not info.filename.endswith(".npy"):
                continue
            key = info.filename[:-4]
            with zf.open(info) as fh:
                version = npy_format.read_magic(fh)
                if version == (1, 0):
                    shape = npy_format.read_array_header_1_0(fh)[0]
                elif version == (2, 0):
                    shape = npy_format.read_array_header_2_0(fh)[0]
                else:
                    shape = None
            if shape is None:
                with np.load(path, allow_pickle=False) as z:
                    shape = z[key].shape
            out[key] = tuple(int(s) for s in shape)
    return out


@dataclass
class CorpusSet:
    names: list            # the corpus arguments, as given
    npz: list              # Path of each profiles .npz
    meta: pd.DataFrame     # every profile, with `corpus` (its file) and `row` (its row in that file)
    n_axis: int
    provenance: list

    def read(self, k: int):
        """(counts, library) of corpus k, fully in memory."""
        with np.load(self.npz[k], allow_pickle=False) as z:
            counts = np.asarray(z["counts"])
            library = np.asarray(z["library"], dtype=np.float64)
        return counts, library


def open_corpora(corpora, axis: list | None = None) -> CorpusSet:
    """The tables of every corpus, checked against the arrays' shapes (the arrays are not read here)."""
    frames, npzs, prov, names = [], [], [], []
    n_axis = None
    for k, arg in enumerate(corpora):
        npz, mpath = resolve_corpus(arg)
        meta = read_meta(mpath)
        shapes = npz_shapes(npz)
        for key in ("counts", "library"):
            if key not in shapes:
                raise ValueError(f"{npz}: no '{key}' array")
        if len(shapes["counts"]) != 2 or shapes["library"] != (shapes["counts"][0],):
            raise ValueError(f"{npz}: counts {shapes['counts']} and library {shapes['library']} do not match")
        n, A = shapes["counts"]
        if len(meta) != n:
            raise ValueError(f"{npz}: {n} profiles, {mpath}: {len(meta)} rows")
        if n_axis is None:
            n_axis = A
        elif A != n_axis:
            raise ValueError(f"{npz}: {A} genes, the previous corpora {n_axis}")
        if axis is not None and A != len(axis):
            raise ValueError(f"{npz}: {A} genes, the axis {len(axis)}")
        if "profile_id" in shapes or "genes" in shapes:
            with np.load(npz, allow_pickle=False) as z:
                if "profile_id" in z.files and [str(s) for s in z["profile_id"]] != meta["profile_id"].tolist():
                    raise ValueError(f"{npz}: profile_id differs from the order of {mpath}")
                if "genes" in z.files and axis is not None and [str(s) for s in z["genes"]] != list(axis):
                    raise ValueError(f"{npz}: its genes are not the axis, in order")
        meta = meta.copy()
        meta["corpus"] = k
        meta["row"] = np.arange(n, dtype=np.int64)
        frames.append(meta)
        npzs.append(npz)
        names.append(str(arg))
        prov.append({"argument": str(arg), "npz": provenance(npz), "meta": provenance(mpath), "profiles": int(n),
                     "sources": sorted(meta["source"].unique().tolist()),
                     "contexts": int(meta["context"].nunique()), "studies": int(meta["study"].nunique())})
    if not frames:
        raise ValueError("no corpus given")
    allm = pd.concat(frames, ignore_index=True)
    dup = allm["profile_id"].duplicated()
    if dup.any():
        raise ValueError(f"duplicate profile_id across corpora, e.g. {allm.loc[dup, 'profile_id'].head(5).tolist()}")
    return CorpusSet(names, npzs, allm, int(n_axis), prov)


def to_cpm(c: np.ndarray, library: np.ndarray, denominator: str, where: str) -> tuple[np.ndarray, np.ndarray]:
    """Counts [n, A] (NaN = not measured) -> CPM with NaN kept, and the measured mask. The denominator is the
    total over the genes the profile measures on the axis ("measured") or its library ("library")."""
    meas = np.isfinite(c)
    c0 = np.where(meas, c, 0.0)
    if (c0 < 0).any():
        raise ValueError(f"{where}: negative counts")
    den = c0.sum(axis=1) if denominator == "measured" else np.asarray(library, dtype=np.float64)
    bad = ~np.isfinite(den) | (den <= 0)
    if bad.any():
        raise ValueError(f"{where}: {int(bad.sum())} profiles with a zero or missing {denominator} denominator")
    return c / den[:, None] * 1e6, meas


def load_cpm(cs: CorpusSet, files: np.ndarray, rows: np.ndarray, genes: np.ndarray, denominator: str,
             chunk: int = 1024) -> np.ndarray:
    """float32 [n, G]: CPM of the genes `genes` (axis columns) for profiles (files[i], rows[i]), in that order,
    NaN where the source does not measure the gene."""
    files, rows = np.asarray(files, dtype=np.int64), np.asarray(rows, dtype=np.int64)
    out = np.empty((rows.size, genes.size), dtype=np.float32)
    for k in np.unique(files):
        pos = np.flatnonzero(files == k)
        counts, library = cs.read(int(k))
        for a in range(0, pos.size, chunk):
            p = pos[a:a + chunk]
            r = rows[p]
            cpm, _ = to_cpm(np.asarray(counts[r], dtype=np.float64), library[r], denominator, cs.names[int(k)])
            out[p] = cpm[:, genes].astype(np.float32)
        del counts
    return out


# ---------------------------------------------------------------- exclusions

@dataclass
class Exclusion:
    contexts: list = field(default_factory=list)
    families: list = field(default_factory=list)
    studies: list = field(default_factory=list)
    lines: list = field(default_factory=list)
    presets: list = field(default_factory=list)

    @classmethod
    def from_args(cls, args) -> "Exclusion":
        lines = split_list(args.exclude_lines)
        if getattr(args, "exclude_lines_file", None):
            lines += [s.strip() for s in Path(args.exclude_lines_file).read_text(encoding="utf-8").splitlines()
                      if s.strip() and not s.strip().startswith("#")]
        ex = cls(contexts=split_list(args.exclude_contexts), families=split_list(args.exclude_families),
                 studies=split_list(args.exclude_studies), lines=lines, presets=split_list(args.exclude_preset))
        for p in ex.presets:
            if p not in PRESETS:
                raise ValueError(f"unknown exclusion preset {p!r} (known: {sorted(PRESETS)})")
            ex.families += PRESETS[p]["families"]
            ex.lines += PRESETS[p]["lines"]
        ex.families = list(dict.fromkeys(ex.families))
        ex.lines = list(dict.fromkeys(ex.lines))
        return ex

    def to_dict(self) -> dict:
        return {"contexts": self.contexts, "families": self.families, "studies": self.studies, "lines": self.lines,
                "presets": {p: PRESETS[p] for p in self.presets}}


def apply_exclusions(meta: pd.DataFrame, ex: Exclusion) -> tuple[np.ndarray, np.ndarray, dict]:
    """(excluded mask, reason per profile, report). A profile leaves when its context, family or study is listed,
    or when one of its fields matches a line pattern."""
    n = len(meta)
    ctx_set = {norm_name(c) for c in ex.contexts}
    fam_set = {norm_name(f) for f in ex.families}
    stu_set = {norm_name(s) for s in ex.studies}
    pats = sorted({norm_name(p) for p in ex.lines if norm_name(p)}, key=lambda p: (-len(p), p))
    ctx_raw = meta["context"].tolist()
    ctx_n = [norm_name(c) for c in ctx_raw]
    fam_n = [norm_name(f) for f in meta["family"].tolist()]
    stu_n = [norm_name(s) for s in meta["study"].tolist()]
    fields = {c: meta[c].tolist() for c in MATCH_FIELDS if c in meta.columns}
    cache: dict = {}
    reason = np.full(n, "", dtype=object)
    hits = {p: set() for p in pats}
    ctx_hit, fam_hit, stu_hit = set(), set(), set()
    for i in range(n):
        why = []
        if ctx_n[i] in ctx_set:
            ctx_hit.add(ctx_n[i])
            why.append(f"context {ctx_raw[i]}")
        if fam_n[i] in fam_set:
            fam_hit.add(fam_n[i])
            why.append(f"family {meta['family'].iat[i]}")
        if stu_n[i] in stu_set:
            stu_hit.add(stu_n[i])
            why.append(f"study {meta['study'].iat[i]}")
        for col, vals in fields.items():
            v = vals[i]
            if v not in cache:
                cache[v] = match_line(v, pats) if pats else None
            p = cache[v]
            if p is not None:
                hits[p].add(ctx_raw[i])
                why.append(f"{col} {v!r} ~ {p}")
        if why:
            reason[i] = "; ".join(why)
    mask = reason != ""
    by_ctx = {}
    for i in np.flatnonzero(mask):
        by_ctx.setdefault(ctx_raw[i], reason[i])
    report = {"rules": ex.to_dict(), "excluded_profiles": int(mask.sum()),
              "by_source": {str(k): int(v) for k, v in meta.loc[mask, "source"].value_counts().items()},
              "contexts": by_ctx,
              "pattern_hits": {p: sorted(h)[:50] for p, h in hits.items() if h},
              "patterns_without_match": [p for p in pats if not hits[p]],
              "listed_contexts_without_match": sorted(c for c in ctx_set if c not in ctx_hit),
              "listed_families_without_match": sorted(f for f in fam_set if f not in fam_hit),
              "listed_studies_without_match": sorted(s for s in stu_set if s not in stu_hit)}
    return mask, reason, report


# ---------------------------------------------------------------- genes and normalisation

def select_genes(cs: CorpusSet, files: np.ndarray, rows: np.ndarray, weights: np.ndarray, n_genes: int,
                 min_measured: float, min_mean_cpm: float, denominator: str, chunk: int = 1024):
    """The model genes, from the reference profiles (weighted): measured in >= min_measured of the weight, mean
    CPM >= min_mean_cpm where measured, then the n_genes with the largest weighted variance of log1p CPM (0: all
    candidates), in axis order."""
    A = cs.n_axis
    tot = 0.0
    s_meas, s_x, s_x2, s_cpm = (np.zeros(A) for _ in range(4))
    files, rows = np.asarray(files, dtype=np.int64), np.asarray(rows, dtype=np.int64)
    for k in np.unique(files):
        pos = np.flatnonzero(files == k)
        counts, library = cs.read(int(k))
        for a in range(0, pos.size, chunk):
            p = pos[a:a + chunk]
            r = rows[p]
            cpm, meas = to_cpm(np.asarray(counts[r], dtype=np.float64), library[r], denominator, cs.names[int(k)])
            c0 = np.where(meas, cpm, 0.0)
            lx = np.log1p(c0)
            w = weights[p][:, None]
            tot += float(weights[p].sum())
            s_meas += (w * meas).sum(axis=0)
            s_x += (w * lx).sum(axis=0)
            s_x2 += (w * lx * lx).sum(axis=0)
            s_cpm += (w * c0).sum(axis=0)
        del counts
    frac = s_meas / max(tot, 1e-300)
    with np.errstate(divide="ignore", invalid="ignore"):
        mean = s_x / s_meas
        var = s_x2 / s_meas - mean ** 2
        mcpm = s_cpm / s_meas
    ok = (frac >= min_measured) & np.isfinite(var) & (var > 1e-12) & np.isfinite(mcpm) & (mcpm >= min_mean_cpm)
    cand = np.flatnonzero(ok)
    if cand.size == 0:
        raise ValueError("no gene passes the gene rule on the reference corpora")
    if n_genes > 0 and cand.size > n_genes:
        cand = cand[np.argsort(-var[cand], kind="stable")[:n_genes]]
    genes = np.sort(cand).astype(np.int64)
    report = {"rule": {"min_measured": min_measured, "min_mean_cpm": min_mean_cpm, "n_genes": n_genes,
                       "rank_by": "weighted variance of log1p CPM", "denominator": denominator},
              "reference_profiles": int(rows.size), "candidates": int(ok.sum()), "selected": int(genes.size),
              "sha256": hashlib.sha256(genes.tobytes()).hexdigest()}
    return genes, report


def rank_rows(x: np.ndarray) -> np.ndarray:
    """Tie-aware quantile ranks in [0, 1] within each row, among its finite entries; NaN stays NaN."""
    x = np.asarray(x)
    out = np.full(x.shape, np.nan, dtype=np.float32)
    for i in range(x.shape[0]):
        ok = np.isfinite(x[i])
        n = int(ok.sum())
        if n == 0:
            continue
        v = x[i, ok].astype(np.float64)
        s = np.sort(v)
        lo = np.searchsorted(s, v, side="left")
        hi = np.searchsorted(s, v, side="right")
        out[i, ok] = ((lo + (hi - lo - 1) / 2.0) / max(n - 1, 1)).astype(np.float32)
    return out


def values(cpm: np.ndarray, mode: str) -> np.ndarray:
    """log1p CPM or within-profile ranks, float32, NaN where not measured."""
    if mode == "log":
        return np.log1p(np.asarray(cpm, dtype=np.float32))
    if mode == "rank":
        return rank_rows(cpm)
    raise ValueError(f"norm {mode!r}")


def gene_stats(v: np.ndarray, w: np.ndarray, mode: str, chunk: int = 4096) -> tuple[np.ndarray, np.ndarray]:
    """Weighted mean and SD of each gene over the rows that measure it (SD floored; genes never measured: 0, 1)."""
    G = v.shape[1]
    s_w, s_x, s_x2 = np.zeros(G), np.zeros(G), np.zeros(G)
    for a in range(0, v.shape[0], chunk):
        x = np.asarray(v[a:a + chunk], dtype=np.float64)
        ok = np.isfinite(x)
        ww = np.asarray(w[a:a + chunk], dtype=np.float64)[:, None] * ok
        x0 = np.where(ok, x, 0.0)
        s_w += ww.sum(axis=0)
        s_x += (ww * x0).sum(axis=0)
        s_x2 += (ww * x0 * x0).sum(axis=0)
    seen = s_w > 0
    mean = np.divide(s_x, s_w, out=np.zeros(G), where=seen)
    var = np.maximum(np.divide(s_x2, s_w, out=np.zeros(G), where=seen) - mean ** 2, 0.0)
    sd = np.maximum(np.sqrt(var), SD_FLOOR[mode])
    sd[~seen] = 1.0
    return mean.astype(np.float32), sd.astype(np.float32)


def standardise(v: np.ndarray, mu: np.ndarray, sd: np.ndarray) -> np.ndarray:
    """(v - mu) / sd clipped to +-Z_CLIP, float32, NaN kept."""
    return np.clip((np.asarray(v, dtype=np.float32) - mu[None, :]) / sd[None, :], -Z_CLIP, Z_CLIP).astype(np.float32)


# ---------------------------------------------------------------- the prepared corpus

def split_validation(names: list, study: list, eligible: np.ndarray, frac: float, unit: str, seed: int,
                     explicit: list) -> np.ndarray:
    """Validation flag per context: explicit names, or a seeded draw of whole contexts (or studies) among the
    eligible ones; at least one unit when there are three or more, and always two left for training."""
    val = np.zeros(len(names), dtype=bool)
    if explicit:
        pos = {c: i for i, c in enumerate(names)}
        unknown = [c for c in explicit if c not in pos]
        if unknown:
            raise ValueError(f"--val-contexts not in the corpora: {unknown}")
        blocked = [c for c in explicit if not eligible[pos[c]]]
        if blocked:
            raise ValueError(f"--val-contexts that are excluded or required: {blocked}")
        val[[pos[c] for c in explicit]] = True
        return val
    idx = np.flatnonzero(eligible)
    unit_of = {i: (names[i] if unit == "context" else study[i]) for i in idx}
    units = sorted(set(unit_of.values()))
    k = int(round(frac * len(units)))
    if len(units) >= 3:
        k = max(k, 1)
    k = min(k, max(len(units) - 2, 0))
    rng = np.random.default_rng([seed, 17])
    chosen = {units[j] for j in rng.permutation(len(units))[:k]}
    for i in idx:
        val[i] = unit_of[i] in chosen
    return val


def balance_weights(primary: list, mode: str) -> np.ndarray:
    """Sampling probability of each training context: equal (none), or equal per study (source), equal within."""
    n = len(primary)
    if mode == "none":
        w = np.ones(n)
    else:
        cnt = Counter(primary)
        w = np.array([1.0 / (len(cnt) * cnt[g]) for g in primary])
    return w / w.sum()


@dataclass
class Prepared:
    meta: pd.DataFrame           # usable profiles, in order; with corpus, row, reason, split
    genes: np.ndarray            # axis columns of the model genes
    cpm: np.ndarray              # float32 [N, G], NaN where not measured
    measured: np.ndarray         # bool [N, G]
    z: np.ndarray                # float32 [N, G] standardised values, NaN where not measured
    mu: np.ndarray
    sd: np.ndarray
    mode: str
    denominator: str
    contexts: list               # context names
    ctx_of: np.ndarray           # [N] context id of each profile
    ctx_rows: list               # per context, all its profile rows
    split: np.ndarray            # [N] "train", "val" or "excluded"
    train_ctx: np.ndarray        # contexts with training profiles
    train_ctx_rows: list         # their training rows
    train_ctx_weight: np.ndarray # sampling probabilities
    profile_weight: np.ndarray   # [N] statistics weight (training rows only)
    platforms: list              # the decoder's vocabulary (training profiles)
    platform_index: np.ndarray   # [N] 1 + position in `platforms`, 0 unknown
    report: dict

    @property
    def N(self) -> int:
        return int(self.cpm.shape[0])

    @property
    def G(self) -> int:
        return int(self.genes.size)

    @property
    def train_rows(self) -> np.ndarray:
        return np.flatnonzero(self.split == "train")

    @property
    def val_rows(self) -> np.ndarray:
        return np.flatnonzero(self.split == "val")

    @property
    def excluded_rows(self) -> np.ndarray:
        return np.flatnonzero(self.split == "excluded")

    def values(self, cpm: np.ndarray) -> np.ndarray:
        return values(cpm, self.mode)

    def standardise(self, v: np.ndarray) -> np.ndarray:
        return standardise(v, self.mu, self.sd)

    def context_status(self) -> list:
        """Per context: excluded (every profile), partial, val or train."""
        out = []
        for rows in self.ctx_rows:
            s = set(self.split[rows].tolist())
            if s == {"excluded"}:
                out.append("excluded")
            elif "excluded" in s:
                out.append("partial")
            elif s == {"val"}:
                out.append("val")
            else:
                out.append("train")
        return out

    def eval_sets(self, cap: int, seed: int) -> dict:
        """Fixed evaluation rows (at most `cap` per set, a seeded choice): the same for the encoder and the PCA."""
        out = {}
        for j, (label, rows) in enumerate((("val", self.val_rows), ("excluded", self.excluded_rows),
                                           ("train_sample", self.train_rows)), start=1):
            if rows.size > cap:
                rows = np.sort(np.random.default_rng([seed, 29, j]).choice(rows, size=cap, replace=False))
            out[label] = (j, rows)
        return out

    def norm_payload(self) -> dict:
        return {"genes_axis": self.genes.astype(np.int64), "mu": self.mu, "sd": self.sd, "mode": self.mode,
                "denominator": self.denominator, "z_clip": Z_CLIP, "platforms": list(self.platforms)}


def prepare(args, log=print) -> Prepared:
    """Read, filter, exclude, split, choose genes, normalise (see the module docstring)."""
    t0 = time.time()
    axis = read_axis(args.axis) if getattr(args, "axis", None) else None
    cs = open_corpora(args.corpus, axis=axis)
    meta = cs.meta
    kinds = split_list(args.kinds) or list(KINDS)
    unknown = sorted(set(kinds) - set(KINDS))
    if unknown:
        raise ValueError(f"unknown kinds {unknown}")
    cells = meta["n_cells"].to_numpy(dtype=np.float64)
    usable = meta["kind"].isin(kinds).to_numpy() & ~(np.isfinite(cells) & (cells < args.min_cells))
    dropped = {"profiles": int((~usable).sum()),
               "by_kind": {str(k): int(v) for k, v in meta.loc[~usable, "kind"].value_counts().items()}}
    m = meta[usable].reset_index(drop=True)
    if len(m) == 0:
        raise ValueError("no usable profile")
    ex = Exclusion.from_args(args)
    excluded, reason, ex_report = apply_exclusions(m, ex)
    m["reason"] = reason
    contexts = list(pd.unique(m["context"]))
    cid = {c: i for i, c in enumerate(contexts)}
    ctx_of = m["context"].map(cid).to_numpy(dtype=np.int64)
    nC = len(contexts)
    ctx_rows = [np.flatnonzero(ctx_of == c) for c in range(nC)]
    n_all = np.array([r.size for r in ctx_rows])
    n_excl = np.bincount(ctx_of[excluded], minlength=nC)
    fully = n_excl == n_all
    required = split_list(args.require)
    absent = [c for c in required if c not in cid]
    if absent:
        raise ValueError(f"required contexts absent from the corpora (after --kinds/--min-cells): {absent}")
    expect = split_list(args.expect_excluded)
    kept = [c for c in expect if c not in cid or not fully[cid[c]]]
    if kept:
        raise ValueError(f"contexts the exclusions must remove entirely are absent or partly kept: {kept}")
    studies = m["study"].to_numpy()
    primary_study = [Counter(studies[r].tolist()).most_common(1)[0][0] for r in ctx_rows]
    req = set(required)
    eligible = (n_excl == 0) & np.array([c not in req for c in contexts])
    val_ctx = split_validation(contexts, primary_study, eligible, args.val_frac, args.val_unit, args.seed,
                               split_list(args.val_contexts))
    split = np.where(excluded, "excluded", np.where(val_ctx[ctx_of], "val", "train")).astype(object)
    train_rows = np.flatnonzero(split == "train")
    if train_rows.size == 0:
        raise ValueError("no training profile left after exclusions and validation")
    train_ctx = np.unique(ctx_of[train_rows])
    train_ctx_rows = [train_rows[ctx_of[train_rows] == c] for c in train_ctx]
    key = m["source" if args.balance == "source" else "study"].to_numpy()
    primary = [Counter(key[r].tolist()).most_common(1)[0][0] for r in train_ctx_rows]
    w_ctx = balance_weights(primary, args.balance)
    profile_weight = np.zeros(len(m))
    for rows, w in zip(train_ctx_rows, w_ctx):
        profile_weight[rows] = w / rows.size
    log(f"corpora: {len(m)} usable profiles in {nC} contexts ({dropped['profiles']} dropped by kind or cells); "
        f"excluded {int(excluded.sum())} profiles, {int(fully.sum())} whole contexts; validation "
        f"{int(val_ctx.sum())} contexts; training {train_rows.size} profiles in {train_ctx.size} contexts")

    files, frows = m["corpus"].to_numpy(dtype=np.int64), m["row"].to_numpy(dtype=np.int64)
    ref = np.flatnonzero((files < args.reference_corpora) & ~excluded)
    if ref.size == 0:
        raise ValueError("the reference corpora have no usable profile left after the exclusions")
    ref_w = 1.0 / np.bincount(ctx_of[ref], minlength=nC)[ctx_of[ref]]
    genes, gene_report = select_genes(cs, files[ref], frows[ref], ref_w, args.n_genes, args.min_measured,
                                      args.min_mean_cpm, args.denominator)
    log(f"genes: {genes.size} of {cs.n_axis} ({gene_report['candidates']} candidates on "
        f"{ref.size} reference profiles)")
    cpm = load_cpm(cs, files, frows, genes, args.denominator)
    measured = np.isfinite(cpm)
    v = values(cpm, args.norm)
    mu, sd = gene_stats(v[train_rows], profile_weight[train_rows], args.norm)
    z = standardise(v, mu, sd)
    del v
    plat = m["platform"].to_numpy()
    platforms = sorted(set(plat[train_rows].tolist()))
    pidx = {p: i + 1 for i, p in enumerate(platforms)}
    platform_index = np.array([pidx.get(p, 0) for p in plat], dtype=np.int64)
    status_counts = Counter()
    prep = Prepared(meta=m, genes=genes, cpm=cpm, measured=measured, z=z, mu=mu, sd=sd, mode=args.norm,
                    denominator=args.denominator, contexts=contexts, ctx_of=ctx_of, ctx_rows=ctx_rows,
                    split=split, train_ctx=train_ctx, train_ctx_rows=train_ctx_rows, train_ctx_weight=w_ctx,
                    profile_weight=profile_weight, platforms=platforms, platform_index=platform_index, report={})
    status = prep.context_status()
    status_counts.update(status)
    prep.report = {
        "corpora": cs.provenance, "axis_genes": cs.n_axis,
        "filters": {"kinds": kinds, "min_cells": args.min_cells, "dropped": dropped},
        "exclusions": ex_report,
        "contexts": {"total": nC, "status_counts": dict(status_counts),
                     "excluded": [c for c, s in zip(contexts, status) if s == "excluded"],
                     "partial": [c for c, s in zip(contexts, status) if s == "partial"],
                     "val": [c for c, s in zip(contexts, status) if s == "val"],
                     "required": required, "expect_excluded": expect},
        "profiles": {"usable": int(len(m)), "train": int(train_rows.size), "val": int((split == "val").sum()),
                     "excluded": int((split == "excluded").sum()),
                     "train_by_source": {str(k): int(v) for k, v in m.loc[train_rows, "source"].value_counts().items()}},
        "validation": {"unit": args.val_unit, "frac": args.val_frac, "seed": args.seed},
        "balance": {"mode": args.balance, "training_contexts": int(train_ctx.size),
                    "groups": dict(Counter(primary))},
        "genes": {**gene_report, "reference_corpora": args.reference_corpora},
        "normalisation": {"mode": args.norm, "denominator": args.denominator, "sd_floor": SD_FLOOR[args.norm],
                          "z_clip": Z_CLIP, "statistics_from": "training profiles, weighted by their context's "
                                                               "sampling probability"},
        "platforms": platforms,
        "seconds": round(time.time() - t0, 1)}
    return prep


# ---------------------------------------------------------------- evaluation and outputs

def eval_views(prep: Prepared, rows: np.ndarray, seed: int, set_id: int, mask_frac: float) -> dict:
    """Fixed masks on the given rows: x_in (visible values, 0 elsewhere), target (every measured value),
    scored (measured and hidden), platform."""
    rng = np.random.default_rng([seed, 23, set_id])
    meas = prep.measured[rows]
    z = prep.z[rows]
    vis = meas & (rng.random(meas.shape) >= mask_frac)
    return {"rows": rows, "x_in": np.where(vis, z, 0.0).astype(np.float32),
            "target": np.where(meas, z, 0.0).astype(np.float32), "vis": vis, "scored": meas & ~vis,
            "platform": prep.platform_index[rows]}


def recon_metrics(xhat: np.ndarray, target: np.ndarray, scored: np.ndarray, sources=None) -> dict:
    """Masked-gene reconstruction in standardised units: MSE, the MSE of predicting the training mean (0), and
    1 - their ratio; per source too."""
    def one(sel):
        n = int(scored[sel].sum())
        if n == 0:
            return None
        err = float(np.where(scored[sel], (xhat[sel] - target[sel]) ** 2, 0.0).sum()) / n
        base = float(np.where(scored[sel], target[sel] ** 2, 0.0).sum()) / n
        return {"profiles": int(np.asarray(sel).sum()) if np.asarray(sel).dtype == bool else int(len(sel)),
                "scored_entries": n, "masked_mse": err, "mean_mse": base,
                "r2_vs_mean": (1.0 - err / base) if base > 0 else None}

    allrows = np.ones(target.shape[0], dtype=bool)
    out = one(allrows) or {"profiles": int(target.shape[0]), "scored_entries": 0}
    if sources is not None:
        src = np.asarray(sources)
        out["by_source"] = {str(s): one(src == s) for s in sorted(set(src.tolist()))}
    return out


def context_means(Zp: np.ndarray, prep: Prepared) -> tuple[list, np.ndarray, np.ndarray]:
    E = np.stack([Zp[r].mean(axis=0) for r in prep.ctx_rows])
    return list(prep.contexts), E, np.array([r.size for r in prep.ctx_rows], dtype=np.int64)


def embedding_geometry(Zp: np.ndarray, prep: Prepared) -> dict:
    """Mean squared distance of a context's profiles to their mean (within) against the spread of the context
    means (between), over contexts with two or more profiles; by status and by source."""
    status = prep.context_status()
    src = prep.meta["source"].to_numpy()
    ctx_src = [Counter(src[r].tolist()).most_common(1)[0][0] for r in prep.ctx_rows]

    def ratio(ids):
        ids = [c for c in ids if prep.ctx_rows[c].size >= 2]
        if len(ids) < 2:
            return None
        means = np.stack([Zp[prep.ctx_rows[c]].mean(axis=0) for c in ids])
        within = float(np.mean([((Zp[prep.ctx_rows[c]] - means[i]) ** 2).sum(axis=1).mean()
                                for i, c in enumerate(ids)]))
        between = float(((means - means.mean(axis=0)) ** 2).sum(axis=1).mean())
        return {"contexts": len(ids), "within": within, "between": between,
                "ratio": within / between if between > 0 else None}

    nC = len(prep.contexts)
    out = {"all": ratio(range(nC))}
    for s in ("train", "val", "excluded"):
        out[s] = ratio([c for c in range(nC) if status[c] == s])
    out["by_source"] = {str(s): ratio([c for c in range(nC) if ctx_src[c] == s]) for s in sorted(set(ctx_src))}
    return out


def write_embeddings(out: Path, prep: Prepared, Zp: np.ndarray, meta: dict) -> dict:
    """context_embeddings.npz: contexts, embeddings (mean over each context's profiles), n_profiles, status,
    and the profile-level embeddings; meta as a JSON string."""
    names, E, n_prof = context_means(Zp, prep)
    path = Path(out) / "context_embeddings.npz"
    payload = {"contexts": np.array(names, dtype=str), "embeddings": E.astype(np.float32), "n_profiles": n_prof,
               "status": np.array(prep.context_status(), dtype=str),
               "profile_ids": prep.meta["profile_id"].to_numpy(dtype=str),
               "profile_context": prep.ctx_of.astype(np.int64), "profile_embeddings": Zp.astype(np.float32),
               "meta": np.array(json.dumps(jsonable({"format": EMB_FORMAT, **meta})))}
    with open(path, "xb") as fh:
        np.savez_compressed(fh, **payload)
    return {"file": str(path), "contexts": len(names), "dim": int(E.shape[1])}


def read_embeddings(path) -> dict:
    """{names, E [n, d] float64, status {name: ...}, meta, manifest (manifest.json beside the file, if any),
    path, bytes, sha256}. Fails on duplicate names or non-finite vectors."""
    path = Path(path)
    with np.load(path, allow_pickle=False) as z:
        names = [str(s) for s in z["contexts"]]
        E = np.asarray(z["embeddings"], dtype=np.float64)
        status = [str(s) for s in z["status"]] if "status" in z.files else ["unknown"] * len(names)
        meta = json.loads(z["meta"].item()) if "meta" in z.files else {}
    if E.ndim != 2 or E.shape[0] != len(names):
        raise ValueError(f"{path}: embeddings {E.shape} for {len(names)} contexts")
    if len(set(names)) != len(names):
        raise ValueError(f"{path}: duplicate context names")
    bad = [n for n, ok in zip(names, np.isfinite(E).all(axis=1)) if not ok]
    if bad:
        raise ValueError(f"{path}: non-finite embeddings for {bad[:10]}")
    mp = path.parent / "manifest.json"
    manifest = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else None
    return {"names": names, "E": E, "status": dict(zip(names, status)), "meta": meta, "manifest": manifest,
            **provenance(path)}


def profiles_for_contexts(corpora, names, genes: np.ndarray, mu: np.ndarray, sd: np.ndarray, mode: str,
                          denominator: str, cap: int) -> tuple[np.ndarray, dict, list]:
    """The encoder's inputs for the profiles of the named contexts (at most `cap` each, in corpus order), packed
    by context: (X float32 [n, G] with 0 where not measured, {name: (start, stop)}, provenance). Normalised with
    the pre-training statistics mu, sd. No exclusion applies: this serves fine-tuning and inference."""
    cs = open_corpora(corpora)
    m = cs.meta
    sel = m[m["context"].isin(set(names))]
    if cap > 0:
        sel = sel.groupby("context", sort=False).head(cap)
    order, ranges, pos = [], {}, 0
    for name in names:
        idx = sel.index.to_numpy()[(sel["context"] == name).to_numpy()]
        if idx.size == 0:
            continue
        order.append(idx)
        ranges[name] = (pos, pos + idx.size)
        pos += idx.size
    if not order:
        return np.zeros((0, genes.size), dtype=np.float32), {}, cs.provenance
    idx = np.concatenate(order)
    cpm = load_cpm(cs, m["corpus"].to_numpy()[idx], m["row"].to_numpy()[idx], np.asarray(genes, dtype=np.int64),
                   denominator)
    z = standardise(values(cpm, mode), np.asarray(mu, dtype=np.float32), np.asarray(sd, dtype=np.float32))
    return np.where(np.isfinite(z), z, 0.0).astype(np.float32), ranges, cs.provenance


def add_data_arguments(ap) -> None:
    g = ap.add_argument_group("corpus (shared by pretrain.py and pca_baseline.py)")
    g.add_argument("--corpus", action="append", default=[], help="a corpus folder or .npz; repeat for a list")
    g.add_argument("--reference-corpora", type=int, default=1,
                   help="the first K corpora choose the genes, so every data condition of a design gets the same")
    g.add_argument("--axis", type=Path, default=None, help="axis.csv of the network dataset: checks the corpus width")
    g.add_argument("--kinds", default=",".join(KINDS), help="profile kinds used")
    g.add_argument("--min-cells", type=float, default=0.0, help="drop pseudobulks of fewer cells (NaN n_cells stays)")
    g.add_argument("--exclude-preset", default="", help=f"explicit lists of corpus.PRESETS: {', '.join(PRESETS)}")
    g.add_argument("--exclude-contexts", default="")
    g.add_argument("--exclude-families", default="")
    g.add_argument("--exclude-studies", default="")
    g.add_argument("--exclude-lines", default="",
                   help="cell-line or cell-type names, matched against context, cell_line, cell_type, tissue")
    g.add_argument("--exclude-lines-file", type=Path, default=None, help="one name per line")
    g.add_argument("--require", default="", help="contexts that must be in the corpora (their embedding is needed)")
    g.add_argument("--expect-excluded", default="", help="contexts the exclusions must remove entirely")
    g.add_argument("--norm", choices=["log", "rank"], default="log", help="log1p CPM, or within-profile ranks")
    g.add_argument("--denominator", choices=["measured", "library"], default="measured",
                   help="CPM over the genes the profile measures, or over its library")
    g.add_argument("--n-genes", type=int, default=4096, help="model genes (0: every candidate)")
    g.add_argument("--min-measured", type=float, default=0.9)
    g.add_argument("--min-mean-cpm", type=float, default=1.0)
    g.add_argument("--balance", choices=["study", "source", "none"], default="study",
                   help="training contexts drawn with equal mass per study (or source), equal within")
    g.add_argument("--val-frac", type=float, default=0.1)
    g.add_argument("--val-unit", choices=["context", "study"], default="context")
    g.add_argument("--val-contexts", default="", help="explicit validation contexts")
    g.add_argument("--seed", type=int, default=0)
