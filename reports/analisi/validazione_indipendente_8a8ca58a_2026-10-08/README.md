# Validazione indipendente — sessione 8a8ca58a, 8 ottobre 2026

Claude Code, sessione `8a8ca58a`, incarico del proprietario in chat: protocollo scientifico, banco di valutazione,
controlli indipendenti, confronto dei candidati e raccomandazione per la consegna della notte fra l'8 e il 9
ottobre. Binario [R-LEAD](../../../docs/piani/strategia-scientifica.md), che resta la sede delle decisioni operative.
Questa cartella possiede protocollo, banco, risultati comparativi e raccomandazione; **non** possiede banca, trainer
e pipeline di produzione (DATI-TRANSFER, sessione `01a11c34`) né l'adattatore esterno (MODELLI-ESTERNI, sessione
`01a11c35`). Checkpoint: [CP-0069](../../../docs/checkpoints/0069-validazione-indipendente-t1-e-ampliamento.md)
e, per T2, [CP-0070](../../../docs/checkpoints/0070-t2-centratura-su-tutti-i-bersagli.md).

**Esito in una riga:** la consegna resta t36; T1 è valida e inconcludente; T2 è valido e **sfavorevole**
([risultati](RISULTATI_T2.md)); la componente esterna non è arrivata alla valutazione. I numeri dei banchi sono
**locali e di sviluppo**, non punteggi VCC.

## Che cosa leggere prima

1. [RACCOMANDAZIONE.md](RACCOMANDAZIONE.md): candidato, ripiego, esiti classificati, questioni aperte.
2. [RISULTATI_LIVELLO_A.md](RISULTATI_LIVELLO_A.md) e [RISULTATI_LIVELLO_B.md](RISULTATI_LIVELLO_B.md): che cosa è
   misurato, che cosa è interpretazione.
3. [AUDIT_DATI_E_LEAKAGE.md](AUDIT_DATI_E_LEAKAGE.md): uso dei dati, leakage, segnalazioni ai proprietari.

## Indice per area

| Area | File | Tipo |
|---|---|---|
| **Contratto** | [PROTOCOLLO_v1.md](PROTOCOLLO_v1.md), [PROTOCOLLO_v2.md](PROTOCOLLO_v2.md) (emendamento: misura di discriminazione, livello B su due fold) | protocolli congelati prima dei numeri che leggono |
| | [manifest_fold_v1.json](manifest_fold_v1.json), [manifest_fold_v2.json](manifest_fold_v2.json), [build_manifest.py](build_manifest.py), [build_manifest_v2.py](build_manifest_v2.py) | manifest dei fold C/T/J, lignaggi con alias, bracci, regola dei bersagli nascosti |
| | [splits_v1/](splits_v1/INDEX.json), [export_splits.py](export_splits.py) | uno split esplicito per fold, nel formato del consumer di DATI-TRANSFER |
| | [LIVELLO_B.md](LIVELLO_B.md) | come si esegue il banco a sei membri, scritto prima dei suoi numeri |
| **Piani scritti prima delle corse** | [SCOMPOSIZIONE_K0.md](SCOMPOSIZIONE_K0.md), [ESPLORATIVO_SENZA_KOLF.md](ESPLORATIVO_SENZA_KOLF.md), [REGIME_J.md](REGIME_J.md) | piani descrittivi o esplorativi, nessuna regola di adozione |
| | [VALUTAZIONE_T2.md](VALUTAZIONE_T2.md) | T2 sui fold con i vettori comuni consegnati da DATI-TRANSFER: bracci, controlli e lettura con il §8 invariato |
| **Risultati** | [RISULTATI_LIVELLO_A.md](RISULTATI_LIVELLO_A.md), [RISULTATI_LIVELLO_B.md](RISULTATI_LIVELLO_B.md), [RISULTATI_T2.md](RISULTATI_T2.md) | misure e loro lettura; T2 ha la sua pagina, con validità della corsa, meccanismo e i due livelli |
| | `TABELLE_*.md` | tabelle scritte dai lettori, nessun numero ricopiato a mano: livello A ([v1](TABELLE_LIVELLO_A_r1.md), [v2](TABELLE_LIVELLO_A_r1_v2.md)), [scomposizione](TABELLE_SCOMPOSIZIONE_K0_r2.md), [esplorativo](TABELLE_ESPLORATIVO_r3.md), [regime J](TABELLE_REGIME_J_r4.md), livello B ([esito](TABELLE_LIVELLO_B_r1.md), [K562](TABELLE_LIVELLO_B_k562_r1.md), [iPSC](TABELLE_LIVELLO_B_ipsc_r1.md), [esplorativo su K562](TABELLE_LIVELLO_B_k562_x1.md)); T2 ([contrasti](TABELLE_T2_r5.md), livello A con [`disc95`](TABELLE_LIVELLO_A_r5_v2.md) e con [`disc`](TABELLE_LIVELLO_A_r5_v1.md), sei membri su [iPSC](TABELLE_LIVELLO_B_ipsc_t2.md) e [K562](TABELLE_LIVELLO_B_k562_t2.md), esito [alla scadenza](TABELLE_LIVELLO_B_t2_r1.md) e [con due fold](TABELLE_LIVELLO_B_t2_r2.md)) |
| **Audit** | [AUDIT_DATI_E_LEAKAGE.md](AUDIT_DATI_E_LEAKAGE.md), [audit/](audit/audit_catena_r2.json) | catene di provenienza, uso effettivo dei dati, leakage, segnalazioni; al §8 i vettori di T2 ([verifica](audit/audit_vettori_t2_r1.json)) |
| **Decisione e consegna** | [RACCOMANDAZIONE.md](RACCOMANDAZIONE.md), [consegna/CONSEGNA.md](consegna/CONSEGNA.md), [consegna/riserva_t36_r1.json](consegna/riserva_t36_r1.json) | raccomandazione; manifest, versioni, hash e riproduzione; verifica del pacchetto t36 |
| **Coordinamento** | [MESSAGGI.md](MESSAGGI.md), [preflight_kaggle_r1.json](preflight_kaggle_r1.json) | risposte scritte agli altri due incarichi; stato dei kernel alle 18:06 |
| **Verifiche della repo** | [verifiche/](verifiche/tests_r1.txt) | suite, controllo dei documenti, test di DATI-TRANSFER rieseguiti |

## Il banco (`banco/`)

| File | Che cosa fa |
|---|---|
| [metrics.py](banco/metrics.py), [bench_core.py](banco/bench_core.py) | misure per bersaglio del livello A, contrasti con bootstrap appaiato sui bersagli, controlli, audit di tabelle e voti; [test_metrics.py](banco/test_metrics.py) e [test_bench_core.py](banco/test_bench_core.py), 16 prove, con parità contro `multisource.transfer_report` |
| [logo_driver.py](banco/logo_driver.py) | il kernel del livello A: fonti trovate per contenuto, parità degli effetti di produzione, stadio 100 su cache senza il lignaggio escluso, regime J su tabelle filtrate, bracci d'analisi ed esterni |
| [prepara_banco.py](banco/prepara_banco.py) | pacchetto, preflight, lancio unico con registro, raccolta e verifica del codice salvato; `analisi_rN.json` descrive bracci e contrasti in più |
| [prepara_estrazione.py](banco/prepara_estrazione.py), [prepara_livello_b.py](banco/prepara_livello_b.py) | cellule vere dei bersagli del pannello per un fold; banco a sei membri con `bench_v2.py` non modificato |
| `leggi_*.py` | lettori: livello A con la regola del §8, livello B con esito per contrasto, coppie di un banco, scomposizione, contrasti qualunque, regime J |
| [ricalcolo_locale.py](banco/ricalcolo_locale.py), [sensibilita_disc95.py](banco/sensibilita_disc95.py), [verifica_voto_singolo.py](banco/verifica_voto_singolo.py) | controlli indipendenti sul portatile: misure ricalcolate, convenzione delle maschere, voto nullo della tabella a un bersaglio |
| [descrivi_t2.py](banco/descrivi_t2.py), [comune_t2.py](banco/comune_t2.py), [sensibilita_disc_t2.py](banco/sensibilita_disc_t2.py), [confronta_coppia.py](banco/confronta_coppia.py) | per T2: parità a gamma 0 e bersagli scambiati, parte comune rimessa negli effetti, misura stretta con e senza il fold dove non è utilizzabile, riproducibilità di una coppia fra due kernel |
| `r1/` … `r5/` | corse del livello A: pacchetto, lancio, ricevute, risultati, letture. r1 contratto; r2 scomposizione; r3 esplorativo; r4 regime J; r5 T2 |
| [prepara_vettori_t2.py](banco/prepara_vettori_t2.py), `t2_vettori_r1/` | i vettori comuni di T2 consegnati da DATI-TRANSFER: verifica contro la consegna, bersagli dietro ogni vettore, dataset privato per il kernel |
| `celle_*_r1/`, `livello_b_*/` | estrazioni delle cellule vere e banchi a sei membri: pacchetto, lancio, uscite raccolte |

Le tabelle per bersaglio (3–5 MB per corsa) e le copie degli effetti dei fold stanno nella radice dati,
`processed/validazione_indipendente_8a8ca58a_2026-10-08/`; qui restano i puntatori con dimensione e sha256
(`POSIZIONE_per_target.json`, `effetti.json`).

## Regole di questa cartella

- Un numero comparativo si legge solo con la regola del §8 del protocollo che era congelato quando è stato prodotto.
- I punteggi dei banchi sono **locali**: non sono punteggi VCC. I punteggi ufficiali stanno solo in
  [reports/invii/README.md](../../invii/README.md).
- Nessun file di un altro incarico è modificato da qui: un problema trovato diventa una segnalazione con
  riproduzione minima, impatto e criterio di accettazione, consegnata al suo proprietario.
- Gli artefatti di validazione (effetti a lignaggio escluso, banchi) non sono artefatti di produzione e non si inviano.
