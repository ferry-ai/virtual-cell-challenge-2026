# ESM2: supporto effettivo e livello B con i fit esistenti

9 ottobre 2026. Integra il piano AMMI e corregge la lettura scientifica tramite
`PRECISAZIONE_VERDETTO_ESM2_r1.md`. Soltanto preparazione e accessi in lettura:
nessun nuovo fit, job, locator, trasferimento o modifica di permessi.

## Instradamento e input, verificati ora

**Audit del supporto: CPU privata df11.** Il preflight
`esm2_validation_access_preflight_r1.json` verifica 13/13 sorgenti ammesse.
Gli effetti originali T0/R1/T1/P4 nei due fold sono già negli otto file
`effects/<braccio>__<fold>.npz` del job df11 closure; il piano JSON fissa i loro
hash dalle ricevute di consumo. I due fallback sono già nel dataset privato
df11 `vcc-esm2-closure-01a11c35-r1`. Tabelle di verità, asse e pannello
riutilizzano gli input originali del banco. Nessun trasferimento fra account
è necessario per questo audit.

**Livello B: due job CPU privati su davidmaisterx**, uno per fold. Quattro
input nativi su quattro sono accessibili: le due estrazioni cellulari
`vcc-validazione-celle-{k562,ipsc}-8a8ca58a-r1` e i due dataset degli effetti
`vcc-validazione-effetti-{k562,ipsc}-8a8ca58a-r1`. T0 corrisponde per hash al
riferimento usato dal fallback. Le cellule vere rimangono su MX; spostare il
livello B su df11 richiederebbe un trasferimento maggiore di dati cellulari.

Il dataset closure df11 non è accessibile da MX (403). La sola estensione
privata proposta, da autorizzare separatamente, comprende questi due file:

| Sorgente: `davideferrante11/vcc-esm2-closure-01a11c35-r1` | Destinazione | Byte |
|---|---|---:|
| `C-K562_E2f.npz` | job CPU privato `davidmaisterx/esm2-fallback-b-k562-01a11c35-r1` | 19.793.870 |
| `C-iPSC_E2f.npz` | job CPU privato `davidmaisterx/esm2-fallback-b-ipsc-01a11c35-r1` | 19.498.599 |

Totale: **39.292.469 byte**, SHA256 esatti in
`esm2_validation_access_plan_r1.json`. Proposta: locator temporanei nei soli
pacchetti privati, consumo diretto nel cloud, nessuna pubblicazione/ACL, nessun
RNA sul portatile. Il consenso al precedente upload su df11 non viene
interpretato come consenso a questa nuova destinazione MX. Nessuna richiesta
di nuovo addestramento è necessaria o prevista.

## Audit da eseguire senza spostare il supporto

Ricostruire `keep`, maschere valide e `cols95` con le stesse regole del
`bench_core.py` originale. Riprodurre i valori T0/fallback già salvati prima
di leggere la diagnostica. Contare separatamente coppie riempite nella
maschera e coppie con valori numerici effettivamente cambiati; per ciascuna,
quante entrano nella metrica e quante sono escluse per bersaglio, gene o
verità non valida, senza doppio conteggio. Conservare conteggi per bersaglio,
denominatori e hash del supporto. Riportare anche il sottoinsieme cambiato.

Non si amplia `cols95`, non si ricalcola il rango su geni scelti perché
favoriscono il fallback e non si interpreta `{}` in `common_support.json`
come una prova che il fallback sia stato ignorato. Quel file controlla un
altro tipo di braccio; la copertura specifica ESM2 resta da misurare.

## Livello B congelato

Riutilizzare `bench_v2.py` e snapshot originali verificati, scorer
cell-eval2 0.16.0, emissione t28, 400 cellule previste per bersaglio, cinque
semi del generatore, split della verità al seme2026. C-K562 usa i 272
bersagli GWPS; C-iPSC i 55 della libreria strong, distinta dalla verità
primaria pan-genome del livello A.

Confronti T0/fallback sul fold intero e sui bersagli cambiati determinati
prima dello scoring, con lo stesso flusso casuale per entrambi. Controllo
T0 contro righe scambiate secondo il seme congelato, un seme di emissione:
il PDS deve diminuire. Il sottoinsieme cambiato con meno di quattro bersagli
segue lo skip del banco originale, non una nuova soglia.

Riportare PDS, MSE, NMAE, FID, REACH e JAC, valori grezzi e scalati locali,
denominatori, media dei sei e dei cinque senza JAC, delta appaiati per seme,
risultati per fold e macro a peso uguale. La decisione resta PROTOCOLLO_v1 §8
con l'emendamento disc95 di v2. Nessuna soglia nuova e nessun punteggio VCC.

Questo complemento CPU è separato dalla dipendenza NTC→AMMI cells e non ne
ritarda preparazione o lancio. I pacchetti eseguibili e i preflight di risorse
devono essere completati prima di chiedere il consenso al trasferimento e
prima del lancio; questo piano non dichiara che i nuovi banchi siano partiti.
