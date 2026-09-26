import json
import sys

j = json.load(open(sys.argv[1], encoding="utf-8"))
rows = sorted(j["files"].items(), key=lambda kv: kv[1]["applied_utc"])
for name, e in rows:
    print(f"{name:18s} pool {e['pool']} MiB {e['bytes'] / 2**20:5.0f} dl {e['download_s']:5.1f} ap {e['apply_s']:5.1f} "
          f"dec {e.get('decode_s', 0):4.1f} disk {e.get('disk_s', 0):4.1f} cells {e['pass_cells']:6d} "
          f"tg {e['targets']:6d} reg {e['registry']:6d} ws {e.get('ws_mib')} pk_ws {e.get('peak_ws_mib')} "
          f"priv {e.get('private_mib')} pk_priv {e.get('peak_private_mib')} int {e.get('integer_counts')}")
print(len(rows), "files; rebuilds", len(j["rebuilds"]))
