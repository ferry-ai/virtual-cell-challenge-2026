# Lettura degli output ESM2 + ridge nel regime T

9 ottobre 2026, VALIDAZIONE (Claude Code `8a8ca58a`). **Piano scritto prima dei numeri di questa corsa**: vale
l'orario del commit che lo introduce; la corsa r6 del livello A è lanciata dopo. È la prima lettura chiesta dal
mandato del Lead delle 01:55 (`reports/analisi/lead_piano_2026-10-08/MANDATO_RETI_2026-10-09_r1.md`): prima la
correttezza tecnica, poi i regimi con le regole già congelate.

## Che cosa è arrivato

Il fit ESM2 + ridge di MODELLI-ESTERNI sulla vista T (`davideferrante11/esm2-t-01a11c35-r3`) è terminato alle
01:56 e verificato da loro alle 01:57. Leggo, senza modificarlo, il file delle predizioni native nella radice
dati: 798.872.453 byte, sha256 `06935074…93fd`, uguale alla loro ricevuta.

**Il modello** (dal loro manifest del fit, non ricalcolato da me): ridge con alpha 1,0 sugli embedding ESM2 della
proteina del bersaglio, senza alcun ingresso di contesto; 163.143 righe di 47 contesti in dieci lignaggi; i
bersagli nascosti sono esclusi dalla vista T prima delle statistiche (controllo di DATI-TRANSFER; per i vettori
comuni l'ho verificato sui denominatori nell'[audit](AUDIT_DATI_E_LEAKAGE.md), §8). Gli embedding vengono dalla
sola sequenza, secondo i metadati dell'asset: non contengono risposte a perturbazioni.

## Primo passo, fatto prima di leggere qualunque verità: correttezza tecnica

[banco/esm2_t_r2/esame.json](banco/esm2_t_r2/esame.json), prodotto da `banco/prepara_esm2_t.py esamina`.

| Controllo | Esito |
|---|---|
| Identità del file | sha256 uguale alla ricevuta di MODELLI-ESTERNI |
| Assi | 18.533 geni, uguali all'asse ufficiale; 3.102 righe = 66 bersagli × 47 contesti |
| Bersagli | esattamente i 66 del gruppo nascosto del [manifest](manifest_fold_v2.json) |
| Valori | tutti finiti; ESM2 disponibile per ogni richiesta |
| Solo bersaglio | lo stesso bersaglio ha la stessa previsione in tutti i contesti, a meno di 2,2e-16; la parte generica è la stessa riga per tutti |
| Copertura | 16.162 geni previsti per ogni bersaglio |
| Scala | logaritmo naturale del fold change; valore assoluto mediano 0,016, 95° percentile 0,090, massimo 2,14 |
| Quanto è «generico» | la parte specifica vale in mediana il 69 % della norma di una previsione (50–91 %); la correlazione media fra bersagli è 0,56 sulle previsioni intere e 0,12 sulle parti specifiche |

La prima versione dell'esame chiedeva l'uguaglianza esatta fra contesti e ha trovato un arrotondamento di
2,2e-16: è conservata in `banco/esm2_t_r1/`, e la seconda dichiara la tolleranza (1e-12). **Tecnicamente il file è
quello che dichiara di essere.**

## Che cosa legge il banco, e sotto quale nome

I 66 bersagli nascosti contro la verità di ciascuno dei sei lignaggi, con la struttura a bersagli nascosti già
usata nella corsa r4. **Il regime è T, non J e non C:** le altre risposte di ogni lignaggio erano nel training.
Un modello senza ingresso di contesto dà la stessa risposta a tutti i lignaggi: qui si misura se quella risposta
somiglia a ciò che accade, lignaggio per lignaggio. **Il regime T da solo non dice nulla sui contesti nuovi.**

Bracci, convertiti da me nel formato dello stadio 100
([conversione](banco/esm2_t_r2/conversione.json)); solo le righe dei 66 bersagli sono previste:

| Braccio | Che cos'è |
|---|---|
| `E2` | la previsione nativa, senza ampiezza e senza testa cis |
| `E2g` | la sola parte generica: una riga, uguale per ogni bersaglio |
| `E2c` | come entrerebbe nel transfer: 1,576 × `E2`, con la testa cis del transfer dove il transfer predice |
| `T0` | il transfer sui bersagli nascosti: la sola testa cis, cioè **un** gene vicino per 20 bersagli su 66 e nulla per gli altri 46 |

## Contrasti e controlli

| Che cosa | Domanda | Se fallisce |
|---|---|---|
| `E2 − E2g` | la sequenza aggiunge qualcosa di specifico del bersaglio oltre la riga generica? **È la domanda principale** | — |
| `E2` contro `E2` con le previsioni scambiate fra i 66 bersagli | il banco vede quella specificità? Il braccio scambiato deve tornare a 0,5 | la corsa non si legge |
| `E2 − T0`, `E2c − T0` | contro ciò che il transfer sa fare lì | — |
| `E2c − E2` | che cosa aggiunge la testa cis sopra il ridge | — |
| Parità di produzione di T0, R1, T1 | come in ogni corsa | la corsa non si legge |

Misure: `disc95` (primaria; i geni del rango vengono dalla verità, uguali per ogni braccio), `r_spec`, `sign50`,
`nmae_conf`, errore quadratico; per il ponte di scala, l'ampiezza ottima contro la verità e la quota comune, che
il banco misura invece di assumere.

## Come si legge (scritto prima)

- È una lettura **descrittiva**: nessuna promozione. Il §8 del contratto promuove solo con i fold C e il banco a
  sei membri.
- Dirò che il ridge **ha imparato qualcosa del bersaglio** solo se la macro di `disc95` per `E2 − E2g` è positiva
  e risolta **e** il controllo a previsioni scambiate è risolto. Se non è risolta, la conclusione è che in T non
  si misura un segnale specifico oltre la parte generica. In nessuno dei due casi segue qualcosa per D, E, F:
  per quelli servono i fit a lignaggio escluso (C-K562 e C-iPSC sono in corsa).
- Un guadagno delle sole misure d'ampiezza (`nmae_conf`, errore quadratico) senza `disc95` né `r_spec` si legge
  come parte comune, non come specificità.

## Precedenti

- **S-001, S-002, S-006** (reti che predicono soprattutto la risposta comune). Differenza di disegno: qui la parte
  generica è un braccio a sé (`E2g`), quindi il contrasto principale la toglie per costruzione. Segnale precoce:
  `disc95` di `E2` contro 0,5 e contro il braccio scambiato.
- **S-009** (stessa ancora e stessa trasformazione in fit, banco ed esportazione). Il banco legge il file nativo
  del fit, non una riesportazione; la conversione è dichiarata e i suoi file hanno dimensione e sha256.
- ERRORI, errori di metodo: lignaggi già letti sono sviluppo; la soglia non si sposta dopo il numero; lo stato di
  un altro incarico si rilegge prima di scriverlo.

## Limiti

Sessantasei bersagli; sei verità, tutte di lignaggi che il modello ha visto con altri bersagli; proxy nello spazio
degli effetti, nessun membro ufficiale; la scala nativa non è quella dello stadio 100. La correttezza numerica del
fit (parità con una regressione densa) è una prova di MODELLI-ESTERNI su 128 righe, non rifatta qui.

## Aggiunta delle 02:39, prima della corsa r7: il fit J senza K562

Scritta dopo aver letto il regime T ([risultati](RISULTATI_ESM2_T.md)) e **prima** dei numeri della corsa r7.
MODELLI-ESTERNI ha concluso anche il fit senza il lignaggio K562 e senza i bersagli nascosti
(`davideferrante11/esm2-j-k562-01a11c35-r1`, verificato da loro alle 02:11); file nativo con sha256
`cedca755…405a`, uguale alla loro ricevuta, esame tecnico superato
([esame](banco/esm2_jk562_r1/esame.json)).

- **Che cosa si legge.** Contro la verità di K562 è **regime J** (né il lignaggio né i bersagli erano nel
  training): è la prima lettura J di una componente esterna. Contro le altre cinque verità è regime T con K562
  tolto, descrittiva.
- **Già misurato senza verità** ([confronto](banco/esm2_jk562_r1/confronto_con_T.json)): le previsioni di questo
  fit e del fit T sono quasi le stesse (correlazione per bersaglio mediana 0,996, minima 0,990; norma 1,009).
  **Attesa scritta prima:** la lettura contro K562 ripete quella del regime T (`disc95` intorno a 0,52, non
  distinguibile dal braccio a previsioni scambiate); se è così, vuol dire che le righe di K562 pesano poco nel
  modello, non che il modello generalizzi.
- **Bracci e contrasti:** `E2jk`, `E2jkg`, `E2jkc` come sopra; `E2jk − E2jkg`, `E2jk` contro il suo braccio a
  previsioni scambiate, `E2jk − T0`, `E2jkc − T0`, e `E2jk − E2` (che cosa cambia togliendo K562).
- **Regola:** la stessa, letta sul solo fold K562: servono insieme `E2jk − E2jkg` positivo e risolto e il controllo
  a previsioni scambiate risolto. Nessuna promozione: è un lignaggio, e un regime J non sostituisce il regime C.
