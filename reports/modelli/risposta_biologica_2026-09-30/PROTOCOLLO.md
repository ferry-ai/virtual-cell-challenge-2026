# Rete biologica di R-LAB: ruoli dei dati e regole, prima di ogni training (P0-M)

30 settembre 2026 sera, Claude (sessione `a1ec75f0`), scheda
[R-LAB](../../../docs/piani/piano-giorno-2026-09-30.md). **Scritto prima di qualunque training**:
nessun modello di questa cartella è stato addestrato. I ruoli sono una **proposta**, finché il
proprietario non li approva (R-COMP, passo 2).

## 1. I ruoli

Sono in [holdout_registry.json](holdout_registry.json): per ogni dataset, dove i suoi esiti
perturbati sono già stati letti come verità, con la fonte, e il ruolo proposto.
- **Development**: ogni dataset con almeno una lettura di esito. Serve a scegliere, e le sue letture
  si sommano: un confronto nuovo su HepG2 non è una conferma indipendente (CP-0050).
- **Riserva**: esiti che nessuno ha letto, da leggere una sola volta dopo aver congelato modello e
  regola. **Fra i dati già sul disco nessun grande schermo CRISPRi a livello di cellula è intatto.**
  Il mirato HIPSCI, per esempio, è stato letto nella covariazione del 28–29/09. La candidata
  primaria è H1 della gara 2025, mai scaricata: 18.077 geni su 18.080 in comune con l'asse 2026, e
  25 dei suoi 300 bersagli nel pannello di validazione (misurato il 30/09).
- **Validazione ufficiale**: il pannello A/B/C, osservato solo come punteggio aggregato; ogni invio
  la consuma.
- **Test**: D/E/F, dal 22 ottobre.

## 2. Regole che valgono da subito

1. Chi legge un esito lo scrive nel registro dei ruoli, in una versione nuova del file: un dataset
   letto passa a development.
2. La riserva si scarica e si congela con il suo hash; non si apre per scegliere varianti, né per
   controllare un dubbio.
3. Le separazioni C/T/J sono per famiglia, studio e donatore o clone, e si fissano prima del fit. Centri,
   PC, programmi e normalizzazioni si stimano solo sul training del fold.
4. La soglia di utilità e le regressioni ammesse sui sei membri si scrivono prima del test, in un
   protocollo nuovo di questa cartella; un proxy a due membri non decide.
5. Un confronto «più dati» o «singole cellule» tiene fermo tutto il resto: stesso test, stessi split,
   stesso campionatore di valutazione (§9 del piano).

## 3. Che cosa manca prima del primo training

- Il via del proprietario sui ruoli e sulla riserva.
- Gli shard cellulari dei job J01–J03 (`reports/sorgenti/corpus_cellulare_2026-09-30/PIANO_JOB.md`).
- `splits.py` e `test_leakage.py` (P4), scritti e provati prima di leggere qualunque esito.
