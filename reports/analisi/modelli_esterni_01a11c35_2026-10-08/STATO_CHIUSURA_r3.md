# Due fit AMMI none completati; cells attende NTC

Snapshot del 9 ottobre 2026, verifica metadati conclusa alle 18:12 UTC.
Integra gli snapshot precedenti senza sostituire le ricevute originali.

## Misurato

I due job privati `davidmaisterx/ammi-c-k562-none-17-01a11c35-r5` e
`davidmaisterx/ammi-c-ipsc-none-17-01a11c35-r5` sono COMPLETE. Il codice remoto
corrisponde esattamente ai pacchetti preparati. Le ricevute attestano CUDA
Tesla T4, seme17, due epoche e guardie superate; tutte le righe selezionate e
le masse previste sono consumate in ciascuna epoca.

| Fold | Righe per epoca | Contesti con righe | Lignaggi | Export nativi | Ottimizzazione, due epoche |
|---|---:|---:|---:|---:|---:|
| C-K562 | 384 | 30 | 5 | 2 | 1,022 s |
| C-iPSC | 925 | 18 | 5 | 24 | 1,716 s |

Sono tempi dell'ottimizzazione, non del job. La fase risposte richiede
133,909 s e 579,845 s rispettivamente; fit inclusi checkpoint/guardie
98,511 s e 23,508 s; export 8,190 s e 112,026 s. Non sono un benchmark fra
fold o una previsione dei tempi cells.

Evidenze: `ammi_c-k562_none_metadata_verified_r1.json` e
`ammi_c-ipsc_none_metadata_verified_r1.json`, che fissano hash delle ricevute
di raccolta e di identità remota. `summarize_ammi_metadata_v1.py` ricontrolla
gli hash dei metadati raccolti, copertura per epoca, masse, esclusioni e CUDA.
Il codice produttore verificato impone parità esatta dopo ricarica del
checkpoint prima di scrivere COMPLETE. I binari restano nel cloud: i loro
hash saranno verificati integralmente al consumo nel banco.

Questi sono i due fit iniziali previsti, recuperati dopo l'errore tecnico r4
prima dell'ottimizzatore. L'emendamento `AMMI_NONE_SENZA_NTC_r1.md` e la prova
`none_equivalence_r2.json` consentono none senza leggere controlli cellulari:
nessuna cellula fittizia. Cells conserva l'obbligo di tutte le NTC.

## Limiti della copertura e del risultato

È un pilot, non D-053 completo. Le esclusioni sono K562+CD4T nel primo fold,
iPSC+K562 nel secondo. HepG2, Jurkat e RPE1 hanno zero supervisione nel
pannello con supporto comune; le ricevute nominano queste lacune. Il limite
prefissato di 64 righe per contesto resta applicato. Tutti i contesti con
righe selezionate sono effettivamente usati, ma questo non equivale a usare
tutte le perturbazioni del catalogo.

Guardie superate e lieve riduzione della loss non dimostrano beneficio.
Il confronto esterno resta da eseguire, con A0 (ancora annidata) distinta dal
T0 originale, cells–A0 e cells–none su entrambi i fold e gli altri contrasti
congelati. Un solo seme non dimostra stabilità. Nessun fit di produzione AMMI
o invio AMMI è stato avviato. ESM2 resta concluso senza beneficio dimostrato:
`RISULTATI_CHIUSURA_ESM2_r1.md`.

## Dipendenze ancora aperte

Alle 18:12:26 UTC il watcher DATI PID912 indica RUNNING per il produttore
`davideferrante11/dt-ntc-inputs-01a11c34-r5`; mancano ancora le ricevute finali
delle 12 parti. Nessuna esclusione di parti per anticipare cells.
DATI ha trasferito a questa chat la sola esecuzione una tantum di
`extend_ammi_access_ntc.py` dopo `ntc_df11_terminal_verified_r1.json` e
`ntc_ready_manifest_r2.json`, verificando prima l'assenza di
`ammi_private_access_with_ntc_r1.json`. Il consenso umano AMMI copre questo
passaggio. La raccolta/verifica NTC resta al watcher DATI; non lo duplico.

Il preflight in sola lettura `ammi_bank_base_access_preflight_r1.json`
dimostra che MX non accede ai 3 dataset e 6 kernel privati df11 del banco
originale (HTTP403). Solo il kernel pubblico MX è accessibile. Il banco
preparato con proprietario MX richiede quindi risoluzione degli accessi;
il preflight non autorizza né esegue nuovi trasferimenti. La scelta della
destinazione e il piano minimo di file saranno concretizzati con i quattro
output completi, conservando scorer, split e supporto originali.
