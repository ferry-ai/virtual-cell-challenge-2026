# CP-0070 — T2, centratura su tutti i bersagli: valido e sfavorevole a lignaggio escluso

- **Data:** 2026-10-08
- **Tipo:** esperimento
- **Redatto da:** Claude Code (Opus 5.5), sessione 8a8ca58a
- **Revisione umana:** no
- **Stato:** immutabile
- **Strade:** S-012, S-011

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Centrare ogni fonte del transfer sulla media di **tutti** i suoi bersagli, invece che sulla media delle sue righe
sul pannello, migliora la previsione di un lignaggio mai visto? È il candidato T2 di DATI-TRANSFER.

## 2. Cosa è stato fatto

Tutto in [validazione_indipendente_8a8ca58a_2026-10-08](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/README.md); orari letti con `date`, dai commit o
dai `launch.json`, Europe/Rome.

1. **Piano prima dei numeri:** [VALUTAZIONE_T2.md](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/VALUTAZIONE_T2.md), commit `34984c39` delle 21:36:52.
   Regola di lettura: il §8 del contratto con la misura del v2, invariata.
2. **Ingresso:** i vettori comuni congelati consegnati da DATI-TRANSFER alle 21:00 (16 fonti, da 95 a 18.080
   bersagli dietro ogni vettore), verificati per hash contro la consegna e contro gli oggetti per fonte.
3. **Livello A** (corsa r5, lanciata alle 21:40): lo stadio 100 di produzione con la chiave `common` congelata,
   sulla cache di ogni fold senza il lignaggio escluso; bracci T2, T1 e T0, più i bracci a gamma 0 per la parità.
4. **Livello B** (lanciato alle 21:58): `bench_v2.py` non modificato, emissione t28, 400 cellule, cinque semi, sui
   fold C-iPSC (55 bersagli) e C-K562 (272), coppie T2:T0, T2:T1 e T1:T0.
5. **Identità del candidato:** gli effetti di produzione di T2, consegnati da DATI-TRANSFER alle 22:10, riletti e
   confrontati con quelli che il banco ottiene eseguendo la stessa ricetta in produzione.

## 3. Cosa si è osservato

- **La corsa è valida.** Parità di produzione di T0, R1 e T1; a gamma 0 gli effetti con e senza il file dei vettori
  hanno lo stesso sha256 in ogni fold; nessun gene votato è senza sostegno; il braccio a bersagli scambiati torna a
  0,47–0,53; i vettori del lignaggio escluso non sono letti
  ([risultati](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/RISULTATI_T2.md), §1; [descrizione](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/r5/descrizione_t2_r5.json)).
- **Il candidato è lo stimatore valutato.** I tre file di produzione di T2 hanno sha256 `d496a38d…0ab2`, lo stesso
  della ricevuta del banco ([ricevuta](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/r5/completion_extra/stage100_manifests/T2__PROD.json)).
- **Che cosa cambia negli effetti.** T2 aggiunge a ogni bersaglio una stessa riga: contiene l'11–19 % della
  risposta comune che la centratura sul pannello toglie (coseno 0,29–0,44) e per il resto è un'altra direzione; la
  quota degli effetti comune a tutti i bersagli sale da 0,02 % a 0,35–0,63 %
  ([parte comune](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/r5/comune_t2_r5.json)).
- **Livello A, sei fold, contro t36.** `disc95` −0,0005 [−0,0030; +0,0020], nessun fold risolto; `sign50` −0,0042
  [−0,0065; −0,0020] e `nmae_conf` +0,0026 [+0,0014; +0,0037], risolti, in peggio, su CD4T, HCT116, HEK293 e K562
  ([tabelle](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/TABELLE_T2_r5.md)). Con la misura stretta del v1 la macro è −0,0035 [−0,0069; −0,0001] sui sei
  fold e −0,0020 [−0,0053; +0,0011] sui cinque dove è utilizzabile
  ([ricalcolo](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/r5/sensibilita_disc_t2_r5.json)).
- **Livello B, contro t36.** Fold K562: sei membri −0,0087 ± 0,0045, risolto, negativo in tutti e cinque i semi;
  NMAE −0,0292 ± 0,0259, risolto; PDS −0,0202 ± 0,0243, non risolto. Fold iPSC: +0,0023 ± 0,0125. Macro su due
  fold −0,0032 ± 0,0074 ([tabelle](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/TABELLE_LIVELLO_B_t2_r2.md)). Contro T1 gli stessi versi: K562 −0,0079
  ± 0,0041, risolto.
- **Riproducibilità.** In entrambi i kernel T1 − T0 coincide seme per seme con le corse r1
  ([K562](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/livello_b_k562_t2/riproduce_r1_T1_T0.json),
  [iPSC](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/livello_b_ipsc_t2/riproduce_r1_T1_T0.json)).
- **Esito della regola:** VALIDO E SFAVOREVOLE, per la regressione risolta della media sul fold C-K562. Alla
  scadenza delle 23:00, con un solo fold a sei membri, era inconcludente.

## 4. Interpretazione e incertezza

- **Misura:** nessuna misura migliora; sul fold K562 la media dei sei membri peggiora in modo risolto.
  **Interpretazione:** la media su tutti i bersagli di una fonte è la risposta comune di un'altra popolazione di
  perturbazioni, non una stima più precisa di quella dei 300 bersagli di gara; sottrarla lascia nelle previsioni
  una riga comune che non somiglia alla risposta del lignaggio escluso. **Ipotesi:** è quella riga a peggiorare
  NMAE e profondità di segno; non è isolata con un contrasto dedicato.
- **Perché potrebbe non essere così.** Due soli fold hanno cellule vere, entrambi lignaggi di sviluppo, e K562 è
  stato letto molte volte. La perdita è piccola (0,009 su scala locale) e le scale locali non sono il sito. Il
  fold iPSC non risolve nulla: lì la deviazione fra semi delle coppie di T2 è quattro volte quella di T1 − T0.
  Sui lignaggi senza cellule vere c'è solo il livello A.
- **Che cosa non è stato provato:** una centratura su tutti i bersagli limitata alle tabelle piccole, che è la
  domanda lasciata aperta da S-011.

## 5. Spiegazione semplice

Prima di fare la media fra cellule diverse, a ogni esperimento si toglie la sua «risposta di fondo», quella che
compare qualunque gene si spenga. Finora la si stimava sui soli 300 geni di gara presenti in quell'esperimento;
T2 la stima su tutti i geni che l'esperimento ha spento, anche diecimila. Sembra una stima migliore perché usa più
dati, ma è la risposta di fondo di **altri** geni: quelli di gara ne hanno una un po' diversa, e toglierne una
sbagliata lascia nella previsione un errore uguale per tutti.

## 6. Conseguenze

- T2 non è promosso e non è un candidato della consegna, che resta **t36**
  ([raccomandazione](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/RACCOMANDAZIONE.md), §8). Non serve generarlo.
- La strada S-011 resta aperta nella sua domanda vera: T2 non la isola, perché cambia la centratura di tutte le
  tabelle. Nuova strada S-012.
- Per il trainer esteso vale un'avvertenza, non un esito: una risposta generica stimata su tutti i bersagli di un
  contesto va confrontata sui fold con quella stimata sul pannello.
- Il banco ha ora un percorso provato per valutare una ricetta con vettori comuni congelati e per verificare che
  il candidato esportato sia lo stimatore valutato.

## 7. Cosa corregge

Nessun checkpoint. Completa [CP-0069](0069-validazione-indipendente-t1-e-ampliamento.md), che lasciava T2 in
valutazione, e precisa un fatto successivo: gli effetti di produzione di T2 esistono dalle 22:10, con il via del
proprietario delle 21:51. Fra le 21:44 e le 23:08 tre documenti di questa validazione hanno detto il contrario
da una lettura vecchia; sono corretti con nota datata e l'errore è una riga di `docs/ERRORI.md`.

## 8. Domanda di comprensione

Perché una media calcolata su più bersagli può essere una stima peggiore della risposta comune dei bersagli di
gara?
