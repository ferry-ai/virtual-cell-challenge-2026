"""Register the inherited CD4 transport failure and its already observed independent recovery."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
LEDGER = REPO / "reports/analisi/lead_scientist_2026-09-29/learning"
sys.path.insert(0, str(LEDGER))
import ledger

source = Path("C:/Users/ferra/vcc2026-data/processed/ingestione_completa_2026-10-03/")
source /= "out_vcc-cd4-d3-rest-p1of2-r1_error/vcc_cd4_d3_rest_p1of2_r1/shards.log"
dest = HERE / "cd4_d3_rest_p1_error.log"
with dest.open("xb") as f:
    f.write(source.read_bytes())
verified = REPO / "reports/sorgenti/ingestione_completa_2026-10-03/cd4/esito_verifica_d3_rest_r1/source_complete.json"
v = json.loads(verified.read_text())
assert v["ok"] and all(v["verdict"].values())
evidence = [{"path": p.relative_to(REPO).as_posix(), "sha256": ledger.sha(p), "bytes": p.stat().st_size,
             "supports": claim} for p, claim in [(dest, "IncompleteRead nella lettura di un blocco remoto"),
                                                 (verified, "Rilettura indipendente dell'unione p0 r1 e p1 r2")]]
record = dict(schema_version=1, eid="E-20261004-002", revision=1, previous_sha256=None,
              recorded_utc=datetime.now(timezone.utc).isoformat(), claim_type="operational_incident",
              state="verified_remotely", title="CD4 D3_Rest p1: lettura HTTP incompleta, rilancio r2 verificato",
              symptom="Il kernel p1 r1 si ferma con IncompleteRead: 8378417 byte letti, 10191 ancora attesi.",
              cause="Trasferimento HTTP interrotto durante r.read(); la causa di rete o del servizio non è isolata.",
              cause_verified=False,
              fix="Claude ha rilanciato la stessa parte come p1 r2, conservando r1; la verifica indipendente di linea è passata.",
              regression_test="La verifica deve rifiutare una parte senza complete.json e unione con buchi o SHA divergenti.",
              next_guard="Mai montare r1 fallita come parte valida; richiedere stato COMPLETE e verifica indipendente di copertura, celle e SHA.",
              scope="Solo recupero di CD4 D3_Rest; nessuna correzione generale al trasporto HTTP dichiarata.",
              evidence=evidence,
              remote_verification={"evidence_path": evidence[1]["path"], "observed_utc": v["utc"],
                                   "criterion": "139 shard riletti con SHA corretti; 2778524 righe = 1901024 celle idonee + 877500 escluse; intervalli contigui."})
print(ledger.append(LEDGER / "incidents", record))
