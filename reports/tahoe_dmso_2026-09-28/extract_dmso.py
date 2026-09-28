#!/usr/bin/env python3
"""Extract Tahoe vehicle cells using HTTP ranges, never whole-shard downloads.

Requires numpy and pyarrow. Run --plan-only before extraction. Checkpoints use
SQLite transactions (one shard); keep state.sqlite, plan.json and metadata/ to
resume. Outputs contain raw counts, not normalized expression. See LAYOUT.md.
"""
import argparse
import collections
import hashlib
import heapq
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import struct
import tempfile
import time
import urllib.request

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

REPO = "tahoebio/Tahoe-100M"
API = "https://huggingface.co/api/datasets/" + REPO
VEHICLE = "DMSO_TF"
COLUMNS = ["genes", "expressions", "drug", "cell_line_id", "plate"]
VERSION = 1


def atomic_json(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


class HTTP:
    """Count received HTTP body bytes; abort if a server ignores Range."""
    def __init__(self):
        self.bytes = 0
        self.requests = 0

    def get(self, url, start=None, end=None, limit=16 * 1024**2):
        headers = {"User-Agent": "tahoe-dmso-extractor/1", "Accept-Encoding": "identity"}
        if start is not None:
            headers["Range"] = f"bytes={start}-{end}"
            # Distinguish ranges for intermediary caches, without signed-URL reuse.
            url += ("&" if "?" in url else "?") + f"range_start={start}&range_end={end}"
        for attempt in range(5):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=90) as r:
                    self.requests += 1
                    if start is not None:
                        expected = f"bytes {start}-{end}/"
                        if r.status != 206 or not r.headers.get("Content-Range", "").startswith(expected):
                            raise ValueError("Server did not honor the exact Range; refusing full download")
                        limit = end - start + 1
                    data = r.read(limit + 1)
                    self.bytes += len(data)
                    if len(data) > limit or (start is not None and len(data) != limit):
                        raise ValueError("Unexpected HTTP body length")
                    return data, r.headers
            except (OSError, TimeoutError):
                if attempt == 4:
                    raise
                time.sleep(2**attempt)

    def json(self, url):
        body, headers = self.get(url)
        return json.loads(body), headers


class RangeFile(io.RawIOBase):
    """Seekable source; no read-ahead, no on-disk expression cache."""
    def __init__(self, url, size, http):
        self.url, self.size, self.http, self.pos = url, size, http, 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = offset + (0 if whence == 0 else self.pos if whence == 1 else self.size)
        if self.pos < 0:
            raise ValueError("Negative seek")
        return self.pos

    def read(self, n=-1):
        n = min(self.size - self.pos, n if n >= 0 else self.size)
        if n <= 0:
            return b""
        data, _ = self.http.get(self.url, self.pos, self.pos + n - 1)
        self.pos += n
        return data


def url_for(revision, path):
    return f"https://huggingface.co/datasets/{REPO}/resolve/{revision}/{path}"


def footer(source, size):
    """Fetch only the 8-byte trailer and the Thrift footer, not a 64-KiB tail."""
    source.seek(size - 8)
    trailer = source.read(8)
    if trailer[4:] != b"PAR1":
        raise ValueError("Not an unencrypted Parquet file")
    length = struct.unpack("<I", trailer[:4])[0]
    if length > 64 * 1024**2 or length + 8 > size:
        raise ValueError("Implausible Parquet footer")
    source.seek(size - 8 - length)
    data = b"PAR1" + source.read(length) + trailer
    return pq.read_metadata(pa.BufferReader(data)), data


def column(rg, name):
    return next(rg.column(i) for i in range(rg.num_columns)
                if rg.column(i).path_in_schema.split(".")[0] == name)


def possible(rg):
    stats = column(rg, "drug").statistics
    if stats is None or not stats.has_min_max:
        return True
    lo, hi = stats.min, stats.max
    if isinstance(lo, bytes):
        lo, hi = lo.decode(), hi.decode()
    return lo <= VEHICLE <= hi


def plan_shard(source, md):
    """Read drug labels only where stats cannot exclude vehicle cells."""
    pf = pq.ParquetFile(source, metadata=md, pre_buffer=False)
    selected, count = [], 0
    for i in range(md.num_row_groups):
        rg = md.row_group(i)
        if not possible(rg):
            continue
        stats = column(rg, "drug").statistics
        if (stats is not None and stats.has_min_max and stats.min == stats.max
                and stats.min in (VEHICLE, VEHICLE.encode()) and stats.null_count is not None):
            n = rg.num_rows - stats.null_count
        else:
            labels = pf.read_row_group(i, columns=["drug"], use_threads=False)["drug"]
            n = pc.sum(pc.cast(pc.equal(labels, VEHICLE), pa.int64())).as_py() or 0
        if n:
            payload = sum(column(rg, c).total_compressed_size for c in COLUMNS)
            selected.append({"index": i, "n_vehicle": n, "rows": rg.num_rows,
                             "column_bytes": payload})
            count += n
    return {"groups": selected, "n_vehicle": count, "rows": md.num_rows,
            "num_row_groups": md.num_row_groups}


def discover(out, http, revision):
    path = out / "inventory.json"
    if path.exists():
        result = json.loads(path.read_text())
        if revision not in ("main", result["revision"]):
            raise ValueError("Revision differs from checkpoint")
        return result
    info, _ = http.json(API + "/revision/" + revision)
    sha = info["sha"]
    entries = []
    url = API + f"/tree/{sha}?recursive=true&limit=1000"
    while url:
        page, headers = http.json(url)
        entries.extend(page)
        match = re.search(r'<([^>]+)>; rel="next"', headers.get("Link", ""))
        url = match.group(1) if match else None
    shards = sorted(({"path": x["path"], "size": x["size"]} for x in entries
                     if x["path"].startswith("data/train-") and x["path"].endswith(".parquet")),
                    key=lambda x: x["path"])
    if not shards:
        raise ValueError("No expression shards found")
    result = {"revision": sha, "shards": shards, "sources": [API, url_for(sha, "README.md")],
              "inventory_bytes": http.bytes}
    atomic_json(path, result)
    return result


def make_plan(out, inventory, http):
    path = out / "plan.json"
    plan = json.loads(path.read_text()) if path.exists() else {
        "revision": inventory["revision"], "shards": {}, "bytes_read": 0,
        "elapsed_seconds": 0, "complete": False}
    started, before = time.monotonic(), http.bytes
    previous_bytes, previous_time = plan["bytes_read"], plan["elapsed_seconds"]
    for shard in inventory["shards"]:
        name = shard["path"]
        if name in plan["shards"]:
            continue
        source = RangeFile(url_for(inventory["revision"], name), shard["size"], http)
        md, raw = footer(source, shard["size"])
        (out / "metadata" / (Path(name).name + ".footer")).write_bytes(raw)
        entry = plan_shard(source, md)
        source.close()
        entry["footer_bytes"] = len(raw) - 4
        plan["shards"][name] = entry
        plan["bytes_read"] = previous_bytes + http.bytes - before
        plan["elapsed_seconds"] = previous_time + time.monotonic() - started
        atomic_json(path, plan)
        print(f"plan {len(plan['shards'])}/{len(inventory['shards'])}: {name}, {entry['n_vehicle']} vehicle", flush=True)
    plan["complete"] = True
    plan["n_vehicle"] = sum(s["n_vehicle"] for s in plan["shards"].values())
    plan["extraction_column_bytes"] = sum(g["column_bytes"] for s in plan["shards"].values() for g in s["groups"])
    plan["selected_row_groups"] = sum(len(s["groups"]) for s in plan["shards"].values())
    plan["selected_shards"] = sum(bool(s["groups"]) for s in plan["shards"].values())
    plan["full_shard_bytes"] = sum(s["size"] for s in inventory["shards"])
    atomic_json(path, plan)
    return plan


def load_genes(out, revision, http):
    path = out / "metadata" / "gene_metadata.parquet"
    if not path.exists():
        data, _ = http.get(url_for(revision, "metadata/gene_metadata.parquet"))
        path.write_bytes(data)
    table = pq.read_table(path).to_pydict()
    order = np.argsort(table["token_id"])
    result = {"token_id": np.asarray(table["token_id"], dtype=np.int64)[order]}
    for key in ("gene_symbol", "ensembl_id"):
        result[key] = np.asarray([x or "" for x in table.get(key, [""] * len(order))], dtype=str)[order]
    if len(np.unique(result["token_id"])) != len(order):
        raise ValueError("Duplicate token IDs in gene metadata")
    return result


def audit_metadata(out, revision, http):
    """Cache small metadata tables; never download the 2.29-GB obs table."""
    audit_path = out / "metadata_audit.json"
    if audit_path.exists():
        return
    audit = {"sources": [], "tables": {}}
    for name in ("sample", "cell_line", "drug"):
        path = out / "metadata" / f"{name}_metadata.parquet"
        url = url_for(revision, f"metadata/{name}_metadata.parquet")
        if not path.exists():
            data, _ = http.get(url)
            path.write_bytes(data)
        table = pq.read_table(path)
        audit["sources"].append(url)
        audit["tables"][name] = {"rows": table.num_rows, "schema": str(table.schema)}
        if name == "sample":
            controls = table.filter(pc.equal(table["drug"], VEHICLE))
            audit["vehicle_samples"] = controls.to_pylist()
            audit["note"] = "Sample rows are not cell counts; preflight counts expression rows exactly."
    atomic_json(audit_path, audit)


def decode(genes, expressions, tokens):
    """Drop a negative CLS marker as in the official tutorial; reject bad data."""
    if len(genes) != len(expressions):
        raise ValueError("Misaligned genes/counts")
    if expressions and expressions[0] < 0:
        genes, expressions = genes[1:], expressions[1:]
    g, x = np.asarray(genes, dtype=np.int64), np.asarray(expressions, dtype=np.float64)
    if not np.all(np.isfinite(x)) or np.any(x < 0) or np.any(x != np.floor(x)) or np.any(x >= 2**63):
        raise ValueError("Counts must be finite nonnegative integers; check CLS convention")
    idx = np.searchsorted(tokens, g)
    if np.any(idx >= len(tokens)) or np.any(tokens[idx] != g):
        raise ValueError("Unknown gene token (no silent gene loss)")
    unique, inv = np.unique(idx, return_inverse=True)
    counts = np.zeros(len(unique), dtype=np.uint64)
    np.add.at(counts, inv, x.astype(np.uint64))
    nonzero = counts != 0
    return unique[nonzero].astype(np.int32), counts[nonzero]


class Accumulator:
    """Atomic shard checkpoints plus deterministic bottom-k sampling per line."""
    def __init__(self, path, genes, k, seed, identity):
        self.db = sqlite3.connect(path)
        self.db.executescript('''
          PRAGMA journal_mode=DELETE;
          PRAGMA synchronous=FULL;
          CREATE TABLE IF NOT EXISTS config (value TEXT);
          CREATE TABLE IF NOT EXISTS done (shard TEXT PRIMARY KEY, cells INTEGER, bytes INTEGER, seconds REAL);
          CREATE TABLE IF NOT EXISTS bulk (line TEXT, plate TEXT, sums BLOB, n INTEGER, library INTEGER, PRIMARY KEY(line,plate));
          CREATE TABLE IF NOT EXISTS sample (id TEXT PRIMARY KEY, line TEXT, plate TEXT, priority INTEGER, idx BLOB, counts BLOB);
        ''')
        config = json.dumps({"version": VERSION, "identity": identity, "k": k, "seed": seed,
                             "gene_hash": hashlib.sha256(genes["token_id"].tobytes()).hexdigest()}, sort_keys=True)
        old = self.db.execute("SELECT value FROM config").fetchone()
        if old and old[0] != config:
            raise ValueError("Incompatible checkpoint settings")
        if not old:
            self.db.execute("INSERT INTO config VALUES (?)", (config,))
            self.db.commit()
        self.genes, self.k, self.seed = genes, k, seed
        self.heaps = collections.defaultdict(list)
        for ident, line, priority in self.db.execute("SELECT id,line,priority FROM sample"):
            heapq.heappush(self.heaps[line], (-priority, ident))

    def process(self, name, source, md, entry, byte_counter=lambda: 0, fail_after=None):
        if self.db.execute("SELECT 1 FROM done WHERE shard=?", (name,)).fetchone():
            return False
        started, before = time.monotonic(), byte_counter()
        totals, seen = {}, 0
        pf = pq.ParquetFile(source, metadata=md, pre_buffer=False)
        # Rollback restores the database. On an exception discard this object:
        # in-memory heaps may contain uncommitted selections.
        with self.db:
            for group in entry["groups"]:
                rg, offset = group["index"], 0
                for batch in pf.iter_batches(batch_size=256, row_groups=[rg], columns=COLUMNS, use_threads=False):
                    labels = batch.column(batch.schema.get_field_index("drug"))
                    mask = pc.fill_null(pc.equal(labels, VEHICLE), False)
                    positions = np.flatnonzero(mask.to_numpy(zero_copy_only=False)) + offset
                    selected = batch.filter(mask).to_pylist()
                    offset += batch.num_rows
                    for position, row in zip(positions, selected):
                        line, plate = row["cell_line_id"], row["plate"]
                        if not line or not plate:
                            raise ValueError("Missing cell line or plate")
                        idx, counts = decode(row["genes"], row["expressions"], self.genes["token_id"])
                        key = (line, plate)
                        if key not in totals:
                            totals[key] = [np.zeros(len(self.genes["token_id"]), dtype=np.uint64), 0, 0]
                        totals[key][0][idx] += counts
                        totals[key][1] += 1
                        totals[key][2] += int(counts.sum())
                        ident = f"{name}:{rg}:{position}"
                        priority = int.from_bytes(hashlib.blake2b(f"{self.seed}:{ident}".encode(), digest_size=8).digest(), "big") >> 1
                        heap = self.heaps[line]
                        if self.k and (len(heap) < self.k or priority < -heap[0][0]):
                            if len(heap) == self.k:
                                _, removed = heapq.heappop(heap)
                                self.db.execute("DELETE FROM sample WHERE id=?", (removed,))
                            heapq.heappush(heap, (-priority, ident))
                            self.db.execute("INSERT INTO sample VALUES (?,?,?,?,?,?)", (ident, line, plate, priority, idx.tobytes(), counts.tobytes()))
                        seen += 1
                        if fail_after is not None and seen >= fail_after:
                            raise RuntimeError("Injected interruption")
            if seen != entry["n_vehicle"]:
                raise ValueError(f"Plan count mismatch: {seen} != {entry['n_vehicle']}")
            for (line, plate), (sums, n, library) in totals.items():
                old = self.db.execute("SELECT sums,n,library FROM bulk WHERE line=? AND plate=?", (line, plate)).fetchone()
                if old:
                    sums += np.frombuffer(old[0], dtype=np.uint64)
                    n, library = n + old[1], library + old[2]
                self.db.execute("INSERT OR REPLACE INTO bulk VALUES (?,?,?,?,?)", (line, plate, sums.tobytes(), n, library))
            self.db.execute("INSERT INTO done VALUES (?,?,?,?)", (name, seen, byte_counter() - before, time.monotonic() - started))
        return True

    def export(self, out):
        rows = self.db.execute("SELECT line,plate,sums,n,library FROM bulk ORDER BY line,plate").fetchall()
        n_genes = len(self.genes["token_id"])
        bulk = dict(sums=np.stack([np.frombuffer(r[2], dtype=np.uint64) for r in rows]) if rows else np.zeros((0, n_genes), dtype=np.uint64),
                    n_cells=np.array([r[3] for r in rows], dtype=np.int64), library=np.array([r[4] for r in rows], dtype=np.uint64),
                    cell_line=np.array([r[0] for r in rows], dtype=str), plate=np.array([r[1] for r in rows], dtype=str), **self.genes)
        save_npz(out / "pseudobulk.npz", bulk)
        n, nnz = self.db.execute("SELECT COUNT(*),COALESCE(SUM(LENGTH(idx)/4),0) FROM sample").fetchone()
        data, indices, indptr = np.empty(nnz, np.uint64), np.empty(nnz, np.int32), np.zeros(n + 1, np.int64)
        lines, plates, ids = [], [], []
        for i, (ident, line, plate, idx, counts) in enumerate(self.db.execute("SELECT id,line,plate,idx,counts FROM sample ORDER BY line,priority,id")):
            a, b = indptr[i], indptr[i] + len(idx) // 4
            indices[a:b], data[a:b] = np.frombuffer(idx, np.int32), np.frombuffer(counts, np.uint64)
            indptr[i + 1] = b
            lines.append(line)
            plates.append(plate)
            ids.append(ident)
        save_npz(out / "cells.npz", dict(data=data, indices=indices, indptr=indptr, shape=np.array([n, n_genes]),
                 format=np.array(b"csr"), cell_line=np.asarray(lines, dtype=str), plate=np.asarray(plates, dtype=str),
                 cell_id=np.asarray(ids, dtype=str), **self.genes))
        return dict(collections.Counter(lines))


def save_npz(path, arrays):
    tmp = path.with_suffix(".tmp")
    with tmp.open("wb") as f:
        np.savez_compressed(f, **arrays)
    os.replace(tmp, path)


def run(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "metadata").mkdir(exist_ok=True)
    http = HTTP()
    inventory = discover(out, http, args.revision)
    genes = load_genes(out, inventory["revision"], http)
    audit_metadata(out, inventory["revision"], http)
    plan = make_plan(out, inventory, http)
    print(json.dumps({k: plan[k] for k in ("n_vehicle", "extraction_column_bytes", "selected_shards", "selected_row_groups", "bytes_read")}), flush=True)
    if args.plan_only:
        return
    if plan["extraction_column_bytes"] > args.max_read_gb * 10**9:
        raise SystemExit("Planned expression reads exceed --max-read-gb. Inspect plan.json; no expression data was read.")
    acc = Accumulator(out / "state.sqlite", genes, args.cells_per_line, args.seed, inventory["revision"])
    for shard in inventory["shards"]:
        name = shard["path"]
        if acc.db.execute("SELECT 1 FROM done WHERE shard=?", (name,)).fetchone():
            continue
        md = pq.read_metadata(out / "metadata" / (Path(name).name + ".footer"))
        with RangeFile(url_for(inventory["revision"], name), shard["size"], http) as source:
            acc.process(name, source, md, plan["shards"][name], lambda: http.bytes)
        print(f"extracted {name}: {plan['shards'][name]['n_vehicle']} vehicle", flush=True)
    sampled = acc.export(out)
    done = [dict(zip(["shard", "cells", "bytes", "seconds"], row)) for row in acc.db.execute("SELECT * FROM done ORDER BY shard")]
    kept = dict(acc.db.execute("SELECT line,SUM(n) FROM bulk GROUP BY line"))
    manifest = {"version": VERSION, "complete": len(done) == len(inventory["shards"]),
                "revision": inventory["revision"], "sources": inventory["sources"] + [url_for(inventory["revision"], "metadata/gene_metadata.parquet")] + json.loads((out / "metadata_audit.json").read_text())["sources"],
                "vehicle": VEHICLE, "cells_per_line": args.cells_per_line, "seed": args.seed,
                "shards_read": [x for x in done if x["cells"]], "shards_done": len(done),
                "cells_kept_per_line": kept, "cells_sampled_per_line": sampled,
                "bytes_read": plan["bytes_read"] + sum(x["bytes"] for x in done),
                "bytes_scope": "Completed preflight and extraction shards; excludes API/gene metadata, failed attempts and interrupted uncommitted shards; HTTP bodies only",
                "http_bytes_this_invocation": http.bytes, "http_requests_this_invocation": http.requests,
                "elapsed_seconds": plan["elapsed_seconds"] + sum(x["seconds"] for x in done),
                "elapsed_scope": "Completed shard planning/extraction, excluding export and failed attempts",
                "plan": {k: v for k, v in plan.items() if k != "shards"}}
    if sum(kept.values()) != plan["n_vehicle"]:
        raise ValueError("Final count does not match preflight")
    atomic_json(out / "manifest.json", manifest)
    acc.db.close()
    print(json.dumps({"complete": True, "cells": sum(kept.values()), "sampled": sampled}), flush=True)


def selftest():
    """Exercise real-layout Parquet, pruning, raw sums, sampling and rollback."""
    with tempfile.TemporaryDirectory(prefix="tahoe-selftest-", dir=Path(__file__).parent) as tmp:
        root = Path(tmp)
        schema = pa.schema([("genes", pa.list_(pa.int64())), ("expressions", pa.list_(pa.float32()))] +
                           [(x, pa.string()) for x in ["drug", "sample", "BARCODE_SUB_LIB_ID", "cell_line_id", "moa-fine", "canonical_smiles", "pubchem_cid", "plate"]])
        rows = []
        for i, drug in enumerate(["ZZZ", "ZZZ", VEHICLE, "AAA", VEHICLE, VEHICLE, VEHICLE, VEHICLE]):
            rows.append(dict(genes=[0, 42, 7, 42], expressions=[-1., 2., float(i + 1), 3.], drug=drug,
                             sample="s", BARCODE_SUB_LIB_ID=str(i), cell_line_id="A" if i < 6 else "B",
                             **{"moa-fine": ""}, canonical_smiles="", pubchem_cid="", plate="1" if i < 5 else "2"))
        genes = dict(token_id=np.array([7, 42, 99]), gene_symbol=np.array(["G7", "G42", "G99"]), ensembl_id=np.array(["E7", "E42", "E99"]))
        entries = []
        for part, part_rows in enumerate([rows[:4], rows[4:]]):
            path = root / f"part{part}.parquet"
            pq.write_table(pa.Table.from_pylist(part_rows, schema=schema), path, row_group_size=2, write_statistics=(part == 0))
            with path.open("rb") as f:
                md, _ = footer(f, path.stat().st_size)
                entry = plan_shard(f, md)
            entries.append((path, md, entry))
        assert [e[2]["n_vehicle"] for e in entries] == [1, 4]
        assert [g["index"] for g in entries[0][2]["groups"]] == [1]
        class LocalHTTP:
            def __init__(self):
                self.ranges = []

            def get(self, url, start, end):
                self.ranges.append((start, end))
                return Path(url).read_bytes()[start:end + 1], {}

        transport = LocalHTTP()
        path, md, entry = entries[0]
        with RangeFile(str(path), path.stat().st_size, transport) as source:
            actual = plan_shard(source, md)
        assert actual == entry
        drug_column = column(md.row_group(1), "drug")
        start = drug_column.dictionary_page_offset or drug_column.data_page_offset
        assert transport.ranges == [(start, start + drug_column.total_compressed_size - 1)], transport.ranges
        # No hidden footer fetch or other columns when metadata is provided.
        from unittest.mock import patch

        class IgnoredRange(io.BytesIO):
            status = 200
            headers = {}

            def read(self, *args):
                raise AssertionError("Must not read a full-file response")

        with patch("urllib.request.urlopen", return_value=IgnoredRange()):
            try:
                HTTP().get("https://example.invalid/shard", 5, 9)
            except ValueError as error:
                assert "Range" in str(error)
            else:
                raise AssertionError("Ignored Range was accepted")
        acc = Accumulator(root / "state.sqlite", genes, 2, 42, "synthetic")
        with entries[0][0].open("rb") as f:
            acc.process("part0", f, entries[0][1], entries[0][2])
        try:
            with entries[1][0].open("rb") as f:
                acc.process("part1", f, entries[1][1], entries[1][2], fail_after=2)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Interruption not injected")
        assert acc.db.execute("SELECT COUNT(*) FROM done").fetchone()[0] == 1
        acc.db.close()
        acc = Accumulator(root / "state.sqlite", genes, 2, 42, "synthetic")
        for i, (path, md, entry) in enumerate(entries):
            with path.open("rb") as f:
                assert acc.process(f"part{i}", f, md, entry) == bool(i)
        assert acc.export(root) == {"A": 2, "B": 2}
        with np.load(root / "pseudobulk.npz", allow_pickle=False) as pb:
            np.testing.assert_array_equal(pb["sums"], [[8, 10, 0], [6, 5, 0], [15, 10, 0]])
            np.testing.assert_array_equal(pb["n_cells"], [2, 1, 2])
            np.testing.assert_array_equal(pb["library"], [18, 11, 25])
        with np.load(root / "cells.npz", allow_pickle=False) as cells:
            assert cells["shape"].tolist() == [4, 3]
            assert cells["indptr"][-1] == len(cells["data"]) == 8
            resumed_ids = cells["cell_id"].copy()
        acc.db.close()
        fresh = Accumulator(root / "fresh.sqlite", genes, 2, 42, "synthetic")
        for i, (path, md, entry) in enumerate(entries):
            with path.open("rb") as f:
                fresh.process(f"part{i}", f, md, entry)
        fresh.export(root)
        with np.load(root / "cells.npz", allow_pickle=False) as cells:
            np.testing.assert_array_equal(cells["cell_id"], resumed_ids)
        fresh.db.close()
        idx, x = decode([7], [2.], genes["token_id"])
        assert idx.tolist() == [0] and x.tolist() == [2]
        try:
            decode([0, 500], [-1., 2.], genes["token_id"])
        except ValueError:
            pass
        else:
            raise AssertionError("Unknown token accepted")
    print("SELFTEST PASS: 2 shards, 5 vehicle cells, 3 line/plate groups, 4 sampled cells; CLS, duplicate tokens, absent statistics, mixed groups, rollback/resume and deterministic sampling verified")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", help="Persistent output/checkpoint directory")
    parser.add_argument("--cells-per-line", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--revision", default="main", help="Resolved to immutable HF commit on first run")
    parser.add_argument("--plan-only", action="store_true", help="Only footers/drug columns; exact cell count and projected bytes")
    parser.add_argument("--max-read-gb", type=float, default=20., help="Maximum planned extraction column bytes in decimal GB")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        selftest()
    elif not args.out or args.cells_per_line < 0 or args.max_read_gb <= 0:
        parser.error("--out required; cells-per-line >= 0 and max-read-gb > 0")
    else:
        run(args)


if __name__ == "__main__":
    main()
