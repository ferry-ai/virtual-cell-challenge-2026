# Peer review del pilot Stack

29 settembre 2026. **Revisione statica indipendente più tre regressioni sintetiche**.
Nessun checkpoint caricato, nessun training, inferenza reale o scoring eseguito da
questa revisione. Nessun risultato del pilot letto. Skill applicata:
`engineering:code-review`. Ambito: `stack_pilot.py`, `stack_remote_runner.py`,
`score_stack_pilot.py`, `requirements_stack.txt`, protocollo, test e API Arc al commit
`cacc2e4b09435c3e536d46237d10b50f222dd144`.

**Esito:** non ho individuato un blocco certo dell'inferenza o un disallineamento
fra prompt, output e asse dei geni nel percorso esaminato. Prima di leggere il
risultato va usato lo scorer aggiornato con le guardie sotto. Il nullo della
correzione sintetica ha una proprietà composizionale da descrivere precisamente;
non richiede di cambiare la formula preregistrata.

L'adapter è rimasto identico alla preparazione congelata:
SHA256 `b259371df3d0d515003597c4d9ce5755c25840f0d36fc96d8ac390ffe1275508`,
verificato direttamente e coincidente con `stack_plan_r1.json` e
`stack_setup_r1/setup_manifest.json`. Non sono stati modificati l'adapter,
`test_stack_pilot.py`, il protocollo o l'archivio congelato.

## P2 — controllare la provenienza dell'inferenza, non soltanto il bundle

**Rilevato nella prima lettura:** `score_stack_pilot.py`, righe 123–129 della versione
prima della correzione, controllava solo `inference_manifest.bundle_sha256`.
Predizioni prodotte con lo stesso bundle ma adapter, checkpoint o lista geni diversi
potevano essere accettate e valutate come il pilot congelato. Non affermo che sia
successo: è un percorso di accettazione non protetto.

**Correzione minima e stato verificato:** l'attuale `verify_inference_provenance`,
righe **97–103**, confronta bundle, adapter, checkpoint e genelist con i valori
congelati; il main la chiama prima di leggere la verità perturbata. Implementata
dall'autore dello scorer e riletta durante questa revisione. Non cambia predizioni,
metriche, soglie o selezione. Il nuovo scorer va congelato in un nuovo snapshot;
quello vecchio resta prova storica.

## P2 — impedire che lo stesso bersaglio scompaia da entrambi i bracci

**Rilevato nella prima lettura:** `per_target`, righe 85–89 della prima versione,
faceva `pivot().reindex(targets)` senza verificare l'insieme effettivo dei bersagli.
Un bersaglio assente da entrambi i CSV diventava NaN in entrambi. La comparazione
delle maschere poteva passare, come la verifica delle medie se gli aggregati erano
calcolati sugli stessi bersagli rimasti. Si sarebbe potuto riportare il pilot dei
12 preregistrati avendone valutati meno.

**Correzione minima e stato verificato:** righe **85–94** attuali richiedono l'insieme
esatto dei bersagli e PDS presente e finita per ognuno. Restano legittimi i NaN degli
altri membri quando previsti dalla loro eleggibilità. Correzione implementata
dall'autore e riletta; non aggiunge un filtro sulla bontà dei risultati.

## P2 nella lettura scientifica — il rapporto sintetico nullo non annulla tutta la risposta su S

La formula congelata di `stack_pilot.py`, righe **232–253**, è coerente con l'ibrido
registrato: fuori dall'intersezione S mantiene `q0`; su S inclina il basale mediante
il rapporto sintetico e lo riscalibra alla massa `q0(S)`.

Quando perturbazione e controllo sintetici coincidono, il vettore `d` è zero. Ma:

```
q_null[g] = basal[g] * q0(S) / basal(S),  g in S
q_null[g] = q0[g],                        g outside S
```

Quindi è nullo il cambiamento **relativo fra geni di S**, non necessariamente
l'effetto su ciascun gene rispetto al basale completo. Il valore
`shared_lfc_rms == 0` descrive `d`, non tutto il log-fold-change della previsione.
La frase del protocollo «l'effetto Stack si annulla su S» va letta in questo senso.

Controesempio sintetico, con uguale massa totale 37:

| Vettore | A | B | C fuori S |
|---|---:|---:|---:|
| Basale | 10 | 20 | 7 |
| Transfer q0 | 15 | 17 | 5 |
| Ibrido con d=0 | 10,666667 | 21,333333 | 5 |

Il trasferimento di massa fra S e il complemento resta ereditato dal transfer.
La diagnostica corretta in log2, indipendente dalle unità dei vettori, è:

```
inherited_shared_mass_log2_shift = log2[(q0(S)/q0(total)) / (basal(S)/basal(total))]
```

Diventa `log2(q0(S)/basal(S))` soltanto quando i due totali sono uguali.
`predicted_profile` conserva quel totale nel percorso corrente, ma la versione
normalizzata rende esplicito il significato composizionale. Nel controesempio lo
spostamento vale `log2(32/30)`, pur essendo nullo il rapporto sintetico.

**Azione:** conservare la formula e qualificare la lettura del nullo. Un eventuale
addon diagnostico può ricostruire questo termine dai controlli, dagli effetti
congelati e dal supporto S, senza vedere la verità perturbata né cambiare le
predizioni. Non chiamare tale termine un errore di Stack: è parte dell'ibrido.

Ho aggiunto soltanto il file indipendente
`test_stack_compositional_null_review.py`: **3 test PASS, 0,032 secondi** nel runner
unittest, senza pesi né dati. Coprono masse S diverse, invarianza del risultato
normalizzato rispetto alle unità e il caso ottenuto con il vero
`predicted_profile` su input sintetico. Il test congelato precedente usava masse S
uguali e pertanto non distingueva queste due nozioni di nullo.

## P3 — diagnostica incompleta della massa generata fuori supporto

Il protocollo promette di rendere esplicita la massa fuori supporto. Il codice
attuale registra `shared_genes` e `model_genes` alle righe **337–343**, ma non le
frazioni di massa degli output Stack perturbato/controllo fuori S. In
`corrected_profile` quelle masse sono escluse dalla normalizzazione e poi perse.
Il conteggio dei geni non quantifica questa differenza.

Non è un errore nell'applicazione della formula e non giustifica cambiare l'adapter
già congelato. È una limitazione della diagnostica disponibile: la massa del
decoder fuori S non potrà essere ricostruita dai soli due H5AD finali, che contengono
già l'ibrido ricampionato. Per una futura revisione dell'adapter, registrare separatamente
le due frazioni prima della normalizzazione. Il termine composizionale precedente,
invece, è ricostruibile anche senza conservare gli output intermedi Stack.

## Controlli senza difetti riscontrati

- **Assi e cellule:** `align_shared` (220–229) riallinea esplicitamente entrambi gli
  input all'ordine del modello. Il reader Arc mantiene quell'ordine; l'API seleziona
  le sole cellule destinazione, esclude il padding e riallinea all'input. Il controllo
  di forma a 267–269 è appropriato. Verificati anche `ICL_FinetunedModel` e mixin:
  non sostituiscono questo percorso di inferenza.
  [API congelata](https://github.com/ArcInstitute/stack/blob/cacc2e4b09435c3e536d46237d10b50f222dd144/src/stack/models/core/inference.py),
  [riallineamento](https://github.com/ArcInstitute/stack/blob/cacc2e4b09435c3e536d46237d10b50f222dd144/src/stack/models/utils.py).
- **Maiuscole:** il reader Arc converte i nomi input in maiuscolo. Il controllo
  indipendente `genelist_metadata_r1.json` registra 15.012 geni, tutti già maiuscoli,
  unici anche dopo conversione, con SHA uguale a quello consentito. Non emerge
  una collisione di simboli nel file concreto.
  [Reader congelato](https://github.com/ArcInstitute/stack/blob/cacc2e4b09435c3e536d46237d10b50f222dd144/src/stack/data/training/datasets.py).
- **Prompt e controllo sintetico:** righe 353–357 usano la stessa cardinalità,
  gli stessi controlli destinazione e lo stesso seed. Il caching per cardinalità
  non confonde le etichette dei target; il controllo sintetico è comune ai target
  con uguale numerosità, perciò non è una replica indipendente per ciascuno.
  L'API ricicla i prompt corti ed esegue in `no_grad`: i due sospetti non sono bug.
- **Unità e conteggi:** l'input conserva conteggi integrali, `lfc / log(2)` converte
  correttamente gli effetti transfer in log2 per `predicted_profile`, e l'output
  campiona nuove cellule con lo stesso Poisson e gli stessi limiti per i due bracci.
  La somma del profilo è conservata prima del campionamento; non viene bloccata la
  somma dei conteggi realizzati. L'identità fuori S riguarda il profilo atteso,
  non i singoli conteggi dopo il ricampionamento.
- **Separazione della verità:** `prepare` legge solo righe NTC HepG2 per il bundle;
  `infer` riceve quel bundle e non apre la verità perturbata. La scelta dei 12 usa
  conteggi sorgente e hash prima dei risultati. Non ho trovato selezione adattiva
  dentro l'adapter.
- **Metriche:** direzioni delle pendenze corrette; stessa popolazione eleggibile
  fra bracci; bootstrap appaiato con numero di campioni completi riportato. La
  correzione MSE rapporto-di-somme era già stata individuata prima di questa review:
  è presente e non viene presentata come finding nuovo. Anche il problema CRLF
  della preparazione era già noto e non è un nuovo finding.
- **Runtime:** archivio e pesi hanno allowlist e checksum, caricamento CPU seguito
  da trasferimento GPU, batch 1 e worker 0. Non ho verificato il picco di memoria o
  il resolver installando l'ambiente: la compatibilità effettiva resta provata dai
  controlli remoti `pip check`, import e inferenza, non dai test sintetici.

Il pilot resta esplorativo sui 12 target registrati e non certifica l'assenza di
HepG2 dal pretraining. Questa review non cambia il suo criterio per una conferma
distinta, non approva un invio e non anticipa alcun risultato del modello.
