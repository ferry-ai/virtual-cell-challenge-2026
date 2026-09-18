"""Stage 8: validate and package a prediction into a .vcc in bounded memory.

`vcc prep` is the authority on the format, and this stage does not replace it --
it calls the official validators on the metadata and mirrors the rest check for
check. What it replaces is the one line that makes prep unusable here:
`ad.read_h5ad(path)`, which materialises the whole matrix before validating
anything. Measured on trial-01, that is an 8.07 GiB allocation on a 7.81 GiB
machine (CP-0004 §3.5).

The run has three phases and each one is reported separately, because they
establish different things:

1. **validate** -- every official check, streamed. A clean report is a statement
   about FORMAT and nothing else.
2. **package** -- write the payload, compress, archive.
3. **verify** -- re-open the archive with the official container validator,
   stream-decompress the payload, and compare it to the input array by array.

None of the three is server acceptance. Nothing here uploads anything.

    scripts/py.cmd scripts/48_package_prediction.py \
        --run-id k01 --prediction <artifacts>/q01full/prediction.h5ad
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config
from vcc2026.manifest import RunManifest
from vcc2026.packaging import (
    PackagingError,
    assert_payload_matches_input,
    extracted_payload,
    inspect_layout,
    official,
    package_prediction,
    payload_transformations,
)
from vcc2026.resources import GiB, peak_rss_bytes, require, snapshot


def _sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", required=True)
    p.add_argument("--prediction", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None,
                   help="run directory (default: <artifact_root>/<run-id>)")
    p.add_argument("--vcc-name", default="prediction.vcc")
    p.add_argument("--workdir", type=Path, default=None,
                   help="where the transient payload and compressed payload go. "
                        "Defaults to the run directory. Point it at scratch "
                        "storage when the run directory has a small quota (on "
                        "Kaggle: /kaggle/temp, with the .vcc in /kaggle/working).")
    p.add_argument("--expect-sha256", default=None,
                   help="refuse to run unless the input hashes to this")
    p.add_argument("--genes", type=Path, default=None)
    p.add_argument("--perts", type=Path, default=None)
    p.add_argument("--values-per-block", type=int, default=1 << 24)
    p.add_argument("--zstd-level", type=int, default=3)
    p.add_argument("--zstd-threads", type=int, default=None,
                   help="default: the official worker count, capped at 8")
    p.add_argument("--reserve-gib", type=float, default=6.0)
    p.add_argument("--validate-only", action="store_true")
    p.add_argument("--skip-verify", action="store_true")
    p.add_argument("--allow-overwrite", action="store_true")
    args = p.parse_args()

    t0 = time.perf_counter()
    controls = config.paths().raw / "controls"
    genes = args.genes or controls / "gene_names.csv"
    perts = args.perts or controls / "pert_counts.csv"
    run = args.out or config.run_dir(args.run_id)
    run.mkdir(parents=True, exist_ok=True)
    report_path = run / "packaging.json"
    if report_path.exists() and not args.allow_overwrite:
        print(f"{report_path} exists; use a new --run-id.", file=sys.stderr)
        return 2

    prediction = args.prediction
    prep, vccfile, sizing, cli_version = official()

    print(f"input      : {prediction}")
    if not prediction.exists():
        print(f"missing input: {prediction}", file=sys.stderr)
        return 2

    # --- the input must be the file we think it is --------------------------
    print("hashing input (streamed) ...")
    t_hash = time.perf_counter()
    input_sha = _sha256(prediction)
    hash_seconds = time.perf_counter() - t_hash
    print(f"  sha256   : {input_sha}  ({hash_seconds:.0f}s)")
    if args.expect_sha256 and input_sha != args.expect_sha256:
        print(
            f"REFUSING: input hashes to {input_sha}, expected {args.expect_sha256}. "
            "The prediction is not the one this run was asked to package.",
            file=sys.stderr,
        )
        return 2

    layout = inspect_layout(prediction)
    print(f"layout     : {layout.n_obs:,} x {layout.n_vars:,}, "
          f"{layout.nnz:,} stored entries")
    print(f"             data {layout.data_dtype}"
          f"{'/' + layout.data_compression if layout.data_compression else ''}, "
          f"indices {layout.indices_dtype}, indptr {layout.indptr_dtype}")

    # --- resources: refuse before writing, not halfway through --------------
    # Peak disk is the payload plus its compressed copy; the payload is removed
    # as soon as it is compressed, so the archive never coexists with it.
    est_payload = layout.file_bytes
    # payload + its compressed copy while packaging; archive + the
    # extracted payload while verifying. Both land near 2x the input.
    est_disk = int(est_payload * 2.3)
    official_peak = sizing.prep_peak_gib(layout.nnz, casts=False, reordered=False)
    before = snapshot(run)
    print(f"resources  : RAM {before.ram_total_bytes / GiB:.2f} GiB total, "
          f"{before.ram_available_gib:.2f} GiB available; disk "
          f"{before.disk_free_gib:.2f} GiB free")
    print(f"             official vcc prep would peak at ~{official_peak:.1f} GiB; "
          f"this stage streams instead")
    print(f"             estimated transient disk {est_disk / GiB:.2f} GiB")
    if not args.validate_only:
        try:
            require(disk_bytes=est_disk, path=run,
                    reserve_bytes=int(args.reserve_gib * GiB))
        except RuntimeError as exc:
            print(f"REFUSING: {exc}", file=sys.stderr)
            return 3

    payload = {
        "run_id": args.run_id,
        "stage": "48_package_prediction",
        "input": {
            "path": str(prediction),
            "sha256": input_sha,
            "bytes": layout.file_bytes,
            "hash_seconds": hash_seconds,
        },
        "layout": layout.as_dict(),
        "official_cli_version": cli_version,
        "official_prep_peak_gib_model": official_peak,
        "transformations": payload_transformations(),
        "resources_before": before.as_dict(),
        "uploaded": False,
        "note": (
            "Local validation, packaging and verification only. Nothing was "
            "uploaded, no submission quota was consumed, and no server has "
            "accepted this artifact."
        ),
    }
    vcc_path = run / args.vcc_name
    exit_code = 0

    try:
        if args.validate_only:
            from vcc2026.packaging import validate_prediction

            print("\nvalidating (streamed) ...")
            report = validate_prediction(
                prediction, genes_path=genes, perts_path=perts,
                values_per_block=args.values_per_block,
            )
            payload["validation"] = report.as_dict()
            for name, ok in report.checks.items():
                print(f"  {'PASS' if ok else 'FAIL'}  {name}")
            for name, ok in report.csr_checks.items():
                print(f"  {'PASS' if ok else 'FAIL'}  csr:{name}")
            if not report.ok:
                for failure in report.failures:
                    print(f"  ! {failure.splitlines()[0]}", file=sys.stderr)
                exit_code = 1
            print(f"  ({report.seconds:.0f}s, peak RSS "
                  f"{(report.peak_rss_bytes or 0) / GiB:.2f} GiB)")
        else:
            print("\nvalidating and packaging (streamed) ...")
            result = package_prediction(
                prediction,
                vcc_path,
                genes_path=genes,
                perts_path=perts,
                workdir=args.workdir or run,
                temp_dir=args.workdir or run,
                values_per_block=args.values_per_block,
                zstd_level=args.zstd_level,
                zstd_threads=args.zstd_threads,
                force=args.allow_overwrite,
            )
            payload["package"] = result.as_dict()
            report = result.validation
            for name, ok in (report.checks | {f"csr:{k}": v for k, v in
                                              report.csr_checks.items()}).items():
                print(f"  {'PASS' if ok else 'FAIL'}  {name}")
            print(f"\nwrote {vcc_path.name}: "
                  f"{result.archive_bytes / GiB:.2f} GiB "
                  f"({result.seconds:.0f}s total)")
            print(f"  meta       : {json.dumps(result.meta)}")
            print(f"  peak RSS   : {(result.peak_rss_bytes or 0) / GiB:.2f} GiB")
            print(f"  peak disk  : {result.peak_disk_bytes / GiB:.2f} GiB")
    except PackagingError as exc:
        print(f"\nPACKAGING REFUSED:\n{exc}", file=sys.stderr)
        payload["error"] = str(exc)
        exit_code = 1

    # --- verify what was written, independently of what wrote it ------------
    if exit_code == 0 and not args.validate_only and not args.skip_verify:
        print("\nverifying the archive ...")
        verification: dict = {}
        try:
            vccfile.validate_vcc(str(vcc_path))
            verification["official_container_validator"] = "passed"
            print("  PASS  official container validator (vccfile.validate_vcc)")
        except Exception as exc:  # noqa: BLE001
            verification["official_container_validator"] = f"FAILED: {exc}"
            print(f"  FAIL  official container validator: {exc}", file=sys.stderr)
            exit_code = 1

        verification["meta_from_archive"] = vccfile.read_vcc_meta(str(vcc_path))
        verification["nnz_from_archive"] = vccfile.nnz_from_vcc(str(vcc_path))
        print(f"  meta read back: {json.dumps(verification['meta_from_archive'])}")

        # Compare the archive's payload against the INPUT, not against a
        # re-derived payload: re-deriving would test the writer against itself,
        # and would cost a second full-size temporary on the machine where disk
        # is the binding constraint.
        t_v = time.perf_counter()
        verify_dir = (args.workdir or run) / "verify"
        try:
            with extracted_payload(vcc_path, verify_dir) as actual:
                summary = assert_payload_matches_input(
                    prediction, actual, values_per_block=args.values_per_block
                )
                verification["payload_vs_input"] = summary
            print(f"  PASS  payload X arrays are bit-identical to the input; "
                  f"gene axis and labels match ({time.perf_counter() - t_v:.0f}s)")
            print(f"        obs index rewritten by prep's rule: "
                  f"{summary['obs_index_rewritten']}")
        except AssertionError as exc:
            verification["payload_vs_input"] = f"FAILED: {exc}"
            print(f"  FAIL  payload comparison: {exc}", file=sys.stderr)
            exit_code = 1
        finally:
            try:
                verify_dir.rmdir()
            except OSError:
                pass

        if vcc_path.exists():
            verification["archive_sha256"] = _sha256(vcc_path)
            verification["archive_bytes"] = vcc_path.stat().st_size
            print(f"  archive sha256: {verification['archive_sha256']}")
        payload["verification"] = verification

    payload["resources_after"] = snapshot(run).as_dict()
    payload["peak_rss_bytes"] = peak_rss_bytes()
    payload["total_seconds"] = time.perf_counter() - t0
    payload["exit_code"] = exit_code
    report_path.write_text(json.dumps(payload, indent=2, default=str),
                           encoding="utf-8")

    man = RunManifest(run_id=args.run_id, stage="48_package_prediction",
                      config={k: str(v) for k, v in vars(args).items()})
    man.add_input("prediction", prediction)
    man.add_input("genes", genes)
    man.add_input("perturbations", perts)
    man.add_output("report", report_path)
    if vcc_path.exists():
        man.add_output("vcc", vcc_path)
    man.metrics = {
        "exit_code": exit_code,
        "nnz": layout.nnz,
        "peak_rss_bytes": payload["peak_rss_bytes"],
        "total_seconds": payload["total_seconds"],
    }
    man.note("Streaming packager: the official validators on metadata, streamed "
             "equivalents on the matrix. Not an official CLI release.")
    man.note("Nothing uploaded. A passing archive is not server acceptance.")
    man.write(run / "manifest_48_package_prediction.json",
              allow_overwrite=args.allow_overwrite)

    print(f"\ntotal {payload['total_seconds']:.0f}s, peak RSS "
          f"{(payload['peak_rss_bytes'] or 0) / GiB:.2f} GiB")
    print(f"-> {report_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
