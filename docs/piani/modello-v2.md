# R-V2 — il modello per il set finale, costruito adesso

- **Stato:** in corso.
- **Aggiornato:** 26 settembre 2026, 00:20 (ora italiana).
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
| F1 | Cache "universo": effetti di **tutti** i bersagli di ogni sorgente locale (K562 genome-wide, HepG2), non solo dei 300 | Claude | in corso | cache nuova nella radice dati, report con copertura |
| F2 | Banco con lo scorer vero su un contesto pubblico tenuto fuori (HepG2 a cellule singole): i sei membri, non proxy | Claude; job Colab `046_bench_hepg2_v2` in coda su Drive dal 26/09 00:17, parte quando il proprietario avvia le celle 1–2 del notebook | in coda | report con ancore locali: t16/t19/t20 e ampiezze in forma solo-K562 |
| F3 | Motore di valutazione C/T/J e basi di confronto (nullo, risposta comune, trasferimento, modello lineare con embedding dei geni) | codex, run `20260926-001005-v2-f3-ctj`: fermato dopo 3 min per quota ChatGPT esaurita, ha lasciato un `ctj.py` parziale non applicato; il prosieguo lo fa Claude | in corso | patch rivista e test |
| F4 | Modulo cis e pesi per contesto nel modello d'invio | Claude | cis fatto (t20) | t20 registrato |
| F5 | Descrittori dei bersagli nuovi: STRING, CORUM, GO, reti TF con segno, embedding di proteine | libero | serve il via ai download | tabelle sull'asse ufficiale |
| F6 | Contesti: stato dai controlli (p53, IFN, ciclo, linea) e somiglianza con le sorgenti | libero | aperto | pesi per contesto provati sul banco |
| F7 | Calcolo in cloud: ambiente, dati, esecuzione di F2 e degli addestramenti | ingegneri | serve l'autorizzazione | ambiente riproducibile |
| F8 | Prova generale del 22 ottobre: 300 bersagli finti e contesti tenuti fuori, dall'input al .vcc | libero | dopo F1-F3 | tempo e copertura misurati |

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
