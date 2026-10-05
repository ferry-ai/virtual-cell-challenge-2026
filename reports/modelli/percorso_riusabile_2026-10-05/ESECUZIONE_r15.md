# Rifit e generazione avviati

5 ottobre2026, 23:29:37 Europe/Rome: push accettato, versione1,
`davideferrante11/vcc-generate-t28-frozen-bank-r1`.
[Ricevuta](generation_successors_r1/dispatch_r1/launch.json),
[primo stato provider RUNNING](generation_successors_r1/dispatch_r1/provider_status_r1.json).
RUNNING non prova ancora stage100 riuscito o file .vcc pronto.

Pacchetto congelato in [ready](generation_successors_r1/ready.json), input/mount/hash
espliciti. Ricetta t25, emitter t28 e K562 storico preservati; sei cache corrette
sostituiscono solo gli adapter difettosi. [Verifiche precedenti](ESECUZIONE_r14.md).
Il runtime produce effetti, cellule e pacchetto stage100/45/48. Nessuna fonte aggiunta
silenziosamente durante il job. Non duplicare questo lancio.

Vecchio t25/t28: quattro fonti votanti K562, CD4mix, HCT116 e HEK293T, peso1.
Nuovo candidato: queste quattro più H1joint e quattro esperimenti KOLF, nove fonti
con target sul pannello. Sono tredici nomi di fonte registrati; HepG2, Jurkat,
RPE1 e K562essential hanno ancora zero target sul pannello, non contribuiscono.
Quattro esperimenti KOLF non significano quattro linee cellulari distinte.
Conteggio previsto dal pacchetto, consumo effettivo da confermare nei manifest.

Banca persistente [storage r11](cloud_catalog_r11/manifest.json):45unità,
395,75GB grezzi; entrambi i blocchi singlecellGWPS ora chiusi. Questa release di
fit è PARZIALE, non tutta la banca. HIPSCI/Tian/Norman/SCP/A549 e altre fonti
restano nel catalogo con adapter/QC/identità da completare; nessuna esclusione
definitiva per dimensione o overlap. Campioni non usati da questo lineare.

Prossimo: controllare esecuzione reale e integrità degli output, recuperare una sola
prediction.vcc identificata dal manifest48, inviare subito con autorizzazione umana
già ricevuta, senza aspettare banco predittivo. Nessun miglioramento dimostrato.
Consegna entro02 è obiettivo. Grok r11 terminato senza nuova consegna adottata;
nessun worker attivo. Parent segue questo job. Nessun push Git implicito.
