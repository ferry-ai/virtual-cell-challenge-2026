# Diagnosi: quanto vale la risposta comune della linea nuova nel profilo aggregato?

5 ottobre 2026, sera. Claude Code per Alfredo, che ha chiesto in chat di individuare il collo di bottiglia e lavorarci
«con serietà».

**Registrato prima di ogni numero di questa diagnosi.** È una misura del **tetto**, non un modello.

## Ipotesi

- La ricetta toglie a ogni sorgente la media della sua tabella (γ = 1), quindi la previsione non ha la risposta
  comune della linea nuova. La verità invece la contiene.
- Se quella parte è una frazione grande dell'energia vera, il collo di bottiglia della direzione aggregata (MSE e PDS)
  è **prevedere la risposta comune della linea dai suoi controlli**. È un problema di modello appreso, con dati di
  addestramento in 34 tabelle.

## Misure (cubo r2, 5 linee tenute fuori, stessi bersagli e misure dello [stadio 1](PROTOCOLLO.md))

**c_L** è la risposta comune vera di L: la media pesata n/(n+100), fra le tabelle di L, della media raw su tutte le
chiavi utilizzabili di ciascuna tabella. È un **oracolo**: usa la verità di L.

| Braccio | Che cosa è |
|---|---|
| `all` | T_all (come nello stadio 1) |
| `comune_vero` | c_L, uguale per tutti i bersagli |
| `all+comune_vero` | T_all + c_L (**tetto** di un predittore perfetto della parte comune) |
| `all+comune_sorgenti` | T_all + la media delle risposte comuni delle tabelle sorgente (il termine «generico» di P4, non un oracolo) |

**Si riportano, per linea:**
- il coseno con la verità e l'indice del PDS;
- la quota d'energia della verità spiegata da c_L: ‖c_L·d‖²·K / Σ_k ‖y_k·d‖², nello spazio Δ al primo ordine.

## Lettura (fissata ora)

- **Se `all+comune_vero − all` ≥ +0,15 di coseno su almeno 4 linee su 5:** il collo di bottiglia è confermato. Il
  passo dopo è un predittore appreso di c_L dai controlli, con il suo protocollo.
- **Se è sotto +0,05:** l'ipotesi cade, e il limite è la parte specifica del bersaglio.
- **Fra le due soglie:** zona intermedia, da discutere con il proprietario.
- **Il PDS si legge a parte:** una parte comune uguale per tutti non discrimina, e può abbassarlo.

## Previsione (soggettiva)

- **Quota d'energia di c_L:** 0,2–0,5.
- **`all+comune_vero − all`:** da +0,10 a +0,35 di coseno.
- **PDS:** in calo da 0,00 a 0,10.
