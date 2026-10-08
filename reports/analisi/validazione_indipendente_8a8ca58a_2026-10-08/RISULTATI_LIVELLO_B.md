# Risultati del livello B: sei membri con lo scorer vero, su cellule vere del lignaggio escluso

8 ottobre 2026, VALIDAZIONE (Claude Code `8a8ca58a`). **Misurato** su Kaggle CPU con `bench_v2.py` non
modificato, `cell-eval2` 0.16.0, emissione t28, 400 cellule previste per bersaglio, cinque semi appaiati; letto
con il §8 del [contratto v2](PROTOCOLLO_v2.md). [Come si esegue](LIVELLO_B.md), scritto prima dei numeri.

**Che cosa sono questi numeri.** Punteggi **locali**: ancore locali, verità a metà delle cellule vere, due lignaggi
di sviluppo. Non sono punteggi VCC; danno il verso di un confronto, non la sua entità sul sito. «± » è la
deviazione standard sui cinque semi del generatore, a verità e modello fissi: non è incertezza biologica.

## 1. Controllo del banco: il sei membri vede la specificità, ma poco

Stesso braccio T0, con le righe degli effetti scambiate fra i bersagli (un seme).

| Fold | Media locale T0 | Media locale T0 scambiato | PDS T0 | PDS scambiato | NMAE, FID, JAC |
|---|---:|---:|---:|---:|---|
| C-iPSC (55 bersagli) | 0,523 | 0,431 | 0,316 | −0,123 | quasi invariati: 1,746 → 1,727; 0,990 → 0,953; 0,139 → 0,154 |

**Misurato:** assegnare a ogni bersaglio gli effetti di un altro toglie al punteggio locale solo 0,09 su 0,52, quasi
tutto dal PDS (0,44 di differenza) e dalla profondità di segno; NMAE, fedeltà e Jaccard cambiano poco, e il Jaccard
sale. **Interpretazione:** su queste scale locali la media dei sei membri dipende in gran parte da proprietà che
non riguardano il bersaglio (ampiezza, numero di geni chiamati: circa 340 per bersaglio contro 41 della verità).
Un delta della media va sempre letto insieme al PDS, come chiede la guardia del §8.
