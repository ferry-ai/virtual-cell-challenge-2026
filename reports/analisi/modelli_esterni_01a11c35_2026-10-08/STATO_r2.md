# Stato e consegna r2 — 8 ottobre 2026

**Approfondire.** PIE è il candidato principale sul piano scientifico; ESM2 più
ridge mascherata è l'alternativa operativamente più leggera. L'integrazione isolata
è implementata e verificata su fixture; nessuna predizione biologica o misura di
vantaggio è stata prodotta. Questo non è un candidato promosso per il freeze.

Ora letta dal sistema durante la preparazione della nota: 18:31 Europe/Rome.
Questa nota aggiorna `CONSEGNA.md` senza riscriverne la situazione precedente.

## Pronto e consegnato

- Ricerca e confronto delle forme di adozione in `CANDIDATI.md`: congelato,
  feature, teacher, residuale, gating, distillazione e fine-tuning; fonti primarie
  e limiti separati dai risultati pubblicati su altri benchmark.
- Reader PIE con tre teste distinte, assi, hash, maschere e fallback; rifiuto
  delle esposizioni incompatibili e del bridge non verificato. Nessuna calibrazione.
- `export_stage100.py` produce file per contesto con `targets`, `genes`, `lfc`
  float32 ln e `observed` bool; assenza = zero con maschera falsa. Non applica
  ×1,5 dell'emissione, ampiezza, centratura o cis. Legge solo l'output verificato
  dell'adattatore, non converte arbitrariamente output ESM2 nativi.
- Runner ridge originale: alpha 1.0 preregistrato; `context_ids` sono identità
  studio/linea/stato e governano unicità e ricevuta D-053; `context_groups` sono
  lignaggi e governano esclusioni C/J. Studi diversi con stesso lignaggio/target
  restano righe distinte. Nessun pooling automatico. Query richiede entrambi.
- Inventario acquisizione con revisioni/hash e acquisitore riprendibile; nessun
  payload acquisito. DATI-TRANSFER ha confermato di non aver trovato questi asset.

Comando aggiuntivo dopo il bridge PIE:

```powershell
.\scripts\py.cmd reports/analisi/modelli_esterni_01a11c35_2026-10-08/export_stage100.py --source <output_adattatore> --out <nuova_cartella>
```

`expected_rows_by_context` nel manifest ridge conta i **context_ids**; il NPZ train
deve ora contenere `context_ids` oltre ai campi della consegna r1. I simboli devono
essere canonici. DATI-TRANSFER applica hidden_rule anche ai target fuori pannello
e ad ogni componente prima delle statistiche: la lista dei soli 66 bersagli del
pannello non basta. La ricevuta del runner non sostituisce questo audit upstream.

## Protocollo e provenienza

VALIDAZIONE è la sessione Claude Code `8a8ca58a`, trovata nel commit `c9fd904`;
non occorre più chiedere al proprietario il nome della chat. Accettato il contratto
v1 prima dei risultati: `ACCORDO_VALIDAZIONE_v1.md`. Registro e indice della nostra
cartella sono stati aggiunti dal responsabile, senza modifiche nostre ai condivisi.

`exposure_public_r1.json` ricostruisce dai soli indici pubblici train/val:

| Fold checkpoint | Linee con label train/val | Righe train / val |
|---|---|---|
| HepG2 | Jurkat, K562, RPE1 | 2670 / 298 |
| Jurkat | HepG2, K562, RPE1 | 2526 / 280 |
| K562 | HepG2, Jurkat, RPE1 | 2603 / 290 |
| RPE1 | HepG2, Jurkat, K562 | 2550 / 284 |

**Misurato:** hash, identificativi e conteggi degli indici alla revisione fissata.
Non certificano contenuto dei pesi, selezione upstream mai guidata dal test o
completezza delle esposizioni. Ledger deliberatamente non marcato reviewed.
DepMap e fonti di conoscenza restano esposizioni distinte da giudicare.
H1 test non aperta. Il piano iniziale acquisisce HepG2: non usarlo per C-K562;
serve un piano con checkpoint/fold K562 e relativi hash, oppure escludere quel
confronto come inadmissibile. Non cambiare fold dopo aver visto lo score.

I 6.290 geni in comune con l'asse Replogle sono il supporto del pilot nativo,
non una dimostrazione di un limite architetturale assoluto di PIE su nuovi geni.
La query di un nuovo asse richiede la preparazione e verifica degli input relativi.

## Misure e verifiche

- `interface_tests_r3.txt`: 13 test piccoli passati in 3,937 s, inclusi
  roundtrip parquet→adattatore→stage100, alterazione hash, assi, esclusioni,
  perdita mascherata, confronto con least squares indipendenti e studi distinti.
- `docs_check_r2.txt`: controllo documentale passato; r1 conserva il difetto di
  registrazione anteriore al commit di VALIDAZIONE.
- `repo_tests_r1.txt`: 290 test in 365,910 s, tre errori per assenza di
  `cell_eval2.config` e due errori di indice Git per cartelle ancora non tracciate
  della nostra sessione e di DATI-TRANSFER. Non sono successi; nessuna modifica
  all'ambiente condiviso per mascherarli. Il test degli indici va ripetuto dopo
  l'aggiunta dei nostri file; la cartella altrui resta responsabilità del suo autore.

Verifica finale del pacchetto: `interface_tests_r4.txt`, 13 prove passate in
10,342 s, include zero+maschera falsa nell'export. `tree_tests_r2.txt` dopo l'aggiunta
dei nostri file: 11 test, rimane un solo errore relativo alla cartella non ancora
tracciata di DATI-TRANSFER; il difetto della nostra cartella è risolto.
`docs_check_r3.txt` segnala un nuovo file di stato `banco/r1/status_r9.json` della
sessione VALIDAZIONE non ancora coperto dal suo registro. È cambiamento concorrente,
non una correzione effettuata da noi. L'ultimo controllo globale non è quindi verde;
il precedente r2 era passato. Nessuno dei due è prova di beneficio biologico.

## Cosa manca alla prova scientifica

1. Risposta alla richiesta esplicita già presentata per scaricare asset e usare
   cloud. Drive è autorizzato come archivio. PIE minimo 45.644.647.954 byte;
   ESM2 solo 98.539.820 byte. Non sono stati lanciati download, cloud, invii o push.
   Il portatile ha circa 121 GB liberi nella misura iniziale; il vincolo più
   importante è preparare il runtime con gli asset necessari, non la sola RAM.
2. Vista CRISPRi del fold da DATI-TRANSFER, con contesti/righe effettivi,
   esclusioni, pesi, scale e policy esplicita sulle feature mancanti. T1 r1 è
   produzione; non può diventare una vista di validazione per rinomina.
3. Review esposizioni/licenza e bridge di normalizzazione da VALIDAZIONE.
   `ln(2)` non dimostra equivalenza delle quantità. Le condizioni PIE non
   commerciali e l'assenza di licenza esplicita in PIE_sources sono in CANDIDATI.
4. Inferenza reale, congelamento hash delle predizioni e valutazione indipendente
   secondo §8; solo allora decisione adottare/scartare. Nessuno score inventato.

La regola locale che richiede il permesso è `CLAUDE.md`, Global rules:
“The owner authorises anything that spends quota […] every download and every
push, in chat.” La richiesta pendente riguarda asset e calcolo; l'autorizzazione
alle comunicazioni DATI-TRANSFER/VALIDAZIONE è già stata concessa e utilizzata.
