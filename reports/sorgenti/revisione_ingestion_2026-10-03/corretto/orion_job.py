"""Orion (X-Atlas, HCT116 and HEK293T) cells into contract shards, from the original parquet files, in three phases.

    meta    per GEM file, only the identity and guide columns (gene_target, pass_guide_filter, sample) by HTTP byte
            ranges; no count is read. Checked against the pass of 26/09 (rows, non-targeting cells per line).
    sample  campionamento_v2.select_orion on that table; written and hashed BEFORE any count is read.
    shards  per GEM file: whole file to the runtime disk (size and LFS sha256 of the frozen list), selected rows on the
            native token axis as integer CSR, every scalar column of the source kept as `orion_<name>`, one shard per
            GEM file, file deleted. A finished GEM file of an earlier attempt (--reuse) is not downloaded again.

The file list is the one frozen on 26/09 (`universo_2026-09-26/orion_<line>/manifest.json`, bytes and sha256 per
file): a file that changed on the host fails its checksum instead of being mixed in. The axis reconciliation is the
existing one (stage 102 / orion_universe.token_columns): tokens matched to the official axis by name, the first of
several tokens with one name keeps it; later ones are marked ambiguous and never summed.

    python orion_job.py meta   --spec specs/orion_v2.json --line HCT116 --out <new dir>
    python orion_job.py sample --spec specs/orion_v2.json --line HCT116 --meta <meta dir> --out <new dir>
    python orion_job.py shards --spec specs/orion_v2.json --line HCT116 --sample <sample dir> --axis gene_names.csv \
        --stage <local dir> --out <new dir> --data-root <Drive data root> [--reuse <earlier out> ...] [--max-files N]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import campionamento_v2 as cv  # noqa: E402
import common  # noqa: E402

NTC_LABEL = "Non-Targeting"
DESIGN_COLS = ["gene_target", "pass_guide_filter", "sample"]
LIST_COLS = ["gene_token_id", "gene_expression"]


def checked_table(root: Path, line: str, hash_field: str, *, require_parity: bool = False):
    """Bind a table to its phase receipt; a failed metadata pass cannot feed sampling."""
    digest = common.check_sidecar(root / f"{line}.parquet")
    receipt = common.load_json(root / f"{line}.json")
    if receipt.get("line") != line or receipt.get(hash_field) != digest:
        raise ValueError("table and phase receipt do not match")
    if require_parity and (receipt.get("ok") is not True or not receipt.get("parity")
                           or any(v is not True for v in receipt["parity"].values())):
        raise ValueError("metadata parity did not pass")
    return digest, receipt


def reuse_fingerprint(spec: dict, line: str, axis: Path, sample_sha: str) -> str:
    """Bind reused shards to counts, gene mapping, selection, spec and conversion code."""
    record = {"spec": spec, "line": line, "sample_sha256": sample_sha,
              "axis_sha256": common.sha256_file(axis),
              "files_manifest_sha256": common.sha256_file(common.REPO / spec["lines"][line]["files_manifest"]),
              "code": {p.name: common.sha256_file(p) for p in
                       (Path(__file__), HERE / "common.py", HERE / "campionamento_v2.py",
                        common.CORPUS / "adapters.py", common.CORPUS / "contracts.py",
                        common.CORPUS / "rlab_job.py")}}
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def frozen_files(spec: dict, line: str) -> list[dict]:
    doc = common.load_json(common.REPO / spec["lines"][line]["files_manifest"])
    files = [f for f in doc["files"] if "path" in f and "sha256" in f]
    if len(files) != spec["lines"][line]["expected"]["files"]:
        sys.exit(f"{line}: {len(files)} files in the frozen list, the spec expects another number")
    return files


def token_axis(tokens: pd.DataFrame, axis_csv: Path | None) -> pd.DataFrame:
    """var of the native token axis with its mapping to the official axis (first token of a name keeps it)."""
    n = int(tokens["gene_token_id"].max()) + 1
    names = tokens.set_index("gene_token_id").reindex(range(n))["gene_name"].fillna("").astype(str).to_numpy()
    axis = []
    if axis_csv:
        axis = [l.strip().split(",")[0] for l in Path(axis_csv).read_text(encoding="utf-8").splitlines()[1:] if l.strip()]
    where = {g: i for i, g in reversed(list(enumerate(axis)))}
    seen, dup, official, mapping = {}, np.zeros(n, int), np.full(n, -1), []
    for i, s in enumerate(names):
        dup[i] = seen.get(s, 0)
        seen[s] = dup[i] + 1
        if s and dup[i] == 0 and s in where:
            official[i] = where[s]
        mapping.append("unique" if official[i] >= 0 else ("ambiguous" if s in where else "none"))
    hit = official[official >= 0]
    if np.unique(hit).size != hit.size:
        raise ValueError("two gene tokens map to one axis gene")
    return pd.DataFrame({"feature_id": [f"orion_token_{i}" for i in range(n)], "symbol": names,
                         "feature_type": "Gene Expression", "measured": names != "", "official_index": official,
                         "mapping": mapping, "symbol_duplicate_rank": dup}, index=[f"f{i}" for i in range(n)])


def phase_meta(spec: dict, line: str, out: Path) -> None:
    import pyarrow.parquet as pq  # noqa: PLC0415
    _, _, _, inspect_remote = common.corpus()
    common.new_dir(out)
    frames, per_file, schema = [], [], None
    for f in frozen_files(spec, line):
        fh = inspect_remote.RangeFile(spec["source"]["base"] + f["path"], block=1 << 20)
        if fh.size != f["bytes"]:
            sys.exit(f"{f['name']}: {fh.size} bytes on the host, {f['bytes']} in the frozen list")
        pf = pq.ParquetFile(fh, pre_buffer=False)
        schema = schema or [(x.name, str(x.type)) for x in pf.schema_arrow]
        t = pf.read(columns=DESIGN_COLS).to_pandas()
        t.insert(0, "row", np.arange(len(t)))
        t.insert(0, "gem_file", f["name"])
        frames.append(t)
        per_file.append({"file": f["name"], "rows": int(len(t)), "fetched_bytes": int(fh.fetched), "etag": fh.etag,
                         "ntc": int((t["gene_target"] == NTC_LABEL).sum())})
        print(f"{f['name']}: {len(t)} rows, {fh.fetched} bytes read", flush=True)
    obs = pd.concat(frames, ignore_index=True)
    obs.to_parquet(out / f"{line}.parquet", index=False)
    digest = common.write_sidecar(out / f"{line}.parquet")
    ok = obs["pass_guide_filter"] == 1
    exp = spec["lines"][line]["expected"]
    got = {"rows": int(len(obs)), "cells_pass_filter": int(ok.sum()),
           "ntc_cells": int((ok & (obs["gene_target"] == NTC_LABEL)).sum()),
           "targets_with_cells": int(obs.loc[ok & (obs["gene_target"] != NTC_LABEL), "gene_target"].nunique())}
    parity = {k: got[k] == exp[k] for k in got if k in exp}
    common.dump_new(out / f"{line}.json", {"line": line, "table_sha256": digest, "schema": schema, "measured": got,
                                           "expected_26_09": exp, "parity": parity, "ok": all(parity.values()),
                                           "files": per_file, "utc": common.now()})
    if not all(parity.values()):
        sys.exit(f"{line}: the metadata pass differs from the pass of 26/09: {parity}")


def phase_sample(spec: dict, line: str, meta: Path, out: Path) -> None:
    table_sha, _ = checked_table(meta, line, "table_sha256", require_parity=True)
    common.new_dir(out)
    obs = pd.read_parquet(meta / f"{line}.parquet")
    d = spec["design"]
    frame = pd.DataFrame({"gem_file": obs["gem_file"].values, "target": obs["gene_target"].astype(str).values,
                          "pass_guide_filter": obs["pass_guide_filter"].values,
                          "is_control": (obs["gene_target"] == NTC_LABEL).values},
                         index=obs["gem_file"].astype(str) + ":" + obs["row"].astype(str))
    s = cv.select_orion(frame, line, d["salt"], d["k"], d["name"], tuple(d["window"]) if d.get("window") else None)
    s.to_parquet(out / f"{line}.parquet", index=False)
    digest = common.write_sidecar(out / f"{line}.parquet")
    common.dump_new(out / f"{line}.json", {"line": line, "sample_sha256": digest, "meta_table_sha256": table_sha,
                                           "design": d, **cv.summary(s), "utc": common.now()})
    print(f"{line}: sample {digest}", flush=True)


def read_selected(parquet: Path, rows: np.ndarray, n_tokens: int):
    """(X on the token axis, scalar columns) of the selected row ordinals of one GEM file."""
    import pyarrow.parquet as pq  # noqa: PLC0415
    import scipy.sparse as sp  # noqa: PLC0415
    pf = pq.ParquetFile(parquet, pre_buffer=False)
    scalars = [x.name for x in pf.schema_arrow if x.name not in LIST_COLS]
    idx, val, lens, keep, row0 = [], [], [], {c: [] for c in scalars}, 0
    for batch in pf.iter_batches(batch_size=2048):
        n = batch.num_rows
        local = rows[(rows >= row0) & (rows < row0 + n)] - row0
        row0 += n
        if not local.size:
            continue
        tok, ex = batch.column("gene_token_id"), batch.column("gene_expression")
        off = tok.offsets.to_numpy(zero_copy_only=False)
        if not np.array_equal(off, ex.offsets.to_numpy(zero_copy_only=False)):
            raise ValueError(f"{parquet.name}: token and expression lists differ")
        tv, ev = tok.values.to_numpy(zero_copy_only=False), ex.values.to_numpy(zero_copy_only=False)
        for r in local:
            idx.append(tv[off[r]:off[r + 1]])
            val.append(ev[off[r]:off[r + 1]])
            lens.append(int(off[r + 1] - off[r]))
        for c in scalars:
            col = batch.column(c).to_pylist()
            keep[c].extend(col[r] for r in local)
    if row0 <= (rows.max() if rows.size else -1):
        raise ValueError(f"{parquet.name}: {row0} rows, the sample names row {rows.max()}")
    indices = np.concatenate(idx) if idx else np.zeros(0, np.int64)
    values = np.concatenate(val) if val else np.zeros(0, np.float32)
    if indices.size and (indices.min() < 0 or indices.max() >= n_tokens):
        raise ValueError(f"{parquet.name}: gene token outside gene_metadata")
    x = sp.csr_matrix((values, indices, np.concatenate([[0], np.cumsum(lens)])), shape=(len(rows), n_tokens))
    x.sum_duplicates()
    return x, keep, row0


def phase_shards(spec: dict, line: str, a) -> None:
    adapters, _, _, _ = common.corpus()
    sample_sha, receipt = checked_table(a.sample, line, "sample_sha256")
    if receipt.get("design") != spec["design"]:
        raise ValueError("sample design differs from the job spec")
    fingerprint = reuse_fingerprint(spec, line, a.axis, sample_sha)
    common.new_dir(a.out)
    common.new_dir(a.stage)
    s = pd.read_parquet(a.sample / f"{line}.parquet")
    s = s[s["selected"]]
    cfg, src = spec["lines"][line], spec["source"]
    tok_path = a.stage / "gene_metadata.parquet"
    tok_url = src["base"] + src["gene_metadata"]["path"]
    common.download(tok_url, src["gene_metadata"].get("bytes") or common.head(tok_url)["bytes"], tok_path,
                    sha256=src["gene_metadata"]["sha256"])
    var = token_axis(pd.read_parquet(tok_path), a.axis)
    files = frozen_files(spec, line)[: a.max_files]
    source = common.source_record(cfg["source_id"], src["release"], src["license"],
                                  [{"locator": src["base"] + f["path"], "bytes": f["bytes"], "sha256": f["sha256"]}
                                   for f in files])
    sink = common.ShardSink(a.out, a.stage, cfg["unit"], source, common.writer_record(Path(__file__), a.runtime_manifest),
                            a.reuse, require={"sample_sha256": sample_sha, "ingestion_fingerprint": fingerprint})
    by_file = {g: d for g, d in s.groupby("gem_file")}
    depth_equal = depth_seen = 0
    for f in files:
        d = by_file.get(f["name"])
        if d is None or sink.have(f["name"]) is not None:
            continue
        rows = np.sort(d["cell"].str.rsplit(":", n=1).str[1].astype(np.int64).to_numpy())
        local = a.stage / f"{f['name']}.parquet"
        got = common.download(src["base"] + f["path"], f["bytes"], local, sha256=f["sha256"])
        x, keep, n_rows = read_selected(local, rows, len(var))
        local.unlink()
        meta = d.set_index(d["cell"].str.rsplit(":", n=1).str[1].astype(np.int64)).loc[rows]
        target = np.asarray(keep["gene_target"], dtype=object).astype(str)
        if not np.array_equal(target, meta["target"].to_numpy().astype(str)):
            raise ValueError(f"{f['name']}: the rows read are not the cells the sample chose")
        ntc = target == NTC_LABEL
        on_axis = np.asarray(x.sum(axis=1)).ravel().astype(float)
        published = pd.to_numeric(pd.Series(keep.get("total_counts", on_axis)), errors="coerce").to_numpy(dtype=float)
        depth_equal += int(np.isclose(published, on_axis, atol=0.5).sum())
        depth_seen += len(rows)
        extra = {f"orion_{c}": np.asarray(v, dtype=object).astype(str) for c, v in keep.items()}
        obs = adapters._obs(len(rows), cell_key=[f"{cfg['study']}|{f['name']}|row{r}" for r in rows],
                            study=cfg["study"], library=f["name"], barcode=[f"row{r}" for r in rows],
                            target=np.where(ntc, "NTC", target), target_published=target, guides=common.MISSING,
                            modality="CRISPRi", control_kind=np.where(ntc, "NTC", "none"), context=line,
                            batch=f["name"], chemistry=cfg["chemistry"],
                            depth_native=np.where(np.isfinite(published) & (published >= on_axis - 0.5), published, on_axis),
                            depth_published=np.where(np.isfinite(published), published, on_axis),
                            depth_on_file_axis=on_axis, n_genes_detected=np.diff(x.indptr), source_row=rows,
                            sample_pi=meta["pi"].to_numpy(float), sample_role=meta["role"].to_numpy().astype(str),
                            sample_stratum_n=meta["n_stratum"].to_numpy(), **extra)
        obs.index = [f"{f['name']}_r{r}" for r in rows]
        uns = {"rows": {"gem_file": f["name"], "selected": int(len(rows)), "of": int(n_rows), "sample_sha256": sample_sha},
               "read": {"how": "whole parquet to the runtime disk by parallel ranges, size and LFS sha256 checked; "
                               "selected rows decoded with pyarrow", "seconds": got["seconds"]},
               "sample": {"design": spec["design"]["name"], "k": int(spec["design"]["k"]), "salt": spec["design"]["salt"]},
               "notes": "barcode is the row ordinal in the GEM file (cell identity = file sha256 + row); guides is "
                        "MISSING unless a later spec maps a guide column; every scalar column of the source is in "
                        "obs as orion_<name>"}
        sink.put(f["name"], x, obs, var, uns, extra={"selected": int(len(rows))})
    done = {r["shard"] for r in sink.shards}
    want = {f["name"] for f in files if f["name"] in by_file}
    cells_want = int(sum(len(by_file[n]) for n in want))
    unit = sink.finish({"every_gem_file_done": done == want,
                        "cells_equal_sample": sum(r["cells"] for r in sink.shards) == cells_want,
                        "whole_line": a.max_files is None},
                       {"sample_sha256": sample_sha, "published_depth_equals_row_sum": [depth_equal, depth_seen]})
    tok_path.unlink()
    ok = common.complete(a.out, f"{spec['job_id']}_{line.lower()}", [unit], a.data_root)
    print("complete" if ok else "PARITY FAILED", flush=True)
    sys.exit(0 if ok else 1)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("phase", choices=["meta", "sample", "shards"])
    p.add_argument("--spec", type=Path, required=True)
    p.add_argument("--line", choices=["HCT116", "HEK293T"], required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--meta", type=Path)
    p.add_argument("--sample", type=Path)
    p.add_argument("--axis", type=Path)
    p.add_argument("--stage", type=Path)
    p.add_argument("--data-root", type=Path)
    p.add_argument("--runtime-manifest", type=Path)
    p.add_argument("--reuse", type=Path, nargs="*", default=[])
    p.add_argument("--max-files", type=int, help="smoke test: only the first N GEM files (never a complete unit)")
    a = p.parse_args()
    spec = common.load_json(a.spec)
    if a.phase == "meta":
        phase_meta(spec, a.line, a.out)
    elif a.phase == "sample":
        phase_sample(spec, a.line, a.meta, a.out)
    else:
        if not (a.sample and a.stage and a.axis):
            sys.exit("shards needs --sample, --stage and --axis")
        phase_shards(spec, a.line, a)


if __name__ == "__main__":
    main()
