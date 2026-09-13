"""Stage 6: verify a prediction against the contract, then package it as .vcc.

Two verifications run here, and they are not the same verification.

**The official one.** `vcc prep` is the tool the server uses, so it is the
authority on the format: gene set and order, context labels, the exact
perturbation list per context, the per-perturbation cell count, raw integer
counts, no control rows, the density cap, the per-cell count cap. It is run
first with `--dry-run`, which reports what packaging would do without writing,
and only then for real. Its stdout, stderr and exit status are saved: a
validation that left no log is not evidence that it passed.

**The one prep cannot do.** Format validation is blind to *which* context's data
sits under which label. The challenge FAQ is explicit that swapping two contexts
makes "every metric degrade toward chance" and look "like a weak model rather
than a bug". Since every prediction in this project is generated from one
context's own control cells, each context's aggregate profile must be nearest to
that context's basal profile -- so this script re-reads the written file from
disk, independently of the generator that produced it, and checks exactly that.
It also re-derives the contract invariants from the file rather than trusting
the writer that made it.

Nothing here uploads anything.

    scripts/py.cmd scripts/46_validate_package.py --run-id q00full
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config
from vcc2026.genes import official_axis
from vcc2026.inference import nearest_basal_context, read_basal_profile
from vcc2026.manifest import RunManifest, file_fingerprint
from vcc2026.resources import GiB, peak_rss_bytes, snapshot

REPO = Path(__file__).resolve().parents[1]
VCC_CMD = REPO / "scripts" / "vcc.cmd"


def sizing_estimate(nnz: int) -> dict:
    """What the installed CLI's own sizing model says this file will cost.

    Read from `vcc.sizing` rather than reimplemented: those constants were fitted
    on the scoring service's production instrumentation, and a local copy would
    drift. Recorded next to every packaging attempt because the estimate is what
    explains an attempt that does not finish.
    """
    try:
        from vcc import sizing
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "available": True,
        "source": "vcc.sizing (installed vcc-cli)",
        "nnz": nnz,
        "scipy_bytes_per_nnz": sizing.bytes_per_nnz(nnz),
        "crosses_int32_index_limit": nnz > sizing.INT32_INDEX_LIMIT,
        "int32_index_limit": sizing.INT32_INDEX_LIMIT,
        "prep_peak_gib_no_cast_in_order": sizing.prep_peak_gib(
            nnz, casts=False, reordered=False
        ),
        "prep_peak_gib_worst_case": sizing.prep_peak_gib(
            nnz, casts=True, reordered=True
        ),
        "scoring_container_peak_gib": sizing.estimated_peak_gib(nnz),
        "hard_cap_nnz": sizing.HARD_CAP_NNZ,
        "fraction_of_hard_cap": nnz / sizing.HARD_CAP_NNZ,
        "exceeds_hard_cap": sizing.exceeds_hard_cap(nnz),
        "prep_memory_warning": sizing.prep_memory_warning(nnz, casts=False),
        "prep_memory_warning_note": (
            "None on Windows: the CLI sizes the warning against os.sysconf, which "
            "Windows does not provide, so it cannot fire here even when packaging "
            "would exceed the machine. Do not read its absence as a pass."
        ),
    }


def _categorical(group: h5py.Group, name: str) -> np.ndarray:
    """Read an anndata categorical obs column back as strings."""
    node = group[name]
    if isinstance(node, h5py.Dataset):
        return node.asstr()[:] if node.dtype == object else node[:]
    cats = node["categories"].asstr()[:]
    codes = node["codes"][:]
    return np.asarray(cats)[codes]


def read_contract(path: Path, *, block_rows: int = 4000) -> dict:
    """Re-derive every contract invariant from the written file.

    Streamed in row blocks: the matrix holds around two billion stored values
    and loading X whole is roughly 17 GB.
    """
    ch = config.challenge()
    axis = official_axis()
    panel = [
        str(g)
        for g in pd.read_csv(
            config.paths().raw / "controls" / "pert_counts.csv"
        )["target_gene"]
    ]

    with h5py.File(path, "r") as f:
        n_obs, n_genes = (int(v) for v in f["X"].attrs["shape"])
        var_names = list(f["var/_index/values"].asstr()[:])
        obs = f["obs"]
        obs_columns = [k for k in obs.keys() if k != "_index"]
        perts = _categorical(obs, ch.pert_col)
        contexts = _categorical(obs, ch.context_col)
        indptr_raw = f["X/indptr"][:]
        indptr = indptr_raw.astype(np.int64)
        data_ds = f["X/data"]
        indices_dtype_name = str(f["X/indices"].dtype)

        # A CSR offset array that wrapped through int32 still opens as a valid
        # h5ad and yields a garbage matrix, so it is checked directly rather
        # than inferred from the writer's intent. A full submission sits within
        # 3% of int32's ceiling (see `indptr_dtype` in submission.py).
        indptr_dtype_name = str(indptr_raw.dtype)
        indptr_monotonic = bool(np.all(np.diff(indptr) >= 0))
        indptr_non_negative = bool(indptr.min() >= 0)
        indptr_matches_data = int(indptr[-1]) == int(data_ds.shape[0])
        nnz = int(indptr[-1])
        all_integral = True
        all_finite = True
        min_value = np.inf
        stored_zeros = 0
        max_counts_per_cell = 0.0
        per_cell_nnz_max = 0
        for start in range(0, n_obs, block_rows):
            stop = min(start + block_rows, n_obs)
            lo, hi = int(indptr[start]), int(indptr[stop])
            values = data_ds[lo:hi]
            if values.size:
                all_integral &= bool(np.all(values == np.floor(values)))
                all_finite &= bool(np.all(np.isfinite(values)))
                min_value = min(min_value, float(values.min()))
                stored_zeros += int((values == 0).sum())
            bounds = indptr[start : stop + 1] - lo
            lengths = np.diff(bounds)
            if values.size:
                # reduceat raises on an index equal to the array length, which an
                # empty trailing row would produce, so clamp and zero those rows.
                idx = np.minimum(bounds[:-1], values.size - 1)
                totals = np.where(lengths > 0, np.add.reduceat(values, idx), 0.0)
                max_counts_per_cell = max(max_counts_per_cell, float(totals.max()))
            if lengths.size:
                per_cell_nnz_max = max(per_cell_nnz_max, int(lengths.max()))

    pairs = Counter(zip(contexts.tolist(), perts.tolist()))
    per_context_targets = {}
    for ctx in sorted(set(contexts.tolist())):
        per_context_targets[ctx] = sorted(
            {t for (c, t) in pairs if c == ctx}
        )
    cell_counts = sorted({v for v in pairs.values()})

    checks = {
        "csr_offsets_monotonic": indptr_monotonic,
        "csr_offsets_non_negative": indptr_non_negative,
        "csr_offsets_match_stored_values": indptr_matches_data,
        "gene_dim_is_18533": n_genes == ch.n_genes,
        "gene_order_matches_official_axis": var_names == list(axis.symbols),
        "obs_has_required_columns": {ch.pert_col, ch.context_col} <= set(obs_columns),
        "counts_are_whole_numbers": all_integral,
        "counts_are_finite": all_finite,
        "counts_non_negative": bool(min_value >= 0) if np.isfinite(min_value) else True,
        "no_explicitly_stored_zeros": stored_zeros == 0,
        "no_non_targeting_rows": ch.ntc_label not in set(perts.tolist()),
        "under_global_storage_cap": nnz <= ch.max_stored_entries,
        "under_max_counts_per_cell": max_counts_per_cell <= ch.max_counts_per_cell,
        "cells_per_perturbation_uniform": len(cell_counts) == 1,
        "cells_per_perturbation_is_official": cell_counts == [ch.cells_per_pert],
        "contexts_are_official": sorted(set(contexts.tolist()))
        == sorted(ch.contexts_validation),
        "every_context_predicts_the_full_panel": all(
            targets == sorted(panel) for targets in per_context_targets.values()
        ),
        "no_extra_perturbations": all(
            set(targets) <= set(panel) for targets in per_context_targets.values()
        ),
    }
    return {
        "path": str(path),
        "n_obs": n_obs,
        "n_genes": n_genes,
        "stored_entries": nnz,
        "stored_entries_per_cell": nnz / n_obs if n_obs else None,
        "csr_indptr_dtype": indptr_dtype_name,
        "csr_indices_dtype": indices_dtype_name,
        "max_stored_in_one_cell": per_cell_nnz_max,
        "max_counts_in_one_cell": max_counts_per_cell,
        "stored_zeros": stored_zeros,
        "min_stored_value": None if not np.isfinite(min_value) else min_value,
        "obs_columns": obs_columns,
        "contexts": sorted(set(contexts.tolist())),
        "n_targets_per_context": {k: len(v) for k, v in per_context_targets.items()},
        "cells_per_perturbation_observed": cell_counts,
        "checks": checks,
        "all_checks_pass": all(bool(v) for v in checks.values()),
    }


def verify_context_provenance(path: Path, contexts) -> dict:
    """Re-read the file and confirm each context's data sits under its own label.

    Independent of the generator: the profiles come from the written file and
    the basal states from the control bundle.
    """
    axis = official_axis()
    basals = {}
    for ctx in contexts:
        ctrl = config.paths().raw / "controls" / f"context_{ctx}.h5ad"
        basals[ctx] = read_basal_profile(ctrl).profile

    totals = {ctx: np.zeros(len(axis), dtype=np.float64) for ctx in contexts}
    with h5py.File(path, "r") as f:
        n_obs = int(f["X"].attrs["shape"][0])
        ctx_labels = _categorical(f["obs"], config.challenge().context_col)
        indptr = f["X/indptr"][:].astype(np.int64)
        data_ds, idx_ds = f["X/data"], f["X/indices"]
        block = 4000
        for start in range(0, n_obs, block):
            stop = min(start + block, n_obs)
            lo, hi = int(indptr[start]), int(indptr[stop])
            values = data_ds[lo:hi].astype(np.float64)
            columns = idx_ds[lo:hi]
            bounds = indptr[start : stop + 1] - lo
            labels = ctx_labels[start:stop]
            present = set(labels.tolist())
            if len(present) == 1:
                # The common case: a block holds one context. bincount over the
                # whole block is orders of magnitude faster than np.add.at per
                # row, and this loop runs over two billion stored values.
                ctx = next(iter(present))
                totals[ctx] += np.bincount(
                    columns, weights=values, minlength=len(axis)
                )[: len(axis)]
                continue
            # Mixed block: rows of one context need not be contiguous, and the
            # check must not depend on their being so.
            for ctx in present:
                sel = np.flatnonzero(labels == ctx)
                take = np.concatenate(
                    [np.arange(bounds[i], bounds[i + 1]) for i in sel]
                )
                totals[ctx] += np.bincount(
                    columns[take], weights=values[take], minlength=len(axis)
                )[: len(axis)]

    per_context = {}
    for ctx in contexts:
        best, scores = nearest_basal_context(totals[ctx], basals)
        per_context[ctx] = {
            "nearest_basal_context": best,
            "similarity_to_each_basal": scores,
            "label_matches_nearest_basal": best == ctx,
            "margin_over_runner_up": (
                float(scores[best] - max(v for k, v in scores.items() if k != best))
                if len(scores) > 1 else None
            ),
        }
    return {
        "per_context": per_context,
        "all_labels_match_nearest_basal": all(
            v["label_matches_nearest_basal"] for v in per_context.values()
        ),
        "method": (
            "cosine similarity of log1p CPM profiles, aggregated over every "
            "predicted cell of a context, against each context's basal control "
            "profile; re-read from the written file"
        ),
        "why": (
            "vcc prep validates the format and cannot see swapped A/B/C data. "
            "Every block is generated from one context's own controls, so a swap "
            "shows up here as a label whose nearest basal profile is a different "
            "context."
        ),
    }


def run_cli(args_list, log_path: Path, *, timeout: float = 7200) -> dict:
    """Run a vcc CLI command, saving its output as the evidence that it ran.

    A timeout is itself a measurement here. `vcc prep` loads the whole matrix
    into memory before it validates anything, so on a machine with less RAM than
    the prediction needs it does not fail fast -- it pages. "Did not finish in N
    seconds, with the machine's memory state recorded" is the honest result, and
    it is recorded rather than retried.
    """
    cmd = [str(VCC_CMD), *args_list]
    started = time.time()
    timed_out = False
    try:
        proc = subprocess.run(
            cmd, capture_output=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        code, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        code = None

        def _text(stream):
            if stream is None:
                return ""
            if isinstance(stream, bytes):
                return stream.decode("utf-8", "replace")
            return stream

        out, err = _text(exc.stdout), _text(exc.stderr)
    elapsed = time.time() - started
    state = snapshot(log_path.parent)
    log_path.write_text(
        f"$ {' '.join(shlex.quote(c) for c in cmd)}\n"
        f"exit_code: {code}\n"
        f"timed_out: {timed_out} (limit {timeout}s)\n"
        f"elapsed_seconds: {elapsed:.1f}\n"
        f"ram_total_gib: {state.ram_total_bytes / GiB:.2f}\n"
        f"ram_available_gib_after: {state.ram_available_gib}\n"
        f"disk_free_gib_after: {state.disk_free_gib:.2f}\n"
        f"--- stdout ---\n{out}\n--- stderr ---\n{err}\n",
        encoding="utf-8",
    )
    return {
        "command": cmd,
        "exit_code": code,
        "timed_out": timed_out,
        "timeout_seconds": timeout,
        "elapsed_seconds": elapsed,
        "stdout": out or "",
        "stderr": err or "",
        "log": str(log_path),
        "machine_state_after": state.as_dict(),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", required=True)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--prediction", type=Path, default=None)
    p.add_argument("--vcc-name", default="prediction.vcc")
    p.add_argument("--skip-package", action="store_true",
                   help="run the dry-run validation only")
    p.add_argument("--skip-prep", action="store_true",
                   help="re-derive the contract and verify provenance, without "
                        "invoking the official CLI at all. Use when the machine "
                        "is busy: vcc prep loads the whole matrix and would "
                        "contend for the memory another job is using.")
    p.add_argument("--prep-timeout", type=float, default=1800,
                   help="seconds to allow each vcc prep invocation; a timeout is "
                        "recorded as a measurement, not retried")
    p.add_argument("--attempt", default=None,
                   help="label for this attempt; every output of this run is "
                        "suffixed with it. Defaults to a UTC timestamp, so a "
                        "rerun never lands on a previous attempt's evidence.")
    p.add_argument("--allow-overwrite", action="store_true")
    args = p.parse_args()

    attempt = args.attempt or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = args.out or config.run_dir(args.run_id)
    pred = args.prediction or (run / "prediction.h5ad")
    if not pred.exists():
        raise SystemExit(f"{pred} missing; run 45_generate_prediction.py first")

    out = run / f"validation_{attempt}.json"
    dry_log = run / f"prep_dry_run_{attempt}.log"
    package_log = run / f"prep_package_{attempt}.log"
    manifest_path = run / f"manifest_46_validate_package_{attempt}.json"
    for pth in (out, dry_log, package_log, manifest_path):
        if pth.exists() and not args.allow_overwrite:
            raise SystemExit(
                f"{pth} exists; pass a different --attempt. Validation evidence "
                f"is never overwritten."
            )

    ch = config.challenge()
    genes_csv = config.paths().raw / "controls" / "gene_names.csv"
    perts_csv = config.paths().raw / "controls" / "pert_counts.csv"
    before = snapshot(run)

    print(f"prediction : {pred}  ({pred.stat().st_size / GiB:.2f} GiB)")
    print(f"disk free  : {before.disk_free_gib:.2f} GiB\n")

    print("re-deriving the contract from the written file ...")
    t0 = time.perf_counter()
    contract = read_contract(pred)
    contract["seconds"] = time.perf_counter() - t0
    for name, ok in contract["checks"].items():
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print(f"  ({contract['seconds']:.0f}s)\n")

    print("verifying context provenance (prep cannot) ...")
    t0 = time.perf_counter()
    provenance = verify_context_provenance(pred, contract["contexts"])
    provenance["seconds"] = time.perf_counter() - t0
    for ctx, v in provenance["per_context"].items():
        print(f"  {ctx}: nearest basal = {v['nearest_basal_context']} "
              f"(margin {v['margin_over_runner_up']:.4f})  "
              f"{'OK' if v['label_matches_nearest_basal'] else 'MISMATCH'}")
    print(f"  ({provenance['seconds']:.0f}s)\n")

    base = ["prep", str(pred), "-g", str(genes_csv), "--perts", str(perts_csv)]
    if args.skip_prep:
        print("vcc prep: SKIPPED (--skip-prep). The official validation has NOT "
              "run; nothing below is a statement about the official format.")
        dry = {
            "command": [str(VCC_CMD), *base, "--dry-run"],
            "exit_code": None,
            "timed_out": None,
            "timeout_seconds": None,
            "elapsed_seconds": None,
            "stdout": "",
            "stderr": "",
            "log": None,
            "skipped": True,
            "skipped_reason": "--skip-prep",
        }
    else:
        print("vcc prep --dry-run ...")
        dry = run_cli([*base, "--dry-run"], dry_log, timeout=args.prep_timeout)
    if not dry.get("skipped"):
        print(f"  exit {dry['exit_code']}"
              f"{' TIMED OUT' if dry['timed_out'] else ''} "
              f"({dry['elapsed_seconds']:.0f}s) -> {Path(dry['log']).name}")
    if dry["stdout"]:
        print("  " + dry["stdout"].strip().replace("\n", "\n  ")[:1500])
    if dry["exit_code"] != 0 and dry["stderr"]:
        print("  " + dry["stderr"].strip().replace("\n", "\n  ")[:1500])

    package = None
    vcc_path = run / args.vcc_name
    # Packaging is gated on EVERY check, not just the official dry run. A
    # contract failure or a context-provenance mismatch means the prediction is
    # wrong in a way `vcc prep` either already rejected or cannot see; writing an
    # archive from it would turn a file we have just shown is not submittable
    # into a submittable-looking artifact.
    local_ok = contract["all_checks_pass"] and provenance[
        "all_labels_match_nearest_basal"
    ]
    if args.skip_package or args.skip_prep:
        print("\npackaging skipped.")
    elif not local_ok:
        print("\nNOT PACKAGING: the contract re-check or the context-provenance "
              "check failed. Those are the two things that decide whether this "
              "file is a submission at all.", file=sys.stderr)
    else:
        if dry["exit_code"] != 0:
            print("\ndry-run FAILED; not packaging. Validation limits are not "
                  "bypassed -- fix the prediction, do not force the package.")
        else:
            print("\nvcc prep (packaging) ...")
            cmd = [*base, "-o", str(vcc_path)]
            if args.allow_overwrite:
                cmd.append("--force")
            package = run_cli(cmd, package_log, timeout=args.prep_timeout)
            print(f"  exit {package['exit_code']} "
                  f"({package['elapsed_seconds']:.0f}s)")
            if package["stdout"]:
                print("  " + package["stdout"].strip().replace("\n", "\n  ")[:2000])
            if package["exit_code"] != 0 and package["stderr"]:
                print("  " + package["stderr"].strip().replace("\n", "\n  ")[:2000])

    # Exit code, because a caller scripting this must be able to tell. A silent
    # zero after a failed contract check is how an invalid prediction reaches an
    # upload.
    exit_code = 0
    if not contract["all_checks_pass"]:
        exit_code = 1
    if not provenance["all_labels_match_nearest_basal"]:
        exit_code = 1
    if not args.skip_prep:
        if dry.get("timed_out"):
            exit_code = max(exit_code, 4)
        elif dry["exit_code"] not in (0, None):
            exit_code = max(exit_code, 1)
        if package is not None and package["exit_code"] not in (0, None):
            exit_code = max(exit_code, 1)

    result = {
        "run_id": args.run_id,
        "stage": "46_validate_package",
        "prediction": file_fingerprint(pred, full=True),
        "official_lists": {
            "genes": file_fingerprint(genes_csv, full=True),
            "perturbations": file_fingerprint(perts_csv, full=True),
        },
        "contract_recheck": contract,
        "context_provenance": provenance,
        "vcc_prep_dry_run": {k: v for k, v in dry.items() if k != "stdout"} | {
            "stdout_tail": dry["stdout"][-4000:],
        },
        "vcc_prep_package": (
            None if package is None else
            {k: v for k, v in package.items() if k != "stdout"} | {
                "stdout_tail": package["stdout"][-4000:],
            }
        ),
        "vcc_artifact": (
            file_fingerprint(vcc_path, full=True) if vcc_path.exists() else None
        ),
        "cli_sizing_model": sizing_estimate(contract["stored_entries"]),
        "contract_source": {
            "authority": "virtualcellchallenge.org/evaluation + vcc prep --help",
            "n_genes": ch.n_genes,
            "n_perturbations": ch.n_perturbations,
            "cells_per_pert": ch.cells_per_pert,
            "contexts": list(ch.contexts_validation),
            "pert_col": ch.pert_col,
            "context_col": ch.context_col,
            "max_stored_entries": ch.max_stored_entries,
            "max_counts_per_cell": ch.max_counts_per_cell,
        },
        "uploaded": False,
        "note": (
            "Local validation and packaging only. Nothing was uploaded and no "
            "submission quota was consumed. A passing prep is a statement about "
            "FORMAT; it says nothing about predictive quality."
        ),
        "resources_before": before.as_dict(),
        "resources_after": snapshot(run).as_dict(),
        "peak_rss_bytes": peak_rss_bytes(),
        "attempt": attempt,
        "exit_code": exit_code,
        "packaged": vcc_path.exists(),
    }
    out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    man = RunManifest(run_id=args.run_id, stage="46_validate_package",
                      config=vars(args))
    man.add_input("prediction", pred)
    man.add_input("genes", genes_csv)
    man.add_input("perturbations", perts_csv)
    man.add_output("validation", out)
    if dry_log.exists():
        man.add_output("prep_dry_run_log", dry_log)
    if vcc_path.exists():
        man.add_output("vcc", vcc_path)
        man.add_output("prep_package_log", package_log)
    man.metrics = {
        "contract_all_checks_pass": contract["all_checks_pass"],
        "context_provenance_ok": provenance["all_labels_match_nearest_basal"],
        "prep_dry_run_exit": dry["exit_code"],
        "prep_package_exit": None if package is None else package["exit_code"],
    }
    man.note("Format validation cannot detect swapped contexts; provenance is "
             "checked separately against each context's basal profile.")
    man.note("Nothing uploaded.")
    man.write(manifest_path, allow_overwrite=args.allow_overwrite)

    print(f"\ncontract re-check     : "
          f"{'ALL PASS' if contract['all_checks_pass'] else 'FAILURES ABOVE'}")
    print(f"context provenance    : "
          f"{'OK' if provenance['all_labels_match_nearest_basal'] else 'MISMATCH'}")
    if vcc_path.exists():
        print(f"package               : {vcc_path.name} "
              f"({vcc_path.stat().st_size / GiB:.2f} GiB)")
        print(f"sha256                : {result['vcc_artifact']['sha256']}")
    print(f"-> {out}")
    if exit_code:
        print(f"FAILED (exit {exit_code})", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
