
import json, pickle, subprocess, sys, time
from pathlib import Path
INPUT, OUT = Path("/kaggle/input"), Path("/kaggle/working")
P = json.loads('{"key": "replogle_k562_gwps|K562", "symbols": ["ACLY", "ADNP", "AGO1", "AKAP1", "AKIRIN1", "AKT2", "ALG12", "ANKRD52", "ANKZF1", "ANP32B", "AP2A2", "API5", "ARL14EP", "ASCC2", "BCKDK", "BCL6", "BCL7C", "BRD1", "BRPF1", "C5orf22", "CAND1", "CARM1", "CAT", "CCDC112", "CDK8", "CHD3", "CHD6", "CHKB", "CLCN6", "COIL", "COMMD8", "COQ10B", "CSNK2A1", "CYTH2", "DBF4B", "DBN1", "DCAF16", "DCP2", "DDHD1", "DEAF1", "DEK", "DHRS1", "DHX35", "DLAT", "DMTF1", "DNTTIP1", "DRG2", "DTNBP1", "DVL3", "E2F1", "E2F4", "EAPP", "EEF1A2", "ELK1", "EPC2", "EPM2AIP1", "EZH2", "FAM120A", "FCGRT", "FHL3", "FOXN2", "FOXO4", "FUBP3", "FXYD5", "FZD2", "GIGYF2", "GLI3", "GLYR1", "GMEB2", "GPATCH8", "GRAMD1A", "GTF2IRD1", "HDAC1", "HDAC8", "HMGN3", "HMGN4", "HMGXB3", "HOMEZ", "HSBP1", "HSP90AB1", "IFI27L2", "IFNAR2", "IFNGR2", "IL10RB", "IREB2", "KDM5A", "KHDRBS1", "KHSRP", "KIF2A", "KMT2A", "LDLR", "LENG1", "LMAN1", "LMBRD2", "LPCAT3", "MAN2A1", "MAP2K2", "MAPK12", "MARCKSL1", "MBD4", "MED13", "MED15", "MED25", "MLLT10", "MSANTD4", "MSI2", "MTA1", "MTF1", "MTHFSD", "MTM1", "MYD88", "MYPOP", "MYRF", "NABP2", "NAIF1", "NCLN", "NFE2L1", "NGLY1", "NIPAL3", "NIPSNAP3A", "NT5DC1", "NUP37", "PAN2", "PAPOLA", "PATL1", "PCGF1", "PCGF6", "PDCD4", "PDE6D", "PDK1", "PGLS", "PHF19", "PHF23", "PHF8", "PI4KB", "PIM2", "PIN1", "PINK1", "PKN3", "PLAGL2", "PLCG1", "PNP", "POLD4", "POR", "PPIF", "PPIP5K2", "PQBP1", "PRDX3", "PRKAB2", "PRKACA", "PRMT2", "PRMT6", "PRMT7", "PRNP", "PSKH1", "PTMS", "PTOV1", "PYCR1", "R3HCC1L", "RAB5A", "RABEP2", "RBM18", "RBM26", "RBM4B", "RBM5", "RC3H2", "REV1", "RFK", "RNF10", "RNF141", "RNF2", "RSRC1", "S100A11", "SAP30L", "SCAF8", "SFXN4", "SH2D3A", "SHPRH", "SIN3B", "SLC25A13", "SLC39A1", "SLIRP", "SMARCA5", "SMARCC2", "SMYD2", "SND1", "SNRK", "SNX4", "SRSF5", "SSR4", "STAT6", "STK3", "STT3A", "SUPT7L", "SYVN1", "TAF15", "TARBP2", "TBC1D13", "TBCK", "TEAD4", "TEX2", "TFCP2", "THAP3", "THAP7", "TIMM17B", "TIMM50", "TMCO6", "TMED3", "TMEM147", "TMEM186", "TMEM209", "TMEM41B", "TMF1", "TRAPPC6A", "TRIB3", "TRIM35", "TRIP4", "TRMT1", "TRPC4AP", "TWF2", "UNK", "UPF3B", "UROS", "USP28", "VAPB", "VIM", "WBP4", "YIPF6", "ZBTB34", "ZBTB41", "ZBTB48", "ZC3HAV1", "ZDHHC12", "ZDHHC4", "ZFP62", "ZHX3", "ZKSCAN1", "ZKSCAN2", "ZKSCAN3", "ZNF16", "ZNF174", "ZNF219", "ZNF22", "ZNF25", "ZNF251", "ZNF280C", "ZNF282", "ZNF32", "ZNF324", "ZNF397", "ZNF410", "ZNF444", "ZNF462", "ZNF496", "ZNF507", "ZNF514", "ZNF526", "ZNF530", "ZNF543", "ZNF627", "ZNF628", "ZNF641", "ZNF670", "ZNF714", "ZNF740", "ZNF768", "ZNF777", "ZNF783", "ZNF784", "ZNF786", "ZNF821", "ZRANB3"], "prepass_kernel": "rcell-prepass-k562-r1", "cap": 128, "max_controls": 2048, "seed": 2026}')
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
if P["key"] not in st["key_names"]:
    raise SystemExit("the prepass state does not know the key " + P["key"])
known = set(st["symbols"])
targets = [{"key": P["key"], "symbol": s} for s in P["symbols"]]
(OUT / "targets.json").write_text(json.dumps(targets, indent=0))
log = {"mounts": {"gen": str(GEN), "prepass": str(PRE)}, "holdout_group_of_prepass": st.get("holdout_group"),
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
