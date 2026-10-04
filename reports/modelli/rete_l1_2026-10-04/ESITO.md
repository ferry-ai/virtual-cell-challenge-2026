# Rete L1: esito secondo le regole registrate

4 ottobre 2026, sera:
- protocollo nel commit fb65db2, codice in e99119c e 059e76a;
- addendum 1 nel commit 31e1d80, prima del banco della variante.

Le uscite sono in [esito/](esito/). **Sono nMAE di un banco locale su porte DE approssimate, non punteggi VCC.**

## 1. Esito

| Braccio | Regola | Macro nMAE [IC 95%] | H1 | Esito |
|---|---|---|---|---|
| `rete` (registrata) | ≤ 0,99, IC < 1, batte `copia2` in ≥ 5/7 | **0,947 [0,933; 0,961]**, 6/7 | **1,495** | passa la regola; **scartata** dall'addendum 1 per H1 |
| `rete_anti` (addendum 1) | ≤ 0,99, IC < 1, **H1 < 1**, ≤ `copia1` in ≥ 5/7 | 0,974 [0,970; 0,978], 5/7 | **1,121** | **non passa** (H1) |

- **Conseguenza registrata:** niente invio stanotte. Il t35 non si genera; la previsione in
  `reports/invii/prediction_t35_2026-10-04/` resta come registrazione di un candidato non inviato.
- Il generatore con lo spostamento dei conteggi (`genera_l1.py`) e il suo controllo (`verifica_slide.py`) **non sono
  stati eseguiti**.

## 2. Numeri per piega

| Piega | `copia1` | `copia2` | `rete` | `rete_anti` | Magnitudine mediana `rete_anti` | |y| mediano |
|---|---|---|---|---|---|---|
| H1 | 0,999 | 1,098 | 1,495 | **1,121** | 0,227 | 0,262 |
| KOLF | 1,001 | 1,021 | 0,826 | 0,993 | 0,110 | 0,509 |
| RPE1 | 0,971 | 0,984 | 0,967 | 0,944 | 0,101 | 0,536 |
| HepG2 | 0,962 | 0,994 | 0,876 | 0,916 | 0,152 | 0,591 |
| Jurkat | 0,930 | 0,978 | 0,814 | 0,883 | 0,159 | 0,427 |
| HipSci | 0,988 | 1,069 | 0,713 | 0,945 | 0,183 | 0,536 |
| Tian | 1,012 | 1,034 | 0,936 | 1,015 | 0,229 | 0,679 |

## 3. Lettura

- **Misurato:** sulle linee di schermi su geni essenziali la stima L1 abbassa l'nMAE (fino a 0,71 in HipSci). In H1,
  l'unica piega con bersagli simili al pannello e verità pulite, peggiora in entrambe le versioni.
- **Misurato:** in H1 il segno del transfer K562 è giusto nel 59% dei geni DE. La `rete_anti` vi mette magnitudini
  vicine a |y| (0,227 contro 0,262): con `q = 0,59` l'ottimo L1 è un quantile basso di |y|, molto più piccolo.
- **Interpretazione:** la magnitudine ottima dipende dalla soglia di rilevamento della verità, cioè da quante cellule
  e quanta profondità ha la linea di arrivo. La rete non vede la soglia e la impara dalle linee rumorose, dove i geni
  DE hanno |y| doppio. Per A, B, C il numero di cellule vere per bersaglio non è nei dati che abbiamo. Senza saperlo,
  la magnitudine resta un'ipotesi.
- **Interpretazione:** è la stessa diagnosi del 4/10. Il regime del pannello (bersagli tipici, verità pulite) è
  diverso da quello dei dati di training, e un banco che non lo contiene sovrastima. Qui il banco lo conteneva (H1), e
  ha fermato l'invio.

## 4. Che cosa servirebbe per riprendere

- Il numero di cellule vere per bersaglio in A, B, C, o almeno la distribuzione di |log2FC| dei geni DE nella
  verità. Si può forse ricavare dalle ancore e dalle baseline ufficiali del cell_eval2 (da verificare), oppure da
  Davide.
- Un ingresso della rete che porti la soglia di rilevamento, addestrato anche su H1 e su CD4 (Flex, pannello).
- Il controllo dello spostamento dei conteggi (`verifica_slide.py`) prima di qualsiasi generazione.
