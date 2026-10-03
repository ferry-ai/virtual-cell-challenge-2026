# Rete sulle sorgenti r2: confronto locale delle varianti, scritto prima di lanciarlo

3 ottobre 2026, ore 20 circa. Lo scrive Claude Code per Alfredo, che in chat ha lasciato a Claude la scelta del
metodo («scegli tu»). È un confronto **esplorativo**: serve a scegliere quali varianti portare al banco con lo scorer
vero. Non decide nessun invio.

## Perché

Il t30 ha preso +0,027878, ramo c ([CP-0056](../../../docs/checkpoints/0056-t30-punteggio-ufficiale.md)). Dal
`monitor.jsonl` della r1:
- il fattore d'ampiezza appreso scende da 1,56 a circa 0,36 entro il passo 500, ed è lì il checkpoint migliore;
- il coseno di validazione della rete è 0,058, quello della media a pesi uguali 0,055.

La rete ha imparato quasi solo a ridurre gli effetti.

## Varianti

Stesso seme (0), stessi 3.000 passi, stessa configurazione della r1; cambia solo quanto è indicato. Il codice è
[`rete.py`](rete.py) di questa cartella: con i valori predefiniti calcola quello che calcolava la r1.

| Nome | `--amp` | `--loss` | `--loss-genes` |
|---|---|---|---|
| `r1` | learned | mse_cos | all |
| `fix` | fixed | mse_cos | all |
| `cos` | learned | cos | all |
| `fixcos_top` | fixed | cos | top (10%) |
| `fix_top` | fixed | mse_cos | top (10%) |

## Dati e divisione (locale)

- **Chiavi:** le 25 chiavi di addestramento scaricate dal kernel `rete-sorgenti-r1-train`, verificate con sha256 (in
  `vcc2026-data/kaggle/rete_sorgenti_r1_train_output/consegna/chiavi`).
- **Validazione:** `rpe1`, che non è mai bersaglio né sorgente in addestramento.
- **Test nominale:** `tian_neuron`, non letto qui.
- **Addestramento:** `k562` (le due chiavi), `hipsci`, `tian_ipsc`.

Le linee di validazione della r1 (KOLF, Jurkat) non sono in locale: arrivano con le chiavi complete del kernel lungo.

## Che cosa si legge

Le metriche fisse di `evaluate`, che non dipendono dalla configurazione, all'ultima valutazione e al checkpoint
migliore:
- `net_cos_all` contro `uni_cos_all`: il coseno su tutti i geni, quindi la direzione;
- `net_size`: |ŷ| / |verità| sui geni osservati, dove 1 vuol dire dimensione naturale;
- la perdita r1 di rete e media.

**Criterio per portare una variante al banco:**
1. `net_cos_all − uni_cos_all ≥ +0,01` su RPE1;
2. `net_size` ad almeno metà di quello della media a pesi uguali.

Se nessuna variante supera il primo punto, i pesi appresi non aiutano oltre la media. Allora il candidato per il banco
è `net0`, cioè la media a pesi uguali con l'ampiezza della ricetta, e la rete resta ferma.

**Limiti:**
- RPE1 è una sola linea, e il coseno è una misura vicina allo scorer ma non è lo scorer;
- un seme;
- nessun intervallo: è una scelta di cosa provare, non una misura da citare come risultato.
