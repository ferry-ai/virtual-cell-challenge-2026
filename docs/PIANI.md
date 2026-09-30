# Piani aperti — scegliere il prossimo lavoro

**Priorità aggiornata al 30/09:** [R-COMP — modello competitivo](piani/modello-competitivo.md):
t28 concluso ([CP-0052](checkpoints/0052-t28-punteggio-ufficiale.md)); riconciliare i dataset,
congelare una riserva indipendente e verificare un nuovo modello. La direzione generale che lega
i piani è nel §0 di [PROGETTO](PROGETTO.md#direzione-generale); dove sta che cosa, per ambito, in
[AMBITI](AMBITI.md).

**Perimetro:** le priorità e le dipendenze fra i piani (§2), le regole per prendere e lasciare un
lavoro nella cartella condivisa (§3), i piani chiusi (§4). Stato, prossimo passo e assegnazione di
un piano stanno nell'intestazione della sua scheda, non qui. Creato il 24/09 su richiesta del
proprietario; si aggiorna quando cambiano priorità, dipendenze o l'elenco delle schede. Le priorità
di ricerca sono proposte promettenti, non risultati acquisiti.

## 1. Dove leggere che cosa

Che cosa leggere oltre alla scheda lo dice la tabella dei compiti di [CLAUDE.md](../CLAUDE.md); la
sede di ogni tipo di informazione è in [docs/CLAUDE.md](CLAUDE.md). Un risultato vecchio può restare
valido; un'ipotesi recente non diventa un fatto. I report conservano l'evidenza, le schede il
prossimo passo: non cercare un incarico attuale nei «prossimi passi» di un vecchio report.

## 2. Ordine dei piani aperti

I dettagli e le assegnazioni si aggiornano **nelle schede**, senza duplicarli qui.
«Prima» significa ordine delle dipendenze, non autorizzazione a consumare quota.
L'aggiunta all'indice non avvia job, monitor o invii automatici.

| ID | Priorità e motivo | Scheda | Prima di eseguire |
|---|---|---|---|
| R-COMP | **Adesso**, richiesta del 29/09: copertura reale dei dataset, modello biologico, training C/T/J e sei metriche con riserva indipendente | [Modello competitivo](piani/modello-competitivo.md) | Assegnazioni esistenti preservate; storico degli outcome e manifest prima dei nuovi training |
| R-REV | **Adesso**, su richiesta del proprietario del 28/09 (12:30): le azioni della revisione critica, in ordine; la prima, l'unione del loro branch nel `main` del portatile, è fatta dal 28/09 | [Revisione critica](piani/revisione-critica.md) | Via del proprietario per invii, download, calcolo in cloud e push (mandato della scheda) |
| S-INVII | Scadenze e lettura delle prove già preparate | [Invii e set finale](piani/invii-finale.md) | Verificare stato effettivo e coordinarsi con chi segue gli invii |
| R-V2 | Adesso, su richiesta del proprietario: il modello per il set finale, filoni F1–F8 | [Modello v2](piani/modello-v2.md) | Via del proprietario per download, calcolo in cloud e invii |
| R-DATI | Prima: rendere utilizzabili dati, controlli e repliche | [Dati e affidabilità](piani/dati-affidabilita.md) | Audit locale e dei metadati; stimare costo prima di acquisire |
| R-SWITCH | Promettente: soglie, intensità e cellule rispondenti | [Switch e distribuzioni](piani/switch-distribuzioni.md) | Cellule, guide e controlli da R-DATI; score indipendente dalla risposta valutata |

**Stato delle schede.** Lo stato di un piano è nell'intestazione della sua scheda (R-V2, per
esempio, è in corso dalla ripresa del 28/09 alle 19:22). S-INVII, R-DATI e R-SWITCH sono ferme
al 28/09, con una nota datata che rimanda a dove il lavoro è proseguito. Diverse assegnazioni
nominano sessioni che il 30/09 alle 02:07 risultavano chiuse, `f4f38e58` e la lead di Codex
`01a0ee03` ([riordino](../reports/analisi/riordino_repo_2026-09-30/RIORDINO.md), §1): vedi §3. Le proposte della [revisione critica del 28/09](../reports/analisi/revisione_criticita_2026-09-28/REVISIONE.md)
(§6) sono, dalle 12:30 del 28/09 e su richiesta del proprietario, la scheda
[R-REV](piani/revisione-critica.md), in ordine di esecuzione. Dal 29/09 la priorità complessiva
è [R-COMP](piani/modello-competitivo.md); gli incarichi già aperti in R-REV e R-V2 restano assegnati.

**Le dieci ipotesi della ricerca del 24 settembre:** H1 (programmi, nella forma lineare) e H6 (pesi
per somiglianza basale fra linee) sono state provate il 26/09 e hanno perso; le altre restano aperte.
H2–H3 stanno nella condizione di riapertura di R-MODELLI, chiusa il 30/09 (§4); H4–H5 in R-SWITCH;
H7–H10 fra R-DATI e quella stessa condizione di riapertura. La matrice completa di ipotesi, alternative e prove resta nel
[report di ricerca](../reports/analisi/ipotesi_trasferimento_2026-09-24/IPOTESI.md).
Le opzioni successive non scompaiono: reti biologiche, embedding, generazione,
tempo e reti causali hanno condizioni di apertura nelle schede.

## 3. Lavorare in una cartella condivisa

Un'assegnazione scritta in una scheda non prova che la sessione sia ancora attiva, né che sia
chiusa. Si verifica con la sessione stessa, se è raggiungibile ([AGENTI §3](AGENTI.md#3-coordinamento-fra-sessioni-nella-stessa-cartella)),
altrimenti chiedendo al proprietario. Come si committano i file condivisi è nella stessa sezione.

1. Leggere `git status --short`, la scheda scelta e le modifiche ai file da
   toccare. Un file non tracciato o un incarico senza assegnatario non è libero
   per definizione. Prima di lanciare un lavoro pesante verificare anche i job
   secondo PROCEDURE; lo stato scritto in una scheda non prova che un job sia vivo.
2. Dopo il coordinamento disponibile, annotare **nella singola scheda** agente,
   sessione identificabile, data/ora con fuso, sottoattività, file di lavoro e
   destinazione nuova degli output. Non assegnare né liberare il lavoro altrui.
   Una nota scaduta richiede verifica, non autorizza a prendere il controllo.
3. Rileggere subito prima di una modifica condivisa; applicare patch piccole,
   preservare le variazioni concorrenti. La presa in carico in Markdown è una
   convenzione, **non un lock atomico**. Se due agenti rivendicano lo stesso
   ambito, risolvere il conflitto prima di modificarlo; proseguire su ambiti disgiunti.
4. Usare report e output distinti; non sovrascrivere prove o protocolli.
   Aggiornare l'indice solo per priorità, dipendenze o nuove schede. Le regole
   sui checkpoint e sulle autorizzazioni stanno in CLAUDE.md e in docs/CLAUDE.md.
5. A fine lavoro lasciare esito, evidenza e prossimo passo nella scheda. Per una
   chiusura, registrare la prova e la condizione di riapertura; conservare la
   scheda e spostare il suo collegamento sotto «Piani chiusi».

## 4. Piani chiusi e risultati precedenti

Una scheda su sette è chiusa, R-MODELLI; le altre linee chiuse sono precedenti alle schede.

| Scheda | Chiusa | Esito e condizione di riapertura |
|---|---|---|
| R-MODELLI, programmi, stato cellulare e bersagli nuovi | 30/09, scelta del proprietario | I confronti 1–3 e 5 sono stati eseguiti in R-V2 e R-COMP, e nessuno ha superato la sua regola; il 4 (ruoli con segno, reti) non è stato eseguito. Si riapre con i descrittori dei bersagli nuovi (H2–H3, filone F5 di R-V2). Dettagli nella [scheda](piani/trasferimento-modelli.md), sezione «Chiusura» |

Per le linee precedenti:

| Filone precedente | Esito e come usarlo oggi |
|---|---|
| Predittore neurale del 18–19 settembre | Esperimento scartato: [CP-0026](checkpoints/0026-predittore-neurale-condizionato.md); t07 ufficiale in [CP-0027](checkpoints/0027-t07-punteggio-ufficiale.md). R-MODELLI è una nuova ipotesi con prove esplicite, non la promozione del vecchio modello |
| Ipotesi che togliere le chiamate spurie bastasse alla fedeltà | Esito contrario nel t14: [CP-0032](checkpoints/0032-t14-controlmodel-fedelta.md). ControlModel resta una alternativa, non una soluzione dimostrata |
| Vecchia calibrazione dell'ampiezza | D-042 e [CP-0033](checkpoints/0033-t15-ampiezza-doppia.md), con limiti di [CP-0034](checkpoints/0034-audit-segni-e-ampiezza.md). La curva è ancora aperta in S-INVII |
| Banchi e piani dell'11–19 settembre | [PROGETTO.md](PROGETTO.md) §2 e [REGISTRO.md](REGISTRO.md); leggere il checkpoint pertinente, non tutta la cartella |
| Catena di cicli e orchestratore | Ritirati: D-040 in [DECISIONI.md](DECISIONI.md), percorsi in [ARCHIVIO.md](ARCHIVIO.md), stato in [AGENTI](AGENTI.md) §2. Questo indice è manuale e non li riattiva |

Non modificare gli esiti storici per farli coincidere con un piano nuovo. Una
correzione segue il registro e i checkpoint; un nuovo esperimento ha un nuovo output.
