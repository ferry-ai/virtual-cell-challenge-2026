# Il pseudoconteggio dello stimatore pseudobulk: un artefatto nelle sorgenti CD4 e Orion

27 settembre 2026, pomeriggio. Nella scheda [R-V2](../../docs/piani/modello-v2.md). Trovato guardando che cosa
toglie il t23 al t22. **Misure sugli effetti e sulle cache, non punteggi VCC.**

## Che cosa si è visto (misurato)

Le misure sono fatte con gli effetti del t22 (`processed/effects_t22_2026-09-26/`), la quota del t23
(`../quota_condivisa_2026-09-27/t23/share.csv`), le cache r5 dello stadio 98 e i profili basali dei contesti
(`processed/basal_sources_2026-09-26.csv`, geni espressi = almeno 5 CPM).

- **Dove sta l'energia del t22.** Il 72 % sta su geni non espressi nel contesto, che il generatore quasi non
  muove. Dell'energia sui geni espressi, il 36–43 % sta su geni a cui il t23 dà quota 0, cioè geni che meno di
  due universi sanno stimare.
- **In A e C i geni espressi con più energia sono sei geni del cromosoma Y**: USP9Y, UTY, KDM5D, ZFY, DDX3Y,
  EIF1AY. Portano il 5,3 % (A) e il 5,5 % (C) dell'energia pesata con log1p sui geni espressi. A e C li
  esprimono nei controlli, B no.
- **Vengono dalla sorgente CD4.** K562, HCT116 e HEK293T non li misurano. Nelle cache r5 `cd4_Rest`,
  `cd4_Stim8hr` e `cd4_mix` sono i primi geni della sorgente per effetto medio, e salgono con il 99–100 % dei
  293 knockdown del pannello (in `cd4_mix` la mediana grezza di USP9Y è +2,2 in logaritmo naturale).
- **Seguono il numero di cellule del bersaglio.** Nel t22 la media dei sei geni per bersaglio ha Spearman
  −0,52 con il logaritmo delle cellule CD4 del bersaglio (p 1e-21, 293 bersagli); nel grezzo di `cd4_mix`
  −0,43.
- **Non è la composizione dei donatori.** Geni che cambiano fra donatori per genotipo (ERAP2, CHI3L2) o sul
  cromosoma X (KDM5C) non si spostano: mediane vicine a 0, positivi nel 41–57 % dei bersagli.

## Il meccanismo (letto nel codice, `src/vcc2026/multisource.py`)

`effects_from_pseudobulk` calcola, per donatore (o per pool di lotti GEM in Orion),
`ln((S_t + 0,5) / L_t) − ln((S_c + 0,5) / L_c)`. Per un gene senza conteggi in nessuno dei due gruppi, come i
geni Y in un donatore femmina, il risultato è `ln(L_c / L_t)`: il rapporto fra i totali. È positivo perché i
controlli sono il gruppo più grande, e cresce quanto meno cellule ha il bersaglio. La stessa distorsione,
attenuata, colpisce un conteggio nullo nel bersaglio dove i controlli prevedono molto meno di 0,5 conteggi. In
HCT116 315 geni vicini a 1 CPM risultano indotti da oltre il 90 % dei knockdown del pannello (misurato in r5).
K562 passa per un altro stimatore (`effects_from_bulk`) e non ha nessun gene così.

## La correzione (implementata)

`effects_from_pseudobulk(..., pseudo_scale="library")` e `--pseudo-scale library` nello stadio 98. Il gruppo
più piccolo tiene 0,5 conteggi, l'altro riceve la stessa frazione del proprio totale. Con il bersaglio più
piccolo il cambio di espressione diventa `ln((S_t + 0,5) / (E_t + 0,5))`, con `E_t` il conteggio che i
controlli prevedono nel gruppo del bersaglio. Un gene assente da entrambi i gruppi dà 0; uno zero dove i
controlli prevedono 0,03 conteggi dà circa −0,06 (prima +2,8).

- **Il default non cambia** (`"constant"`). Con il codice nuovo gli effetti del t22 si ricostruiscono identici
  byte per byte (sha256 `7d6a3b15…` nei tre contesti), e lo stadio 98 in modalità di default riproduce le nove
  cache di r5 byte per byte (`confronto_r5_parita.json`).
- **Test** in `tests/test_multisource.py`: gene assente in un donatore, zero dove i controlli prevedono quasi
  nulla, gene perso letto come perso, totali uguali identici nelle due modalità.

## r6: un primo tentativo sbagliato (misurato, non usato)

La prima versione metteva il pseudoconteggio alla media geometrica dei due totali. Toglie i geni indotti, ma
rende repressi da oltre il 90 % dei knockdown 993 geni in HCT116, 823 in HEK293T e 221 in `cd4_mix`, e in Orion
porta l'energia a 1,75 e 1,98 volte quella di r5 (`confronto_r5_r6.json`, `r6/`). Con i controlli circa mille
volte più grandi del bersaglio, il bersaglio riceveva 0,016 conteggi e uno zero diventava una repressione forte.
La cache r6 resta in `processed/multisource_2026-09-27_r6/` come prova; nessuna ricetta la usa.

## r7: la seconda correzione, misurata e non usata

Pseudoconteggio di 0,5 nel gruppo più piccolo e la stessa frazione del totale nell'altro
(`pseudo_scale="library"`, ancora nel codice; `confronto_r5_r7.json`, `r7/`). Toglie tutti i geni indotti
(CD4 da 7–17 a 0 per sorgente, HCT116 da 315 a 0) e lascia pochi geni repressi da oltre il 90 % dei knockdown
(24 in `cd4_mix`, 1–9 altrove). Muove però molto più dell'artefatto: con i controlli molto più grandi del
bersaglio sposta anche i geni con pochi conteggi attesi, di `ln(E_t / (E_t + 0,5))`, da −0,05 a −0,4 per 10 e
1 conteggio atteso, mentre lì il pseudoconteggio costante era quasi senza distorsione. Il 57 % delle voci di
HCT116 cambia di oltre 0,01; la correlazione mediana per bersaglio con r5 scende a 0,72 in HCT116, 0,78 in
HEK293T, 0,87 in `cd4_mix`. Per un confronto a un fattore serve una correzione che tocchi solo l'artefatto.

## r8: una correzione minima, ma con la regola sbagliata (misurato, non usato)

Pseudoconteggio costante, e per ogni gene si scarta il donatore (o il pool Orion) senza evidenza. La prima regola
era `S_t + E_t < 1`: nessun conteggio nel bersaglio dove i controlli ne prevedono meno di uno
(`confronto_r5_r8.json`, `r8/`). In CD4 funziona: nessun gene indotto da oltre il 90 % dei knockdown, l'89–99 %
delle voci identico a r5. In Orion peggiora: i geni indotti passano da 315 a 495 in HCT116 e da 2 a 82 in
HEK293T, l'energia sale di 3,2 e 2,6 volte. Il motivo: fra otto pool, per un gene poco espresso restano solo quelli
in cui il bersaglio ha mostrato per caso un conteggio. È una selezione sull'esito, e ogni pool rimasto legge
un'induzione. La regola giusta guarda solo i controlli.

## r9: la correzione tenuta (misurato)

Pseudoconteggio costante, e per ogni gene si scarta il donatore (o il pool) i cui controlli prevedono meno di
un conteggio nel gruppo del bersaglio, qualunque sia il conteggio del bersaglio (`min_expected` 1; stadio 98
con `--min-expected 1.0`, cache `processed/multisource_2026-09-27_r9/`, `confronto_r5_r9.json`, `r9/`).
Sotto un conteggio atteso il pseudoconteggio costante legge un'induzione: circa +0,5 a 0,5 conteggi attesi, e
senza limite verso lo zero.

| Sorgente | Voci identiche a r5 | Correlazione per bersaglio con r5 (mediana) | Energia rispetto a r5 | Voci diventate non misurate | Geni indotti da oltre il 90 % (r5 → r9) |
|---|---|---|---|---|---|
| `cd4_Rest` | 92 % | 0,86 | 0,87 | 29.590 | 16 → 0 |
| `cd4_Stim8hr` | 94 % | 0,89 | 0,92 | 16.275 | 14 → 0 |
| `cd4_Stim48hr` | 94 % | 0,97 | 0,98 | 18.862 | 7 → 0 |
| `cd4_mix` | 86 % | 0,88 | 0,95 | 20.291 | 17 → 0 |
| `orion_hct116` | 94 % | 0,91 | 0,68 | 169.277 | 315 → 0 |
| `orion_hek293t` | 95 % | 0,92 | 0,86 | 90.498 | 2 → 0 |

K562 è identico byte per byte. I geni repressi da oltre il 90 % dei knockdown restano pochi (0–14 per
sorgente, come in r5). Le voci che cambiano sono quelle con pochissimi conteggi attesi: diventano non misurate,
e le altre sorgenti (o lo zero, se nessuna le misura) ne prendono il posto.

## t25: il t22 sulla cache r9

Ricetta `configs/recipes/t25.json`: quella del t22, costruita con lo stadio 100 su r9 invece che su r5; è un
solo fattore. Misurato sugli effetti costruiti (`processed/effects_t25_2026-09-27/`):
- i sei geni Y portano lo 0,08 % dell'energia pesata sui geni espressi in A e in C, contro il 5,3 % e il 5,5 %
  del t22;
- l'energia pesata è 0,99, 1,02 e 0,96 volte quella del t22 (A, B, C);
- la correlazione per bersaglio con il t22 sui geni espressi ha mediana 0,90, 0,92 e 0,88: cambia più dei soli
  geni Y (B, senza geni Y, è a 0,92), perché cambiano anche i geni con pochi conteggi di CD4 e Orion e con loro
  la risposta media che la ricetta sottrae;
- i geni mossi per bersaglio passano da 13.958 a 13.728 (mediana).

Previsione e regola registrate alle 11:41:47 UTC del 27/09, prima della generazione
([previsione](../prediction_t25_2026-09-27/prediction.json)). Generazione avviata alle 13:42 (ora italiana).

## Che cosa va ricontrollato

- Gli **universi** CD4, HCT116 e HEK293T sono stati costruiti con il pseudoconteggio costante. Tutto ciò che li
  usa porta l'artefatto: atlante r1 e r2, la quota del t23, i descrittivi della condivisione. Gli accumulatori
  di Orion permettono di rifare la stima senza riscaricare; CD4 va riletto dal pseudobulk genome-wide.
- Il **t23** toglie i geni Y perché li mette a quota 0. Un suo eventuale guadagno mescola la rimozione
  dell'artefatto, l'esclusione dei geni non stimabili, la pesatura e la riscalatura: serve un'ablazione.
