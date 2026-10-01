# Piani aperti — scegliere il prossimo lavoro

**Dopo lo scoring del 1° ottobre:** il t29 non promuove la rete. La sua regola richiede un
banco locale a sei membri almeno al livello del transfer prima di un altro invio neurale
([CP-0055](checkpoints/0055-t29-rete-cellulare-punteggio.md)). Il riferimento resta la ricetta
esistente; stato e punteggi in [PROGETTO §0](PROGETTO.md).

**Un programma, tre ruoli:** [R-COMP](piani/modello-competitivo.md) è il programma generale,
[R-LEAD](piani/strategia-scientifica.md) ne precisa metodo e confronti,
[R-LAB](piani/piano-giorno-2026-09-30.md) documenta l'esecuzione su corpus e rete.
Non sono tre ricerche da avviare separatamente. La prossima consegna proposta è in R-LEAD:
correzioni verificabili e banco diagnostico, prima di attribuire progresso a più dati o capacità.

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
| R-LEAD | Direzione scientifica dal 1/10: rendere identificabile il training, poi transfer con residuo biologico, dati ponte e popolazioni; precisa il programma R-COMP senza sostituire l'assegnazione R-LAB | [Strategia scientifica](piani/strategia-scientifica.md) | Diagnosi riproducibili e D-050; split, controlli e confronti corretti prima di attribuire prestazioni a corpus o architettura |
| R-LAB | Esecuzione dello stesso programma: riusare corpus e reti già prodotti per capire il divario dal transfer | [Piano del giorno](piani/piano-giorno-2026-09-30.md) | Ramo c di t29 e confronti R-LEAD; il quarto training è una verifica tecnica e non sostituisce il banco |
| R-COMP | Programma generale dal 29/09: copertura reale, modello biologico, C/T/J e sei metriche; dal 30/09 attuato attraverso R-LAB | [Modello competitivo](piani/modello-competitivo.md) | Storico degli outcome, riserva e criteri di promozione prima dei nuovi training |
| R-REV | Verifiche trasversali ancora utili: prova generale a forma piena, banco K562, basali sull'asse comune; leggere l'esito di ogni azione prima di ripeterla | [Revisione critica](piani/revisione-critica.md) | La forma ridotta e le azioni 2/6 hanno già un esito; risorse e autorizzazioni vanno verificate alla ripresa |
| S-INVII | Presidio della ricetta e della consegna finale; t29 è già letto | [Invii e set finale](piani/invii-finale.md) | Un pacchetto pronto non è un ordine di invio; per la rete vale il ramo c di t29 |
| R-V2 | Raccolta dei filoni precedenti e delle alternative; il nuovo programma scientifico è R-LEAD/R-COMP | [Modello v2](piani/modello-v2.md) | Confrontare gli stati datati con gli esiti in AMBITI; non rilanciare un filone già concluso dalla sua vecchia riga |
| R-DATI | Supporto a R-LAB/R-LEAD: qualità, controlli, repliche e dati che risolvano un limite misurato | [Dati e affidabilità](piani/dati-affidabilita.md) | Inventario e corpus già prodotti in R-LAB; motivare la nuova acquisizione e fissare gli split prima di confrontare corpus diversi |
| R-SWITCH | Ipotesi disponibile sulle popolazioni, subordinata a confronti e dati adeguati; non un rimedio dimostrato al t29 | [Switch e distribuzioni](piani/switch-distribuzioni.md) | Cellule, guide e controlli indipendenti; confronto a pari media e verifica sui sei membri |

**Come riprendere.** Leggere l'intestazione aggiornata della scheda, non l'ultimo «prossimo
passo» trovato in una cronologia. R-LAB contiene più consegne successive; R-V2, R-DATI e
R-SWITCH conservano parti del 24–29/09. Una scheda aperta non prova un job attivo, né che
un'ipotesi sia ancora promettente. Gli incarichi restano registrati nelle schede (§3).

**Priorità proposta dopo t29:** prima A/B di R-LEAD e il banco diagnostico sui modelli
esistenti; la prova generale di R-REV resta un requisito di consegna indipendente dal successo
della rete. Residuo sul transfer, ulteriori dati e modelli di popolazione vengono dopo i
rispettivi confronti. Il quarto training R-LAB conserva il proprio protocollo: può rispondere
a una domanda tecnica, ma non soddisfa da solo la regola per un nuovo invio. Questo ordine
non cancella protocolli, non chiude intere famiglie di modelli e non avvia né interrompe job.

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

R-MODELLI è la scheda formalmente chiusa; le otto schede elencate sopra hanno ruoli e
dipendenze diversi. La bocciatura di un candidato non chiude automaticamente la sua famiglia.

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
