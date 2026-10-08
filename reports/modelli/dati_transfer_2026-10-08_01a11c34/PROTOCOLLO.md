# Protocollo DATI-TRANSFER r1

8 ottobre 2026. Protocollo di sviluppo e consegna; la valutazione comparativa e
il suo manifest numerico appartengono a VALIDAZIONE. Nessun esito letto per scegliere
le soglie di questo documento.

## Contrasti

T0 conserva t36. T1 conserva stimatore, pesi, centratura sul pannello, ampiezza e
cis del transfer; usa la release canonica r1 senza il voto Tian 2019 neuroni RFK.
È un contrasto di ammissione nuovo: r1 e la sua vecchia regola restano immutabili.
La fonte neuronale resta nell'inventario per riconciliazione dei target/QC, non
viene esclusa definitivamente dal programma.

T2 usa la stessa banca di T1 ma stima la risposta media di ogni sorgente sui
target singoli ammessi del training, con peso uguale per target e maschere per gene.
Le esclusioni di linea, target/componenti e riserve precedono statistiche, pooling,
maschere apprese e centratura. Non si deriva un fold da un vettore di produzione.
Nessuna fonte mancante usa una media del pannello di ripiego.

KO e CRISPRa restano bracci distinti; nessuna inversione automatica dei segni né
criterio universale di discesa dell'mRNA. Etichette guida o combinazioni richiedono
crosswalk esplicito, con provenienza. I dati senza mapping restano lacune nominate.

## Accettazione tecnica

Hash e assi devono coincidere; gli output sono esclusivi. Ogni unità attesa è
derivata, riusata oppure ha una lacuna nominata. La ricevuta separa cellule nella
banca, rappresentate negli aggregati, campionate, lette e contributi al modello.
I contributi sono contati per target/gene e per strato biologico, senza equiparare
una tabella aperta a un voto o a supervisione cellulare.

Un test altera le risposte escluse e richiede invarianti gli output appresi;
il controllo positivo altera una risposta ammessa e deve cambiare il risultato.
Un secondo test verifica parità del ramo nullo. Protezione obbligatoria H1 test.
La release è parziale finché la riconciliazione D-053 non è completa.

## Precedenti

- S-010: ampliamento delle fonti, guadagno descrittivo t36. T1 separa l'ammissione
  dalla modifica della popolazione di centratura T2; nessuna promozione dal solo fit.
- S-006: correzione comune dominante. T2 sottrae una statistica del training
  congelata, non aggiunge una testa libera. La quota comune rimane una diagnostica.
- S-009: divergenza banco/export, PDS e rumore. VALIDAZIONE deve consumare lo stesso
  artefatto del candidato; emitter e trasformazioni rimangono identici.
- S-005: lettura incompleta mascherata dai pesi teorici. La ricevuta conserva
  l'uso effettivo, incluso zero, per ogni contesto previsto.

**Segnale precoce e arresto:** hash, mapping, split, assi o parità errati fermano
il consumer prima del fit. Una fonte T2 mancante blocca il rilascio T2. Una
regressione PDS o un guadagno non risolto nel banco appartengono alla decisione di
VALIDAZIONE e non autorizzano una promozione. Un test tecnico non è uno score VCC.
