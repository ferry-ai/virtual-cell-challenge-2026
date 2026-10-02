# Strada B: tre varianti a un fattore della ricetta t22, registrate prima di ogni misura

2 ottobre 2026, 23:35 CEST, Claude Code per Alfredo (sessione `42343bb9`), che ha dato il via in chat. Nessun numero
di questi bracci esiste ancora. Le soglie e la regola non si spostano dopo i risultati (CP-0030).

## Da dove viene

- **La proposta:** la [revisione del 2 ottobre](../../analisi/letteratura_strade_2026-10-02/README.md) e la sua
  [correzione](../../analisi/letteratura_strade_2026-10-02/CORREZIONE_STRADA_A.md): la MSE si sblocca solo se migliora
  la direzione del profilo, quindi la priorità va al trasferimento.
- **Che cosa è già stato provato, e non si ripete:**

  | Variante | Esito | Fonte |
  |---|---|---|
  | riponderazione delle sorgenti, Bayes empirico | negativo | [atlante](../atlante_2026-09-26/RISULTATI.md), [gerarchico](../trasferimento_gerarchico_2026-09-26/RISULTATI.md) |
  | accordo per bersaglio come fattore in [0, 1] | negativo: triplica l'energia, peggiora l'nMAE | [atlante](../atlante_2026-09-26/RISULTATI.md) |
  | risposta comune | negativo: non si trasferisce | [risposta comune](../risposta_comune_2026-09-26/RISULTATI.md) |
  | quota condivisa per gene | conta l'esclusione dei geni con una sola sorgente | [ablazione t23](../ablazione_t23_2026-09-27/RISULTATI.md) |
  | testa cis entro 5 kb | piccola, positiva sul proxy, invisibile su HepG2 | [modulo cis](../modulo_cis_2026-09-26/RISULTATI.md) |

- **Le tre varianti nuove** vengono da forme dichiarate in classifica e da una delle due entrate pubbliche. Ognuna
  differisce da ciò che è già stato provato per un punto preciso, scritto sotto.

## I bracci

Riferimento `ref`: la forma del t22 (ristretti, γ = 1, quattro sorgenti a peso uguale, ampiezza 1,576, cis entro
5 kb × 2). Ogni braccio cambia **un** fattore. Il codice è in [`arms.py`](arms.py), provato su dati sintetici in
[`test_arms.py`](test_arms.py).

| Braccio | Che cosa cambia | Differenza da ciò che è già stato provato |
|---|---|---|
| `alloc` | ampiezza per bersaglio f = clip((A/med A)¹ × (m/med m)^−0,875; 1/3; 3), con A il coseno medio fra coppie di sorgenti e m la norma del trasferito | **energia totale del contesto conservata**, fattore anche sopra 1, taglio a [1/3, 3]: il braccio `agree_target` dell'atlante poteva solo togliere e triplicava l'energia dopo la riscalatura |
| `normrest` | ampiezza per bersaglio r = mediana delle norme delle singole sorgenti / norma della media, tagliata a [1/3, 3], energia conservata | ipotesi opposta ad `alloc`: la media rimpicciolisce di più i bersagli dove le sorgenti discordano (entrata pubblica: fedeltà da 0,31 a 0,44 su HepG2) |
| `cis50` | la testa cis estesa da 5 a 50 kb: fasce 0–1–2–5–10–20–30–50 kb dalle coppie K562 senza i bersagli del pannello; × 2 entro 5 kb come ora, × 1 da 5 a 50 kb | finestra oltre 5 kb mai provata; mediane K562 da −0,13 log2 (5–10 kb) a −0,03 (30–50 kb) |
| `cis50_perm` | i valori di `cis50` oltre 5 kb messi sui vicini di un altro bersaglio (derangement fisso, seme 1) | controllo di volume per `cis50` |

**Dettagli fissati ora:**
- **Geni su cui si leggono A, m e le norme:** quelli espressi almeno a 5 CPM nei controlli del contesto da prevedere.
- **Bersagli senza A leggibile** (meno di due sorgenti con almeno 20 geni in comune): A pari alla mediana.
- **Costanti:** `arms.py`, righe `ALPHA`, `BETA`, `LOW`, `HIGH`, `EPS`, `CIS_*`.

## Dove si misura

1. **Banco HepG2 con lo scorer vero** (stadio 75): verità su metà delle cellule di Nadig 2024, replica sull'altra
   metà, i sei membri. Bersagli: quelli HepG2 coperti da almeno due delle quattro sorgenti della ricetta.
2. **Replica su Jurkat** (Nadig 2024), stesso disegno, se il file è disponibile.
3. **Descrittivo:** per ogni braccio, l'energia E e il coseno aggregato fra profilo previsto e vero nello spazio della
   MSE ([legge 1 + E/4786](../risposta_comune_2026-09-26/RISULTATI.md)). Dice se la direzione migliora anche quando
   la MSE scalata resta 0.

**Statistica:** differenza appaiata braccio − `ref` della media dei sei membri scalati (MSE compresa, tosata come
nello scorer), bootstrap sui bersagli con 10.000 ricampionamenti e seme 0, intervallo al 95%.

## Regola

- **Passa** un braccio con il limite basso dell'intervallo sopra 0 su HepG2 **e** la differenza media ≥ 0 su
  Jurkat. Se Jurkat non c'è, la sola HepG2 dà al massimo «candidato da confermare».
- **`cis50`** passa solo se, in più, batte `cis50_perm` con la stessa regola.
- **Se più bracci passano,** il candidato è quello con la differenza media più alta su HepG2. Una combinazione si
  registra a parte, dopo, come ipotesi nuova.
- **Se nessuno passa,** la ricetta del t22 resta il riferimento, e questi bracci non si rigirano con altre costanti.
- **Un braccio che passa** diventa una ricetta solo con una previsione registrata prima della generazione. Va in gara
  solo con l'ok esplicito di Alfredo. Nessun esito dice qualcosa di garantito su D, E, F.

## Che cosa serve per girarlo (oggi non è su questo PC)

- **Il disco esterno D:** con `NadigOConner2024_hepg2.h5ad` (sha256 `1af2f7b3…`) e, se c'è, il file Jurkat.
- **Le cache dello stadio 98** delle quattro sorgenti con i bersagli fuori pannello (universi K562, CD4, HCT116,
  HEK293T), oggi sul PC di Davide.
- **In alternativa:** gli effetti per bersaglio di ogni sorgente esportati sui bersagli HepG2, file più piccoli.
- **Le coordinate dei geni** (stadio 74).
