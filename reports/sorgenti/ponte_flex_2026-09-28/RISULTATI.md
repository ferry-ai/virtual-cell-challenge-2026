# Il ponte Flex–3': gli stessi knockdown K562 letti con due chimiche

28 settembre 2026, notte. Scrive il lead (Claude, sessione del proprietario). Esplorativo, **senza regola**: nessun
numero qui decide qualcosa, e nessuno è un punteggio VCC.

Etichette: **misurato**, **interpretazione**, **ipotesi**.

## La domanda

I contesti di gara sono letti con 10x Flex. Tutte le sorgenti di perturbazione del progetto sono in 3', tranne
VIPerturb-seq (Bradu et al. 2026), uno schermo CRISPRi genome-wide in K562 letto con Flex.
- Quanto degli effetti di un knockdown sopravvive al cambio di chimica?
- Il poco accordo fra Flex e 3' viene dalla chimica o dal rumore di VIPerturb-seq?

## r1: Flex contro 3' e i riferimenti (misurato, `bridge.py`, `r1/summary.json`)

Per bersaglio: coseno degli effetti ristretti sui geni misurati da entrambi, esclusi il gene del bersaglio e la sua
finestra cis di 5 kb. «Forti» = almeno 30 geni con |z| ≥ 3 in entrambi gli universi.

| Coppia | Bersagli condivisi | Coseno mediano | Bersagli forti | Coseno mediano sui forti |
|---|---|---|---|---|
| VIPerturb (Flex) – K562 genome-wide (3') | 3.771 | 0,009 | 1.481 | 0,047 |
| VIPerturb (Flex) – K562 essenziale (3') | 988 | 0,040 | 651 | 0,079 |
| K562 essenziale – K562 genome-wide (stesso laboratorio, 3') | 2.053 | 0,204 | 1.592 | 0,284 |
| HCT116 (3') – K562 genome-wide (3'; un'altra linea, un altro laboratorio) | 8.370 | 0,014 | 2.803 | 0,050 |

**Pendenza per gene** di Flex su 3', sui bersagli forti della prima coppia:
- 7.410 geni;
- mediana 0,075;
- decimo percentile 0,011, novantesimo 0,196.

## r2: quanto VIPerturb-seq concorda con sé stesso (misurato, `split_half.py`, `r2/`)

**Come.**
- Metà dei pool dello schermo (0–3) contro l'altra metà (4–7). Ogni metà è unita in un solo pool (`half_pools.py`) e
  stimata con `kolf_effects.py` esattamente come lo schermo intero.
- Una metà: 3.820 cellule di controllo, 6.063 bersagli con effetti; l'altra: 4.129 e 6.162.
- Un solo insieme fisso di bersagli per tutte le coppie: i 1.481 forti della prima coppia di r1.

| Coppia (stessi bersagli) | Bersagli | Coseno mediano | Quartili |
|---|---|---|---|
| VIPerturb metà A – metà B | 1.232 | **0,110** | 0,079–0,162 |
| VIPerturb metà A – K562 genome-wide (3') | 1.288 | 0,030 | 0,003–0,084 |
| VIPerturb metà B – K562 genome-wide (3') | 1.327 | 0,033 | 0,004–0,087 |
| VIPerturb intero – K562 genome-wide (3') | 1.481 | 0,047 | 0,009–0,119 |
| K562 essenziale – K562 genome-wide (3') | 678 | 0,271 | 0,133–0,417 |

**Confronto appaiato** sui 1.232 bersagli che hanno tutte e tre le coppie:
- le due metà concordano fra loro (mediana 0,110) più di quanto ciascuna concordi con il 3' (0,029 e 0,031);
- succede nel 92,7 % dei bersagli.

**Profondità piena, approssimata.** Con il passo di Spearman-Brown, 2r/(1+r), la concordanza di VIPerturb con sé
stesso è circa 0,20. È un'approssimazione: presuppone due metà parallele, e un coseno non è esattamente una
correlazione.

## Lettura (interpretazione)

- **VIPerturb-seq è rumoroso per bersaglio.** Il suo accordo con sé stesso (0,11 a metà profondità, circa 0,20 a
  profondità piena) è sotto quello di due esperimenti 3' dello stesso laboratorio (0,27–0,28).
- **Il rumore da solo non basta a spiegare il ponte basso.** A parità di profondità, una metà Flex concorda con
  l'altra metà Flex circa 3,5 volte più che con il 3' (0,110 contro 0,030–0,033). Resta quindi una differenza fra lo
  schermo Flex e quello 3' che il rumore di VIPerturb non spiega.
- **Questa differenza non è attribuibile alla sola chimica.** Mescola chimica, laboratorio, protocollo, tempo
  dall'infezione e stato delle cellule, come ogni confronto fra studi.
- **Correzione di una lettura data in chat la sera del 27/09 (non scritta nella repo).** «Il salto di piattaforma
  vale quanto un cambio di linea» si basava sul coseno Flex–3' di 0,047 contro 0,050 fra HCT116 e K562. Con il tetto
  di rumore misurato la frase va letta così:
  - il coseno Flex–3' osservato è basso anche perché VIPerturb è rumoroso;
  - una parte della distanza resta dopo averne tenuto conto;
  - quanto grande sia questa parte rispetto a un cambio di linea non si sa senza il tetto di rumore dei confronti
    fra linee.

## Limiti

- **Un solo schermo Flex:** tutte le conclusioni su «Flex» valgono per VIPerturb-seq.
- **Stime fatte due volte:** gli effetti a metà profondità sono stimati due volte con lo stesso stimatore; la
  selezione dei bersagli forti viene da r1 (Flex intero contro 3'), quindi non è indipendente dal confronto intero.
- **Il K562 essenziale** copre solo 678 dei 1.481 bersagli fissi.

## File

| File | Che cosa |
|---|---|
| `bridge.py` | r1: coseni fra universi e pendenze per gene |
| `half_pools.py` | una metà dei pool di un archivio di somme, unita in un pool |
| `split_half.py` | r2: metà contro metà, e ciascuna contro il 3', su un insieme fisso di bersagli |
| `r1/` | uscite di r1 |
| `r2/` | uscite di r2, con indice e manifest dei due universi a metà profondità |
