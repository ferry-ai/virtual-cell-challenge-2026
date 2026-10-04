# Prossimo ibrido: piano e audit del prepasso

4 ottobre 2026, Codex, chat `01a10649-0c7f-7551-8bfe-8eca0fe03654`, macchina `LAPTOP-DLG1LHV1`. Mandato del proprietario: prendere in carico l'audit del prepasso e preparare il prossimo training, lasciando a Claude1 la chiusura dello score e la diagnosi del banco. Partenza da `13099149ed49c86af3e8d1faa95ca2e887f3ecea`.

| File | Contenuto e stato |
|---|---|
| [PROMPT_CLAUDE1.md](PROMPT_CLAUDE1.md) | Consegna da passare a Claude1: score, difetti riprodotti, banco/export e cause candidate |
| [PIANO_TRAINING.md](PIANO_TRAINING.md) | Piano del prossimo ibrido e dipendenze; proposta, non protocollo congelato |
| [AUDIT_PREPASSO.md](AUDIT_PREPASSO.md) | Riconti del pilot e prova eseguibile della perdita di un contesto sotto 30 controlli |
| [audit_prepass.py](audit_prepass.py), [audit_r1.json](audit_r1.json) | Codice della verifica locale, hash e risultati; nessun cambiamento al trainer |
| [VINCITORI_2025.md](VINCITORI_2025.md) | Fonti primarie ricontrollate e contrasti per pseudobulk, cellule, ESM2 e distribuzioni |
| [audit_score.py](audit_score.py), [score_audit_r1.json](score_audit_r1.json) | Ricalcolo indipendente sui JSON ufficiali comparsi durante la sessione; nessuna chiamata al sito |
| [audit_timing.py](audit_timing.py), [timing_audit_r1.json](timing_audit_r1.json) | Intervallo fra le due letture nel log HepG2: la pianificazione globale va profilata prima di scegliere la distribuzione |
| [VERIFICHE.md](VERIFICHE.md) | Esiti dei controlli e limiti della suite generale nel checkout condiviso |

## Risultato ufficiale disponibile durante il lavoro

**Misurato sullo status originale:** t30 **0,135248601985599**, delta t25 **−0,00498945892923655**, delta t28 **−0,0095966030208608**. Media dei sei scalati ricontrollata; stesso pannello e versione delle ancore. La regola congelata ricade nel ramo b, non conclusivo, appena sopra la soglia di perdita −0,005: questo non promuove il modello né annulla il peggioramento osservato.

Il PDS scalato perde **0,04223697**: contributo alla media **−0,00703950**. Fedeltà (+0,01372641 sul membro) e Jaccard (+0,00230591) compensano in parte; NMAE e reach peggiorano leggermente. La MSE scalata resta zero, mentre il grezzo peggiora da 3,01717 a 3,16823. Il primo problema da diagnosticare è quindi la perdita di discriminazione, non un fallimento uniforme di tutte le metriche. Il dato non identifica la causa né il contesto responsabile.

La chiusura canonica (checkpoint, STRADE, indice invii) resta a Claude1: questa lettura non crea uno score distinto. Fonti: [status t30](../../invii/trial_2026-10-04/status_lDMSYUZU5cFYHcRqI0lq.json), [status t25](../../invii/trial_2026-09-27/status_ekxW6wo83Csum25pkddl.json), [status t28](../../invii/trial_2026-09-29/status_ZvrYZ4UazadAyuq4AsDB_20260929T2305.json).

## Perimetro e limiti

Eseguiti soltanto riconti leggeri e fixture sul portatile; lettura di fonti web primarie. Nessun nuovo training, download di dataset/pesi, job cloud, invio o push. La prova del prepasso non misura la sufficienza biologica dei controlli; l'audit dei JSON non ricertifica l'archivio o il corpus ampliato. Il piano prevede quella verifica prima dell'accettazione del prossimo training.

Coordinamento e prossimo passo nella sottoattività di [R-LEAD](../../../docs/piani/strategia-scientifica.md). Nessuna modifica al codice o agli output delle altre sessioni.
