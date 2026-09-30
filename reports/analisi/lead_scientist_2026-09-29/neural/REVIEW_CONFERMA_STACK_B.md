# Revisione indipendente del codice di conferma Stack B

29 settembre 2026. **Revisione di implementazione e test sintetici**; nessuna
inferenza reale o lettura degli outcome B/riserva durante questa revisione.
Nessuna modifica ai file revisionati, alle formule o alle soglie.

Esito: nessun difetto bloccante rilevato. La conferma reale richiede ancora
selezione A/B completa e valida, un solo candidato scelto, protocollo finale B
separato e input/runtime congelati. Il protocollo finale B non esiste al momento
del controllo; il codice si arresta se manca. Non è una verifica GPU né una prova
di miglioramento del modello.

## Identità controllate

| File | SHA256 |
|---|---|
| `stack_confirmation_b_infer.py` | `c63fb09e3aed7dbf7d01e5c7058054e9f55be4c90740b072876c1870502132dc` |
| `stack_confirmation_b_score.py` | `f98994c6fed6776d37a3aa4427a892cc4cc769f5c5530a4227e3b0fe65fd8fe3` |
| `test_stack_confirmation_b.py` | `f4d54c4b5b0bc3950446c73c24eebc95b9364bf262f250db28826a071c87707e` |

Il confronto testuale con i due file A congelati mostra una sola modifica
scientifica in inferenza: `model_adata` conserva l'asse misurato proprio di ogni
input (infer B, righe 70–73), come il pilota B, righe 325–328. Il supporto S in
uscita resta comune. Tutte le altre differenze riguardano descrizione, provenienza,
protocollo separato e guardia della selezione A/B.

## Controlli sostanziali

- Infer B righe 39–50: hash dell'adapter, protocollo diverso da A, identità del
  selettore e ricevuta incorporata con B selezionato sono richiesti prima degli
  input scientifici. La derivazione del bundle conserva i membri byte per byte.
- Infer B righe 100–131: stesso cache del controllo sintetico per dimensione
  prompt, stesso helper congelato, q0/qStack float64 esportati prima del sampling,
  assi stringa senza pickle. Il test percorre pilota B ed exporter sullo stesso
  modello fittizio: 14 chiamate identiche, 24 profili identici bit per bit, input
  esclusivi sorgente/destinazione presenti e fallback esatto fuori S.
- Score B righe 64–75: tre semi 1/2/3, 400 cellule, Poisson, library appaiate per
  target, cap invariati. Il confronto AST dei test verifica identità di tutte le
  funzioni numeriche e dei cicli di generazione rispetto allo scorer A.
- Score B righe 126–177: D >= 0,005, tutti i D per seme > 0, limite inferiore
  IC95% > 0 e variazione PDS >= 0. PDS individuato per nome; 2.000 bootstrap
  appaiati, stessa eleggibilità e nessuna rimozione dei draw incompleti. MSE
  rimane separata e usa l'aggregazione del comparatore, non una media dei rapporti.
- Score B righe 244–251: la ricostruzione q0 rispetta la promozione dtype della
  versione NumPy d'inferenza; la tolleranza riguarda soltanto il controllo.
  Le cellule usano sempre gli esatti profili esportati.

## Test eseguiti

Comandi dal repository con `.\scripts\py.cmd -m unittest discover -s
reports/analisi/lead_scientist_2026-09-29/neural`:

- `-p test_stack_confirmation_b.py`: **3 test PASS**, 5,100 s.
- `-p test_stack_confirmation_score.py`: **12 test PASS**, 1,303 s.

Il modello fittizio verifica il percorso del codice e le identità, non le
proprietà stocastiche del decoder reale. Rimangono i limiti preregistrati:
controlli sintetici condivisi, un'unica inferenza Stack, tre semi delle sole
cellule finali, bootstrap condizionale ai ranghi PDS del pannello completo e
pretraining HepG2 non escluso. Nessuno di questi limiti modifica il gate.
