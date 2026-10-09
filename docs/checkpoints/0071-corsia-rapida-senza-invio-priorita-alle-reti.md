# CP-0071 — Corsia rapida senza invio: T3 pronto negli effetti, t38 non inviato; priorità alle reti

- **Data:** 2026-10-09
- **Tipo:** cambio-di-strategia
- **Redatto da:** Claude Code (Opus 5.5), sessione 8a8ca58a
- **Revisione umana:** no
- **Stato:** immutabile
- **Strade:** nessuna: nessun esito è stato letto. Il t38 non è stato inviato e T3 non è stato valutato sui fold

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Che cosa è successo alla corsia rapida aperta dal proprietario nella notte fra l'8 e il 9 ottobre (un refit del
transfer da inviare entro le 02:00), e quale direzione di lavoro vale dopo?

## 2. Cosa è stato fatto

Ricostruito da VALIDAZIONE sui file delle altre sessioni, letti agli orari indicati; gli orari dei fatti sono
quelli scritti nei file o nei loro tempi di modifica, Europe/Rome. Le parti misurate da questa sessione sono
dette tali.

1. **23:47 dell'8/10.** Il Lead registra la previsione del t37 = T1 con l'emissione del t36
   (`reports/invii/prediction_t37_2026-10-08/prediction.json`), su richiesta del proprietario di un invio rapido.
2. **23:55.** Il proprietario chiede un refit su tutte le fonti possibili: il t37 è superato prima di ogni
   generazione (`reports/invii/trial_2026-10-08/NO_SUBMIT_T1_r1.json`).
3. **00:01–00:11 del 9/10.** Il Lead affida a DATI-TRANSFER l'intero percorso fino al singolo invio
   (`../../reports/analisi/lead_piano_2026-10-08/MANDATO_REFIT_COMPLETO_r2.md`); DATI-TRANSFER congela il protocollo di **T3**
   (`../../reports/modelli/dati_transfer_2026-10-08_01a11c34/CONSEGNA_T3_PROTOCOLLO_r1.md`): T1 ricostruita al byte più cinque voti KO per studio e lignaggio,
   peso 0,25, non centrati, su 34 bersagli del pannello.
4. **00:19.** Previsione del t38 = T3 registrata prima del fit e della generazione
   (`reports/invii/prediction_t38_2026-10-09/prediction.json`): delta atteso zero, soglia ±0,005 contro t36.
5. **00:27–00:31.** Fit di T3 eseguito e verificato nel cloud (`../../reports/modelli/dati_transfer_2026-10-08_01a11c34/candidate_t3_r1.json`).
6. **00:44, misurato da questa sessione.** Un file di effetti di T3 riletto con lo sha256 della ricevuta e messo a
   confronto con T1, senza verità ([scheda](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/consegna/schede/t3_contro_t1_r1.json)).
7. **00:39–01:49.** Quattro tentativi di generazione di DATI-TRANSFER (`../../reports/modelli/dati_transfer_2026-10-08_01a11c34/STATO_r9.md`, `STATO_r10.md`,
   `STATO_r11.md`, `deadline_incident_r1.json`).
8. **01:52, misurato da questa sessione.** Pacchetto t36 riverificato; nessun upload pendente nello stato locale
   del client.
9. **01:54–01:55.** Il proprietario ferma la consegna e sposta la priorità sulle reti
   (`../../reports/modelli/dati_transfer_2026-10-08_01a11c34/stop_delivery_r1.json`, `../../reports/analisi/lead_piano_2026-10-08/MANDATO_RETI_2026-10-09_r1.md`).

## 3. Cosa si è osservato

- **Nessun invio.** Alle 02:00 non esiste una nuova entry: il t37 non è mai stato generato, il t38 non è stato
  impacchettato né caricato (`../../reports/modelli/dati_transfer_2026-10-08_01a11c34/STATO_r11.md`, `deadline_incident_r1.json`: `new_vcc_entry_created:
  false`, `t38_uploaded: false`). La consegna valutata resta t36, il cui pacchetto ha lo sha256 registrato
  ([verifica delle 01:52](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/consegna/riserva_t36_r3.json)).
- **T3 esiste come effetti.** Parità di T1 nel ramo nullo, 22 chunk KO, 12 contesti, 34 bersagli cambiati e
  nessuno fuori dal sostegno KO, sha256 `b8c61f6d…f6a6` (ricevute di DATI-TRANSFER; lo sha256 di un file è
  riletto da questa sessione: [recupero](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/consegna/schede/t3_effetti_recupero_r1.json)).
- **Scheda tecnica di T3 contro T1 (misurata, senza verità).** Dove votano CRISPRi e KO: correlazione mediana
  0,994, minima 0,984; distanza mediana 11 %. In più, 6.722 coppie bersaglio-gene previste dal solo KO, dove il peso
  0,25 si semplifica e resta la stima KO intera; fanno quasi tutta la distanza da T1 (9,4 % della sua norma).
  Segnalata come DT-5 alle 00:45 e dichiarata nella descrizione del t38 alle 00:59
  (`reports/invii/trial_2026-10-09/submission_texts_addendum_DT5.md`).
- **Generazione.** Riportato da DATI-TRANSFER: il primo kernel ha fallito dopo il fit su un argomento della riga di
  comando; il secondo ha generato le 360.000 cellule e si è fermato dopo, su un nome di file; il terzo si è fermato
  al preflight per un controllo di disco; il quarto ha generato tutte le cellule e si è fermato al confezionamento
  per lo stesso tipo di controllo. DATI-TRANSFER registra la scadenza mancata come errore proprio di pianificazione.
- **T3 non è valutato sui fold.** La sua combinazione non è una ricetta dello stadio 100 e il banco non può
  rifarla senza gli effetti per fold ([messaggi](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/MESSAGGI.md), 00:13).
- **Reti.** Riportato dal Lead: il fit ESM2 + ridge sulla vista T risulta concluso alle 01:56, con gli output
  presenti e non ancora verificati; gli altri fit sono in corsa; J-iPSC si è fermato prima del fit.

## 4. Interpretazione e incertezza

- Non c'è un esito scientifico: nessun punteggio, nessun banco su T3. L'attesa registrata da DATI-TRANSFER (delta
  zero) e la mia scheda dicono la stessa cosa: T3 è vicino a T1 e a t36 sui bersagli che cambia.
- **Interpretazione.** Le tre varianti «più fonti» della serata hanno cambiato poco le previsioni: 16 bersagli
  (T1), 34 a un quarto (T3), oppure hanno peggiorato di poco (T2). La validazione ha misure a favore solo per la
  composizione delle fonti, ed è esplorativa ([CP-0069](0069-validazione-indipendente-t1-e-ampliamento.md)).
- **Incertezza.** La cronaca delle generazioni è quella di chi le ha eseguite: non ho letto i log dei kernel. Che
  cosa valga T3 sul sito resta ignoto.

## 5. Spiegazione semplice

Si voleva mandare al sito, prima delle due di notte, una versione nuova della previsione che usasse più dati.
La ricetta nuova è stata calcolata in pochi minuti, ma trasformarla nel file da inviare (360.000 cellule
simulate) è fallito quattro volte per ragioni tecniche. Alle due non c'era nulla da inviare, e il proprietario ha
deciso di mettere da parte questa strada e lavorare sulle reti. Sul sito resta il risultato di prima.

## 6. Conseguenze

- **Direzione** (proprietario, 01:55, registrata dal Lead): il transfer rapido va in secondo piano; priorità alle
  reti, a partire dai fit ESM2 + ridge. Nessuna scadenza nuova.
- **Per VALIDAZIONE:** leggere gli output ESM2 prima come correttezza tecnica, poi nei regimi C, T e J con le
  regole del contratto; il regime T da solo non dimostra nulla sui contesti nuovi.
- **T3 e t38** restano conservati: effetti, previsione e cellule recuperabili. Nessuna generazione, confezionamento
  o invio rapido riparte senza una nuova decisione.
- Lo stato generale e R-LEAD sono aggiornati in questo stesso commit; gli indici degli invii elencano t37 e t38
  come non inviati.

## 7. Cosa corregge

Nessun checkpoint. Aggiorna la direzione scritta nello stato generale dopo
[CP-0070](0070-t2-centratura-su-tutti-i-bersagli.md).

## 8. Domanda di comprensione

Perché una previsione registrata e mai inviata non lascia una voce in `docs/STRADE.md`?
