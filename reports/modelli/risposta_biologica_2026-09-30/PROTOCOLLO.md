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

- Il via del proprietario sui ruoli degli altri dataset. Per H1 c'è: vedi §4.
- Gli shard cellulari dei job J01–J03 (`reports/sorgenti/corpus_cellulare_2026-09-30/PIANO_JOB.md`).
- `splits.py` e `test_leakage.py` (P4), scritti e provati prima di leggere qualunque esito.

## 4. H1 2025: la scelta del proprietario (30/09, sera)

Aggiunto dalla sessione `ec2e5b07`. Il proprietario ha visto locatore e byte di H1 (bucket pubblico
di Arc, 34,36 GB in tre h5ad) e ha scelto in chat: **lo split di test (100 bersagli) è la riserva;
train (150) e validation (50) vanno nel training.** Trascrizione in
`reports/sorgenti/corpus_cellulare_2026-09-30/AUTORIZZAZIONI.md`. Il registro in vigore è
[holdout_registry_r2.json](holdout_registry_r2.json); la versione r1 resta com'era.

**Limite, scritto prima di qualunque lettura.** Con train e validation nel training, H1 non è più un
contesto nuovo. La riserva misura quindi bersagli nuovi in un contesto già visto: è una domanda
diversa da quella della gara, che chiede bersagli noti in contesti nuovi. Per il contesto nuovo
restano i fold C/T/J. La regola con cui leggere la riserva si scrive in un protocollo nuovo, prima
di aprirla.

Il job 089 scarica i tre file, li verifica col crc32c del bucket, calcola lo sha256 e li copia su
Drive senza aprirli. Il file di test porta nel manifest il ruolo «RISERVA: non aprire».
