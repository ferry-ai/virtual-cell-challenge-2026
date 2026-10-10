# Esito dell'ablazione della parte JEPA

10 ottobre 2026, 14:37–15:59 CEST. Il protocollo è [ABLAZIONE_JEPA.md](ABLAZIONE_JEPA.md), registrato prima dei
numeri (commit `b0de6a9`). Valori in [esito/ablazione_confronto.json](esito/ablazione_confronto.json) e
`esito/ablazione_result_*.json`.

Ogni braccio è un insieme di 10 reti (semi 2–11). Le differenze sono appaiate sugli stessi bersagli, con IC 90%
bootstrap. **È il banco del cubo, non il sito.**

## Regola registrata: la parte JEPA **non «serve»** nel senso del protocollo

`ref − nojepa` (con la parte JEPA − senza):

| Linea | Coseno [IC 90%] | PDS [IC 90%] |
|---|---|---|
| H1 | −0,016 [−0,023; −0,010] | **+0,033** [+0,009; +0,061] |
| HepG2 | −0,007 [−0,013; −0,001] | **+0,018** [+0,008; +0,028] |
| RPE1 | −0,019 [−0,024; −0,014] | −0,009 [−0,023; +0,005] |
| Jurkat | +0,004 [−0,000; +0,008] | +0,007 [−0,002; +0,016] |
| K562 | −0,008 [−0,014; −0,001] | −0,002 [−0,018; +0,014] |
| **Media** | **−0,009** (0 linee sopra 0) | **+0,009** |

**Come si legge la regola:**
- il coseno doveva salire di almeno +0,005: invece **scende**;
- la condizione sul PDS è soddisfatta.

## Che cosa fa davvero la parte JEPA (misurato, letto dopo la regola)

**Non è decorativa. Sposta la rete dal coseno al PDS:**
- toglie circa un centesimo di coseno;
- restituisce circa un centesimo di PDS;
- su H1 e HepG2 il PDS cresce con l'IC sopra 0.

**Il pezzo che conta è SIGReg.** Togliere solo SIGReg (`ref − nosig`) dà quasi lo stesso effetto di togliere tutto:
- coseno −0,011 di media;
- PDS +0,014 di media (H1 +0,041, HepG2 +0,023, Jurkat +0,015, tutti con l'IC sopra 0).

**Più peso peggiora tutti e due:** con `jepa03 − ref` scendono coseno (−0,006) e PDS (−0,007); su H1 e K562 il PDS
cala con l'IC sotto 0. Il peso 0,1 è meglio di 0,3.

**Le corse complete, contro `all`:**

| Braccio | Coseno | PDS | Guardia PDS su H1 |
|---|---|---|---|
| `nojepa` | +0,062 | +0,011 | fallisce |
| `nosig` | +0,064 | +0,006 | fallisce |
| `ref` | +0,053 | +0,020 | fallisce |
| `jepa03` | +0,048 | +0,013 | fallisce |

## Che cosa ne segue (interpretazione)

1. **Il guadagno di coseno sul cubo non viene dal JEPA,** che anzi lo riduce. Viene dal residuo appreso con il
   coseno, dall'InfoNCE e dalla media dei semi.
2. **SIGReg tiene i latenti isotropi e così protegge la discriminazione fra bersagli.** È l'unica parte della rete che
   lavora nella direzione che il sito ha premiato nel `Alfredo·t39·oeRXw89O`: sul sito il PDS è sceso, sul cubo il
   coseno era salito.
3. **Ipotesi da verificare, non misurata:** una rete con più peso sul PDS (SIGReg più forte e residuo centrato)
   potrebbe trasferire meglio al sito. Il banco del cubo però non predice il PDS del sito, quindi va prima tarato.
