# Quanto del corpus entra in un training: misure, stime e proposta

3 ottobre 2026, fra le 16:51 e le 17:20 CEST (ore lette con `date`), Claude Code, sessione `c7c07a` (claude2, regia
dell'ingestione dopo il [passaggio di consegne](HANDOFF_CLAUDE2.md)). Risponde alla domanda del proprietario in chat:
«questi dati da un tera confluiranno nel training di Kaggle o sono limitati dalla piattaforma?». Ogni riga dice se è
**misurata**, **stimata** o **proposta**. Nessun training è stato lanciato per scrivere questa nota.

## Risposta

Il terabyte non entra per intero in un training, e il limite che conta non è lo spazio di Kaggle ma il tempo di GPU.

- Il terabyte è il peso dei file **sorgente** (circa 2.150 GB, di cui 1.736 di CD4), che non si conservano: si
  leggono e si convertono. Il corpus convertito è stimato intorno ai 300 GB.
- Lo spazio si può distribuire: 200 GB di dataset privati per account su tre account, più gli output dei kernel
  (20 GB l'uno), che un training monta direttamente. Che un solo kernel monti tutto insieme **non è stato provato**.
- Il tempo di GPU no: un training legge circa 1.300 cellule al secondo, la quota è di 30 ore a settimana per account e
  ogni esperimento sono tre training (una linea esclusa per volta).

## Misure

| Che cosa | Valore | Dove si legge |
|---|---|---|
| Velocità dei training r3 (tre bracci insieme, Kaggle T4×2, 4 CPU) | 1.284–1.887 cellule/s nella finestra di misura; 1.247–1.323 cellule/s sull'intera corsa, valutazione compresa | `plan.json` e `done.json` in `reports/modelli/rete_cellulare_2026-10-03/esito/train_{h1,hepg2,rpe1}_r3/` |
| Durata di un training r3 | 2 epoche su 3,85–3,97 milioni di cellule ammesse in 97–104 minuti | gli stessi `done.json` |
| Dove va il tempo | 17–40% in attesa dei dati; memoria GPU al picco 1,4 GB su 15 | gli stessi `plan.json` (`data_wait_fraction`, `gpu_peak_mb`) |
| Peso della loss per gruppo di linee | 1/G per gruppo, criterio di accettazione passato da r3 | `reports/modelli/rete_cellulare_2026-10-03/PROTOCOLLO.md` §6, §7, §11 |
| Quota GPU di Kaggle | 30 ore a settimana per account; su `davideferrante11` 14,08 usate e 15,92 rimaste alle 16:54, rinnovo il 10/10 | `kaggle quota` (letto in sessione, non salvato) |
| Sessioni Kaggle insieme | 5 CPU («Maximum batch CPU session count of 5 reached», 17:12) e 2 GPU | [lancio_orion_r2.jsonl](kaggle_cpu/lancio_orion_r2.jsonl); `reports/modelli/rete_cellulare_2026-10-03/incidente_E-20261003-001/osservazioni.json` |
| Macchina di un kernel CPU | 4 CPU, 31 GB di RAM, 20 GB di output | [nettest.json](kaggle_cpu/esito_nettest_r1/nettest.json) |
| Shard Orion HCT116 | 25 shard su Drive alle 16:59: 350 MB in media; 2,2–2,3 byte per valore non nullo sui primi tre del kernel Kaggle | elenco di `data/processed/ingestione_completa_2026-10-03/j16_orion_full_shards_hct116_p{0,1}of2_r1/` su Drive; log del kernel `vcc-orion-hct116-p0of4-r2` |
| CD4, `D1_Rest` | 3.074.496 cellule, 11,85 miliardi di valori (3.856 per cellula), 142,8 GB: 12 byte per valore, non compresso | `reports/sorgenti/corpus_cellulare_2026-09-30/p1_r4/remote/cd4_D1_Rest.json` |
| CD4, idonee in `D1_Rest` | 1.754.014 su 3.074.496 a guida singola (57%) | [INGESTIONE §3](../archivio_cloud_2026-10-02/INGESTIONE.md) |
| Cellule per bersaglio in Orion | mediana 150 (HCT116) e 200 (HEK293T) | `sample/<linea>.json` dei job 135 e 136 su Drive |

## Stime

Sono proiezioni delle misure sopra, da sostituire con i `complete.json` quando arrivano.

| Corpus convertito | Cellule | GB | Come è stimato |
|---|---|---|---|
| Orion, due linee | 7,94 milioni | circa 90 | 350 MB × 109 shard per HCT116; stessa densità per cellula su HEK293T |
| CD4, tutte le idonee | circa 19 milioni | 160–185 | 57% di 33,6 milioni; 3.856 valori per cellula a 2,2–2,5 byte |
| CD4, campione con k = 10 per (file, guida) e tutti i controlli | circa 3,7 milioni | circa 30 | [INGESTIONE §3](../archivio_cloud_2026-10-02/INGESTIONE.md), con la densità misurata qui |
| KOLF pan-genome | 2,66 milioni | 17–20 | 7,87 miliardi di valori a 2,2–2,5 byte |

| Corpus del training | Cellule | Un passaggio, per training | Un esperimento (3 linee escluse, 1 passaggio) |
|---|---|---|---|
| Oggi (r3) | 3,85 milioni | circa 50 minuti (misurato) | circa 2,5 ore |
| Tutto tranne CD4 intero | circa 17 milioni | 2,5–3,7 ore | 8–11 ore |
| Tutto, con CD4 intero | circa 36 milioni | 5–8 ore | 16–23 ore |

La velocità è quella di r3: un'altra rete, un altro batch o un altro caricamento dei dati la cambiano.

## Proposta (decide il proprietario, con R-LEAD per il training)

1. **Ridurre le cellule, mai i contesti.** Il corpus di prova tiene ogni gruppo di linee, ogni bersaglio e tutti i
   controlli, con un tetto di *k* cellule per (contesto, bersaglio). I gruppi passano da 9 a circa 21
   ([line_groups_expanded_v1.json](orion/line_groups_expanded_v1.json), proposta non ancora adottata da R-LEAD): è
   quel numero a decidere la generalizzazione. Con *k* intorno a 40 la stima è di 6–8 milioni di cellule.
2. **Misurare se serve di più:** lo stesso modello a *k* = 10, 20, 40, con la regola scritta prima. Se il banco non
   sale, il training su tutto non aggiunge niente.
3. **Orion e le sorgenti piccole e medie per intero** (Southard, DLD-1, Mixscale, VIPerturb, microglia, KOLF): portano
   linee nuove e costano solo CPU. Il tetto si applica nel pre-passo.
4. **CD4 a tranche**, non per intero: prima tranche con *k* = 10 e tutti i controlli. Il campione prende le prime *k*
   cellule per (file, guida) in un ordine fissato dall'hash (`../archivio_cloud_2026-10-02/campionamento.py`,
   `select_cd4`): un *k* più alto contiene il precedente, quindi una tranche successiva è un'aggiunta. Il parametro
   `window` che la seleziona esiste per Orion (`orion/campionamento_v2.py`) e va portato a CD4.
   **Aspetta il sì del proprietario:** il mandato del 3/10 chiedeva di non impoverire CD4 per risparmiare spazio
   ([revisione di Codex](../revisione_ingestion_2026-10-03/README.md)). La proposta lo cambia per il tempo di GPU,
   non per lo spazio, e solo per CD4.
5. **Training finale su tutto** solo se il punto 2 lo giustifica: 2 passaggi su 36 milioni di cellule sono 10–16 ore,
   cioè due sessioni Kaggle con ripresa.

**Esito, 3/10 alle 17:46.** Il proprietario ha inoltrato una [strategia](STRATEGIA_DATI_TRAINING.md) che mantiene
l'acquisizione completa, CD4 compreso: il punto 4 non è adottato. I punti 1, 2 e 5 vi compaiono come campioni
annidati da 32, 64 e 128 cellule per combinazione, da dimensionare sull'inventario reale.

**Correzione di una stima, 3/10 alle 17:24.** Gli shard HEK293T sono più densi di quelli HCT116: 15 KB per cellula
sui primi due letti dal log di `vcc-orion-hek293t-p0of8-r2` (18.003 cellule in 274,7 MB; 23.768 in 356,6 MB), contro
11 KB. Orion intero va quindi verso i 105 GB, non 90. Il numero esatto verrà dai manifest delle parti.

## Altri cloud, prezzi letti il 3/10

Nessun acquisto è autorizzato da questa nota. La velocità su queste macchine **non è misurata**: prima di spendere
serve una prova breve che misuri le cellule al secondo.

| Opzione | Prezzo | Che cosa cambia |
|---|---|---|
| Kaggle | gratis | 30 ore GPU a settimana per account, sessioni da 12 ore, 4 CPU |
| Colab Pro+ | circa 50 $ al mese per 600 unità; L4 circa 1,7 unità l'ora (fonti terze, da ricontrollare) | legge Drive, dove sta il corpus; usa il dispatcher esistente |
| RunPod, RTX 3090 (16 CPU, 125 GB di RAM) | 0,22 $ l'ora (community), 0,50 $ (secure); disco di rete 0,07 $ per GB al mese (listino di runpod.io) | ingestione e training sulla stessa macchina |
