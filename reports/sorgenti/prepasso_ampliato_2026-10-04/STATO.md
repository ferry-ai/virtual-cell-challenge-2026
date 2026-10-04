# Stato del corpus ampliato, 4/10 notte (aggiornato dalla sessione 2b35612c)

Questa pagina registra lo stato, non le regole: le regole sono in [DECISIONE.md](DECISIONE.md).

## Misurato

- **Gemelli compatti delle sorgenti nuove, completi e verificati** (manifest scaricati nella radice dati,
  `processed/rete_ancorata_v4_2026-10-03/out_fast*`). Nei manifest, `worker_peak_rss_mb` è il picco di memoria
  residente per processo:

  | Sorgente | Shard | Kernel | Picco per processo |
  |---|---:|---|---:|
  | HEK293T | 223 (112 + 111) | `rcell-v4-fast-hek293t-a-r2`, `-b-r1` | 11.308,7 MB |
  | HCT116 | 109 (55 + 54) | `rcell-v4-fast-hct116-a-r2`, `-b-r1` | 10.948,5 MB |
  | KOLF2.1J pan-genome | 133 | `rcell-v4-fast-kolf-pan-r1` | 3.854,3 MB |

  I gemelli di CD4 D1 (435 shard) non sono ancora costruiti. **Aggiornamento del 4/10, 11:15:** costruiti e verificati
  tutti e tre, con decodifica confrontata esattamente con gli shard. I manifest sono in
  `processed/rete_ancorata_v4_2026-10-03/out_fast-cd4-d1-*-r1/twins/fast_manifest.json`.

  | Unità | Gemelli / shard verificati | Falliti | GB dei gemelli / delle sorgenti | Kernel |
  |---|---:|---:|---|---|
  | CD4 D1_Rest | 154 / 154 | 0 | 5,68 / 15,08 | `rcell-v4-fast-cd4-d1-rest-r1` |
  | CD4 D1_Stim8hr | 140 / 140 | 0 | 6,16 / 15,69 | `rcell-v4-fast-cd4-d1-stim8hr-r1` |
  | CD4 D1_Stim48hr | 141 / 141 | 0 | 6,67 / 16,94 | `rcell-v4-fast-cd4-d1-stim48hr-r1` |
- **Replica dei gemelli del pilot su `davidmaisterx`**: i 365 gemelli (134 + 91 + 140) sono identici byte per byte a
  quelli di `rcell-v4-fast-{a,b,c}-r1` (sha256 dei manifest confrontati il 4/10).

- **Montaggi in un kernel, misurati il 4/10 alle 11:20** ([sonda](sonda_montaggi.py), `vcc-probe-mounts-r1`, esito in
  `esito_sonda_montaggi_r1/mounts.json`):
  - un kernel CPU di `davideferrante11` accetta 18 uscite di kernel e 4 dataset, per 137,7 GB in tutto;
  - tutti i 22 montaggi sono visibili e listati entro 5 secondi dall'avvio, perché il montaggio è pigro;
  - le sorgenti sono gli 11 kernel di gemelli esistenti, 4 parti CD4 D2, pre-passo, ancore, training D-056 HepG2, cubo e
    codice.
  Il training sul corpus ampliato può quindi montare i gemelli di tutte le sorgenti in un solo kernel, almeno fino a
  22 sorgenti. Il limite superiore non è stato cercato.

## In corsa

- `vcc-sampled-hct116-l64-r1` (davideferrante11, 04:19): primo kernel degli shard campionati, livello 64, 2 processi
  ([lanci](lancio_sampled_r1.jsonl)).

## Vincolo operativo e piano

Gli shard delle sorgenti nuove sono output privati dei kernel di `davideferrante11`. Un kernel di un altro account non
li può montare, quindi shard campionati, pre-passo e gemelli del corpus ampliato si costruiscono su `davideferrante11`
(CPU, senza quota). Su quell'account, dopo il training D-056 di RPE1, la quota GPU resta di circa 2 ore fino al rinnovo
del 10/10. Il primo training sul corpus ampliato si fa lì: con quelle 2 ore, oppure dopo il rinnovo, che arriva prima
dei dati D/E/F del 22/10. In alternativa, gli shard campionati (stima: circa 40 GB) si copiano su un altro account
passando dal portatile, se il tempo di trasferimento misurato lo consente. Prossimi kernel, a sessione CPU libera:
HEK293T, KOLF pan, CD4 D1 (tre unità), poi le quattro famiglie del pilot e le CD4 D2–D4 quando verificate.
