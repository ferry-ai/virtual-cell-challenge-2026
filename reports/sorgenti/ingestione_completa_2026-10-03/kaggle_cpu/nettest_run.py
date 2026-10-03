"""Kaggle CPU kernel: can it reach the ingestion sources, how fast, and with what machine? (3/10, full ingestion)

HEAD of one file per host (Hugging Face for Orion, S3 for CD4, Zenodo for Southard, GEO FTP for DLD-1), then a timed
download of one whole Orion parquet (370 MB) to the kernel's disk, and the machine (CPUs, RAM, disk). Writes
nettest.json to /kaggle/working. Reads no private data and writes nothing else.
"""
import json
import os
import shutil
import subprocess
import time
import urllib.request

OUT = "/kaggle/working"
URLS = {
    "huggingface_orion": "https://huggingface.co/datasets/Xaira-Therapeutics/X-Atlas-Orion/resolve/main/data/HEK293T_Batch1.parquet",
    "s3_cd4": "https://genome-scale-tcell-perturb-seq.s3.amazonaws.com/marson2025_data/D1_Rest.assigned_guide.h5ad",
    "zenodo_southard": "https://zenodo.org/api/records/15200179/files/fibroblast_CRISPRa_final_pop.h5ad/content",
    "geo_dld1": "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE337nnn/GSE337988/suppl/filelist.txt",
}


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (r.stdout or r.stderr).strip()


report = {"machine": {"cpus": os.cpu_count(), "memory": sh("free -g | head -2"), "disk": sh("df -h /kaggle/working | tail -1"),
                      "tmp_disk": sh("df -h /tmp | tail -1")}, "head": {}, "download": None}
for name, url in URLS.items():
    t = time.time()
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "vcc2026-nettest/1"})
        with urllib.request.urlopen(req, timeout=60) as r:
            report["head"][name] = {"status": r.status, "bytes": r.headers.get("Content-Length"),
                                    "seconds": round(time.time() - t, 2)}
    except Exception as e:  # noqa: BLE001
        report["head"][name] = {"error": repr(e)[:300], "seconds": round(time.time() - t, 2)}
    print(name, report["head"][name], flush=True)
dest = "/tmp/orion_test.parquet"
t = time.time()
try:
    req = urllib.request.Request(URLS["huggingface_orion"], headers={"User-Agent": "vcc2026-nettest/1"})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as fh:
        shutil.copyfileobj(r, fh, length=16 << 20)
    size = os.path.getsize(dest)
    secs = time.time() - t
    report["download"] = {"bytes": size, "seconds": round(secs, 1), "mb_per_s": round(size / 2**20 / secs, 1)}
    os.remove(dest)
except Exception as e:  # noqa: BLE001
    report["download"] = {"error": repr(e)[:300], "seconds": round(time.time() - t, 1)}
print("download", report["download"], flush=True)
with open(os.path.join(OUT, "nettest.json"), "w") as fh:
    json.dump(report, fh, indent=1)
