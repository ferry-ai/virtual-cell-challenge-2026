# Prove fatte sul branch `codex/teammate-rlead` (5–7 ottobre), da usare come test già fatti

7 ottobre 2026, notte. Claude Code per Alfredo, che ha chiesto di raccogliere per Davide le prove di questi giorni,
così da poterle riusare senza rifarle. Ogni riga rimanda alla cartella con previsione registrata, codice, manifest e
ricevute. **I dati e i pacchetti stanno fuori da Git**, in `vcc2026-data/` sul PC di Alfredo; qui ci sono hash e
percorsi.

**Numerazione:** t36, t37 e t38 sono provvisori, perché `main` è canonico. Prima di un merge vanno confermati con
Davide, insieme allo 0,1472 che la classifica mostra come ultimo invio del team (presumibilmente il t28 rifatto sulla
banca estesa, la cui ricevuta non è ancora su `main`).

## 1. Invii ufficiali (A/B/C, pannello di validazione)

| Invio | Cosa cambia | Punteggio | Contro il riferimento | Lettura con la regola registrata |
|---|---|---|---|---|
| t28 (riferimento, `main`) | effetti t25 ×1,5 + dispersione per gene | 0,144845 | — | — |
| **t36** | base `all` (tutte le tabelle del cubo r2, 10 gruppi, ampiezza 1,576) + w·R della rete CellNet (i file `export_abc_r2` di Davide, gli stessi del t30), emissione del t28 | **0,141392**, rango 446 | **−0,0035** sul t28 | ramo b, non conclusivo; fuori dalla banda prevista (0…+0,06) |
| t37 | base `all` senza R, emissione del t28 | non inviato | — | pacchetto pronto (sha256 `d83b7b6b…`) |
| **t38** | t36 con un solo cambio: `--effects-scale` 1,5 → 1,0 | in corso | contro il t36 | regola: ≥ +0,005 l'ampiezza 1,0 diventa l'emissione dei candidati successivi |

**Membri scalati del t36 contro il t28** (da [comparison.json](../../invii/prediction_t36_2026-10-06/comparison.json)):

| Membro | t28 | t36 | Δ | Peso sulla media |
|---|---|---|---|---|
| PDS | 0,622 | 0,591 | −0,031 | −0,005 |
| reach | 0,199 | 0,185 | −0,014 | −0,002 |
| Jaccard | 0,006 | 0,004 | −0,002 | ≈ 0 |
| nMAE | 0,049 | 0,074 | +0,025 | +0,004 |
| fedeltà | −0,007 | −0,006 | +0,002 | ≈ 0 |
| MSE | 0 | 0 | 0 | — |

**Che cosa se ne ricava (interpretazione):**
- **il guadagno di `all` su `prod` del banco v2** (+0,04…+0,11 sulle cinque linee tenute fuori) **non passa su A/B/C**.
  Il banco sovrastima già R (t30), e ora anche la base;
- **la base `all` + R migliora le ampiezze** (nMAE grezza 0,968 → 0,954) **e peggiora la direzione** (coseno PDS
  0,781 → 0,767);
- per separare la base da R servirebbe il t37, ma la differenza attesa sta sotto 0,01 in entrambi i sensi.

## 2. Che cosa non migliora e perché (dai numeri ufficiali)

Distacco del t28 dalla mediana delle prime 100 squadre, sulla media dei sei membri
([margini_orizzonte_2026-10-04](../margini_orizzonte_2026-10-04/README.md)):

| Membro | Distacco | Leva |
|---|---|---|
| MSE | 0,038 | la direzione del profilo aggregato: serve coseno ≥ 0,22, noi siamo a circa 0,1 |
| PDS | 0,023 | la direzione specifica del bersaglio |
| nMAE | 0,015 | l'ampiezza: il t25 (scala 1,0) era a 0,118 |
| reach, fedeltà, Jaccard | ≈ 0 | già vicini alla mediana |

- **La MSE esclude il gene bersaglio:** il knockdown modellato (ln fc mediano −1,74 sulla diagonale) non la aiuta.
- **Nessun parametro di emissione muove MSE e PDS.** È il risultato dei tetti misurati sul cubo
  ([ESITO_TETTI.md](../../modelli/guadagno_appreso_2026-10-05/ESITO_TETTI.md)): ampiezza, proiezione PCA e
  selezione delle chiamate valgono al più circa +0,01. **La leva misurata è il numero di linee sorgente** (circa +0,01
  di coseno per linea, senza saturazione a 8): è la strada della banca estesa.

## 3. Prove sul cubo e strumenti riusabili

| Cartella | Che cosa contiene | Esito |
|---|---|---|
| [guadagno_appreso_2026-10-05/](../../modelli/guadagno_appreso_2026-10-05/) | guadagno appreso per coppia sul transfer `all`; curva del coseno contro il numero di linee; tetti PCA (M2) e chiamate DE (M2b); calibrazione della MSE sul sito (M1); `esporta_all.py` per la base `all` | il guadagno non passa; PCA e top-N non passano; c ≤ 0,10 sul sito |
| [pooling_esatto_2026-10-06/](../../sorgenti/pooling_esatto_2026-10-06/) | pooling identico allo stadio 98 per il rifit sulla banca estesa (`pool_units` chiama la funzione originale), scorciatoia esatta per donatori disgiunti, `compare_tables`, 5 test sintetici | 5/5 OK; fare lo shrinkage prima della media cambia gli effetti (mediana 21% relativo) |
| [all_piu_R_2026-10-06/](../../modelli/all_piu_R_2026-10-06/) | `combina_R.py`: base + w·R sulle coppie osservate, con parità a w = 0 | parità OK su A/B/C; w > 0 su 230/300 bersagli |
| [rete_l1_2026-10-04/](../../modelli/rete_l1_2026-10-04/) | spostamento dei conteggi verso le ampiezze della rete L1 (t35, +0,0126 sul t34) | **da non applicare** a t28, t36 o al candidato esteso: hanno già la nMAE grezza (0,95–0,97) sotto l'obiettivo L1 (circa 1,02), quindi lo spostamento costerebbe circa −0,014…−0,02 |

## 4. Come riusarle sul candidato della banca estesa

1. **Emissione:** usare quella del t28, salvo che il t38 passi la regola. In quel caso `--effects-scale 1.0` con la
   dispersione per gene.
2. **Non sommare R** alla nuova base senza un braccio di confronto: sul sito R ha perso sia sopra `prod` (t30) sia,
   insieme ad `all`, nel t36.
3. **Lettura:** ogni cartella `prediction_*` ha un `leggi_*.py` che applica la regola registrata e scrive
   `comparison.json` senza sovrascrivere. Si possono copiare cambiando entry e riferimento.

## 5. Dati fuori da Git (PC di Alfredo, `vcc2026-data/`)

| Percorso | Contenuto |
|---|---|
| `processed/effects_all_2026-10-05/` | base `all` (A/B/C) |
| `processed/effects_t36_2026-10-06/` | `all` + w·R, con `manifest.json` (hash di base, correzione e uscita) |
| `processed/export_abc_r2_davide/` | i file di Davide, hash uguali a `SHA256SUMS` e al manifest del t30 |
| `artifacts/t36pack/`, `allt28pack_r2/` (t37), `t38pack/` | i pacchetti `.vcc` con `packaging.json` |

**Non dice:** nulla su D, E, F; ogni invio è un solo seme.
