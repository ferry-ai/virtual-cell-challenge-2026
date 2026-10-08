
import json, pickle, subprocess, sys, time
from pathlib import Path
INPUT, OUT = Path("/kaggle/input"), Path("/kaggle/working")
P = json.loads('{"key": null, "key_contains": "kolf_strong", "symbols": ["ACLY", "ARL14EP", "BRPF1", "C5orf22", "CAND1", "CAPRIN2", "CDK8", "CYTH2", "DCP2", "E2F4", "EAPP", "EZH2", "FOXN2", "GIGYF2", "GTF2IRD1", "HSBP1", "HSP90AB1", "KDM5A", "KHDRBS1", "MARCKSL1", "MED15", "MTA1", "NABP2", "PATL1", "PCGF1", "PCGF6", "PGLS", "PIN1", "PQBP1", "PRDX3", "PSKH1", "RBM18", "RBM26", "RBM5", "RNF2", "SCAF8", "SHPRH", "SIN3B", "SMARCA5", "SUPT7L", "TAF4", "TBC1D13", "TFCP2", "TIMM17B", "TIMM50", "TMF1", "TRIB3", "USP28", "ZBTB34", "ZBTB41", "ZKSCAN1", "ZNF219", "ZNF324", "ZNF397", "ZNF462"], "prepass_kernel": "rcell-prepass-k562-r1", "cap": 128, "max_controls": 2048, "seed": 2026}')
t0 = time.time()


def mount(slug):
    hits = [p for p in INPUT.glob("**/" + slug) if p.is_dir()]
    if len(hits) != 1:
        raise SystemExit(f"{slug}: {len(hits)} mounts: {hits[:3]}")
    return hits[0]


GEN = mount("rcell-gen-r1")
PRE = mount(P["prepass_kernel"]) / "prepass"
with open(PRE / "prepass.pkl", "rb") as fh:
    st = pickle.load(fh)
if P.get("key") is None:
    hits = [k for k in st["key_names"] if P["key_contains"] in k]
    if len(hits) != 1:
        raise SystemExit("keys containing %s: %s" % (P["key_contains"], hits))
    P["key"] = hits[0]
if P["key"] not in st["key_names"]:
    raise SystemExit("the prepass state does not know the key " + P["key"])
known = set(st["symbols"])
targets = [{"key": P["key"], "symbol": s} for s in P["symbols"]]
(OUT / "targets.json").write_text(json.dumps(targets, indent=0))
log = {"mounts": {"gen": str(GEN), "prepass": str(PRE)}, "holdout_group_of_prepass": st.get("holdout_group"),
       "key": P["key"], "keys_of_the_state": len(st["key_names"]),
       "symbols_requested": len(targets), "symbols_unknown_to_the_corpus": sorted(set(P["symbols"]) - known)}
r = subprocess.run([sys.executable, str(GEN / "extract_cells.py"), "--prepass", str(PRE), "--targets",
                    str(OUT / "targets.json"), "--shard-roots", str(INPUT), "--cap", str(P["cap"]),
                    "--max-controls", str(P["max_controls"]), "--seed", str(P["seed"]),
                    "--out", str(OUT / "real_cells.npz")], capture_output=True, text=True)
(OUT / "extract.log").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr[-20000:])
log["extract"] = {"returncode": r.returncode, "seconds": round(time.time() - t0, 1)}
log["ok"] = r.returncode == 0
if log["ok"]:
    log["sidecar"] = json.loads((OUT / "real_cells.json").read_text())
(OUT / "extract_done.json").write_text(json.dumps(log, indent=1))
print(json.dumps({k: log[k] for k in ("ok", "extract", "symbols_unknown_to_the_corpus")}), flush=True)
if not log["ok"]:
    raise SystemExit("extract failed: see extract.log")
