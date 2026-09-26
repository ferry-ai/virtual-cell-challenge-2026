# R-V2 — il modello per il set finale, costruito adesso

- **Stato:** in corso.
- **Aggiornato:** 26 settembre 2026, 15:15 (ora italiana).
- **Assegnazione:** regia e filoni F1, F2 e F4: Claude (app, sessione `f4f38e58`), dal
  26/09 alle 00:20. Filone F3: codex via agent hub, lancio annotato qui sotto. Gli altri
  filoni sono liberi: prenderli annotando agente, sessione e ora in questa scheda.
- **Origine:** richiesta del proprietario del 25/09 notte: le architetture di lungo periodo
  si applicano adesso, con molti agenti, due ingegneri a tempo pieno e calcolo in cloud.
- **Rapporto con le altre schede:** esegue ciò che [R-MODELLI](trasferimento-modelli.md)
  proponeva; usa i dati di [R-DATI](dati-affidabilita.md); i punteggi ufficiali restano in
  [S-INVII](invii-finale.md).

## Obiettivo

Un modello che predice la risposta a un knockdown CRISPRi in un contesto nuovo (D/E/F) per
bersagli nuovi, con componenti biologiche esplicite, scelto su un banco che calcola i sei
membri ufficiali con lo scorer vero su contesti pubblici tenuti fuori. Il 22 ottobre deve
produrre un invio in poche ore.

## Architettura di destinazione

`effetto(t, c) = trasferimento(t, c) + cis(t) + programmi(z_t, z_c) + residuo`, dove:
- **trasferimento:** l'effetto dello stesso bersaglio misurato in altre sorgenti, ristretto
  per affidabilità, pesato per somiglianza fra contesti (H6) invece che a pesi uguali;
- **cis:** la repressione CRISPRi dei geni vicini al TSS, già nel t20
  ([banco](../../reports/modulo_cis_2026-09-26/RISULTATI.md));
- **programmi:** per i bersagli che nessuna sorgente ha misurato, coordinate sui programmi
  predette da descrittori del bersaglio (reti, complessi, embedding), modulate dallo stato
  del contesto letto dai controlli. La proiezione lineare dell'effetto trasferito sui
  programmi è già stata provata e perde
  ([programmi](../../reports/programmi_2026-09-26/RISULTATI.md)): i programmi servono dove
  manca l'effetto del bersaglio, non al posto del dettaglio misurato;
- **emissione:** un generatore di cellule calibrato sui controlli del contesto.

## Filoni

| ID | Filone | Chi | Stato | Consegna |
|---|---|---|---|---|
| F1 | Cache "universo": effetti di **tutti** i bersagli di ogni sorgente, non solo dei 300 | Claude | K562 fatto (9.866 bersagli, [report](../../reports/universo_2026-09-26/RISULTATI.md)); CD4 e Orion aspettano il via ai download | cache nella radice dati, report con copertura |
| F2 | Banco con lo scorer vero su un contesto pubblico tenuto fuori (HepG2 a cellule singole): i sei membri, non proxy | Claude; job Colab `046_bench_hepg2_v2` in coda su Drive dal 26/09 00:17, parte quando il proprietario avvia le celle 1–2 del notebook | in coda | report con ancore locali: t16/t19/t20 e ampiezze in forma solo-K562 |
| F3 | Motore di valutazione C/T/J e basi di confronto (nullo, risposta comune, trasferimento, modello lineare con embedding dei geni) | codex, run `20260926-001005-v2-f3-ctj`: fermato dopo 3 min per quota ChatGPT esaurita, ha lasciato un `ctj.py` parziale non applicato; il prosieguo lo fa Claude | in corso | patch rivista e test |
| F4 | Modulo cis e pesi per contesto nel modello d'invio | Claude | cis fatto (t20) | t20 registrato |
| F5 | Descrittori dei bersagli nuovi: STRING, CORUM, GO, reti TF con segno, embedding di proteine | libero | serve il via ai download | tabelle sull'asse ufficiale |
| F6 | Contesti: stato dai controlli (p53, IFN, ciclo, linea) e somiglianza con le sorgenti | Claude (H6 su Mixscale) | somiglianza basale intera: non predice il trasferimento e pesarla peggiora ([report](../../reports/contesti_2026-09-26/RISULTATI.md)); restano aperte somiglianze per programma o per bersaglio | pesi per contesto provati sul banco |
| F7 | Calcolo in cloud: ambiente, dati, esecuzione di F2 e degli addestramenti | ingegneri | serve l'autorizzazione | ambiente riproducibile |
| F8 | Prova generale del 22 ottobre: 300 bersagli finti e contesti tenuti fuori, dall'input al .vcc | libero | dopo F1-F3 | tempo e copertura misurati |

## Esiti della notte del 26 settembre

- **Bersagli nuovi** ([report](../../reports/bersagli_nuovi_2026-09-26/RISULTATI.md)): per un
  bersaglio che nessuna sorgente ha misurato, il modulo cis da solo dà 0,555–0,579 di PDS proxy
  e 0,1 × STRING + cis fino a +0,035; lo stesso bersaglio misurato in K562 dà 0,711–0,755. Il
  modello lineare con embedding dei geni non discrimina nemmeno in campione.
- **Priorità che ne segue:** la copertura. Estrarre tutti i bersagli delle sorgenti genome-scale
  (CD4: file pseudobulk di 44,6 GB su S3 pubblico; Orion HCT116 e HEK293T: 109 e 223 file in
  streaming, accumulatori troppo grandi per il portatile) vale più di qualunque modello per
  bersagli senza misure. Poi cis + associazione per quelli che restano scoperti.
- **Ripiego per i bersagli scoperti, nello stadio 100:** blocco `association` (0,1 × media dei
  partner STRING nella cache universo, gene proprio di ogni partner escluso) prima del modulo
  cis; identico bit per bit sui 300 bersagli di oggi, provato con una ricetta solo-K562 (13 dei
  28 bersagli scoperti hanno partner).

## Esiti del pomeriggio del 26 settembre

- **Architettura a due canali** ([report](../../reports/trasferimento_appreso_2026-09-26/RISULTATI.md)):
  la direzione specifica del bersaglio viene dal trasferimento (t20); un modello di gradient
  boosting, addestrato solo su sorgenti pubbliche, impara quali geni si muovono in ogni contesto e
  ripesa il trasferimento (`src/vcc2026/transfer_model.py`, stadio 104; `src/vcc2026/priors.py`
  spostato dallo stadio 100, uscita identica bit per bit). r3/r4 davano +0,008…+0,010 di PDS
  attraverso il generatore, ma l'[audit di codex](../../reports/audit_piani_dati_2026-09-26/RISULTATI.md)
  ha trovato centri calcolati prima degli split (R-019). **Nel banco isolato (r5) il guadagno sulle
  linee nuove scende a +0,004…+0,008 (un intervallo su tre sopra zero) e l'nMAE proxy peggiora di
  +0,017…+0,051: per la regola fissata prima, niente t21.** Lo stadio 104 resta sperimentale,
  fuori dalla pipeline d'invio; la sua sorte si decide sul banco F2 con lo scorer vero.
- **Risposta comune** ([report](../../reports/risposta_comune_2026-09-26/RISULTATI.md)): la parte di
  risposta condivisa da tutti i knockdown vale l'1–14 % dell'energia nelle sorgenti pubbliche e non
  si trasferisce fra linee (correlazione 0,05–0,11); aggiungerla non abbassa l'errore quadratico.
  La `mse` ufficiale non si recupera da lì.
- **Pesi per contesto:** né la somiglianza del profilo basale (H6) né lo stato di p53 letto dai
  controlli migliorano in modo coerente ([contesti](../../reports/contesti_2026-09-26/RISULTATI.md)).
- **Agenti:** revisione di codex (due perdite trovate e corrette), critica di claude2, letteratura
  di grok, dataset di antigravity: in `reports/trasferimento_appreso_2026-09-26/agenti/`. La sessione
  `76a3a45e` lavora in parallelo sui prior dei bersagli nuovi.

## Domanda strategica aperta

Le squadre in testa hanno PDS 0,82–0,87 con mse 0,6–0,85, molto oltre quello che il trasferimento
da linee diverse ci ha dato finora. Una spiegazione possibile (**ipotesi**, non verificata) è
l'uso di dati pubblici della **stessa linea** dei contesti, dopo averla identificata. Per D/E/F
significherebbe: identificare le tre linee dai controlli (lo stadio 99 fa impronte genetiche),
cercare Perturb-seq pubblici di quelle linee, trattarli come sorgenti. La regola del proprietario
ammette dati della stessa linea solo come esperimento dichiarato, con le identità fuori dal
repository pubblico: serve la sua decisione su se e come farlo.

## Che cosa serve dal proprietario

- Login di claude2 sull'account 2 e di grok: `hub.py doctor` del 26/09 alle 00:10 dà
  claude2 sull'account principale e grok senza login.
- Autorizzazione del calcolo: connettore RunPod (da autorizzare nelle impostazioni dei
  connettori) oppure Colab.
- Via ai download di F5 e delle sorgenti nuove, con dimensioni e licenze prima di scaricare.
- Via agli invii: nessun filone invia da solo.

## Protezioni

Valgono [GENERALIZZAZIONE](../GENERALIZZAZIONE.md) e D-044: nei regimi T/J nessuna risposta
dei bersagli di test entra in training, basi, embedding o pesi. Un proxy non è un punteggio.
Ogni affermazione su un dataset va controllata da una seconda famiglia di modelli prima di
arrivare al proprietario.

## Criterio di chiusura

Un modello scelto sul banco F2 con regola registrata prima, pronto a produrre un invio D/E/F
in poche ore, e un checkpoint che confronta i filoni con il t20.
