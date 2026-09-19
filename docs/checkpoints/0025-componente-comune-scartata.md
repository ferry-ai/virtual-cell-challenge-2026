# CP-0025 — Componente comune RPE1: scartata dalla sua regola

- **Data:** 2026-09-18
- **Tipo:** esperimento
- **Redatto da:** agente
- **Revisione umana:** no. Il proprietario ha scelto il disegno a due banchi prima dei risultati, non ha rivisto questa scheda.
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Aggiungere alla ricetta `t03` la risposta che i knockdown di RPE1 condividono
([CP-0024](0024-identita-del-bersaglio-su-hepg2.md)), con un peso scelto su bersagli diversi
da quelli giudicati, migliora la previsione? Il verdetto possibile è solo tenerla o scartarla.

## 2. Cosa è stato fatto

- Regola `configs/common_component_rule.yaml`, scritta prima dei job 024-027. Due banchi:
  - HepG2 (ricetta `t03` ± `w` × componente, stadio 75);
  - bersagli ufficiali in K562 (generatore senza effetto ± componente, stadio 73).
- In ciascun banco il peso si sceglie su un insieme di bersagli e il verdetto si dà su un
  altro, disgiunto.
- Si tiene solo se passano entrambi i banchi, battendo sia la ricetta senza componente sia la
  stessa componente permutata fra i geni.
- Stadio 91 → `reports/common_component_2026-09-18/c001/verdict.json`. I quattro `bench.json`
  sono copiati accanto.

## 3. Cosa si è osservato

**Misurato — verdetto: `DISCARD`**, nessun problema di validità.

| banco | peso scelto | risultato sul verdetto | esito |
|---|---|---|---|
| HepG2 (300 bersagli di taratura, 299 di verdetto) | 2,0 | +0,0107 sulla ricetta, +0,0161 sulla componente permutata; chiamate per bersaglio 521 → 962 (permutata 802) | passa |
| K562, bersagli ufficiali (111 + 113) | 0: ogni peso peggiora la media locale | nulla da valutare | non passa |

**Misurato — il guadagno su HepG2 si riduce fuori campione.** Sui bersagli di taratura, a
peso 2,0 era +0,045; sui bersagli di verdetto è +0,0107. Fra i pesi, non decisivi, `d_base`
va da +0,003 a +0,013 e `d_perm` da −0,008 a +0,017.

## 4. Interpretazione e incertezza

**Interpretazione.** Sui geni essenziali di HepG2 la componente aggiunge poco oltre il volume
di chiamate. Sui bersagli ufficiali in K562 peggiora la previsione: chiama quasi ovunque con
precisione dei segni 0,544, e fa crollare il Jaccard dove la verità non ha risposta.

**Limite di misura, non un errore che invalida il verdetto.** La metrica del banco K562 è la
media scalata con le ancore locali, dominata dal Jaccard, le cui ancore locali quasi
coincidono (0,342 e 0,388). Con una metrica meno fragile il «no» sarebbe meno netto. Il
verdetto non si riapre. Il mandato successivo del proprietario esclude esplicitamente medie
dominate da ancore quasi coincidenti.

## 5. Spiegazione semplice

Aggiungere a ogni previsione la stessa «reazione tipica» osservata in un'altra linea
cellulare aiuta pochissimo dove i bersagli sono simili a quelli della linea di partenza, e
danneggia dove i bersagli sono quelli della gara.

## 6. Conseguenze

- Il candidato è chiuso. Nessuna sottomissione.
- Il lavoro passa al predittore condizionato su bersaglio e contesto
  (`configs/conditioned_rule.yaml`, job 028-032), per mandato del proprietario del 18
  settembre.

## 7. Cosa corregge

Nulla. Completa [CP-0024](0024-identita-del-bersaglio-su-hepg2.md) §6, che indicava questa
componente come «candidato da misurare».

## 8. Domanda di comprensione

Perché un guadagno di +0,045 sui bersagli usati per scegliere il peso diventa +0,011 su
bersagli nuovi, e che cosa sarebbe successo scegliendo il peso sugli stessi bersagli del
verdetto?
