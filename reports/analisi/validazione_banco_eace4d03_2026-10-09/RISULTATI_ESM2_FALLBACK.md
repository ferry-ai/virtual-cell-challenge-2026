# ESM2: verifica indipendente dei cinque punti dell'audit del Lead, e che cosa fa davvero il fallback

9 ottobre 2026, VALIDAZIONE (Claude Code `eace4d03`). Regole scritte prima dei numeri nel
[contratto v3](PROTOCOLLO_v3.md), §1–2 (commit `5cf3b157`, 20:50) e nell'[aggiunta](ADDENDUM_v3_1.md) (commit
`e5644665`, 20:56, dopo C-K562 e prima di C-iPSC). Checkpoint: [CP-0075](../../../docs/checkpoints/0075-fallback-esm2-supporto-e-vista-del-generatore.md).
Nessun training. Misure nello spazio degli effetti su due lignaggi di sviluppo: **non sono punteggi VCC** e non
decidono una promozione, che resta al §8 del contratto v1 (sei membri su almeno due fold).

## 1. I cinque punti, uno per uno

| Punto dell'audit | Esito della verifica | Tipo | Dove |
|---|---|---|---|
| ESM2 da solo perde contro il transfer su K562 | Confermato: `disc95` −0,239 [−0,284; −0,193] su C-K562. Su C-iPSC −0,042 [−0,092; +0,009], non risolto | letto dal `results.json` della corsa di chiusura; la parità di quella corsa è ricalcolata qui su due bracci (T0 e fallback), non sul braccio nativo | `results.json` della chiusura, sha256 `5ef9d48c…c8d4` |
| Fallback: delta medio di `disc95` +0,000244 [−0,000278; +0,000796] | Riprodotto per fold: C-K562 +0,000312 [−0,000244; +0,000936], C-iPSC +0,000177 [−0,000719; +0,001098]; livelli identici al pubblicato (differenza 0) su portatile e su Kaggle | misurato, ricalcolato su due macchine | [C-K562](esm2/cloud_r1/completion/supporto_C-K562.json), [C-iPSC](esm2/cloud_r1/completion/supporto_C-iPSC.json), chiave `own_support_as_published` |
| Il confronto a sei componenti non è stato eseguito | Confermato: nessuna ricevuta di lancio di un banco a sei membri per il fallback, né nella cartella di MODELLI-ESTERNI né qui (lettura delle 20:59) | misurato sui file | [messaggi](MESSAGGI.md) |
| Il §8 classifica il livello B mancante come inconcludente e non chiede un guadagno risolto di `disc95` | Confermato sul testo: «INCONCLUDENTE: ogni altro caso, compreso il livello B mancante»; il segnale d'arresto riguarda solo un `disc95` risolto **negativo** | lettura del protocollo | [v1 §8–9](../validazione_indipendente_8a8ca58a_2026-10-08/PROTOCOLLO_v1.md), [v2 §1](../validazione_indipendente_8a8ca58a_2026-10-08/PROTOCOLLO_v2.md) |
| Non è documentato quante coppie riempite entrino nella misura | Ora misurato: 345 su 38.076 giudicabili (C-K562), 6.647 su 189.003 (C-iPSC) | misurato | §2 |

## 2. Quante coppie riempite vede la misura primaria

| | C-K562 | C-iPSC |
|---|---:|---:|
| Coppie riempite sul pannello (come nella ricevuta di MODELLI-ESTERNI) | 428.137 | 484.195 |
| Nei bersagli confrontati (272 e 282) | 382.775 | 452.268 |
| Non giudicabili: la verità del fold non misura quel gene | 344.695 | 263.196 |
| Non giudicabili: colonna di un gene bersaglio | 4 | 69 |
| **Giudicabili** | **38.076** | **189.003** |
| Di cui dentro il rango di `disc95` (7.260 e 11.598 geni) | 345 | 6.647 |
| Quota delle giudicabili che entra nel rango | 0,9 % | 3,5 % |
| Quota delle entrate del rango che sono coppie riempite | 0,017 % | 0,20 % |
| Coppie riempite nel rango per bersaglio: mediana, massimo | 0, 150 | 0, 4.278 |

**Che cosa vuol dire.** Il rango usa i geni che i bracci del manifest prevedono per almeno il 95 % dei bersagli: per
costruzione quasi nessuna coppia che T0 lascia vuota ci sta dentro. Il delta di `disc95` del fallback è vicino a zero
perché la misura non guarda dove il fallback scrive. **Non è evidenza né a favore né contro.** Un gene che la verità
non misura non è uno zero biologico: su quelle coppie (il 90 % su K562, il 58 % su iPSC) non c'è giudizio possibile.

## 3. Dove il banco lo vede: quattro bracci con maschera e scala identiche

Vista del generatore: supporto definito dalla sola verità, una coppia non prevista vale zero, come la emette il
generatore. `zero` è T0 così; gli altri tre riempiono le stesse coppie, alla stessa ampiezza, con il ridge del
bersaglio (`esm2`), con la sua parte generica, con il ridge di un altro bersaglio (`scambiato`). Intervalli:
bootstrap appaiato sui bersagli, 10.000 ricampionamenti. «n.r.» = non risolto.

| Contrasto, misura | C-K562 | C-iPSC |
|---|---|---|
| `esm2` − `zero`, `mse_ratio` (meno è meglio) | **+0,0050** [+0,0044; +0,0057] | **+0,0149** [+0,0139; +0,0160] |
| `esm2` − `zero`, `nmae_conf` (meno è meglio) | +0,0008 n.r. | **−0,0015** [−0,0024; −0,0007] |
| `esm2` − `zero`, `sign50` | **+0,0226** [+0,0182; +0,0272] | **+0,0058** [+0,0013; +0,0103] |
| `esm2` − `zero`, `reach` | −0,0004 n.r. | **+0,0011** [+0,0001; +0,0023] |
| `esm2` − `zero`, `disc95g` | +0,0002 n.r. | non leggibile: controllo +0,045 [−0,003; +0,092] |
| `scambiato` − `zero`, `mse_ratio` / `nmae_conf` / `sign50` | +0,0053 / +0,0013 n.r. / +0,0200 | +0,0155 / −0,0014 / +0,0055 |
| `esm2` − `scambiato`, tutte le misure | solo `sign50` +0,0026 [+0,00002; +0,0052] | nessuna risolta |
| `esm2` − `generico`, `mse_ratio` | **+0,0021** [+0,0016; +0,0026] | **+0,0115** [+0,0106; +0,0124] |

Sulle sole coppie riempite giudicabili (261 e 281 bersagli con almeno 20 coppie):

| | C-K562 | C-iPSC |
|---|---|---|
| Errore quadratico rispetto allo zero: `esm2`, `scambiato`, `generico` | 1,24, 1,25, 1,14 | 1,11, 1,11, 1,02 |
| Coseno con la verità, `esm2` | +0,010 [−0,004; +0,024] n.r. | **+0,0077** [+0,0025; +0,0131] |
| Coseno, `generico` e `scambiato` | +0,014 n.r., +0,005 n.r. | **+0,0073**, +0,0026 n.r. |
| Coseno, `esm2` − `scambiato` | +0,0045 n.r. | +0,0051 [−0,0012; +0,0116] n.r. |
| Moltiplicatore che adatterebbe il riempimento alla verità | 0,05 | 0,02 |
| Geni confidenti della verità coperti: T0 → fallback | 91,1 % → 96,5 % | 92,3 % → 98,7 % |
| Accordo di segno fra i previsti: `esm2` − `zero` | +0,0013 n.r. | +0,0019 [+0,0004; +0,0033], uguale a bersagli scambiati |

Le letture a posteriori su C-K562 sono il coseno, il moltiplicatore e il segno separato dalla copertura; su C-iPSC
erano registrate prima.

## 4. Che cosa si può dire

**Con le parole fissate prima:**
- non si scrive che il fallback riduce l'errore: l'errore quadratico peggiora, risolto, su entrambi i fold;
- non si scrive che il guadagno è specifico del bersaglio: nessun contrasto con il braccio scambiato è risolto,
  salvo un `sign50` di +0,003 su C-K562 al limite dell'intervallo;
- non si scrive che basta la parte generica: anche quella peggiora l'errore quadratico;
- su C-iPSC si scrive che il riempimento **ha una direzione giusta** (coseno risolto sopra zero), **non** che è
  specifica del bersaglio.

**Interpretazione.** Il fallback aggiunge copertura e una risposta comune debole. I miglioramenti di segno e
d'errore assoluto compaiono uguali quando le coppie si riempiono con la previsione di un altro bersaglio: vengono
dall'avere una previsione al posto di uno zero. L'errore quadratico peggiora perché l'ampiezza 1,576, nata sul
punteggio ufficiale del transfer, applicata al ridge è da venti a quarantacinque volte quella che la verità
sosterrebbe.

**Un falso successo evitato.** Sul supporto proprio di ciascun braccio, come nel banco congelato, su C-iPSC il
fallback dava `mse_ratio` −0,0071 e `nmae_conf` −0,0021, risolti a favore. Erano confronti fra supporti diversi:
T0 non pagava le coppie che lasciava a zero. Sullo stesso supporto il primo cambia segno.

**Decisione di priorità e conclusione scientifica restano due cose.**
- «Non adottarlo adesso»: sostenuta. Nessuna misura indica un beneficio specifico, e il ridge nativo perde contro
  il transfer.
- «Non può aiutare»: **non dimostrato**. I sei membri non sono stati misurati: più geni chiamati con una direzione
  comune debolmente giusta possono spostare fedeltà e reach in un senso o nell'altro, e il banco nello spazio degli
  effetti non lo dice. L'esito del §8 resta **inconcludente**.

## 5. Che cosa manca, e chi lo esegue

1. **Livello B a sei membri sui due fold con quattro bracci** (`zero`, `esm2`, `generico`, `scambiato`), stesso
   flusso casuale, cinque semi. Se `esm2` − `zero` è risolto ma `scambiato` − `zero` lo è uguale, il beneficio è
   della copertura e si ottiene senza il ridge. Esecutore da concordare (vedi [messaggi](MESSAGGI.md)); serve il
   consenso del proprietario a portare i file dei bracci su `davidmaisterx`, dove stanno le cellule vere.
2. **Un riempimento con l'ampiezza scelta su fold interni**, non quella del transfer: è un candidato diverso, con
   una regola sua, e riguarda MODELLI-ESTERNI.
3. **AMMI:** gli stessi conteggi di copertura e la stessa vista del generatore si applicano ai suoi export. Vanno
   letti `cells` − A0 (l'ancora annidata del fit) e `cells` − `none`, tenendo A0 distinto dal T0 originale, e il
   braccio a contesto scambiato; guardie tecniche superate non sono beneficio.
