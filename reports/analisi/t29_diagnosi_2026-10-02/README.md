# Diagnosi del t29: perché la rete R-LAB va sotto zero

2 ottobre 2026, sera, Claude Code sulla macchina del teammate. Alfredo riferisce in chat che il t29 (rete R-LAB r2,
braccio `desc`, generatore del t22, entry `K6Q36uGCaEwQ1wRLmBLp`) ha un punteggio ufficiale **negativo**. I sei
membri non sono ancora in questo repository: l'invio è di un altro account della squadra, e la classifica pubblica
non mostra la squadra (alle 21:55 e alle 22:20 il suo ultimo invio non risultava `published`).

Le ipotesi qui sotto sono scritte **prima** di vedere i sei membri e prima di girare la diagnosi sugli effetti veri.
Vengono dalla lettura del codice e dai file già nel repository.

## Verificato nel codice (non è la causa)

- **Unità:** l'esportatore scrive ln fold change, e lo stadio 45 converte in log2 (`lfc / ln 2`,
  `src/vcc2026/inference.py`).
- **Ingresso del contesto:** la rete normalizza da sé i conteggi grezzi (log1p CP10k dentro `context()`), quindi
  l'esportatore le passa la stessa forma del training.
- **Geni:** abbinati per simbolo; 18.527 su 18.533 osservati in ogni contesto (`t29_effects_manifest.json`).
- **Contesti:** non scambiati. La verifica di provenienza dello stadio 45 dà A, B e C più vicini al proprio basale.
- **Generatore e impacchettamento:** identici al t22.

**Non verificabile da qui:** che la matrice dei descrittori passata all'esportazione sia la stessa del training. I
file sono sul PC del proprietario.

## Ipotesi, in ordine di peso atteso

1. **Uno spostamento denso e uguale per tutti i bersagli.**
   - **Indizio:** gli effetti del t29 hanno |lfc| medio 0,113–0,130 in ln, cioè circa 0,16–0,19 in log2, mediato su
     **tutti** i 18.527 geni (`lfc_abs_mean_observed`).
   - **Confronto:** gli effetti del t22 muovevano 208–300 geni rilevabili per bersaglio.
   - **Perché fa male:** con 400 cellule per bersaglio, uno spostamento di quell'ampiezza su ogni gene espresso
     produce migliaia di geni chiamati DE per bersaglio, quasi tutti in comune fra i 300 bersagli.
   - **Firma attesa:**
     - PDS scalato vicino a 0, perché i bersagli non si distinguono;
     - Jaccard intorno a 0 e fedeltà molto negativa (`k / max(n_pred, n_conf)` con `n_pred` enorme);
     - nMAE negativo.
2. **Il codice del bersaglio sa poco del bersaglio.**
   - Nel braccio `desc` l'embedding per simbolo è spento: due geni con descrittori simili ricevono risposte simili.
   - Su HepG2 tenuto fuori il coseno della rete era 0,266 contro 0,390 del trasferimento (classe C), e −0,062 sulla
     classe T ([esito di r2](../../modelli/cellnet_esteso_2026-10-01/ESITO.md)).
   - Anche senza l'ipotesi 1, il PDS scende molto sotto lo 0,63 scalato del t22. Il PDS valeva circa 0,105 dei
     0,141 del t22.
3. **Manca il knockdown del gene bersaglio.** Il t22 ha una testa *cis* che abbassa esplicitamente il gene
   bersaglio; la rete deve impararlo e non ha un termine dedicato. Se il gene bersaglio non scende, si perde il
   segnale più facile per PDS e DE.
4. **Il confondimento di libreria nel training (r2):**
   - **Il difetto:** r2 precede le correzioni del passo A di R-LEAD. Le cellule perturbate di una libreria si
     confrontavano con i controlli raccolti da tutto il contesto.
   - **L'effetto:** la differenza sistematica fra librerie diventa un "effetto della perturbazione" comune a tutti i
     bersagli. È la sorgente più probabile della componente condivisa dell'ipotesi 1.
   - **La conferma:** la perturbazione generica di r2 su HepG2 aveva coseno −0,019 sulla classe C, cioè una
     direzione che non è quella della risposta vera.

## Come si decide fra le ipotesi

**Primo dato, il più economico:** i sei membri scalati del t29 (`vcc status K6Q36uGCaEwQ1wRLmBLp --json`
dall'account che l'ha inviato). La firma dell'ipotesi 1 è PDS circa 0 con fedeltà e nMAE molto negativi; quella
della 2 da sola è PDS basso con gli altri membri vicini al t22.

**Poi la diagnosi sugli effetti**, sul PC che ha i file (un minuto, sola CPU, nessun accesso alla rete):

```
python reports/analisi/t29_diagnosi_2026-10-02/diagnose_effects.py \
    --effects <vcc2026-data>/processed/effects_t29_2026-10-01 \
    --reference <vcc2026-data>/processed/effects_t22_2026-09-26 \
    --controls A=<raw/controls>/context_A.h5ad B=<raw/controls>/context_B.h5ad C=<raw/controls>/context_C.h5ad \
    --out t29_diagnosi.json
```

Che cosa misura, per contesto:

| Misura | Ipotesi | Se l'ipotesi è vera |
|---|---|---|
| geni rilevabili per bersaglio (soglia del t22: \|log2\| ≥ 4/√(400 μ), ≥ 5 CPM) | 1 | migliaia contro 200–300 |
| quota della somma dei quadrati portata dal profilo medio | 1, 4 | vicina a 1 |
| geni rilevabili del solo profilo medio | 1, 4 | migliaia |
| spostamento log2 del gene bersaglio, quota negativa | 3 | mediana vicina a 0, quota circa 0,5 |
| coseno con lo stesso bersaglio del t22, sui geni rilevabili del t22 | 2 | basso |
| quota di bersagli il cui profilo t22 più vicino è il proprio | 2 | vicina al caso (1/300) |

**Prova su dati sintetici** (A con i controlli veri, effetti finti):
- **profilo denso e condiviso:** 3.932 geni rilevabili per bersaglio, quota condivisa 0,96, quota del proprio
  bersaglio 0,003;
- **profilo sparso e specifico:** 92 geni, quota condivisa 0,003, gene bersaglio −2,89 log2 in ogni bersaglio.

Lo script distingue i due casi come previsto.

## Che cosa cambia per R-LEAD

Le correzioni del passo A (controlli per libreria, braccio generico, miscela dal logit) attaccano proprio le ipotesi
1 e 4. Il training r1 in corso ha un confronto col braccio `generic` nel protocollo
([PROTOCOLLO](../../modelli/rlead_training_r1_2026-10-02/PROTOCOLLO.md)). Ma **nessun invio di una rete** dovrebbe
partire senza prima girare questa diagnosi sui suoi effetti esportati: un pacchetto con migliaia di geni DE per
bersaglio si riconosce in un minuto, senza consumare un invio.

## Esito: i sei membri, letti contro le ipotesi (aggiunto dopo, 2 ottobre sera)

**Fonte:** CP-0055 di Davide (`0055-t29-rete-cellulare-punteggio.md`, ricevuto in chat; non ancora su GitHub). Il
t29 vale **−0,029625**, rango 893; contro il t22 (+0,141250) perde 0,1709.

Scomposizione della perdita, come (t29 − t22) scalato / 6:

| Membro | t29 grezzo | t22 grezzo | t29 scalato | t22 scalato | Contributo alla perdita |
|---|---|---|---|---|---|
| PDS | 0,503 | 0,787 | 0,007 | 0,634 | −0,1045 (61%) |
| nMAE | 1,095 | 0,927 | −0,157 | 0,120 | −0,0462 (27%) |
| reach | 0,057 | 0,195 | −0,026 | 0,131 | −0,0262 (15%) |
| Jaccard | 0,034 | 0,036 | 0,009 | 0,014 | −0,0008 |
| fedeltà | 0,510 | 0,497 | −0,011 | −0,052 | **+0,0068** |
| MSE | 10,24 | 3,06 | 0 | 0 | 0 (tosato a 0 in entrambi) |

**Lettura contro le ipotesi scritte sopra:**
- **Ipotesi 2 (codice del bersaglio debole): confermata come causa principale.**
  - Il PDS grezzo 0,503 è il caso (0,5): i 300 bersagli non si distinguono.
  - Da sola spiega il 61% della perdita.
- **Ipotesi 1 (spostamento denso e condiviso): confermata a metà.**
  - La parte "condiviso" regge: è ciò che rende i bersagli indistinguibili, e l'MSE grezzo triplica (10,24 contro
    3,06), quindi la risposta comune è sbagliata sui contesti A, B, C.
  - La parte "migliaia di geni DE per bersaglio" **non regge**: fedeltà e Jaccard grezzi sono uguali al t22. Se la
    previsione avesse chiamato migliaia di geni in più, la fedeltà (`k / max(n_pred, n_conf)`) sarebbe crollata, e
    invece sale di poco.
  - La firma prevista sopra (fedeltà molto negativa) è sbagliata.
- **Reach e nMAE:** sui geni che cambiano davvero, la previsione è troppo piccola o nel posto sbagliato.
  - È coerente con due cose già note:
    - la miscela (`pi` medio 0,59–0,67) rimpicciolisce gli effetti;
    - l'ampiezza naturale: il t22 usa l'amplificazione ×1,576, e D-042 ha mostrato che l'ampiezza conta.
  - Questi due membri non separano rete e ampiezza.
- **Ipotesi 3 (nessun knockdown del gene bersaglio) e 4 (confondimento di libreria):** compatibili col PDS al caso, ma
  i sei membri non le distinguono dalla 2. Serve `diagnose_effects.py` sugli effetti veri. La misura
  `own_gene_log2_shift` decide la 3; la quota condivisa e il confronto col t22 decidono fra 2 e 4.

**Per R-LEAD:**
- La domanda giusta è la parte specifica del bersaglio. Il confronto Q1 del training r1 (`ident` contro `generic` sui
  gruppi C) misura proprio questa, in locale.
- Per la regola del CP-0055 (ramo c), nessun invio di una rete prima di un banco locale a sei membri che la mostri
  almeno al livello del trasferimento.
