# t39 (rete ponte): esito e commento per Davide

10 ottobre 2026. Lettura col lettore registrato prima del punteggio
([comparison.json](../../invii/prediction_t39_2026-10-09/comparison.json)). La rete e il suo banco sono descritti in
[ESITO della rete](../../modelli/rete_ponte_jepa_2026-10-09/ESITO.md).

## Risultato (misurato)

**t39 = 0,140816, rango 528.** Entry `oeRXw89O1hefFsdCwifD`, inviato alle 08:48 UTC del 10/10.

| Confronto | Δ | Note |
|---|---|---|
| t39 − t28 | **−0,0040** | **ramo b** della regola, non conclusivo; dentro la banda −0,010…+0,020 |
| t39 − t36 | −0,0006 | |
| t39 − 0,1472 | −0,0064 | lo 0,1472 è l'ultimo invio del team in classifica, ricevuta non verificata |

| Membro scalato | t28 | t36 | t39 | t39 − t28 | Peso sulla media |
|---|---|---|---|---|---|
| PDS | 0,622 | 0,591 | 0,568 | −0,055 | **−0,0091** |
| nMAE | 0,049 | 0,074 | 0,076 | +0,027 | +0,0045 |
| fedeltà | −0,007 | −0,006 | +0,013 | +0,021 | +0,0035 |
| reach | 0,199 | 0,185 | 0,181 | −0,017 | −0,0029 |
| Jaccard | 0,006 | 0,004 | 0,006 | 0,000 | 0 |
| MSE | 0 | 0 | 0 | 0 | 0 |

Il coseno PDS grezzo scende: 0,781 nel t28, 0,767 nel t36, 0,757 nel t39.

## Commento (interpretazione)

1. **Il guadagno del banco non passa sul sito.**
   - Sul cubo la rete aggiungeva +0,05 di coseno e +0,01/+0,02 di PDS.
   - Sul sito il PDS **scende** di 0,055 scalato rispetto al t28 e di 0,023 rispetto al t36.
   - È il quinto caso in cui il banco del cubo sopravvaluta il sito (dopo R nel t30, `all` + R nel t36 e altri).
2. **Quello che la rete aggiunge sul sito sono i membri DE, non la direzione:**
   - la fedeltà sale (positiva per la prima volta, +0,013);
   - l'nMAE resta al livello del t36.

   Non basta a compensare il PDS.
3. **L'ipotesi più probabile è la risposta comune.** Parte del guadagno sul cubo era una risposta comune della linea,
   prevista dai controlli. Sul sito la risposta comune vale circa l'1% dell'energia, contro il 2–31% delle linee del
   cubo. Lì aggiungerla toglie discriminazione fra bersagli senza aiutare la MSE.
   - È coerente col banco, dove la parte comune alzava il coseno e abbassava il PDS.
   - **Non è misurato:** si verificherebbe con la rete centrata (`rete_centrata`).
4. **Il basale ufficiale di A/B/C viene da un'altra tecnologia** rispetto alle tabelle di addestramento: il contesto che
   la rete vede sul sito è fuori dalla distribuzione del banco. È un secondo motivo possibile, non separato.

## Che cosa cambia

- **La rete ponte in questa forma non entra nel candidato finale** (ramo b, con il PDS in calo).
- **Il riferimento del team resta lo 0,1472** (se è davvero la base senza R di Davide), poi il t28.
- **Prossima verifica sensata, se si vuole insistere sulla rete:** la variante centrata sul pannello, che toglie la
  parte comune. Va registrata prima, contro questo t39 e con la stessa emissione. Il guadagno atteso è piccolo: va
  pesato col criterio d'impatto minimo (circa +0,01).
- **Il banco del cubo misura male il PDS del sito.** Prima di usarlo per decidere un invio servirebbe una taratura
  sito/banco sui cinque invii che abbiamo (t28, t30, t36, t38, t39).
