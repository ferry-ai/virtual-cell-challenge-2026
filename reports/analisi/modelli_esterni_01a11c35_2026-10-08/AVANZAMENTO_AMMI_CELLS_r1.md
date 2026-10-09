# AMMI: input pronti e primi lanci cells

**Misurato il 9 ottobre 2026:** i due job privati iniziali su `davidmaisterx`
sono stati accettati e risultavano `RUNNING`: C-K562 alle 21:57 e C-iPSC alle
21:59 Europe/Rome. Le ricevute sono `ammi_c-k562_cells_auto_launch_r1.json` e
`ammi_c-ipsc_cells_auto_launch_r1.json`. L'accettazione non prova che il training
abbia terminato o che le predizioni siano migliori.

## Input e continuazione

DATI ha completato la verifica delle 12 parti mancanti: vedere
`reports/modelli/dati_transfer_2026-10-08_01a11c34/ntc_df11_terminal_verified_r1.json`
e `ntc_ready_manifest_r2.json` nella stessa cartella. L'estensione degli accessi
privati autorizzati ha emesso `ammi_private_access_with_ntc_r1.json`: 48 file NTC,
7.661.250.598 byte. Il portatile non ha scaricato i payload numerici; il consumatore
cloud deve ancora verificarne dimensioni e hash completi prima del fit.

La prima continuazione, PID9048, ha rilevato le sentinelle e preparato entrambi i
runtime. Si è fermata alle 21:50 prima di qualunque push: il compattatore v1
usava un dizionario LZMA da 8 MiB e il sorgente iPSC superava la guardia di 1 MB.
Il compattatore v2 usa 32 MiB e produce un sorgente di 851.314 byte. Non cambia
nessun file estratto, codice scientifico, selezione o iperparametro. K562 conserva
il pacchetto v1 di 869.418 byte. Le ricevute `*_cells_prepared_r2.json` attestano
la parità dei 64 membri di ciascun archivio; il controllo indipendente è
`verify_ammi_packaging_recovery_v1.py`.

La ripresa `resume_ammi_cells_dispatch_v1.py` parte solo in assenza di ricevute,
intenti e lock di push. Riutilizza i pacchetti, senza ripetere estrazione o
emissione dei link; esegue preflight freschi e il launcher che rifiuta job già
esistenti. I due lanci sono i primi degli stessi esperimenti cells autorizzati.
Il processo effettivo PID22492 è iniziato alle 21:55; configurazione e ricevuta
sono `ammi_cells_continuation_config_r2.json` e
`ammi_cells_continuation_started_r2.json`. Stato e ricevuta finali potranno essere
successivi a questa nota: consultarli prima di affermare che il processo è vivo.

La continuazione raccoglie identità remota, stato e soli metadati terminali;
si ferma su errori, senza rilancio automatico. Non avvia produzione, banchi o
submission. Prima del secondo lancio il preflight registrava 92.031,95 secondi
GPU gratuiti non riservati su MX, con acquisti disattivati. Quota e accessi sono
misure datate, non una garanzia futura.

## Che cosa dimostrano i risultati

I due fit NONE sono già conclusi e tecnicamente verificati. I CELLS aggiungono
la descrizione della cellula non perturbata: il confronto serve a misurare se
questa informazione aiuta rispetto a NONE e all'ancora congelata. Fino al banco
non è misurato alcun beneficio predittivo AMMI. Sono pilot a 2 epoche, seme17,
con le esclusioni congelate; non risolvono la copertura D-053 dell'intero catalogo.

La banca di aggregati era riusabile. Il nuovo contratto AMMI chiedeva però NTC
con profondità nativa e selezione per strato, diversi dai campioni persistenti
32/64/128. È questo adattamento che ha richiesto l'estrazione: non dimostra un
beneficio della selezione più grande. La diagnosi DATI è
`reports/modelli/dati_transfer_2026-10-08_01a11c34/AUDIT_RIUSO_NTC_r1.md`.
Il catalogo di riuso non va descritto come già integrato nel trainer.

## Responsabilità dei banchi e materiale preparato

Letta `reports/analisi/validazione_banco_eace4d03_2026-10-09/AUTORIZZAZIONI_r1.json`:
il proprietario ha assegnato a VALIDAZIONE il livello B ESM2 a quattro bracci e
il primo confronto AMMI NONE. Questi job e trasferimenti non saranno duplicati
da MODELLI-ESTERNI. Il consenso registrato per NONE non comprende i futuri export CELLS.

L'audit ESM2 di VALIDAZIONE è già concluso, con esito complessivo inconcludente
fino al livello B. Più copertura non equivale a precisione o specificità del
bersaglio. La nostra precisazione resta `PRECISAZIONE_VERDETTO_ESM2_r1.md`;
la lettura successiva è `RISULTATI_ESM2_FALLBACK.md` nella cartella di VALIDAZIONE.

I nostri `esm2_level_b_templates_r2/` sono modelli eseguibili ma privi degli
accessi privati e non lanciabili. Conservano scorer/generatore congelati e
controlli di parità; il piano di trasporto di 117.040.455 byte era una proposta,
ora non da attuare perché il banco è affidato a VALIDAZIONE. Non confonderlo con
il diverso bundle dei bracci già derivati che VALIDAZIONE è autorizzata a usare.

Per l'eventuale banco AMMI, `bank_input_bridge_v1.py` sostituisce tecnicamente la
proposta di unione tramite symlink contenuta nel piano r1: enumera separatamente
gli alberi nativo e trasferito, perché `Path.rglob` non garantisce la discesa nei
symlink di directory. Cinque fixture verificano il bridge contro il vero lettore
congelato. Nessuno scorer è stato modificato e nessun nuovo accesso è stato emesso.

## Verifiche locali

Quattro test di preparazione cells, tre della continuazione, cinque del bridge
e due di parità dei quattro bracci ESM2 passano: ricevute
`ammi_cells_preparation_tests_r1.txt`, `ammi_cells_continuation_tests_r1.txt`,
`bank_input_bridge_tests_r1.txt`, `esm2_four_arms_tests_r1.txt`.
Le fixture non sostituiscono la verifica numerica remota né il confronto biologico.
Il primo controllo documentale r32 ha osservato tre ricevute mentre venivano
create; la verifica va ripetuta su un inventario stabile.
