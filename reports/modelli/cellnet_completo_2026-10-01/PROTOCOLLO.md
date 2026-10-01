# Terzo training della rete cellulare, con la seconda ondata: protocollo e regola di lettura

1 ottobre 2026, 04:05 CEST, Claude Code (sessione `07ebf08b`), scheda
[R-LAB](../../../docs/piani/piano-giorno-2026-09-30.md). **Scritto prima del lancio del secondo training e prima di
ogni suo numero** ([cellnet_esteso_2026-10-01](../cellnet_esteso_2026-10-01/PROTOCOLLO.md), non ancora lanciato a
quest'ora), e prima del lancio di questo. Codice: [risposta_biologica_2026-09-30](../risposta_biologica_2026-09-30/),
al commit scritto nei file di lancio di questa cartella.

## 1. Che cosa è

Ancora una **verifica tecnica**, non un risultato: un seme, HepG2 tenuto fuori come nei due training precedenti,
nessuna riserva aperta, nessun confronto a sei membri. È la prima corsa con tutte le modalità genetiche ingerite:
CRISPRi, CRISPRa e KO. Il proprietario vuole una rete addestrata su tutti i dataset utilizzabili (30/09). Rispetto al
secondo training cambia solo il corpus.

## 2. Dati

Il corpus del secondo training ([SCOSTAMENTI](../cellnet_esteso_2026-10-01/SCOSTAMENTI.md) §1), più la seconda ondata,
con gli spec di `reports/sorgenti/corpus_cellulare_2026-09-30/wave2_specs.py`:

| Dataset Kaggle | Studio | Modalità | Job |
|---|---|---|---|
| `rlab-a549` | A549, Cas9 | KO | 118 |
| `rlab-tian-norman` | Tian 2019 (iPSC, neuroni), Tian 2021, Norman 2019 (K562) | CRISPRi e CRISPRa | 119 |
| `rlab-kolf-small` | KOLF2.1J, schermi cromatina e metabolico | CRISPRi | 124 (riusa gli shard di cromatina del 116) |
| `rlab-kolf-strong` | KOLF2.1J, schermo forte | CRISPRi | 126 |
| `rlab-southard-rpe1`, `rlab-southard-hs27` | Southard 2025 | CRISPRa | 125 |

Entrano i dataset pubblicati al lancio del pre-passo. Quelli che non lo sono restano fuori, con il motivo scritto nel
file di lancio.

Restano fuori, con il motivo:
- HIPSCI genome-wide: da 1 a 5 NTC per linea;
- Jurkat GSE249595: nessuna chiamata delle guide;
- lo split di test di H1 2025: la riserva;
- KOLF pan-genome: 2,66 milioni di cellule, non ancora ingerito;
- Tahoe: farmaci, che per il proprietario non devono prevalere, e non ingerito;
- tutto ciò che il catalogo segna come non ingerito.

Le stesse regole dei dati dei training precedenti, senza modifiche. Ogni studio con il suo contesto è una chiave:
Southard RPE1 (CRISPRa) e Replogle RPE1 (CRISPRi) sono due chiavi, e lo stesso vale per Norman e Replogle su K562. Le
combinate di Norman hanno la loro classe e non si estraggono per il training. La modalità entra nella rete come input
(`mod_emb`).

## 3. Disegno e budget

- Pre-passo `rlab-prepass-r6` su CPU, con gli argomenti del secondo training: `--holdout-context HepG2
  --same-experiment h1_vcc2025=h1_vcc2025_train,h1_vcc2025_val --workers 4`.
- Kernel GPU T4×2 `rlab-cellnet-r3`, un processo, bracci `--arm desc=descriptors --arm ident=identity`.
  Argomenti: `--epochs 10 --workers 3 --eval-workers 3 --checkpoint-minutes 15 --eval-reserve-seconds 120`, il resto
  di default. Ciclo di ripresa 50 → 100 prima del training, come nel secondo.
- **Budget:** quello che resta della quota settimanale dopo il secondo training, meno 20 minuti di margine, e non
  meno di 60 minuti. Si scrive nel file di lancio prima del lancio. Se restano meno di 60 minuti, il lancio aspetta la
  quota della settimana dopo.

## 4. Regola di lettura, fissata ora

**A. Esito tecnico, voce per voce:** la stessa del secondo training, cioè:
- kernel con codice 0 e `resume_check.json` passato;
- `verify.json` senza shard diversi;
- `coverage.json` con la non-contaminazione passata e, se `epochs_done` ≥ 1, ogni cellula di training ammessa vista;
- `eval.json` completo entro il budget per entrambi i bracci;
- throughput a regime, frazione di attesa dei dati e memoria riportati.

**B. Lettura descrittiva, che non decide nulla sulla rete:** per classe (C, T, J) e per braccio, le misure dei
training precedenti. **Attese scritte ora:**
- (i) guadagno di log-verosimiglianza rispetto a nessun effetto positivo in media su C e T in entrambi i bracci;
- (ii) su J il braccio `identity` non ha informazione sul bersaglio nuovo; `descriptors` sopra `identity` è ciò che
  prevede l'ipotesi dei descrittori;
- (iii) nessuna attesa che la rete batta il trasferimento su C;
- (iv) nessuna attesa che CRISPRa e KO aiutino su HepG2, che è CRISPRi: il confronto con il secondo training (più
  dati, più modalità, stesso resto) è descrittivo.

Con un seme e un contesto tenuto fuori nessuna di queste attese, vera o falsa, è una prova; i numeri non entrano in
PROGETTO §0 come risultati.
