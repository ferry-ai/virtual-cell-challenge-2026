# DATI-TRANSFER — ripresa neurale del 9 ottobre 2026

Tipo: stato tecnico misurato; gli orari esatti sono nelle ricevute.

**Ancore AMMI consegnate:** 17 nuove ancore e due parità T0, tutte recuperate e
verificate per hash, assi, ricetta, sorgenti/esclusioni e codice remoto.
[Manifest](ammi_anchors_verified_r1.json); [consegna completa](HANDOFF_RETI_r1.md).

**NTC in esecuzione:** 18 parti su `davidmaisterx/dt-ntc-inputs-01a11c34-r4` e
12 su `davideferrante11/dt-ntc-inputs-01a11c34-r5`, entrambe RUNNING nel
[controllo r4](neural_inputs_status_r4.json). 47 contesti previsti, non ancora
certificati come estratti. Nessun RNA scaricato sul portatile.

Il difetto del controllo disco su un parent inesistente è stato corretto e
riprodotto in una prova di avvio reale su fixture; nove test PASS. I pacchetti r3
non sono stati eseguiti. Il tentativo df11 r4 ha fallito nel trasporto TLS e non
risulta creato; r5 è un recupero dello stesso lavoro dopo verifica della lista.

MODELLI ha ricevuto ancore, mappa delle 30 parti/plan SHA, pin dell'asse e proposte
di routing interno. Restano estrazione e verifica NTC, accessi privati dal runtime
di training e revisione VALIDAZIONE della corrispondenza fra NTC e verità aggregate.
La primaria K562 è BULK storica: non la dichiariamo abbinata ai campioni single-cell.
Nessun training AMMI/GPU avviato da DATI; D-053 resta aperto.

**T3 conservato:** fit completo, effetti e maschera esistenti rihashati; il file
cellulare di recupero è ancora elencato fra gli output del job terminale ERROR.
Le ricevute riportano 360.000 cellule. Mancano verifica integrale del recupero e
confezionamento; nessuna consegna fast riattivata.
[Percorsi, pin e limiti](t3_preserved_handoff_r1.json).

Le sei ricevute ESM2 di consumo indipendente sono PASS. La valutazione predittiva
appartiene a VALIDAZIONE, non a questa attestazione del consumo.
