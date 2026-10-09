# Esito della rete ponte (JEPA + SIGReg) sul banco del cubo

9 ottobre 2026, 17:46–18:12 CEST. Claude Code per Alfredo, con le decisioni lasciate a me; da leggere anche per
Davide.

**Ordine delle registrazioni** (ognuna committata prima dei suoi numeri):
1. [PROTOCOLLO.md](PROTOCOLLO.md): r1;
2. [EMENDAMENTO_R2.md](EMENDAMENTO_R2.md);
3. [EMENDAMENTO_R3.md](EMENDAMENTO_R3.md);
4. [EMENDAMENTO_R4.md](EMENDAMENTO_R4.md).

**Codice:** [rete_ponte.py](rete_ponte.py). **Valori:** [esito/](esito/).

**Sono indici sugli effetti del cubo** (coseno con la verità della linea tenuta fuori, indice PDS), non punteggi VCC
né membri DE sulle cellule.

## In breve

- **Regola registrata: non passa in nessuna delle quattro corse.** In ogni corsa la causa è la guardia del PDS su
  **H1**: da −0,044 a −0,108, con 96 bersagli e un PDS di base 0,91.
- **L'insieme di cinque reti dà il guadagno più grande mai misurato su questo banco, e si replica su semi
  indipendenti:**
  - coseno **+0,050** (r3, semi 2–6) e **+0,046** (r4, semi 7–11), con l'IC sopra 0 su 5 linee su 5 in entrambe;
  - PDS medio +0,021 e +0,013, positivo su HepG2, RPE1 e Jurkat in entrambe.
- **Per confronto:**
  - i pesi oracolo delle sorgenti davano al massimo +0,013;
  - il guadagno appreso dello stadio 1 dava +0,013;
  - sulla [curva](../guadagno_appreso_2026-10-05/ESITO.md) ogni linea sorgente in più vale circa +0,01. Quindi +0,05
    equivale a circa cinque linee in più.

## Le quattro corse, `rete − all` (media e IC 90% bootstrap appaiato sui bersagli)

| Corsa | Braccio | H1 | HepG2 | RPE1 | Jurkat | K562 | Regola |
|---|---|---|---|---|---|---|---|
| r1, seme 0 | coseno | +0,018 | −0,000 | +0,015 | +0,026 | +0,025 | no (PDS H1) |
| | PDS | **−0,108** | +0,018 | +0,003 | +0,023 | −0,020 | |
| r2, seme 1 | coseno (`centrata`) | +0,016 | −0,008 | −0,000 | +0,013 | +0,031 | no (coseno +0,010; PDS H1) |
| | PDS (`centrata`) | **−0,084** | +0,045 | +0,029 | +0,050 | −0,029 | |
| r3, insieme 2–6 | coseno | +0,032 | +0,055 | +0,036 | +0,063 | +0,065 | no (PDS H1) |
| | PDS | **−0,044** | +0,035 | +0,049 | +0,058 | +0,007 | |
| r4, insieme 7–11 | coseno | +0,041 | +0,038 | +0,028 | +0,056 | +0,067 | no (PDS H1) |
| | PDS | **−0,053** | +0,048 | +0,017 | +0,060 | −0,008 | |

**Nelle corse r3 e r4 l'IC del coseno è sopra 0 su tutte le linee.**

| | r3 | r4 |
|---|---|---|
| Coseno medio | +0,050 | +0,046 |
| PDS medio | +0,021 | +0,013 |

**MSE alla norma della ricetta:**
- migliora su Jurkat e K562 (da −0,17 a −0,21);
- non cambia su HepG2 e RPE1;
- peggiora molto su H1 (da +3 a +5), dove anche `all` ha 10,9.

## Che cosa si capisce (interpretazione)

1. **Una rete singola è rumorosa, l'insieme no.** Con un seme il coseno guadagna +0,02 e il PDS oscilla di ±0,05 fra i
   semi; con cinque semi la varianza si riduce e il guadagno raddoppia.
2. **Il guadagno viene dal residuo, non dai pesi delle sorgenti:** il braccio `rete_pesi` resta vicino ad `all` in
   tutte le corse, coerente col tetto dei pesi oracolo.
3. **Centrare il residuo sul pannello toglie da un quarto a un terzo del coseno** (r3: +0,050 → +0,033; r4:
   +0,046 → +0,034). Parte del guadagno è quindi una risposta comune della linea, prevista dai suoi controlli: è la
   leva della diagnosi del modo comune, presa qui senza oracolo. Centrato, il PDS di K562 migliora, quello di H1 no.
4. **H1 è l'eccezione stabile:** ha pochi bersagli, il PDS di base più alto e la MSE di `all` già fuori scala. La rete
   aggiunge direzione comune dove la discriminazione era già alta.

## Dove sta adesso la rete (fatto)

**Esportata per A/B/C** ([esporta_rete.py](esporta_rete.py), [esito/export_rete.json](esito/export_rete.json)):
- un insieme di 10 reti (semi 2–11), riaddestrato su tutti e 10 i gruppi;
- condizionato sul basale dei controlli ufficiali di ciascun contesto (`competition_A/B/C` del cubo);
- 300/300 bersagli;
- ogni bersaglio ha la norma di `all` × 1,576, quindi rispetto a `all` cambia solo la direzione. Il coseno fra le due
  direzioni ha mediana 0,76 (A), 0,80 (B) e 0,80 (C).

**Pacchetto** (t39 provvisorio):
- in generazione con l'emissione del t28;
- [previsione e regola per il sito](../../invii/prediction_t39_2026-10-09/prediction.json) registrate prima di ogni
  caricamento;
- **non inviato**: serve il via di Alfredo.

## Proposta per la decisione «gradare o no»

- **Per la regola registrata, no:** la guardia di H1 fallisce sempre, e la soglia non si sposta.
- **Per l'informazione:**
  - su 4 linee su 5 il guadagno è grande, stabile e replicato;
  - il t39 è un singolo esperimento pulito contro il t37/`all`, perché cambia solo la direzione.
  - Se Alfredo decide di inviarlo, va letto con la [regola del t39](../../invii/prediction_t39_2026-10-09/prediction.json)
    e dichiarato come **candidato che ha fallito la guardia di H1 sul banco**.
- **Per Davide:** la stessa rete si applica sopra la banca estesa. Più linee sorgente e il residuo appreso sono due
  leve diverse, e probabilmente si sommano. Va verificato.

**Non dice:** nulla su D, E, F; il banco non vede le cellule né i membri DE. Il basale ufficiale di A/B/C viene da
un'altra tecnologia rispetto alle tabelle di addestramento.
