# CP-0074 — t38 (T3: CRISPRi più voti KO): nuovo massimo osservato, non conclusivo contro t36

- **Data:** 2026-10-09
- **Tipo:** esperimento
- **Redatto da:** Claude Code (sessione eace4d03, VALIDAZIONE)
- **Revisione umana:** no
- **Stato:** immutabile
- **Strade:** S-010, S-014

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Che punteggio ufficiale ottiene T3, cioè il transfer CRISPRi della release T1 più cinque voti KO a peso 0,25 su 34
bersagli, con il generatore del t36? La previsione era registrata prima del fit e della generazione: delta atteso
zero contro t36, soglia ±0,005.

## 2. Cosa è stato fatto

L'invio è di DATI-TRANSFER, unico submitter per [mandato del Lead](../../reports/analisi/lead_piano_2026-10-08/MANDATO_RIPRESA_INVIO_T3_2026-10-09_r1.md):
cellule già generate nella notte, recuperate e impacchettate senza nuovo fit né nuova generazione; upload concluso
alle 20:04:41 del 9 ottobre, entry `LJmnhqqh1WTrx1JcoRlr`
([ricevute](../../reports/modelli/dati_transfer_2026-10-08_01a11c34/t38_delivery_verified_r1.json)).

VALIDAZIONE ha letto lo stato ufficiale una volta, alle 21:09:48 (19:09:48 UTC), con
`reports/analisi/validazione_banco_eace4d03_2026-10-09/invii/registro.py leggi-stato`, e lo ha salvato com'è
([stato](../../reports/analisi/validazione_banco_eace4d03_2026-10-09/invii/stati/status_LJmnhqqh1WTrx1JcoRlr_20261009T190948Z.json)).
Lo stesso comando ha scritto il [confronto](../../reports/invii/prediction_t38_2026-10-09/comparison.json)
applicando la regola della [previsione](../../reports/invii/prediction_t38_2026-10-09/prediction.json), il cui file
è entrato nel repository alle 22:57 UTC dell'8 ottobre, prima della creazione dell'entry (17:35 UTC del 9).

## 3. Cosa si è osservato

**Misurato**, dallo stato pubblicato: t38 = **0,14892212354470022**, rango 477 alla lettura; t36 =
0,14724935991548274; differenza **+0,0016727636**. Stesso pannello (`vcc2026-val-1`) e stesse ancore del t36; la
media dei sei scalati coincide con il punteggio; nessun membro imputato.

| Membro scalato | t38 | Differenza da t36 |
|---|---:|---:|
| PDS | 0,639060 | +0,007994 |
| MSE | 0 | 0 |
| NMAE | 0,075503 | +0,003864 |
| Fedeltà | −0,013123 | −0,003602 |
| Reach | 0,188693 | +0,002130 |
| Jaccard | 0,003400 | −0,000349 |

- **Regola registrata:** ramo `delta_within_plus_minus_0.005`, «Inconclusive against t36; added coverage does not
  establish improvement». Il punteggio sta nella banda registrata 0,132…0,162.
- **Massimo osservato:** è il più alto fra i punteggi ufficiali registrati (il precedente era t36).
- **Che cosa aveva detto il banco prima:** T3 non è una ricetta dello stadio 100 e il banco non ha potuto rifarlo
  sui fold; dalla sola scheda tecnica degli effetti VALIDAZIONE aveva scritto, prima della generazione,
  «indistinguibile da t36 entro ±0,005», senza un verso
  ([messaggi dell'8–9/10](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/MESSAGGI.md)). L'esito
  sta in quella banda ([registro](../../reports/analisi/validazione_banco_eace4d03_2026-10-09/invii/RAPPORTO_INVII_r1.md)).

## 4. Interpretazione e incertezza

**Misura:** +0,0017 su un invio. È dello stesso ordine dell'unica differenza misurata fra due semi dello stesso
candidato (t24 − t22 = +0,0016) e sta sotto la soglia operativa di 0,005.
**Interpretazione:** per la regola scritta prima, l'esito non stabilisce un miglioramento. Il movimento è
soprattutto del PDS (+0,008 scalato), con la fedeltà in lieve calo; anche in t36 − t28 il PDS saliva di 0,009 e la
fedeltà scendeva, mentre NMAE e reach si muovevano in modo diverso
([confronto del t36](../../reports/invii/prediction_t36_2026-10-06/comparison.json)).
**Non si può dire:** quale parte del pacchetto conti. T3 differisce dal t36 per i 16 voti nuovi di T1, per i cinque
voti KO su 34 bersagli e per le 6.722 coppie previste dal solo KO a stima intera (segnalazione DT-5, dichiarata nel
testo dell'invio); nessun contrasto li separa, e nessuna di queste fonti è stata valutata su un fold.
**Ipotesi:** che i voti KO portino informazione trasferibile al CRISPRi. Non è misurata: il collegamento fra le
due modalità richiede il confronto descritto nel contratto v3, §3.

## 5. Spiegazione semplice

Abbiamo aggiunto alla ricetta alcuni esperimenti in cui il gene è distrutto invece che spento, contandoli un
quarto. Il voto è salito di un soffio, quanto può cambiare rifacendo lo stesso compito con altri dadi. È il voto
più alto che abbiamo, ma non dimostra che quegli esperimenti aiutino.

## 6. Conseguenze

- Il massimo ufficiale osservato diventa t38; lo riportano l'[indice degli invii](../../reports/invii/README.md) e
  il §0 di PROGETTO. Quale file sia la consegna è una decisione del Lead e del proprietario: per la regola
  registrata il riferimento resta t36, e nessuna promozione stabile segue da un delta sotto soglia.
- Nessuna taratura numerica del banco: il registro conta una previsione di banco per t38, senza segno.
- Prossimo passo informativo sul transfer: un contrasto che separi i voti KO dal resto, su fold a lignaggio
  escluso, prima di un altro invio della stessa famiglia.

## 7. Cosa corregge

Nessuna conclusione. Aggiorna lo stato scritto in [CP-0071](0071-corsia-rapida-senza-invio-priorita-alle-reti.md)
(«t38 non inviato»): quell'invio è stato ripreso e fatto il 9 ottobre sera.

## 8. Domanda di comprensione

Perché un nuovo massimo osservato non basta a dire che i voti KO migliorano la ricetta?
