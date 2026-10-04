"""Extract timing boundaries from the existing pilot log without rerunning the prepass."""
import hashlib
import json
from pathlib import Path

source = Path("C:/Users/ferra/vcc2026-data/processed/rete_cellulare_2026-10-03/out_prepass_hepg2_r1/prepass/train_log.jsonl")
output = Path(__file__).resolve().parent / "timing_audit_r1.json"
raw = source.read_bytes()
events = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
phases = {}
for phase in ("first read", "second read", "prepass done"):
    rows = [r for r in events if r.get("msg") == phase]
    phases[phase] = {"count": len(rows), "first_t": rows[0]["t"], "last_t": rows[-1]["t"]}
assert phases["first read"]["count"] == phases["second read"]["count"] == 365
result = {
    "source": str(source), "sha256": hashlib.sha256(raw).hexdigest(), "phases": phases,
    "gap_between_read_receipts_seconds": phases["second read"]["first_t"] - phases["first read"]["last_t"],
    "interpretation": "The gap includes global planning and waiting for the first second-read result; it is not a direct profile of global computation.",
    "action": "Profile identity, QC, class assignment, evaluation groups, quota construction, serialization and worker startup separately before choosing the execution strategy.",
}
with output.open("x", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
    f.write("\n")
print(json.dumps(result))
