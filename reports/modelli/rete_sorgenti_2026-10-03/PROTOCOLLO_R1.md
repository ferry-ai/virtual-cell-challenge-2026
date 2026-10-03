# Rete sulle sorgenti r1, con la corsa r2 della strada C: protocollo registrato prima di ogni numero

3 ottobre 2026, Claude Code per Alfredo, che ha chiesto in chat di iniziare a addestrare reti e di dare un voto oggi.
L'ora di registrazione è quella del commit che contiene questo file. Le soglie e la regola non si spostano dopo i
risultati (CP-0030).

## Un solo kernel Kaggle, quattro passi

1. **Dati della rete:** [`dati.py`](dati.py) scrive un file per chiave del corpus rlab, con effetti, profilo basale e
   geni misurati. Lo stimatore è quello del banco della strada C, con i gruppi corretti.
2. **Strada C r2:**
   - è [`banco_tipo.py`](../../trasferimento/strada_c_banco_2026-10-03/banco_tipo.py) su H1, KOLF, HepG2 e Jurkat;
   - stessi bracci, costanti, semi e regola del [protocollo](../../trasferimento/strada_c_banco_2026-10-03/PROTOCOLLO.md);
   - cambia **solo** la correzione dei gruppi Tian dell'[esito r1](../../trasferimento/strada_c_banco_2026-10-03/ESITO.md)
     (§2.1).
3. **Addestramento:** [`rete.py`](rete.py), seme 0, configurazione di default di `Config`:
   - 3.000 passi, 64 bersagli × 2.048 geni per episodio;
   - perdita MSE + (1 − coseno), lr 3·10⁻³;
   - arresto dopo cinque valutazioni di fila peggiori della media a pesi uguali, non prima del passo 300.

   **Divisione delle linee:**

   | Ruolo | Gruppi | Uso |
   |---|---|---|
   | addestramento | `k562`, `rpe1`, `hipsci`, `tian_ipsc`, `tian_neuron` | bersagli e sorgenti degli episodi |
   | validazione | `kolf`, `jurkat` | solo per arresto e scelta del checkpoint (`ckpt_best`); mai bersaglio né sorgente in addestramento |
   | test | `h1`, `hepg2` | solo per il voto qui sotto; mai visti in addestramento |

   **Eccezione registrata nelle esclusioni,** valida solo in addestramento: una linea HipSci legge come sorgenti le
   linee HipSci di **altri donatori**, mai i cloni dello stesso donatore. Le altre esclusioni sono quelle della strada
   C. Il test H1 2025 della gara resta chiuso: si usano le sue chiavi train e validation.
4. **Voto:**
   - esportazione degli effetti per le chiavi di test (`h1_vcc2025_train|H1`, `hepg2_nadig|HepG2`) da `ckpt_best`
     (`net`) e dal passo 0 (`net0`, cioè la media a pesi uguali per gruppo);
   - poi il banco con lo scorer vero su H1 e HepG2, con `--exclude-groups kolf jurkat`: i bracci di confronto usano le
     stesse sorgenti della rete;
   - pannello limitato ai bersagli che tutti i bracci coprono.

## Regola

- **La rete passa** se `net − all` ha il limite basso dell'intervallo al 95% sopra 0 su H1 **e** la differenza media
  è ≥ 0 su HepG2.
  - È la media dei sei membri in scala locale, con bootstrap appaiato sui bersagli: 10.000 ricampionamenti, seme 0,
    ancore ricampionate, MSE come rapporto di somme.
  - `all` è la media a pesi uguali per gruppo sulle stesse sorgenti: la rete deve battere il punto da cui parte.
- **Descrittivi:**
  - `net − net0`: la differenza fra esportazione appresa e passo 0. `net0` coincide con `all` solo a meno del modo di
    mediare per gene, che è diverso;
  - `net − cross`, `net − k562`, `net − same`;
  - le curve di `monitor.jsonl`: perdita, coseno, entropia dell'attenzione, ampiezza, gradiente.
- **Strada C r2:** la regola originale, invariata.
- **Cancello tecnico:**
  - il banco come in r1: la replica batte la baseline in almeno 4 membri su 6, pannello di almeno 20 bersagli;
  - in più, per la rete:
    - l'addestramento finisce con `done.json`;
    - `monitor.jsonl` ha almeno tre valutazioni;
    - `net0` e `all` differiscono di meno di 0,02 nella media dei sei su H1 (controllo che il passo 0 sia davvero la
      media).

  Se il cancello della rete non passa, la regola della rete non si legge.
- **Se la rete non passa:** è smentito solo che questa rete, con questo addestramento, batta la propria media di
  partenza su H1. Non è smentita ogni rete sulle sorgenti.
- **Nessun invio ufficiale** segue da questa corsa senza una previsione registrata e l'ok di Alfredo.

## Previsioni

| Previsione | Valore atteso | Fiducia |
|---|---|---|
| La rete passa la regola | — | 0,3 |
| `net − all` su H1 | da −0,02 a +0,05 | 0,6 |
| L'arresto anticipato scatta prima del passo 3.000 | — | 0,5 |
| Entropia normalizzata dell'attenzione a fine corsa | fra 0,6 e 0,95 | 0,6 |
| Strada C r2: `same − cross` su H1 | fra −0,05 e +0,05; la regola non passa | 0,7 |
