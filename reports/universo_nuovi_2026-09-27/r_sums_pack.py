"""Pack R's little-endian, row-major group sums into the memory-mappable sums archive.

    python r_sums_pack.py --dir R_OUTPUT --out NEW_FOLDER/sums.npz [--axis axis.csv]
    python r_sums_pack.py --selftest

The default axis is the project's official axis; an explicit CSV has one column and
a header. Duplicate input symbols use their first column. pack.json records provenance
and mapping counts. Both final names must be new. Temporary disk space is approximately
twice the output matrix size. Inputs must remain unchanged during packing.

Matrix mappings are closed between blocks, including output mappings: a whole-file
memmap alone would not bound resident memory. Metadata is limited to 16 MiB in total
(oversized metadata is rejected), with at most 250,000 groups or input/axis genes
and 32 MiB per fixed-width string array, and matrix buffers to tens of MiB, leaving
headroom below 1.5 GB independently of binary size. No effects dependencies are imported
in a normal pack run.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
METADATA_BYTES = 16 << 20
BLOCK_BYTES = 32 << 20
MAX_ENTRIES = 250_000


def string_array(values: list) -> np.ndarray:
    """Bound NumPy's fixed-width Unicode expansion before allocating it."""
    if len(values) * max(map(len, values), default=0) * 4 > 32 << 20:
        raise ValueError("fixed-width string array exceeds the 32 MiB memory-safety limit")
    return np.asarray(values, dtype=str)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(1 << 20):
            h.update(block)
    return h.hexdigest()


def read_axis(path: Path | None) -> np.ndarray:
    if path is None:
        from vcc2026.genes import official_axis
        symbols = list(official_axis().symbols)
    else:
        with path.open(newline="", encoding="utf-8-sig") as f:
            rows = csv.reader(f)
            header = next(rows, [])
            if len(header) != 1:
                raise ValueError("axis CSV must have a one-column header")
            symbols = []
            for row in rows:
                if len(symbols) >= MAX_ENTRIES:
                    raise ValueError("axis exceeds the 250,000-entry memory-safety limit")
                if len(row) != 1:
                    raise ValueError("axis CSV must have exactly one column")
                symbols.append(row[0])
    if not symbols or any(not s.strip() for s in symbols) or len(set(symbols)) != len(symbols):
        raise ValueError("axis must contain nonempty, unique symbols")
    return string_array(symbols)


def read_groups(path: Path) -> dict:
    values = {k: [] for k in ("target", "pool", "n_cells", "total_counts")}
    seen = set()
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = csv.DictReader(f)
        if not rows.fieldnames or not {"group", *values}.issubset(rows.fieldnames):
            raise ValueError("groups.csv lacks required columns")
        if len(set(rows.fieldnames)) != len(rows.fieldnames):
            raise ValueError("groups.csv repeats a column name")
        for i, row in enumerate(rows):
            if i >= MAX_ENTRIES:
                raise ValueError("groups exceed the 250,000-entry memory-safety limit")
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"malformed CSV row {i}")
            group, pool, cells = (int(row[k]) for k in ("group", "pool", "n_cells"))
            target, total = row["target"], float(row["total_counts"])
            if group != i:
                raise ValueError("group ids must be 0..n-1 in row order")
            if not target.strip() or not 0 <= pool < 8 or not 1 <= cells <= np.iinfo(np.int64).max:
                raise ValueError(f"group {i}: empty target, invalid pool or n_cells")
            if not np.isfinite(total) or total <= 0:
                raise ValueError(f"group {i}: total_counts must be finite and positive")
            if (target, pool) in seen:
                raise ValueError(f"duplicate (target, pool): {(target, pool)}")
            seen.add((target, pool))
            for key, value in zip(values, (target, pool, cells, total)):
                values[key].append(value)
    # NTC is one distinct target, potentially represented in all eight pools.
    if "NTC" not in values["target"]:
        raise ValueError("exactly one control target named NTC is required")
    return {k: string_array(v) if k == "target" else np.asarray(v, dtype=np.float64 if k == "total_counts"
                                                             else np.int64) for k, v in values.items()}


def publish(path: Path, arrays: dict, matrix: Path) -> None:
    """Stream an uncompressed ZIP64 archive, mirroring kolf_sums._publish.

    Linking the completed temporary file is atomic and refuses an existing destination
    on POSIX as well as Windows (rename alone can overwrite on POSIX).
    """
    with tempfile.TemporaryDirectory(prefix=".r-publish-", dir=path.parent) as tmp:
        partial = Path(tmp) / "partial.npz"
        with zipfile.ZipFile(partial, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as z:
            for name, value in arrays.items():
                with z.open(name + ".npy", "w", force_zip64=True) as dst:
                    np.lib.format.write_array(dst, np.asarray(value), allow_pickle=False)
            with matrix.open("rb") as src, z.open("sums.npy", "w", force_zip64=True) as dst:
                shutil.copyfileobj(src, dst, length=8 << 20)
        os.link(partial, path)


def pack(directory: Path, out: Path, axis_path: Path | None = None) -> dict:
    directory, out = Path(directory), Path(out)
    report = out.parent / "pack.json"
    if out.suffix.lower() != ".npz":
        raise ValueError("--out must end in .npz")
    for path in (out, report):
        if os.path.lexists(path):
            raise FileExistsError(path)
    paths = {name: directory / name for name in ("sums_f32.bin", "groups.csv", "genes.txt", "manifest.json")}
    metadata = [p for name, p in paths.items() if name != "sums_f32.bin"]
    if axis_path is not None:
        metadata.append(Path(axis_path))
    if sum(p.stat().st_size for p in metadata) > METADATA_BYTES:
        raise ValueError("metadata exceeds the 16 MiB memory-safety limit")
    inputs = {name: {"path": str(p.resolve()), "bytes": p.stat().st_size} for name, p in paths.items()}
    for name in ("groups.csv", "genes.txt", "manifest.json"):
        inputs[name]["sha256"] = sha256_file(paths[name])
    manifest = json.loads(paths["manifest.json"].read_text(encoding="utf-8-sig"))
    if not isinstance(manifest, dict) or any(not isinstance(manifest.get(k), str) or not manifest[k].strip()
                                             for k in ("url", "layout")):
        raise ValueError("manifest must contain nonempty url and layout strings")
    # There is no prescribed spelling for layout; record it verbatim. The binary
    # contract of this CLI is always little-endian float32, groups x genes, C order.
    axis = read_axis(axis_path)
    table = read_groups(paths["groups.csv"])
    lookup, duplicates, unmapped = {}, 0, 0
    axis_set = set(axis)
    with paths["genes.txt"].open(encoding="utf-8-sig") as f:
        for i, line in enumerate(f):
            if i >= MAX_ENTRIES:
                raise ValueError("input genes exceed the 250,000-entry memory-safety limit")
            symbol = line.rstrip("\r\n")
            if not symbol.strip():
                raise ValueError("genes.txt contains an empty symbol")
            duplicates += int(symbol in lookup)
            unmapped += int(symbol not in axis_set)
            lookup.setdefault(symbol, i)
    n_genes = len(lookup) + duplicates
    ng, na = len(table["target"]), len(axis)
    if n_genes == 0 or inputs["sums_f32.bin"]["bytes"] != ng * n_genes * 4:
        raise ValueError("binary size differs from n_groups * n_genes * 4 (or genes.txt is empty)")
    columns = np.asarray([lookup.get(g, -1) for g in axis], dtype=np.int64)
    present = np.flatnonzero(columns >= 0)
    if not present.size:
        raise ValueError("no input gene maps to the axis")
    keys = [f"{t}|{p}" for t, p in zip(table["target"], table["pool"])]
    digest = hashlib.sha256(json.dumps([keys, table["n_cells"].tolist()]).encode()).hexdigest()
    table.update(genes=axis, file_columns=columns, missing_genes=axis[columns < 0],
                 groups_sha256=digest, url=manifest["url"])
    result = dict(inputs=inputs, layout=manifest["layout"], binary_layout="little-endian float32 row-major",
                  groups=ng, targets=len(set(table["target"])) - 1, targets_including_ntc=len(set(table["target"])),
                  input_genes=n_genes, axis_genes=na, mapped_genes=int(present.size),
                  unmapped_genes=unmapped, duplicate_genes=duplicates, missing_genes=int((columns < 0).sum()),
                  gene_count_semantics="mapped: selected unique columns; unmapped: input occurrences absent "
                                       "from axis; duplicate: occurrences after first (may overlap unmapped)",
                  groups_sha256=digest, url=manifest["url"],
                  ntc_cells_per_pool={str(p): sum(int(n) for t, q, n in
                      zip(table["target"], table["pool"], table["n_cells"]) if t == "NTC" and q == p)
                      for p in range(8)})
    if axis_path is not None:
        result["axis_input"] = dict(path=str(Path(axis_path).resolve()),
                                    bytes=Path(axis_path).stat().st_size, sha256=sha256_file(Path(axis_path)))
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".r-pack-", dir=out.parent) as tmp:
        matrix = Path(tmp) / "sums.npy"
        mm = np.lib.format.open_memmap(matrix, mode="w+", dtype="<f4", shape=(ng, na), fortran_order=True)
        offset = mm.offset
        mm._mmap.close()
        del mm
        rows_per_block = max(1, min(4096, BLOCK_BYTES // (4 * max(n_genes, na))))
        for a in range(0, ng, rows_per_block):
            b = min(ng, a + rows_per_block)
            src = np.memmap(paths["sums_f32.bin"], mode="r", dtype="<f4", offset=4 * a * n_genes,
                            shape=(b - a, n_genes), order="C")
            try:
                if not np.isfinite(src).all() or (src < 0).any():
                    raise ValueError(f"groups {a}..{b - 1}: negative or nonfinite input counts")
                selected = np.asarray(src[:, columns[present]])
                totals = selected.sum(axis=1, dtype=np.float64)
                bad = np.flatnonzero(totals > table["total_counts"][a:b])
                if bad.size:
                    raise ValueError(f"group {a + int(bad[0])}: axis counts exceed total_counts")
                # Map only each contiguous row slice of a Fortran column, then unmap.
                # Never touch a whole-file output mapping: RSS would grow with the file.
                j = 0
                for col in range(na):
                    dst = np.memmap(matrix, mode="r+", dtype="<f4", offset=offset + 4 * (col * ng + a),
                                    shape=(b - a,))
                    try:
                        if columns[col] >= 0:
                            dst[:] = selected[:, j]
                            j += 1
                        else:
                            dst[:] = np.nan
                    finally:
                        dst._mmap.close()
                del selected
            finally:
                src._mmap.close()
        for name in ("groups.csv", "genes.txt", "manifest.json"):
            if sha256_file(paths[name]) != inputs[name]["sha256"]:
                raise ValueError(f"input changed while packing: {name}")
        report_tmp = Path(tmp) / "pack.json"
        report_tmp.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        # Reserve the shared report name before publishing. On interruption it remains
        # evidence of an incomplete attempt; choose a new destination for a retry.
        os.link(report_tmp, report)
        publish(out, table, matrix)
    print(f"packed {ng} groups, {result['targets']} targets + NTC; {present.size} mapped, "
          f"{unmapped} unmapped, {duplicates} duplicate input genes -> {out}", flush=True)
    return result


def selftest() -> int:
    sys.path.insert(0, str(HERE.parent / "universo_kolf_2026-09-27"))
    import kolf_effects

    results = []

    def check(name: str, ok: bool) -> None:
        results.append(bool(ok))
        print(f"{'PASS' if ok else 'FAIL'} {name}", flush=True)

    try:
        with tempfile.TemporaryDirectory(prefix=".r-pack-test-", dir=HERE) as tmp:
            root = Path(tmp)
            source = root / "input"
            source.mkdir()
            axis = root / "axis.csv"
            axis.write_text("gene\nB\nABSENT\nA\nC\n", encoding="utf-8")
            (source / "genes.txt").write_text("A\nB\nA\nOFF\nC\n", encoding="utf-8")
            (source / "manifest.json").write_text(json.dumps(dict(url="synthetic:R", layout="row-major")))
            raw = np.asarray([[100 + i, 200 + 2*i, 900 + i, 300, 400 + 3*i] for i in range(16)], dtype="<f4")
            raw.tofile(source / "sums_f32.bin")
            rows = [[i, "NTC" if i < 8 else "T_TEST", i % 8, 30, float(raw[i].sum())] for i in range(16)]

            def groups(data: list) -> None:
                with (source / "groups.csv").open("w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["group", "target", "pool", "n_cells", "total_counts"])
                    writer.writerows(data)

            groups(rows)
            out = root / "packed" / "sums.npz"
            # Force multiple group blocks even on this small fixture.
            global BLOCK_BYTES
            previous = BLOCK_BYTES
            BLOCK_BYTES = 60
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    report = pack(source, out, axis)
            finally:
                BLOCK_BYTES = previous
            s = kolf_effects.Sums(out)
            wanted = np.column_stack([raw[:, 1], np.full(16, np.nan), raw[:, 0], raw[:, 4]])
            got = s.gather(np.arange(16), np.arange(4), window=2)
            check("Sums reader: every value, axis order, first duplicate and missing NaNs",
                  np.array_equal(got, wanted, equal_nan=True))
            on_axis, whole, digest = s.scan(window=2)
            check("Sums scan: valid counts and archive checksum",
                  whole and np.array_equal(on_axis, np.nansum(wanted, axis=1)) and digest == sha256_file(out))
            check("provenance and mapping counts", report["mapped_genes"] == 3 and report["unmapped_genes"] == 1
                  and report["duplicate_genes"] == 1 and report["ntc_cells_per_pool"] == {str(i): 30 for i in range(8)}
                  and report["inputs"]["groups.csv"]["sha256"] == sha256_file(source / "groups.csv")
                  and json.loads((out.parent / "pack.json").read_text()) == report)
            with contextlib.redirect_stdout(io.StringIO()):
                run = kolf_effects.run(out, root / "effects", official=False, name="r_fixture", window=2)
            with np.load(root / "effects" / run["chunks"][0]["file"]) as z:
                check("effects run: r_fixture target row with enough cells",
                      z["targets"].tolist() == ["T_TEST"] and z["n_cells"].tolist() == [240]
                      and np.isfinite(z["raw"][0, [0, 2, 3]]).all() and np.isnan(z["raw"][0, 1]))
            before = sha256_file(out)
            try:
                pack(source, out, axis)
                refused = False
            except FileExistsError:
                refused = True
            check("never overwrite archive", refused and before == sha256_file(out))
            try:
                pack(source, out.with_name("another.npz"), axis)
                refused = False
            except FileExistsError:
                refused = True
            check("never overwrite pack.json", refused and not out.with_name("another.npz").exists())
            for label, column, value in [("group order", 0, 2), ("pool range", 2, 8),
                                         ("nonpositive cells", 3, 0), ("nonpositive totals", 4, 0),
                                         ("axis exceeds total", 4, 1), ("nonfinite totals", 4, float("nan"))]:
                changed = [r.copy() for r in rows]
                changed[0][column] = value
                groups(changed)
                destination = root / label.replace(" ", "_") / "sums.npz"
                try:
                    pack(source, destination, axis)
                    refused = False
                except ValueError:
                    refused = True
                check(f"reject {label}", refused and not destination.exists())
            for label, changed in [("duplicate group", [r.copy() for r in rows]),
                                    ("missing NTC", [[r[0], "CTRL" if r[1] == "NTC" else r[1], *r[2:]] for r in rows])]:
                if label == "duplicate group":
                    changed[1][2] = 0
                groups(changed)
                try:
                    pack(source, root / label / "sums.npz", axis)
                    refused = False
                except ValueError:
                    refused = True
                check(f"reject {label}", refused)
            groups(rows)
            with (source / "sums_f32.bin").open("ab") as f:
                f.write(b"x")
            try:
                pack(source, root / "bad_size" / "sums.npz", axis)
                refused = False
            except ValueError:
                refused = True
            check("reject binary size", refused)
    except Exception as err:
        check(f"unexpected {type(err).__name__}: {err}", False)
    failed = results.count(False)
    print(f"selftest: {len(results) - failed} of {len(results)} checks passed", flush=True)
    return int(bool(failed))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", type=Path, help="R output folder")
    ap.add_argument("--out", type=Path, help="NEW .npz file; its sibling pack.json must also be new")
    ap.add_argument("--axis", type=Path, help="one-column CSV with header; default: official axis")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    if args.dir is None or args.out is None:
        ap.error("--dir and --out are required, or --selftest")
    pack(args.dir, args.out, args.axis)


if __name__ == "__main__":
    main()
