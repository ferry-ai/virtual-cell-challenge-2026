# Ibrido semplice: transfer ampliato, pseudobulk e campioni

4 ottobre 2026, Codex, chat `01a107a9-9c9c-76c2-9161-258f22bd57b1`.
**Mandato del proprietario:** «ok ibrido semplice, possibilmente a partire dal transfer
più promettente e su tanti contesti diversi ma con psuedobulk e campionamento».

**Stato: disegno e componenti implementati, pacchetto di training non ancora completo.**
Queste scelte precedono nuovi fit. Il manifest definitivo di dati, split e parametri
deve essere congelato prima del lancio. Nessun training reale avviato da questo documento.

## 1. Base scelta e limiti dell'evidenza

Base del candidato: **transfer ampliato, policy `all`**, gerarchico per gruppi,
con le fonti compatibili ammesse dal fold. Il transfer di produzione resta un riferimento
separato. La stessa policy, le stesse unità e le stesse maschere costruiscono T nel
training, nel banco e nell'esportazione. Non sommare a prod una R addestrata contro all.

**Misurato, rilettura esplorativa di output esistenti:** `all − prod`, senza correzione
neurale, nel banco v2 t28 a 400 cellule e cinque semi:

| Linea | Delta medio dei sei membri locali |
|---|---:|
| H1 | +0,037056 |
| HepG2 | +0,097862 |
| RPE1 | +0,042639 |
| Jurkat | +0,039346 |
| K562 | +0,111039 |

[Audit riproducibile](audit_inputs.py), [ricevuta con membri e dispersioni](audit_inputs_r1.json).
È una scelta di partenza sostenuta da questi confronti, non una conferma indipendente,
un punteggio VCC o la prova che all sia migliore di ogni possibile transfer. Il
contrasto storico `cells` resta documentato in S-010; non è stato rieseguito nel v2.
Ampliare il cubo modifica il candidato: il beneficio storico non certifica nuove fonti.

## 2. Rappresentazioni e campionamento

- Archivio completo e metadati restano immutati.
- **Pseudobulk completo delle cellule ammesse**, per studio × contesto × donatore/clone
  × condizione/tempo × modalità × chimica, mantenendo libreria/replica/guida quando
  disponibili. Conservare somme dei conteggi, media delle proporzioni per cellula,
  varianza e frazione di zeri separatamente. Non sostituire la media delle proporzioni
  con il rapporto delle somme. I filtri QC sono applicati prima di aggregare.
- **Campioni cellulari annidati 32/64/128**, come livelli di sviluppo da confrontare,
  non numerosità certificate sufficienti. Ordine hash indipendente dall'effetto;
  rotazione possibile cambiando seme e registrando le identità. Un livello contiene
  il precedente. Se gli strati sono più del cap, il cap sale per conservarli tutti.
  I controlli hanno serbatoi separati, con identica conservazione dei sottocontesti.
- Le medie complete supervisionano l'effetto medio; i campioni rendono economico
  stimare/usare lo stato dei controlli e confrontare il contributo dell'eterogeneità.
  Il primo confronto non richiede una nuova testa generativa delle cellule.
- Bilanciamento: uguale massa per famiglia di linea, poi studio, contesto, bersaglio
  e strato. Il numero di cellule CD4 non determina il peso di CD4. I pesi per la loss
  sono distinti dalle probabilità di inclusione necessarie per stimare la popolazione.

La bocciatura del livello 64 nella ricostruzione dei riassunti del vecchio pilot
([decisione](../../sorgenti/prepasso_ampliato_2026-10-04/DECISIONE_AGGIORNATA.md)) resta valida.
Qui i riassunti non si ricostruiscono dalle 64 cellule: vengono dall'intera popolazione
ammessa. Il valore predittivo e la conservazione degli stati rari rimangono da misurare.

## 3. Modello semplice e confronti

Effetto naturale-logaritmico **T + w R**, T congelato. R è una piccola MLP con uscita
a basso rango, inizializzata a zero e limitata in ampiezza; ingressi: T, descrittori
del bersaglio e, nel braccio condizionato, descrittori dei controlli. Nessun grafo GEARS
nel primo confronto. Nessuna testa di risposta comune rimossa solo all'esportazione.

Bracci riaddestrati sugli stessi fold:

1. T da solo; riferimento prod da solo, con la stessa emissione.
2. T + R senza contesto.
3. T + R con contesto, stessa supervisione e campione.

`hybrid.py` implementa modello, composizione unica per fit/banco/export e loss sulla
media della popolazione (KL fra proporzioni osservate e previste) più penalità del
residuo. Gli iperparametri di default sono valori da fixture, **non parametri scelti
su dati reali**. Non assumere la sufficienza della sola loss: si giudica con lo scorer.
Un basale nullo dove la verità è positiva richiede una scelta esplicita dello stimatore:
il codice lo rifiuta, senza introdurre pseudoconteggi silenziosi.

Il peso w può essere zero; va fissato/validato sulle linee interne, mai sulla linea
esterna. Il primo fit può usare w=1 con R regolarizzata, con confronto a T. La policy
di selezione finale va congelata prima del lancio; non è implementata in questi moduli.
Emissione primaria t28 nel banco, applicata una volta sola dopo l'effetto; t25 eventuale
diagnosi separata. `predict_effect` a w=0 riproduce esattamente T, comprese le maschere.

## 4. Copertura e validazione

D-053 resta integrale: tutti i contesti idonei hanno un ruolo, senza obbligare fonti
incompatibili a diventare ancore CRISPRi. KO/CRISPRa e sole stime aggregate hanno ruoli
espliciti separati. La compatibilità delle fonti è verificata, non dedotta dalla copertura.

Prima del lancio: inventario riconciliato, ricevute di QC/identità/assi, controlli e
statistiche per ogni sottocontesto; ogni lacuna è nominata. Il cubo attuale ha 34
tabelle e 10 gruppi: **non è il corpus completo** e CD4 non è ancora risolta per donatore
nelle tre tabelle. Le dodici unità cellulari CD4 verificate consentono di costruirlo,
non provano che sia già costruito.

Split per famiglia di linea prima di ogni statistica appresa. Le risposte della linea
esterna e, in J, tutti i bersagli nascosti globalmente, sono esclusi da fit, medie delle
fonti, basi, selettori e trasformazioni apprese. Controlli esterni solo all'inferenza.
Donatori e cloni correlati non diventano conferme indipendenti. H1 test resta chiusa.
Le cinque linee del v2 sono sviluppo; la conferma futura va scelta senza aprirne gli esiti.

Accettazione tecnica: parità a R=0; nessun contesto richiesto perso; esposizione e
contributi effettivi per contesto/target/strato; hash e assi coerenti; nessuna lettura
illecita; arresto sui non-finiti. Il banco usa 400 cellule × almeno 5 semi appaiati,
sei membri, risultato senza JAC e PDS per linea. Il segnale favorevole richiede
guadagno risolto positivo anche senza JAC e nessuna perdita risolta di PDS; non basta
una media fra linee. Una promozione richiede anche fit replicati e validazione appropriata.

## 5. Precedenti e guardie

| Strada | Differenza e controllo precoce |
|---|---|
| S-005 | Campioni compatti e bilanciamento verificato; fermare l'accettazione se un contesto ha zero uso |
| S-006 | Residuo inizialmente nullo, limitato e penalizzato; leggere specificità e PDS sulle linee interne |
| S-007 | Il semplice contesto medio non è una novità né una garanzia: braccio senza contesto riaddestrato e confronto dell'eterogeneità a dati fissi |
| S-009 | Un'unica definizione di T e R per fit/banco/export; PDS per linea, non scelta del fold per numerosità |
| S-010 | All come base motivata, prod come controllo; nessuna attribuzione alla rete del vantaggio già presente in T |

**Segnale precoce e arresto:** interrompere l'accettazione su leakage, contesti richiesti
non usati o parità a R=0 fallita; non promuovere una correzione con perdita risolta di
PDS su una linea. Verificare nelle linee interne se specificità e risposta comune
peggiorano prima di proseguire il fit; il limite operativo va congelato nel runner.

## 6. Stato eseguibile e dipendenze

Implementati e provati su fixture: momenti unibili su tutte le cellule ammesse,
campioni annidati che conservano gli strati, esclusioni fold, bilanciamento, blocco di
copertura incompleta, modello residuo, loss e parità dell'effetto. Non ancora collegati
al prepasso distribuito, al trainer operativo e all'esportatore dello stadio 100.

Per arrivare al job: costruire e verificare la banca completa di pseudobulk e campioni,
assemblare il manifest con i ruoli e le ancore lecite per fold, collegare il trainer,
verificare la parità fino alle cellule emesse, congelare il pacchetto e fare preflight
sul runtime. CPU Colab/Kaggle per preparazione; GPU Kaggle per il fit. Il portatile
esegue soltanto queste letture e fixture piccole. Nessun invio o push è implicito.
