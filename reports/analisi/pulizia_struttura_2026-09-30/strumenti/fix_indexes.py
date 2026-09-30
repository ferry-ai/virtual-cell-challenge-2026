"""Correct the stale rows of the category indexes listed in RIORDINO section 6.

Each replacement is exact and must match once; bytes and line endings are kept.
Sources, verified before writing:
- prova generale D4/D9: docs/piani/revisione-critica.md, "Correzioni (29/09 pomeriggio)";
  reports/invii/prova_generale_2026-09-28/RISULTATI.md, "Correzioni dei difetti"; commit 117b2a8.
- lezioni_invii: reports/analisi/lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md, 2.2 and 2.4.
- t23 sent: reports/invii/README.md, score row t23 (+0,141868, CP-0042).
- codex audit: docs/REGISTRO.md R-019 and R-020 (recovered on 28/09 into
  reports/analisi/audit_piani_dati_2026-09-26/); r1 review in the folder's agenti/.
- 3': reports/analisi/lead_scientist_2026-09-29/AUDIT_DATI.md, section 1.
- basali_asse: r1/ empty on disk, session f4f38e58 closed (riordino_repo_2026-09-30).
- K562 bench: no r1/ in the folder; arms built and copied to Drive (commit e7c933b, 29/09 19:48).
"""
from pathlib import Path

REPO = Path(r"C:/Users/ferra/OneDrive/Desktop/vcc2026")
EDITS = {
    "reports/invii/README.md": [
        ("previsioni 1, 3–6 vere; D1 corretto; da correggere D4 (cache sbagliata in silenzio) e D9 (riferimento di γ) (CP-0044)",
         "previsioni 1, 3–6 vere; D1 corretto (CP-0044). D4 (cache sbagliata in silenzio), D9 (riferimento di γ) e gli altri "
         "difetti di codice sono corretti il 29/09 pomeriggio con i loro test (RISULTATI, «Correzioni dei difetti»); resta la "
         "forma piena"),
        ("tosato a 0 in tutti i nostri invii) | sì; il rumore viene da una sola coppia di semi |",
         "tosato a 0 in tutti i nostri invii) | in parte: l'[audit del 29/09](../analisi/lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md) "
         "ne corregge due letture, il rumore stimato da una sola coppia di semi (§2.2) e il peso della risposta comune "
         "sull'MSE (§2.4) |"),
    ],
    "reports/trasferimento/README.md": [
        ("Il t23 (quota condivisa) è pronto e non inviato; [l'ablazione]",
         "Il t23 (quota condivisa) è stato inviato il 28/09: +0,141868, non conclusivo "
         "([CP-0042](../../docs/checkpoints/0042-t23-esclusione-pds.md)); [l'ablazione]"),
        ("in parte: vale solo r5; l'audit di codex che ha trovato le perdite non è nel repository |",
         "in parte: vale solo r5. L'audit di codex sui centri calcolati prima degli split è in "
         "[analisi/audit_piani_dati_2026-09-26/](../analisi/audit_piani_dati_2026-09-26/RISULTATI.md), recuperato il 28/09 "
         "(R-019, R-020); la revisione di r1 è in `agenti/` |"),
    ],
    "reports/modelli/README.md": [
        ("le due Orion sono dello stesso studio e le\n  sorgenti sono quasi tutte in 3'.",
         "le due Orion sono dello stesso studio, e\n  ogni sorgente ha la sua piattaforma: K562 in 3′, CD4 in Flex, "
         "Orion in GEM-X 5′ secondo le schede, da\n  riverificare ([audit dei dati](../analisi/lead_scientist_2026-09-29/AUDIT_DATI.md), §1)."),
    ],
    "reports/sorgenti/README.md": [
        ("Azione 5 di R-REV, in corso nella sessione Claude: protocollo per richiudere i CPM sull'asse comune, verificarli "
         "dal grezzo e misurare l'impatto sulle quote t23/t27 e sui lettori | protocollo, esiti ancora da aggiungere |",
         "Azione 5 di R-REV: protocollo per richiudere i CPM sull'asse comune, verificarli dal grezzo e misurare l'impatto "
         "sulle quote t23/t27 e sui lettori. La sessione `f4f38e58` si è chiusa senza eseguirlo: `r1/` è vuota | solo "
         "protocollo, nessun esito |"),
    ],
    "reports/generatore_e_banchi/README.md": [
        ("Protocollo e regola fissati alle 18:10, prima del codice | protocollo |",
         "Protocollo e regola fissati alle 18:10, prima del codice | protocollo; bracci costruiti e copiati su Drive il "
         "29/09 sera, job non ancora eseguito (nessun `r1/`) |"),
    ],
}

for rel, pairs in EDITS.items():
    p = REPO / rel
    raw = p.read_bytes()
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8").replace("\r\n", "\n")
    for old, new in pairs:
        assert text.count(old) == 1, (rel, old[:70], text.count(old))
        text = text.replace(old, new)
    p.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))
    print(rel, len(pairs), "crlf" if crlf else "lf")
