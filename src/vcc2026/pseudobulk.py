"""Read Replogle-style pseudobulk H5ADs into signatures on the official axis.

**The `*_raw_bulk_01.h5ad` X is a per-cell mean, not a sum of counts.** Measured
on 2026-09-12: rows of `K562_gwps_raw_bulk_01.h5ad` sum to ~12,000, the scale of
a single cell's library, and `X * num_cells_filtered` returns to integers within
float32 precision (max deviation 1.6e-3 over the first sampled rows, >99.9% of
entries integral). Reading X as counts therefore understates the sampling
precision by a factor of the cell count -- a median of 166 in the genome-wide
file -- and any Poisson standard error computed from it would be roughly 13x too
large. The earlier audit noticed the values were non-integer
(`reports/candidate_verification/coverage_summary.json`,
`sample_fraction_noninteger` 0.996) but did not identify the divisor.

So numerosity is not metadata here, it is part of the measurement: this module
multiplies by `num_cells_filtered` to recover effective counts before computing
anything.

Control identity uses the documented label. The `gene_transcript` field is
`{row}_{SYMBOL}_{TSS}_{ENSG}`, and a control row is literally
`{row}_non-targeting_non-targeting_non-targeting`. `core_control` is a narrower
author annotation (514 of 585 non-targeting rows in the genome-wide file) and is
offered as an option, never as the definition -- it is an annotation, not proof
of a guide's identity.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np

from .genes import GeneAxis, align_to_axis, official_axis
from .signatures import Signature, SignatureSet, delta_from_pseudobulk

__all__ = ["PseudobulkFile", "parse_gene_transcript", "NTC_SYMBOL"]

NTC_SYMBOL = "non-targeting"
_ROW_RE = re.compile(r"^(?P<row>\d+)_(?P<symbol>.+)_(?P<tss>[^_]+)_(?P<ensg>[^_]+)$")


def parse_gene_transcript(labels) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Split `{row}_{SYMBOL}_{TSS}_{ENSG}` into (symbol, tss, ensg) arrays.

    The symbol is matched non-greedily from the right so that a symbol
    containing an underscore still parses. Labels that do not match at all
    yield empty strings, which the caller drops rather than guesses at.
    """
    symbols, tss, ensg = [], [], []
    for raw in labels:
        m = _ROW_RE.match(str(raw))
        if m is None:
            symbols.append("")
            tss.append("")
            ensg.append("")
            continue
        symbols.append(m.group("symbol"))
        tss.append(m.group("tss"))
        ensg.append(m.group("ensg"))
    return np.array(symbols), np.array(tss), np.array(ensg)


def _read_categorical(parent: h5py.Group, key: str) -> np.ndarray:
    """Read an h5ad dataframe column across all three encodings anndata has used.

    * current: a group with `categories` and `codes`;
    * legacy:  an integer-code dataset beside a sibling `__categories/<key>`
      (this is what the 2022 Replogle files use -- reading the codes as values
      silently yields the strings "0", "1", ... and every join then misses);
    * plain:   a string or numeric dataset.
    """
    node = parent[key]
    if isinstance(node, h5py.Group):
        cats = node["categories"].asstr()[:]
        codes = node["codes"][:]
        return np.where(codes >= 0, cats[np.maximum(codes, 0)], "")
    legacy = parent.get("__categories")
    if legacy is not None and key in legacy and node.dtype.kind in "iu":
        cats = legacy[key].asstr()[:]
        codes = node[:]
        return np.where(codes >= 0, cats[np.maximum(codes, 0)], "")
    if node.dtype.kind in "OSU":
        return node.asstr()[:]
    return node[:]


@dataclass(frozen=True)
class PseudobulkFile:
    """One Replogle-style pseudobulk file, read lazily and in row blocks.

    Attributes:
        path: the .h5ad on disk.
        source_id: registry id recorded on every signature produced.
        context: biological context label (cell line plus any condition).
    """

    path: Path
    source_id: str
    context: str

    def describe(self) -> dict:
        """Shape, control census and cell-count coverage, without loading X."""
        with h5py.File(self.path, "r") as f:
            shape = tuple(f["X"].shape)
            symbol, tss, ensg = parse_gene_transcript(
                _read_categorical(f["obs"], "gene_transcript")
            )
            ncf = f["obs/num_cells_filtered"][:].astype(np.float64)
            core = f["obs/core_control"][:]
            gene_names = _read_categorical(f["var"], "gene_name")
        ntc = symbol == NTC_SYMBOL
        return {
            "path": str(self.path),
            "source_id": self.source_id,
            "context": self.context,
            "shape": shape,
            "n_rows_unparsed": int((symbol == "").sum()),
            "n_non_targeting_rows": int(ntc.sum()),
            "n_core_control_rows": int(core.sum()),
            "core_control_is_subset_of_ntc": bool(((core) & (~ntc)).sum() == 0),
            "n_rows_missing_cell_count": int(np.isnan(ncf).sum()),
            "median_cells_per_row": float(np.nanmedian(ncf)),
            "n_source_genes": len(gene_names),
            "n_unique_ensg": int(len(set(ensg[~ntc]) - {""})),
            "n_ensg_with_multiple_tss": int(
                sum(1 for _, c in _counts(ensg[~ntc & (ensg != "")]).items() if c > 1)
            ),
        }

    def target_census(self) -> dict[str, int]:
        """Perturbed target symbols and their usable row counts, without reading X.

        Cheap enough to call on every source before deciding what to load, which
        is what keeps a selection step from turning into a full ingestion.
        """
        with h5py.File(self.path, "r") as f:
            symbol, _, _ = parse_gene_transcript(
                _read_categorical(f["obs"], "gene_transcript")
            )
            ncf = f["obs/num_cells_filtered"][:].astype(np.float64)
        usable = (symbol != "") & (symbol != NTC_SYMBOL) & ~np.isnan(ncf) & (ncf > 0)
        out: dict[str, int] = {}
        for s in symbol[usable]:
            out[str(s)] = out.get(str(s), 0) + 1
        return out

    def load_signatures(
        self,
        *,
        targets: set[str] | None = None,
        min_cells: int = 1,
        control: str = "non-targeting",
        pseudocount_cpm: float = 1.0,
        axis: GeneAxis | None = None,
        block_rows: int = 512,
    ) -> tuple[SignatureSet, dict]:
        """Build one signature per perturbation row.

        Args:
            targets: restrict to these gene symbols; None keeps all.
            min_cells: drop rows backed by fewer cells than this. Rows with no
                recorded cell count are always dropped -- their precision is
                unknown, and guessing it would fabricate an uncertainty.
            control: "non-targeting" (documented label, the default) or
                "core_control" (narrower author annotation).
            pseudocount_cpm: CPM pseudocount in the log ratio.
            axis: override the official axis (tests).
            block_rows: rows read from X per chunk; bounds peak memory to
                roughly `block_rows * n_source_genes * 8` bytes.

        Returns:
            (signatures, report) -- the report records every exclusion, so a
            downstream claim about coverage can be traced to a count.
        """
        axis = axis or official_axis()
        if control not in {"non-targeting", "core_control"}:
            raise ValueError(f"unknown control mode: {control!r}")

        with h5py.File(self.path, "r") as f:
            labels = _read_categorical(f["obs"], "gene_transcript")
            symbol, tss, ensg = parse_gene_transcript(labels)
            ncf = f["obs/num_cells_filtered"][:].astype(np.float64)
            core = f["obs/core_control"][:]
            gene_names = np.asarray(_read_categorical(f["var"], "gene_name"), dtype=str)

            is_ntc = symbol == NTC_SYMBOL
            ctrl_rows = np.flatnonzero(
                (is_ntc & core) if control == "core_control" else is_ntc
            )
            has_cells = ~np.isnan(ncf) & (ncf > 0)
            ctrl_rows = ctrl_rows[has_cells[ctrl_rows]]
            if ctrl_rows.size == 0:
                raise ValueError(f"{self.path}: no usable control rows under {control!r}")

            pert_mask = (~is_ntc) & (symbol != "") & has_cells & (ncf >= min_cells)
            if targets is not None:
                pert_mask &= np.isin(symbol, list(targets))
            pert_rows = np.flatnonzero(pert_mask)

            report = {
                "source_id": self.source_id,
                "context": self.context,
                "control_mode": control,
                "min_cells": min_cells,
                "n_rows_total": int(len(labels)),
                "n_control_rows_used": int(ctrl_rows.size),
                "n_rows_unparsed": int((symbol == "").sum()),
                "n_rows_missing_cell_count": int((~has_cells).sum()),
                "n_rows_below_min_cells": int(
                    ((~is_ntc) & has_cells & (ncf < min_cells)).sum()
                ),
                "n_perturbation_rows_used": int(pert_rows.size),
            }
            if pert_rows.size == 0:
                return SignatureSet(), report

            # Control: cell-weighted mean profile, then back to effective counts.
            ctrl_counts = np.zeros(len(gene_names), dtype=np.float64)
            ctrl_cells = 0.0
            for lo in range(0, ctrl_rows.size, block_rows):
                idx = ctrl_rows[lo : lo + block_rows]
                block = f["X"][idx.min() : idx.max() + 1, :].astype(np.float64)
                block = block[idx - idx.min(), :]
                ctrl_counts += (block * ncf[idx][:, None]).sum(axis=0)
                ctrl_cells += float(ncf[idx].sum())
            ctrl_lib = float(ctrl_counts.sum())

            ctrl_aligned = align_to_axis(
                ctrl_counts[None, :], gene_names, ["control"],
                duplicate_policy="sum", axis=axis,
            )

            out = SignatureSet()
            for lo in range(0, pert_rows.size, block_rows):
                idx = pert_rows[lo : lo + block_rows]
                block = f["X"][idx.min() : idx.max() + 1, :].astype(np.float64)
                block = block[idx - idx.min(), :]
                counts = block * ncf[idx][:, None]
                libs = counts.sum(axis=1)

                aligned = align_to_axis(
                    counts, gene_names, symbol[idx],
                    duplicate_policy="sum", axis=axis,
                )
                delta, se, observed = delta_from_pseudobulk(
                    aligned,
                    ctrl_aligned.values[0],
                    ctrl_aligned.observed,
                    library_sizes=libs,
                    control_library_size=ctrl_lib,
                    pseudocount_cpm=pseudocount_cpm,
                )
                for j, row in enumerate(idx):
                    out.add(
                        Signature(
                            source=self.source_id,
                            context=self.context,
                            target=str(symbol[row]),
                            # float32 halves the footprint of a set that is
                            # (n_signatures x 18,533) twice over; the estimates
                            # carry nothing like seven significant digits.
                            delta=delta[j].astype(np.float32),
                            se=se[j].astype(np.float32),
                            observed=observed,
                            n_cells=float(ncf[row]),
                            n_control_cells=ctrl_cells,
                            guide_id=f"{ensg[row]}:{tss[row]}",
                            meta={"tss": str(tss[row]), "ensg": str(ensg[row])},
                        )
                    )

        report["n_signatures"] = len(out)
        report["n_axis_genes_observed"] = int(ctrl_aligned.observed.sum())
        report["n_source_genes_off_axis"] = len(ctrl_aligned.dropped)
        report["n_axis_genes_from_duplicate_symbols"] = len(ctrl_aligned.collapsed)
        report["control_cells"] = ctrl_cells
        report["control_library"] = ctrl_lib
        return out, report


def _counts(values) -> dict[str, int]:
    out: dict[str, int] = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return out
