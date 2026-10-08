# Raccomandazione per il freeze dell'8 ottobre

VALIDAZIONE (Claude Code `8a8ca58a`), orologio letto con `date`: **21:01 dell'8 ottobre 2026, Europe/Rome**, due
ore prima del freeze delle 23:00. **È una raccomandazione scientifica, non un'autorizzazione a un invio.** Ogni
esito è letto con il §8 del [contratto v2](PROTOCOLLO_v2.md), scritto prima dei numeri che legge.

## 1. La raccomandazione

- **Candidato della consegna: t36**, la riserva. Il suo pacchetto è verificato oggi contro il checksum registrato
  prima dell'upload e contro le ricevute ([verifica](consegna/riserva_t36_r1.json)); è l'unico candidato con un
  punteggio ufficiale (0,147249).
- **Ripiego:** t36 è già inviato e valutato: non c'è nulla da reinviare. Il riferimento precedente è il t28
  (0,144845), non riverificato oggi.
- **Nessun candidato nuovo è promosso.** T1 non si distingue da t36; T2 e la componente esterna non sono arrivati
  alla valutazione.
- **Nessun invio è consigliato stanotte:** non c'è un candidato che un punteggio ufficiale potrebbe distinguere
  da t36, e T1 cambia 16 bersagli su 300.

## 2. Esiti, classificati

| Oggetto | Esito | Dove |
|---|---|---|
| Baseline, scorer e banco riproducibili nel runtime | **valido**: effetti di t36, r1 e T1 riprodotti al byte; 42 esecuzioni su 42 senza tabelle del lignaggio escluso; misure ricalcolate in locale alla precisione di macchina | [livello A](RISULTATI_LIVELLO_A.md) §2 |
| Uso dei dati e leakage del percorso T1 | **valido**: quattro catene fonte → derivazione → fit → previsione verificate hash per hash; nessun leakage trovato nei fold; tre segnalazioni ai proprietari | [audit](AUDIT_DATI_E_LEAKAGE.md) |
| K1, **T1 contro t36** | **valido, inconcludente**: livello A macro `disc95` +0,0004 [−0,0005; +0,0013] su sei fold; sei membri, macro su due fold −0,0003 ± 0,0014; unico membro risolto l'NMAE sul fold K562, in peggio | [livello A](RISULTATI_LIVELLO_A.md) §4, [livello B](RISULTATI_LIVELLO_B.md) §2 |
| K0, t36 contro le quattro linee sulle stesse tabelle (retrospettivo) | **valido e sfavorevole per la regola**: sul fold K562 media −0,026 e PDS −0,101, risolti; sul fold iPSC +0,027 e +0,067, risolti | [livello B](RISULTATI_LIVELLO_B.md) §3 |
| K2, T2 (centratura su tutti i bersagli) | **non valutato**: alle 20:50 il fit finale di T2 attendeva il consenso del proprietario (`STATO_r3.md` di DATI-TRANSFER); nessun effetto per fold consegnato | — |
| K3 e K4, componente esterna | **non valutato**: nessun peso acquisito e nessuna inferenza reale; senza scheda di esposizione verificata non è ammissibile | [messaggi](MESSAGGI.md) |
| Regime J | **base misurata**, non un confronto: il transfer prevede solo la testa cis, `disc95` 0,54–0,58 | [livello A](RISULTATI_LIVELLO_A.md) §7 |
| Esplorativo: t36 senza KOLF2.1J | livello A a favore sui quattro lignaggi non staminali, contro su H1; sei membri sul fold K562 in corsa alla stesura (aggiunto in fondo quando arriva) | [livello A](RISULTATI_LIVELLO_A.md) §6 |

T2 non poteva comunque entrare nella scelta di stanotte: il banco a sei membri sul fold K562 dura 109 minuti
misurati, e un candidato si promuove solo con il livello B su due fold.

## 3. Perché t36 e non T1

**Misurato.** T1 aggiunge 16 voti a t36, su 16 bersagli. Dieci raddoppiano un lignaggio che votava già (HEK293
con Xu, iPSC con HIPSCI); sei vengono da un lignaggio nuovo (neuroni di Tian 2021). Tutti e tre i gruppi arrivano
da tabelle di 5–6 bersagli, alle quali la centratura sul pannello toglie il 17–20 % dell'effetto proprio. Su sei
fold nessuna misura di discriminazione si muove in modo risolto; a sei membri la macro è −0,0003 ± 0,0014.

**Interpretazione.** T1 è un passo di copertura, non un miglioramento predittivo dimostrato. Con 16 bersagli su
300 un punteggio ufficiale non potrebbe distinguerla da t36: la differenza attesa sta molto sotto la soglia
operativa di ±0,005 di un singolo invio. Usare T1 come base di lavoro non fa danno misurato; presentarla come
candidato migliore non è sostenuto.

## 4. Che cosa questa notte dice di t36

t36 resta la scelta perché è l'unica con evidenza ufficiale, e nessun difetto di validità è emerso: la sua
previsione si ricostruisce esattamente e non legge nulla che non dovrebbe. Ma tre misure di oggi riguardano la
sua composizione, e vanno dette insieme alla raccomandazione:

1. **Sul fold K562 t36 è peggio della ricetta a quattro linee** sulle stesse tabelle, a sei membri e sul PDS, in
   modo risolto; sul fold iPSC è meglio. Nel livello A la correlazione specifica scende su quattro lignaggi non
   staminali e sale sui due staminali.
2. **Il pezzo che aiuta è H1; quello che costa è l'ingresso di KOLF2.1J**, che vota fino a quattro volte.
3. **La centratura sul pannello distorce le tabelle piccole**, tre delle quali sono in t36.

Il +0,0024 ufficiale di t36 su t28 non contraddice queste misure e non le conferma: un invio, tre contesti di
identità ignota, tabelle Orion cambiate insieme alle fonti.

## 5. Che cosa fare dopo (proposta, in ordine)

1. **Un contrasto vero sulla composizione delle fonti**, costruito da DATI-TRANSFER dalla stessa release: le
   quattro linee più H1, e KOLF con un voto solo. Valutazione con il contratto; se regge su almeno due fold a
   sei membri, un invio con previsione registrata per membro (attesa: PDS in salita rispetto a t36 se A, B e C
   non sono staminali). È un'**ipotesi** nata su lignaggi di sviluppo: solo il sito o lignaggi non letti la
   confermano.
2. **T2 con la segnalazione DT-1**: numero di bersagli dietro ogni vettore comune dichiarato, minimo fissato prima.
   Il banco lo valuta in otto minuti (livello A) più i due banchi a sei membri.
3. **Cellule vere per i fold CD4T, HCT116 e HEK293** (i campioni della banca ci sono): porterebbe il livello B da
   due a cinque lignaggi. È il limite più grosso di questa validazione.
4. **Componente esterna in J**, dove il transfer non prevede quasi nulla: la base da battere è `disc95` 0,56.
   Serve prima il via del proprietario per i pesi e la scheda di esposizione.

## 6. Questioni per il proprietario

- **Kernel pubblici con file di gara** (segnalazione DT-3): il fit T1 e parte dei kernel `dt-all-*` risultano
  lanciati come pubblici e incorporano `pert_counts.csv` e `gene_names.csv` del bundle. Riguarda le condizioni
  d'uso dei file di gara: lo decide il proprietario.
- **Consensi in attesa negli altri due incarichi:** il fit finale di T2 (DATI-TRANSFER) e lo scaricamento di PIE
  (45,6 GB) ed ESM2 (98,5 MB) con la licenza non commerciale di PIE da valutare (MODELLI-ESTERNI).
- **Calcolo usato da questa sessione:** nove kernel Kaggle CPU privati e tre dataset privati di effetti a
  lignaggio escluso, sull'autorizzazione permanente per Colab e Kaggle; nessuna GPU, nessun acquisto, nessun
  push Git, nessun invio.

## 7. Limiti di questa raccomandazione

Banco di sviluppo: sei lignaggi che sono fonti di ogni ricetta, due dei quali con cellule vere. Il livello A è
un proxy nello spazio degli effetti; il livello B usa scale locali. Gli intervalli dicono la variabilità fra
bersagli e fra semi dentro i contesti osservati, non l'incertezza su D, E e F. La copertura D-053 resta aperta e
nessun artefatto valutato qui usa i campioni cellulari.

## 8. Aggiunte dopo l'emissione (orologio letto con `date`)

Il testo sopra è quello emesso alle 21:01 e non è stato ritoccato. **La raccomandazione non cambia.**

- **21:23, esplorativo a sei membri sul fold K562** ([livello B](RISULTATI_LIVELLO_B.md), §6): t36 senza le
  quattro tabelle KOLF dà media +0,0299 ± 0,0081 e PDS +0,1171 ± 0,0197, risolti; con KOLF che vota una volta sola
  il PDS non si muove e l'NMAE migliora. L'ipotesi del piano non cade; non è una conferma, perché il fold è quello
  da cui è nata. Rafforza il punto 1 del §5: il contrasto sulla composizione delle fonti è il primo da costruire.
- **21:27, correzione alla riga K2 del §2.** I vettori comuni congelati di T2 erano sul disco dalle 21:00:34
  (`HANDOFF_T2_MEDIE_r1.md` di DATI-TRANSFER), entro il termine delle 21:15 che avevo indicato alle 19:06; li ho
  letti dopo l'emissione. Restava vero che nessun **effetto** di T2 esiste: il fit finale attende il consenso del
  proprietario. Lo stimatore è in valutazione sui sei fold dalle 21:40, con il [piano](VALUTAZIONE_T2.md)
  committato prima (21:36:52).
- **Che cosa può cambiare entro le 23:00: nulla sulla consegna.** Per il §8 un candidato si promuove solo con il
  livello B su due fold, e il banco sul fold K562 dura 107–109 minuti: alla scadenza T2 è inconcludente per regola,
  qualunque cosa dica il livello A. Non esiste un suo effetto di produzione e nessun invio è autorizzato. L'esito
  completo di T2 serve alla decisione successiva: se autorizzare il suo fit finale e con che cosa confrontarlo.
