# Proposta PIE congelato — r1

**Tipo: ipotesi e protocollo proposto; non ancora concordato con VALIDAZIONE.**
Scritto prima di ogni inferenza e lettura di nuovi risultati. Nessun holdout aperto.
L'accordo, gli input e gli hash saranno un documento successivo; questa versione
non viene retroattivamente adattata ai risultati.

## Domanda e meccanismo

Il transfer conserva lo stesso bersaglio osservato altrove, ma non apprende una
mappa da conoscenza biologica del target e controlli a effetti nuovi. PIE combina
descrittori esterni con evidenza perturbazionale di training: può aggiungere
specificità in J e correggere alcuni errori C. È un'ipotesi, non un effetto misurato.

Primo candidato: PIE wdataset congelato, un checkpoint coerente con la linea
esclusa, senza ensemble di fold. Alternativa di meccanismo: descrittori biologici
congelati con regressione regolarizzata mascherata, fit soltanto nel training del
fold; ESM2 se disponibile e autorizzato, confronto con descrittori già presenti.
TxPert è ulteriore candidato di modello, da qualificare per asset/split/licenza.

## Precedenti

- S-001/S-002: discriminazione persa; misurare target scambiati e generico, non solo MSE.
- S-003: miscela post hoc non promettente; nessuna ricerca di pesi sul test.
- S-006: correzione comune dominante; esaminare quota comune e componente specifica,
  senza sottrarre una nuova media o cambiare ampiezza durante questo confronto.
- S-009: il banco deve riprodurre esattamente il candidato esportato, fallback incluso.
- CP-0051 (Arc Stack): A/B negativi su dodici target; PIE cambia il meccanismo
  (effetti e memoria aggregata, non generazione cellulare in-context). Non si
  rilancia Stack né si presenta PIE come rimedio dimostrato a quel risultato.

**Segnale precoce e arresto:** split/provenienza non verificati, assi duplicati,
normalizzazione incompatibile o baseline alterata a ramo nullo bloccano l'export.
Un difetto d'interfaccia si corregge prima dello score. Assenza di discriminazione
o danno PDS nel development porta a diagnosi e alternativa, mai a tuning sul test.

## Contrasti da ratificare prima della corsa

Input congelati da VALIDAZIONE: release, fold, liste C/J, controlli, baseline già
emessa in scala finale, asse genico, semi e generatore t28. Nessuna risposta H1 test.
Le esposizioni dei pesi e della memoria comprendono train, validation, selezione,
calibrazione e derivati, non solo file di training. J richiede target esclusi da
tutte quelle fonti. Unknown equivale a non ammissibile, non a assenza di esposizione.

Bracci: baseline; PIE sul supporto comune; sostituzione PIE+fallback baseline sul
pannello completo; generico e target permutati come controlli di specificità.
Non moltiplicare per p_de e non interpretarlo come p-value. delta_p_pred resta
diagnostico. lfc_pred può essere convertito di base logaritmica, ma l'export
richiede una verifica distinta di normalizzazione, pseudoconteggio e denominatore.
Nessun nuovo guadagno, centratura, testa cis o generatore. La scala finale del
ramo esterno dev'essere congelata su sviluppo separato prima del confronto.

Proposta di successo: sei membri reali, macro per contesto; limite inferiore
95% del delta medio >0 e guardia delta PDS >=0 per contesto, C/J separati.
VALIDAZIONE deve ratificare aggregazione, unità di bootstrap, soglie e numero di
semi prima di eseguire. Nessuna promozione sulla sola media degli effetti.
Rapportare anche copertura e risultati per supporto, correlazione degli errori
fra modelli, ampiezza, quota comune e prestazione del ramo fallback. Senza queste
misure: approfondire, non adottare. Valutazione della complementarità senza
ottimizzare una miscela sulle righe giudicate.

## D-053 e risorse

Un checkpoint esterno è un esperimento limitato, non sostituisce l'integrazione
di tutte le linee idonee. Ogni esclusione deriva da validazione, supporto misurato
o incompatibilità documentata. Il fallback conserva le richieste fuori supporto.
Fixture locali; CPU pesante Colab/Kaggle CPU, training/inferenza CUDA su Kaggle
solo dopo preflight §3, verifica runtime e coordinamento. I requisiti di training
degli autori non sono una misura dei requisiti d'inferenza nostri.

Freeze obiettivo: 23:00 8/10 Europe/Rome, consegna 02:00 9/10; nessuna stima di
durata o promessa di inferenza prima di misurare risorse e dipendenze.
