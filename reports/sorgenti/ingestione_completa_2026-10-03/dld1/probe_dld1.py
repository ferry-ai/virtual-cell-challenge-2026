"""Kaggle kernel: what is inside GSE337988_RAW.tar (DLD-1, CRISPRi at several MOI), before an adapter is written.

Only structure is recorded, no conversion: the members of the tar with their sizes, and for one channel of the large
experiment the HDF5 tree of its files (10x matrices, guide UMIs, hashing UMIs), the first rows of every small table
(sample sheets, metrics), and the tree of the processed object of the low MOI. The tar (26.5 GB) is read from GEO to
/tmp by parallel ranges and is not kept. Output: dld1_structure.json and the small text members, as they are.

Run as a Kaggle script kernel (push_script.py); nothing is passed on the command line.
"""
import hashlib, json, os, shutil, tarfile, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE337nnn/GSE337988/suppl/"
OUT, WORK = Path("/kaggle/working"), Path("/tmp/dld1")
WORK.mkdir(parents=True, exist_ok=True)
doc, t0 = {"series": "GSE337988", "base": BASE}, time.time()


def get(url, lo=None, hi=None, attempts=6):
    headers = {"User-Agent": "vcc2026-ingestione/1"}
    if lo is not None:
        headers["Range"] = f"bytes={lo}-{hi}"
    for k in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=180) as r:
                return r.read(), dict(r.headers)
        except OSError as err:
            last = err
            time.sleep(5 * (k + 1))
    raise OSError(f"{url}: {last}")


def download(url, dest, threads=8, chunk=64 << 20):
    _, head = get(url, 0, 0)
    size = int(head["Content-Range"].rsplit("/", 1)[-1])
    with open(dest, "wb") as fh:
        fh.truncate(size)
    lock, done = threading.Lock(), [0]

    def part(a):
        body, _ = get(url, a, min(size, a + chunk) - 1)
        with lock:
            with open(dest, "r+b") as fh:
                fh.seek(a)
                fh.write(body)
            done[0] += len(body)
            if done[0] // (2 << 30) != (done[0] - len(body)) // (2 << 30):
                print(f"{dest.name}: {done[0] / 1e9:.1f} of {size / 1e9:.1f} GB, {time.time() - t0:.0f}s", flush=True)

    with ThreadPoolExecutor(threads) as ex:
        list(ex.map(part, range(0, size, chunk)))
    return size, head.get("ETag"), head.get("Last-Modified")


def tree(path, max_items=400):
    import h5py
    out = []

    def visit(name, node):
        if len(out) >= max_items:
            return
        if isinstance(node, h5py.Dataset):
            item = {"name": name, "shape": list(node.shape), "dtype": str(node.dtype)}
            if node.size and node.size <= 12:
                item["values"] = [v.decode() if isinstance(v, bytes) else (v.item() if hasattr(v, "item") else str(v))
                                  for v in node[()].ravel()[:12]]
            elif node.ndim == 1 and node.size:
                item["head"] = [v.decode() if isinstance(v, bytes) else (v.item() if hasattr(v, "item") else str(v))
                                for v in node[:5]]
            out.append(item)
        else:
            out.append({"name": name, "group": True, "attrs": {k: str(v)[:120] for k, v in node.attrs.items()}})

    with h5py.File(path, "r") as f:
        out.append({"name": "/", "group": True, "attrs": {k: str(v)[:120] for k, v in f.attrs.items()}})
        f.visititems(visit)
    return out


listing, _ = get(BASE + "filelist.txt")
(OUT / "filelist.txt").write_bytes(listing)
doc["supplementary_listing_bytes"] = len(listing)
tar_path = WORK / "GSE337988_RAW.tar"
size, etag, modified = download(BASE + "GSE337988_RAW.tar", tar_path)
doc["tar"] = {"bytes": size, "etag": etag, "last_modified": modified, "seconds": round(time.time() - t0, 1)}
print(json.dumps(doc["tar"]), flush=True)
with tarfile.open(tar_path) as t:
    members = [{"name": m.name, "bytes": m.size} for m in t.getmembers() if m.isfile()]
    doc["members"] = members
    print(f"{len(members)} members", flush=True)
    small = [m for m in members if m["bytes"] < (3 << 20) and not m["name"].endswith((".h5", ".h5.gz"))]
    text_dir = OUT / "small_members"
    text_dir.mkdir()
    for m in small[:400]:
        (text_dir / m["name"].replace("/", "__")).write_bytes(t.extractfile(m["name"]).read())
    doc["small_members_copied"] = len(small[:400])
    # One channel of the large experiment: every file that shares the prefix of its first crispr member.
    crispr = sorted(m["name"] for m in members if "crispr" in m["name"].lower())
    doc["crispr_members"] = len(crispr)
    doc["trees"] = {}
    if crispr:
        pick = crispr[len(crispr) // 2]
        prefix = pick.split("crispr")[0]
        chosen = [m["name"] for m in members if m["name"].startswith(prefix)]
        doc["channel_prefix"], doc["channel_members"] = prefix, chosen
        for name in chosen:
            local = WORK / name.replace("/", "__")
            with open(local, "wb") as fh:
                shutil.copyfileobj(t.extractfile(name), fh)
            if name.endswith(".gz"):
                import gzip
                plain = local.with_suffix("")
                with gzip.open(local, "rb") as src, open(plain, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                local = plain
            if local.suffix == ".h5":
                try:
                    doc["trees"][name] = tree(local)
                except Exception as err:
                    doc["trees"][name] = f"{type(err).__name__}: {err}"
                print(f"tree of {name}: {len(doc['trees'][name])} items", flush=True)
tar_path.unlink()
import re
index, _ = get(BASE)                                         # the other supplementary files are not in filelist.txt
doc["supplementary_files"] = sorted(set(re.findall(r'href="([^"?/]+)"', index.decode(errors="replace"))))
for cand in [n for n in doc["supplementary_files"] if "Low_assays" in n][:1]:
    try:
        local = WORK / cand
        size, _, _ = download(BASE + cand, local)
        plain = local
        if cand.endswith(".gz"):
            import gzip
            plain = local.with_suffix("")
            with gzip.open(local, "rb") as src, open(plain, "wb") as dst:
                shutil.copyfileobj(src, dst)
        doc["trees"][cand] = tree(plain)
        doc["low_assays_bytes"] = size
    except Exception as err:
        doc["trees"][cand] = f"{type(err).__name__}: {err}"
doc["seconds"] = round(time.time() - t0, 1)
(OUT / "dld1_structure.json").write_text(json.dumps(doc, indent=1, default=str))
print(json.dumps({"members": len(doc.get("members", [])), "trees": list(doc["trees"]), "seconds": doc["seconds"]}), flush=True)
