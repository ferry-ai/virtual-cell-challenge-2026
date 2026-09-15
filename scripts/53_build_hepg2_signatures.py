"""Build HepG2 signatures from single cells, on the same axis and the same
definition as the existing pseudobulk sources.

The arithmetic is deliberately the one already in the repository: counts are
summed per target, converted to CPM against the source's own library, and
compared with a matched control through `delta_from_pseudobulk` -- same log2
ratio, same CPM pseudocount, same Poisson standard error. Nothing new is
invented for this source, so a HepG2 signature and a K562 one mean the same
thing when a model reads them side by side.

What *is* new is the control. The object carries 56 batches and every one of
them has NTC cells, so each target is compared with the NTC of the batches its
own cells came from, mixed in the proportion those cells appear:

    CPM_control(t) = sum_b  w(t,b) * CPM_ntc(b),      w(t,b) = n(t,b) / n(t)

with an effective control library size `1 / sum_b w(t,b)^2 / L_b`, the
variance-equivalent of that mixture, so the standard error still reflects how
many control counts actually stand behind the comparison. Pooling all NTCs
instead would compare a target that lives in two batches against the average of
fifty-six, and a batch effect would arrive labelled as a perturbation effect.
`--control-matching pooled` does exactly that, for comparison, and says so.

    scripts/py.cmd scripts/53_build_hepg2_signatures.py --run-id e003
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config
from vcc2026.genes import align_to_axis, official_axis
from vcc2026.manifest import RunManifest
from vcc2026.pseudobulk import _read_categorical
from vcc2026.signatures import Signature, SignatureSet, delta_from_pseudobulk

NTC_LEVEL = "control"       # verified in reports/hepg2_2026-09-14/nadig_hepg2_audit.json


def local_targets(signature_dir: Path) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for rows in sorted(signature_dir.glob("*.rows.json")):
        payload = json.loads(rows.read_text(encoding="utf-8"))
        out[rows.name.replace(".rows.json", "")] = {str(r["target"]) for r in payload}
    return out


def accumulate(
    path: Path,
    *,
    keep: set[str],
    ntc_level: str,
    block_rows: int,
    log,
) -> dict:
    """One streaming pass: per-target sums, per-batch NTC sums, cell counts.

    Peak memory is one block of the dense matrix plus the accumulators, never
    the 5.6 GB the object would occupy dense.
    """
    with h5py.File(path, "r") as handle:
        perturbation = np.asarray(_read_categorical(handle["obs"], "perturbation"), dtype=str)
        batch = np.asarray(_read_categorical(handle["obs"], "batch")).astype(str)
        guide = np.asarray(_read_categorical(handle["obs"], "guide_id"), dtype=str)
        genes = np.asarray(_read_categorical(handle["var"], "gene_name"), dtype=str)
        n_cells, n_genes = handle["X"].shape

        is_ntc = perturbation == ntc_level
        wanted = np.isin(perturbation, list(keep)) & ~is_ntc

        targets = sorted(set(perturbation[wanted].tolist()))
        batches = sorted(set(batch.tolist()))
        t_index = {t: i for i, t in enumerate(targets)}
        b_index = {b: i for i, b in enumerate(batches)}

        target_sums = np.zeros((len(targets), n_genes), dtype=np.float64)
        target_lib = np.zeros(len(targets), dtype=np.float64)
        target_cells = np.zeros(len(targets), dtype=np.int64)
        target_batch_cells = np.zeros((len(targets), len(batches)), dtype=np.int64)
        ntc_sums = np.zeros((len(batches), n_genes), dtype=np.float64)
        ntc_lib = np.zeros(len(batches), dtype=np.float64)
        ntc_cells = np.zeros(len(batches), dtype=np.int64)

        t_of_cell = np.full(n_cells, -1, dtype=np.int64)
        t_of_cell[wanted] = [t_index[t] for t in perturbation[wanted]]
        b_of_cell = np.array([b_index[b] for b in batch], dtype=np.int64)

        n_blocks = int(np.ceil(n_cells / block_rows))
        for step, lo in enumerate(range(0, n_cells, block_rows)):
            hi = min(lo + block_rows, n_cells)
            block = np.asarray(handle["X"][lo:hi, :], dtype=np.float64)
            libs = block.sum(axis=1)
            rows_t = t_of_cell[lo:hi]
            rows_b = b_of_cell[lo:hi]
            rows_n = is_ntc[lo:hi]
            for local in np.flatnonzero(rows_t >= 0):
                ti = int(rows_t[local])
                target_sums[ti] += block[local]
                target_lib[ti] += libs[local]
                target_cells[ti] += 1
                target_batch_cells[ti, int(rows_b[local])] += 1
            for local in np.flatnonzero(rows_n):
                bi = int(rows_b[local])
                ntc_sums[bi] += block[local]
                ntc_lib[bi] += libs[local]
                ntc_cells[bi] += 1
            if step % 10 == 0 or hi == n_cells:
                log(f"  blocco {step + 1}/{n_blocks} ({hi}/{n_cells} cellule)")

        guide_of_target: dict[str, list[str]] = {}
        for target, gid in zip(perturbation[wanted], guide[wanted]):
            guide_of_target.setdefault(str(target), []).append(str(gid))

    return {
        "targets": targets,
        "batches": batches,
        "genes": genes,
        "target_sums": target_sums,
        "target_lib": target_lib,
        "target_cells": target_cells,
        "target_batch_cells": target_batch_cells,
        "ntc_sums": ntc_sums,
        "ntc_lib": ntc_lib,
        "ntc_cells": ntc_cells,
        "guide_of_target": {k: sorted(set(v)) for k, v in guide_of_target.items()},
        "n_cells_total": int(n_cells),
        "n_genes_total": int(n_genes),
        "n_ntc_cells": int(is_ntc.sum()),
    }


def matched_control(acc: dict, ti: int, *, matching: str) -> tuple[np.ndarray, float, float]:
    """(counts, library, effective control cells) for this target's control.

    In `batch` mode the mixture weights are the target's own cell proportions,
    and the library returned is the variance-equivalent of the mixture, not the
    sum of every NTC in the object: an average of many batches is not evidence
    of many counts when only two of them are comparable.
    """
    ntc_sums, ntc_lib, ntc_cells = acc["ntc_sums"], acc["ntc_lib"], acc["ntc_cells"]
    if matching == "pooled":
        counts = ntc_sums.sum(axis=0)
        return counts, float(ntc_lib.sum()), float(ntc_cells.sum())

    weights = acc["target_batch_cells"][ti].astype(np.float64)
    usable = (weights > 0) & (ntc_lib > 0)
    if not usable.any():
        counts = ntc_sums.sum(axis=0)
        return counts, float(ntc_lib.sum()), float(ntc_cells.sum())
    weights = np.where(usable, weights, 0.0)
    weights = weights / weights.sum()
    cpm = np.zeros_like(ntc_sums[0])
    for bi in np.flatnonzero(weights > 0):
        cpm += weights[bi] * 1e6 * ntc_sums[bi] / ntc_lib[bi]
    effective_lib = float(1.0 / np.sum(np.square(weights[usable]) / ntc_lib[usable]))
    counts = cpm * effective_lib / 1e6
    cells = float(np.sum(weights[usable] * ntc_cells[usable]))
    return counts, effective_lib, cells


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5ad", type=Path,
                        default=Path("C:/Users/ferra/vcc2026-data/raw/nadig_hepg2/"
                                     "NadigOConner2024_hepg2.h5ad"))
    parser.add_argument("--run-id", default="e003")
    parser.add_argument("--source-id", default="nadig_hepg2")
    parser.add_argument("--context", default="HepG2")
    parser.add_argument("--min-cells", type=int, default=10)
    parser.add_argument("--control-matching", choices=("batch", "pooled"), default="batch")
    parser.add_argument("--pseudocount-cpm", type=float, default=1.0)
    parser.add_argument("--block-rows", type=int, default=2048)
    parser.add_argument("--shared-with", type=Path, default=None,
                        help="signature directory whose targets restrict the build")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--allow-overwrite", action="store_true")
    args = parser.parse_args()

    out_dir = args.out or (config.paths().data_root / "artifacts" / args.run_id)
    sig_dir = out_dir / "signatures"
    sig_dir.mkdir(parents=True, exist_ok=True)
    dest = sig_dir / f"{args.source_id}.npz"
    if dest.exists() and not args.allow_overwrite:
        raise FileExistsError(f"{dest} exists; use a new --run-id (never overwrite)")

    def log(message: str) -> None:
        print(message, flush=True)

    # Which targets are worth materialising, decided before any expression is read.
    reference = args.shared_with or (
        config.paths().data_root / "artifacts" / "e001" / "signatures"
    )
    by_source = local_targets(reference) if reference.exists() else {}
    union_local = set().union(*by_source.values()) if by_source else set()

    with h5py.File(args.h5ad, "r") as handle:
        perturbation = np.asarray(
            _read_categorical(handle["obs"], "perturbation"), dtype=str
        )
    counts = pd.Series(perturbation).value_counts()
    counts = counts.drop(index=[NTC_LEVEL], errors="ignore")
    enough = set(counts[counts >= args.min_cells].index.astype(str))
    keep = (enough & union_local) if union_local else enough
    log(f"bersagli osservati: {len(counts)}; con >= {args.min_cells} cellule: "
        f"{len(enough)}; anche in una sorgente locale: {len(keep)}")

    log("passata in blocchi sul file (la matrice densa non viene mai materializzata)")
    acc = accumulate(args.h5ad, keep=keep, ntc_level=NTC_LEVEL,
                     block_rows=args.block_rows, log=log)

    axis = official_axis()
    genes = acc["genes"]
    sigs = SignatureSet()
    rows_meta = []
    skipped = {"no_control_library": 0, "empty_library": 0}

    for ti, target in enumerate(acc["targets"]):
        lib = float(acc["target_lib"][ti])
        if lib <= 0:
            skipped["empty_library"] += 1
            continue
        ctrl_counts, ctrl_lib, ctrl_cells = matched_control(
            acc, ti, matching=args.control_matching
        )
        if ctrl_lib <= 0:
            skipped["no_control_library"] += 1
            continue
        aligned = align_to_axis(
            acc["target_sums"][ti][None, :], genes, [target],
            duplicate_policy="sum", axis=axis,
        )
        ctrl_aligned = align_to_axis(
            ctrl_counts[None, :], genes, ["control"],
            duplicate_policy="sum", axis=axis,
        )
        delta, se, observed = delta_from_pseudobulk(
            aligned,
            ctrl_aligned.values[0],
            ctrl_aligned.observed,
            library_sizes=np.array([lib]),
            control_library_size=ctrl_lib,
            pseudocount_cpm=args.pseudocount_cpm,
        )
        n_batches = int((acc["target_batch_cells"][ti] > 0).sum())
        sigs.add(Signature(
            source=args.source_id,
            context=args.context,
            target=str(target),
            delta=delta[0].astype(np.float32),
            se=se[0].astype(np.float32),
            observed=observed,
            n_cells=float(acc["target_cells"][ti]),
            n_control_cells=float(ctrl_cells),
            guide_id=None,
            meta={
                "n_batches": n_batches,
                "control_matching": args.control_matching,
                "n_guides": len(acc["guide_of_target"].get(str(target), [])),
                "library": lib,
                "control_library_effective": ctrl_lib,
            },
        ))
        rows_meta.append({
            "target": str(target),
            "n_cells": int(acc["target_cells"][ti]),
            "n_batches": n_batches,
            "n_guides": len(acc["guide_of_target"].get(str(target), [])),
            "n_control_cells_effective": float(ctrl_cells),
        })

    sigs.write_npz(dest)
    log(f"-> {dest} ({len(sigs)} firme)")

    observed_any = sigs.signatures[0].observed if len(sigs) else np.zeros(len(axis), bool)
    report = {
        "source_id": args.source_id,
        "context": args.context,
        "h5ad": str(args.h5ad),
        "control_level": NTC_LEVEL,
        "control_matching": args.control_matching,
        "pseudocount_cpm": args.pseudocount_cpm,
        "min_cells": args.min_cells,
        "n_cells_total": acc["n_cells_total"],
        "n_ntc_cells": acc["n_ntc_cells"],
        "n_batches": len(acc["batches"]),
        "n_targets_observed": int(len(counts)),
        "n_targets_min_cells": len(enough),
        "n_targets_built": len(sigs),
        "n_axis_genes_observed": int(observed_any.sum()),
        "n_source_genes": acc["n_genes_total"],
        "skipped": skipped,
        "targets_shared_with": {k: len(set(rows_meta and [r["target"] for r in rows_meta]) & v)
                                for k, v in by_source.items()},
        "definition": (
            "log2((CPM_target + c) / (CPM_control + c)) on the official axis, "
            "Poisson standard error, identical to the pseudobulk sources"
        ),
        "limits": [
            "Guides are pooled per target: this source has no guide-level rows "
            "in the same sense as the Replogle files, so guide_id is null and "
            "the count of guides behind each target is kept in meta.",
            "The effective control library of a batch-matched mixture is an "
            "approximation of its variance, not a count of control cells.",
            "0/300 VCC panel targets: this source measures transfer between "
            "contexts, never coverage of the competition panel.",
        ],
    }
    qc_path = out_dir / f"signature_qc_{args.source_id}.json"
    qc_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    # A separate file, deliberately: `.rows.json` is the sidecar `read_npz`
    # reconstructs signatures from, and the first version of this script wrote
    # the census over it. The set then loaded as far as the target names and
    # failed on `source`, which is a corruption that looks like a code bug.
    (dest.parent / f"{args.source_id}.census.json").write_text(
        json.dumps(rows_meta, indent=1), encoding="utf-8"
    )

    manifest = RunManifest(
        run_id=args.run_id, stage="53_build_hepg2_signatures",
        config={k: str(v) for k, v in vars(args).items()},
    )
    manifest.add_input("h5ad", args.h5ad)
    manifest.add_output("signatures", dest)
    manifest.add_output("qc", qc_path)
    manifest.metrics = {
        "n_signatures": len(sigs),
        "n_axis_genes_observed": report["n_axis_genes_observed"],
        "n_batches": report["n_batches"],
    }
    manifest.note("Counts summed per target; the dense matrix is never materialised.")
    manifest.note("Controls are batch-matched to each target's own cells.")
    manifest.write(out_dir / f"manifest_53_{args.source_id}.json",
                   allow_overwrite=args.allow_overwrite)
    print(json.dumps(manifest.metrics, indent=2))


if __name__ == "__main__":
    main()
