"""Run one R-LAB ingestion job (P2): adapter blocks become contract shards, published one at a time.

The job spec (JSON) lists units, one per study, channel or screen; each names an adapter of
`adapters.py`, its arguments and the source files with locator, bytes and sha256 (already checked
by the preflight on this runtime). For every block of cells the runner:

1. writes the shard once on the runtime's local disk (`--stage`), gzip-compressed;
2. re-reads the sum of X from the written file and adds it to `uns/parity/sum_after`, in place;
3. runs `contracts.validate_shard`; any problem stops the job;
4. copies the shard to `--out` (Drive) under a temporary name, renames it, and hashes the copy;
5. writes the shard's receipt, then deletes the local file.

A lost runtime keeps every shard already published with its receipt; `--reuse <earlier out>` lets a
new attempt skip those whose receipt and hash still match. After each unit the runner checks the
parity its adapter makes possible and writes the unit manifest; `complete.json` is written last and
only if every unit passed. Nothing is written over: the out and stage directories must be new.

    python rlab_job.py --spec job_spec.json --stage /content/work/<job>/stage --out <Drive dir> \
        --runtime-manifest <env manifest> [--reuse <earlier out>] [--max-cells N] [--set KEY=VALUE ...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adapters  # noqa: E402
from contracts import CONTRACT_VERSION, OBS_REQUIRED, validate_shard  # noqa: E402


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def dump_new(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False, default=lambda v: v.item() if hasattr(v, "item") else str(v))


def expand(value, table: dict):
    if isinstance(value, str):
        for key, sub in table.items():
            value = value.replace("{" + key + "}", sub)
        return value
    if isinstance(value, dict):
        return {k: expand(v, table) for k, v in value.items()}
    if isinstance(value, list):
        return [expand(v, table) for v in value]
    return value


def write_elem():
    try:
        from anndata.io import write_elem as fn
    except ImportError:
        from anndata.experimental import write_elem as fn
    return fn


def write_local(x, obs, var, uns: dict, path: Path, obsm: dict | None = None) -> tuple[list[str], dict]:
    """One write, a re-read of the counts from the file, the parity added in place, the contract.

    `obsm` carries per-cell raw side matrices the source publishes (guide or hash UMIs)."""
    import anndata as ad
    import h5py
    import scipy.sparse as sp
    x = sp.csr_matrix(x)
    if x.data.size and not np.all(np.equal(np.mod(x.data, 1), 0)):
        return ["X is not integer counts"], {}
    x = x.astype(np.int32)
    missing = sorted(set(OBS_REQUIRED) - set(obs.columns))
    if missing:
        return [f"obs lacks {missing}"], {}
    before = int(x.sum(dtype=np.int64))
    uns = {**uns, "contract_version": CONTRACT_VERSION,
           "parity": {"sum_before": before, "cells": int(x.shape[0]), "nnz": int(x.nnz)}}
    ad.AnnData(X=x, obs=obs, var=var, uns=uns, obsm=obsm or None).write_h5ad(path, compression="gzip")
    after, nnz = 0, 0
    with h5py.File(path, "r") as f:
        data = f["X"]["data"]
        for i in range(0, data.shape[0], 50_000_000):
            block = data[i:i + 50_000_000]
            after += int(block.sum(dtype=np.int64))
            nnz += block.size
    with h5py.File(path, "r+") as f:
        write_elem()(f["uns"]["parity"], "sum_after", after)
    problems = validate_shard(path)
    if after != before or nnz != x.nnz:
        problems.append(f"re-read differs: sum {after} vs {before}, nnz {nnz} vs {x.nnz}")
    info = {"cells": int(x.shape[0]), "nnz": int(x.nnz), "sum_before": before, "sum_after": after,
            "targets": int(obs["target"].nunique()),
            "control_kind": dict(Counter(obs["control_kind"].astype(str)))}
    return problems, info


def reusable(reuse: list[Path] | None, unit: str, name: str) -> dict | None:
    """The first earlier attempt (in the order given) holding this shard with a receipt whose size and sha256 match."""
    for earlier in reuse or []:
        receipt = earlier / unit / "receipts" / f"{name}.json"
        shard = earlier / unit / f"{name}.h5ad"
        if not (receipt.is_file() and shard.is_file()):
            continue
        old = json.loads(receipt.read_text(encoding="utf-8"))
        if shard.stat().st_size != old.get("bytes") or sha256(shard) != old.get("sha256"):
            continue
        return {**old, "reused_from": str(shard)}
    return None


def parity(adapter: str, shards: list[dict], uns_seen: list[dict], expect: dict, max_cells) -> dict:
    """The check each adapter makes possible, beyond the per-shard re-read."""
    out = {"per_shard_reread": all(s["sum_after"] == s["sum_before"] for s in shards)}
    cells = sum(s["cells"] for s in shards)
    out["cells"] = cells
    ranges = sorted(tuple(int(v) for v in u["rows"]["range"].split(":")) for u in uns_seen if "range" in u.get("rows", {}))
    if ranges and adapter != "h5rows":
        out["contiguous_from_zero"] = ranges[0][0] == 0 and all(a[1] == b[0] for a, b in zip(ranges, ranges[1:]))
    if adapter == "h5rows" and max_cells is None:
        lo, hi = expect.get("rows", [0, uns_seen[0]["rows"]["of"]])
        out["covers_declared_rows"] = (ranges[0][0] == lo and ranges[-1][1] == hi
                                       and all(a[1] == b[0] for a, b in zip(ranges, ranges[1:])))
        out["cells_equal_declared"] = cells == hi - lo
    if max_cells is not None:
        out["note"] = f"smoke test on the first {max_cells} cells: source-level parity not applicable"
        out["ok"] = out["per_shard_reread"]
        return out
    if adapter == "h5ad":
        of = uns_seen[0]["rows"]["of"]
        out["all_cells_of_file"] = cells == of and ranges[-1][1] == of
        if "cells" in expect:
            out["expected_cells"] = cells == expect["cells"]
    elif adapter in ("hipsci", "h5csc_shards"):
        by_pass: dict[str, list] = {}
        for s, u in zip(shards, uns_seen):
            by_pass.setdefault(u["read"]["pass_range"], [u["read"]["pass_sum_before"], 0])[1] += s["sum_after"]
        out["passes"] = {k: {"parsed": v[0], "in_shards": v[1], "equal": v[0] == v[1]} for k, v in by_pass.items()}
        out["parsed_sum_equals_shards"] = all(v["equal"] for v in out["passes"].values())
        of = uns_seen[0]["rows"]["of"]
        out["all_cells_of_file"] = cells == of and ranges[-1][1] == of
    elif adapter == "mtx10x":
        src = uns_seen[0]["parity_source"]
        kept = sum(s["sum_after"] for s in shards)
        out["matrix_total"] = src["matrix_total"]
        out["kept_plus_ambient"] = kept + src["ambient_umi"]
        out["kept_plus_ambient_equals_matrix"] = abs(out["kept_plus_ambient"] - src["matrix_total"]) < 0.5
        out["all_kept_barcodes"] = cells == uns_seen[0]["rows"]["barcodes_kept"]
    checks = [v for k, v in out.items() if isinstance(v, bool)]
    out["ok"] = all(checks)
    return out


def run_unit(unit: dict, spec: dict, args, table: dict, writer: dict) -> dict:
    name = unit["name"]
    udir = args.out / name
    udir.mkdir()
    stage = args.stage / name
    stage.mkdir(parents=True)
    kwargs = expand(unit["kwargs"], table)
    if args.max_cells is not None:
        kwargs["max_cells"] = args.max_cells
    fn = getattr(adapters, unit["adapter"])
    shards, uns_seen, t0 = [], [], time.time()
    source = {"id": unit["source"]["id"], "release": unit["source"].get("release", "as published"),
              "locator": unit["source"]["files"][0]["locator"], "bytes": unit["source"]["files"][0]["bytes"],
              "sha256": unit["source"]["files"][0].get("sha256", "not recomputed: read by ranges, see md5 or crc32c"),
              "md5": unit["source"]["files"][0].get("md5", "MISSING"),
              "crc32c": unit["source"]["files"][0].get("crc32c", "MISSING"),
              "files_json": json.dumps(unit["source"]["files"]), "license": unit["source"].get("license", "MISSING")}
    for shard_name, x, obs, var, uns in fn(**kwargs):
        uns_seen.append({k: v for k, v in uns.items() if k in ("rows", "read", "parity_source")})
        old = reusable(args.reuse, name, shard_name)
        if old is not None:
            shards.append(old)
            print(f"{name}/{shard_name}: reused from {old['reused_from']}", flush=True)
            continue
        free = shutil.disk_usage(args.stage).free
        if free < spec.get("min_free_stage_bytes", 4 << 30):
            sys.exit(f"stopping: {free} bytes free on the stage disk")
        obsm = uns.pop("_obsm", None)
        uns = {**uns, "source": source, "qc_version": "none", "writer": writer}
        local = stage / f"{shard_name}.h5ad"
        problems, info = write_local(x, obs, var, uns, local, obsm)
        if problems:
            dump_new(udir / "receipts" / f"{shard_name}.FAILED.json", {"problems": problems, "utc": now()})
            sys.exit(f"{name}/{shard_name}: contract problems {problems}")
        digest = sha256(local)
        dest, tmp = udir / f"{shard_name}.h5ad", udir / f"{shard_name}.h5ad.partial"
        shutil.copyfile(local, tmp)
        os.replace(tmp, dest)
        copy_digest = sha256(dest)
        if copy_digest != digest:
            sys.exit(f"{name}/{shard_name}: the copy on the out disk hashes {copy_digest}, the local file {digest}")
        receipt = {**info, "shard": shard_name, "path": str(dest), "bytes": dest.stat().st_size, "sha256": digest,
                   "copy_sha256_reread": copy_digest, "rows": uns.get("rows"), "utc": now()}
        dump_new(udir / "receipts" / f"{shard_name}.json", receipt)
        local.unlink()
        shards.append(receipt)
        print(f"{name}/{shard_name}: {info['cells']} cells, {info['nnz']} nnz, {receipt['bytes']} bytes, "
              f"{time.time() - t0:.0f}s", flush=True)
    check = parity(unit["adapter"], shards, uns_seen, unit.get("expect", {}), args.max_cells)
    manifest = {"unit": name, "adapter": unit["adapter"], "kwargs": kwargs, "source": unit["source"],
                "shards": [{k: s.get(k) for k in ("shard", "path", "bytes", "sha256", "cells", "nnz", "sum_after",
                                                  "targets", "control_kind", "reused_from")} for s in shards],
                "totals": {"shards": len(shards), "cells": sum(s["cells"] for s in shards),
                           "nnz": sum(s["nnz"] for s in shards), "counts": sum(s["sum_after"] for s in shards),
                           "bytes": sum(s["bytes"] for s in shards),
                           "control_kind": dict(sum((Counter(s["control_kind"]) for s in shards), Counter()))},
                "parity": check, "seconds": round(time.time() - t0, 1), "utc": now()}
    dump_new(udir / "manifest.json", manifest)
    stage.rmdir()
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--spec", required=True, type=Path)
    p.add_argument("--stage", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--runtime-manifest", type=Path)
    p.add_argument("--reuse", type=Path, nargs="+", help="earlier attempts, searched in this order")
    p.add_argument("--max-cells", type=int)
    p.add_argument("--set", nargs="*", default=[], help="KEY=VALUE replacing {KEY} in the unit arguments")
    args = p.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    table = dict(kv.split("=", 1) for kv in args.set)
    for path in (args.out, args.stage):
        if path.exists():
            sys.exit(f"refusing: {path} exists")
    need = spec.get("min_free_out_bytes", 0)
    probe = args.out.parent
    while not probe.exists():
        probe = probe.parent
    free = shutil.disk_usage(probe).free
    if free < need:
        sys.exit(f"refusing: {free} bytes free where the shards go, the job asks for {need}")
    args.out.mkdir(parents=True)
    args.stage.mkdir(parents=True)
    writer = {"script": "rlab_job.py", "script_sha256": sha256(Path(__file__)),
              "adapters_sha256": sha256(HERE / "adapters.py"), "contracts_sha256": sha256(HERE / "contracts.py"),
              "snapshot_sha256": os.environ.get("RLAB_SNAPSHOT_SHA256", "MISSING"),
              "commit": os.environ.get("RLAB_COMMIT", "MISSING"),
              "runtime_manifest": str(args.runtime_manifest) if args.runtime_manifest else "MISSING",
              "runtime_manifest_sha256": sha256(args.runtime_manifest) if args.runtime_manifest else "MISSING"}
    started = {"job_id": spec["job_id"], "spec_sha256": sha256(args.spec), "writer": writer, "out_free_bytes": free,
               "min_free_out_bytes": need, "max_cells": args.max_cells,
               "reuse": [str(r) for r in args.reuse] if args.reuse else None, "utc": now()}
    dump_new(args.out / "job_started.json", started)
    units = [run_unit(u, spec, args, table, writer) for u in spec["units"]]
    ok = all(u["parity"]["ok"] for u in units)
    dump_new(args.out / "complete.json" if ok else args.out / "parity_failed.json",
             {"job_id": spec["job_id"], "status": "complete" if ok else "parity_failed",
              "units": {u["unit"]: {"cells": u["totals"]["cells"], "shards": u["totals"]["shards"],
                                    "bytes": u["totals"]["bytes"], "parity_ok": u["parity"]["ok"],
                                    "manifest_sha256": sha256(args.out / u["unit"] / "manifest.json")} for u in units},
              "utc": now()})
    shutil.rmtree(args.stage, ignore_errors=True)
    print("complete" if ok else "PARITY FAILED", flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
