# Piani aperti — scegliere il prossimo lavoro

Creato il 24 settembre 2026 su richiesta del proprietario. **Questo è l'indice
operativo dei piani**, da leggere dopo lo stato in [PROGETTO.md](PROGETTO.md) §0.
Le schede collegate contengono stato, dipendenze, prossimo passo e criterio di
chiusura. Le priorità di ricerca sono proposte promettenti, non risultati acquisiti.

## 1. Dove leggere che cosa

| Domanda | Fonte autorevole per quella domanda |
|---|---|
| Dove siamo, che cosa è stato misurato o inviato? | [PROGETTO.md](PROGETTO.md) §0; poi le evidenze citate |
| Che cosa fare dopo? | Questo indice e la singola scheda in [piani](piani/CLAUDE.md) |
| Come eseguire il lavoro? | [LAVORO.md](LAVORO.md), procedure e risorse |
| Quali vincoli di ricerca rispettare? | [GENERALIZZAZIONE.md](GENERALIZZAZIONE.md) e [DECISIONI.md](DECISIONI.md) |
| Quanto fidarsi di un documento? | [REGISTRO.md](REGISTRO.md), comprese le correzioni |
| Perché una vecchia prova è stata chiusa? | [Indice dei checkpoint](checkpoints/INDICE.md), poi report originale |
| Dove recuperare codice o piani ritirati? | [ARCHIVIO.md](ARCHIVIO.md), solo quando serve |

Un risultato vecchio può restare valido; un'ipotesi recente non diventa un fatto.
I report conservano l'evidenza, le schede conservano il prossimo passo. Non cercare
un incarico attuale nei «prossimi passi» di un vecchio report.

## 2. Ordine dei piani aperti

I dettagli e le assegnazioni si aggiornano **nelle schede**, senza duplicarli qui.
«Prima» significa ordine delle dipendenze, non autorizzazione a consumare quota.
L'aggiunta all'indice non avvia job, monitor o invii automatici.

| ID | Priorità e motivo | Scheda | Prima di eseguire |
|---|---|---|---|
| S-INVII | Scadenze e lettura delle prove già preparate | [Invii e set finale](piani/invii-finale.md) | Verificare stato effettivo e coordinarsi con chi segue gli invii |
| R-V2 | Adesso, su richiesta del proprietario: il modello per il set finale, filoni F1–F8 | [Modello v2](piani/modello-v2.md) | Via del proprietario per download, calcolo in cloud e invii |
| R-DATI | Prima: rendere utilizzabili dati, controlli e repliche | [Dati e affidabilità](piani/dati-affidabilita.md) | Audit locale e dei metadati; stimare costo prima di acquisire |
| R-MODELLI | Promettente: programmi × stato × ruolo del bersaglio | [Trasferimento e modelli](piani/trasferimento-modelli.md) | R-DATI e protocollo C/T/J congelato prima del training |
| R-SWITCH | Promettente: soglie, intensità e cellule rispondenti | [Switch e distribuzioni](piani/switch-distribuzioni.md) | Cellule, guide e controlli da R-DATI; score indipendente dalla risposta valutata |

**Le dieci ipotesi della ricerca del 24 settembre sono tutte mantenute aperte:**
H1–H3 e H6 in R-MODELLI; H4–H5 in R-SWITCH; H7–H10 distribuite fra R-DATI e
R-MODELLI. La matrice completa di ipotesi, alternative e prove resta nel
[report di ricerca](../reports/ipotesi_trasferimento_2026-09-24/IPOTESI.md).
Le opzioni successive non scompaiono: reti biologiche, embedding, generazione,
tempo e reti causali hanno condizioni di apertura nelle schede.

## 3. Lavorare in una cartella condivisa

Le assegnazioni al momento dell'introduzione dell'indice sono **da verificare**:
altri agenti sono attivi e i vecchi incarichi non sono stati censiti qui.

1. Leggere `git status --short`, la scheda scelta e le modifiche ai file da
   toccare. Un file non tracciato o un incarico senza assegnatario non è libero
   per definizione. Prima di lanciare un lavoro pesante verificare anche i job
   secondo LAVORO; lo stato scritto in una scheda non prova che un job sia vivo.
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
   sui checkpoint e sulle autorizzazioni restano in CLAUDE e LAVORO.
5. A fine lavoro lasciare esito, evidenza e prossimo passo nella scheda. Per una
   chiusura, registrare la prova e la condizione di riapertura; conservare la
   scheda e spostare il suo collegamento sotto «Piani chiusi».

## 4. Piani chiusi e risultati precedenti

Nessuna delle quattro nuove schede è chiusa. Per le linee precedenti:

| Filone precedente | Esito e come usarlo oggi |
|---|---|
| Predittore neurale del 18–19 settembre | Esperimento scartato: [CP-0026](checkpoints/0026-predittore-neurale-condizionato.md); t07 ufficiale in [CP-0027](checkpoints/0027-t07-punteggio-ufficiale.md). R-MODELLI è una nuova ipotesi con prove esplicite, non la promozione del vecchio modello |
| Ipotesi che togliere le chiamate spurie bastasse alla fedeltà | Esito contrario nel t14: [CP-0032](checkpoints/0032-t14-controlmodel-fedelta.md). ControlModel resta una alternativa, non una soluzione dimostrata |
| Vecchia calibrazione dell'ampiezza | D-042 e [CP-0033](checkpoints/0033-t15-ampiezza-doppia.md), con limiti di [CP-0034](checkpoints/0034-audit-segni-e-ampiezza.md). La curva è ancora aperta in S-INVII |
| Banchi e piani dell'11–19 settembre | [PROGETTO.md](PROGETTO.md) §2 e [REGISTRO.md](REGISTRO.md); leggere il checkpoint pertinente, non tutta la cartella |
| Catena di cicli e orchestratore | Ritirati: D-040 in [DECISIONI.md](DECISIONI.md), percorsi in [ARCHIVIO.md](ARCHIVIO.md). Questo indice è manuale e non li riattiva |

Non modificare gli esiti storici per farli coincidere con un piano nuovo. Una
correzione segue il registro e i checkpoint; un nuovo esperimento ha un nuovo output.
