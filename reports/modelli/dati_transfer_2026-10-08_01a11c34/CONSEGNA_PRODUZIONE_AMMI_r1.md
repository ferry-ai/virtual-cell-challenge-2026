# Input AMMI produzione — consegna del 9 ottobre sera

**Misurato sui metadata:** [inventario completo](production_input_handoff_r1.json),
calcolato da [script](production_input_handoff.py) con la stessa selezione di chunk
del builder MODELLI v4, il cui hash è registrato. Nessuna estrazione o lancio nuovo.
Le visibilità K562/H1 sono state [verificate sul servizio](production_source_visibility_r1.json).

## Percorso minimo per trasferimenti

| Runtime | File privati tra account, inclusi metadata | Byte | Payload esclusi completion già locali |
|---|---:|---:|---:|
| davideferrante11 | 153 | 5.387.144.661 | 135 file, 5.387.051.931 byte |
| davidmaisterx | 225 | 10.101.106.516 | 209 file, 10.100.920.946 byte |

Su **df11** sono nativi per proprietà gli aggregati H1/K562, le 12 parti NTC r5,
le ancore di produzione e i controlli A/B/C; i 18 produttori di aggregati pubblici
sono accessibili da entrambi gli account. Mancano 81 chunk privati davideferante
(HIPSCI, Tian 2019 iPSC/neuron, Tian 2021 CRISPRi, Xu: 1.154.415.074 byte)
e le 18 parti NTC conservate nei tre kernel privati MX r6a/r6b/r7a
(72 file, 4.232.729.587 byte; i 18 completion JSON sono già locali).

Su **MX** le 18 parti NTC sono native. Fra i file privati necessari, 131 hash
hanno locator già emessi per i pilot; altri 94 hash non sono in quella mappa,
inclusi i 74 chunk K562. La presenza di un locator non ne prova la validità
temporale e non autorizza una destinazione nuova.

**Accessi produzione non autorizzati dal consenso pilot:**
`ammi_private_access_authorization_r1.json` dichiara
`production_inputs_authorized: false`. Servono destinatario e contenuti esatti
per la produzione. Questa consegna non emette locator e non effettua trasferimenti.
La classificazione nativa usa proprietà e visibilità verificate; il mount effettivo
e gli hash numerici devono ancora essere controllati nel runtime scelto.

## Copertura e contratto

- View ammessa: 203.975 righe × 18.533 geni, 47 contesti CRISPRi.
- Selezione builder: 1.478 chunk, **24.449.227.359 byte compressi**;
  il totale mmap della view misura un oggetto differente.
- 43 contesti con supervisione sul pannello prima del filtro features;
  senza bersagli nel pannello: HepG2 Nadig, Jurkat Nadig, K562 essential,
  RPE1, con ID esatti nel JSON. Restano presenti nei controlli.
- 30/30 parti NTC: 1.329.117 candidati prima del merge globale;
  8.832 controlli ufficiali A/B/C, 11 ancore logiche di produzione.
- 1.618 hash unici complessivi, 36.584.109.758 byte. Il runtime deve
  verificare spazio temporaneo e strategia di lettura; nessuna RAM o ETA dedotta.

Il manifest NTC finale è `ntc_ready_manifest_r2.json`; per il builder usare
`ammi_ntc_runtime_contract_r3.json` e le verifiche PASS dei produttori/restauri,
includendo `ntc_df11_terminal_verified_r1.json` e `official_ntc_verified_r1.json`.
Le ancore sono in `production_anchors_verified_r1.json` e il contratto in
`panel_anchor_requests_production_r1.json`. Non sostituire queste ancore con i pilot.

L'uso effettivo va misurato nel fit: questo inventario non dichiara completo D-053.
ESM/code restano quelli del builder MODELLI. La decisione congelata dopo i contrasti
cells–T0 e cells–none resta un prerequisito distinto dagli accessi. MODELLI mantiene
l'esclusiva del confezionamento e del lancio.
