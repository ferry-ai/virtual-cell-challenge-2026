# Piani — un incarico operativo, supporti e alternative

**Per lavorare adesso:** [R-LEAD](piani/strategia-scientifica.md), con il
[prompt per Claude](PROMPT_CLAUDE.md). Dopo t29 la prima consegna è un esperimento
interpretabile e un confronto completo, non l'espansione automatica del corpus.
Stato generale e riferimento in [PROGETTO §0](PROGETTO.md).

Questo indice mantiene priorità e dipendenze; stato e presa in carico stanno nelle schede.
Il rinnovo del 1–2 ottobre conserva [le versioni precedenti](storico/rinnovo_2026-10-01/INDICE.md).
Non sono incarichi da riprendere dai loro vecchi «prossimi passi».

## 1. Dove leggere che cosa

[CLAUDE.md](../CLAUDE.md) instrada per compito; [AMBITI](AMBITI.md) per area;
[docs/CLAUDE.md](CLAUDE.md) indica la sede canonica di ogni informazione.
Un report contiene evidenza datata, una scheda il lavoro attuale. L'esistenza di codice,
un protocollo o una riga «in corso» non prova che un job sia attivo o concluso.

## 2. Ordine dei piani aperti

| Ruolo | Scheda | Quando usarla |
|---|---|---|
| **Implementazione principale** | [R-LEAD — P0–P6](piani/strategia-scientifica.md) | Presa in carico unica: input/esposizione, diagnosi, correzioni, banco, estensioni condizionate e finale |
| Obiettivo del programma | [R-COMP](piani/modello-competitivo.md) | Perimetro e criterio competitivo; nessun secondo percorso da avviare |
| Inventario dell'esecuzione | [R-LAB](piani/piano-giorno-2026-09-30.md) | Corpus, training e artefatti disponibili; nuovi job scelti attraverso R-LEAD |
| Verifiche residue | [R-REV](piani/revisione-critica.md) | Forma piena, banco K562, basali e residui; la tabella distingue concluso e da fare |
| Consegna finale | [S-INVII](piani/invii-finale.md) | Manifest, pacchetto e lettura ufficiale; preparazione indipendente dal successo neurale |
| Supporto condizionato | [R-DATI](piani/dati-affidabilita.md) | Una lacuna di dati misurata nel banco, non una nuova raccolta indiscriminata |
| Ipotesi condizionata | [R-SWITCH](piani/switch-distribuzioni.md) | Limite di popolazione misurato e guide/repliche indipendenti |
| Catalogo precedente | [R-V2](piani/modello-v2.md) | Ritrovare filoni ed esiti; riapertura motivata attraverso R-LEAD |

R-COMP e R-LAB descrivono scopo e mezzi dello stesso lavoro. Le alternative conservano
valore come ipotesi, senza diventare otto piani da eseguire insieme. Ogni nuovo confronto
ha una regola scritta prima dei numeri. Nessuna voce dell'indice autorizza quota o invii.

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

| Scheda | Esito | Riapertura |
|---|---|---|
| [R-MODELLI](piani/trasferimento-modelli.md) | Chiuso dal proprietario il 30/09; i confronti sono registrati nella scheda e nello storico | Nuovo protocollo motivato da R-LEAD; nessuna riapertura implicita nel rinnovo |

Le ipotesi H1–H10 del 24/09 sono nel [report di ricerca](../reports/analisi/ipotesi_trasferimento_2026-09-24/IPOTESI.md).
I loro esiti e le successive correzioni si trovano tramite AMBITI e gli indici dei report.
Una bocciatura di candidato non chiude automaticamente la famiglia di modelli.
