# R-LEAD — imparare risposte trasferibili a contesti nuovi

- **Subentro Codex, aggiornamento 4/10 18:34 CEST (ora letta da sistema):** chat `01a107a9-9c9c-76c2-9161-258f22bd57b1`, macchina
  `LAPTOP-DLG1LHV1`, da `d16094d`, consegna finale `8aa1a0a` riletta. Il proprietario conferma in chat:
  «Claude ha concluso: subentra tu». Perimetro: continuazione dei job CD4 e preparazione del banco v2
  sulle reti esistenti, nella nuova cartella [ripresa_banco_v2](../../reports/generatore_e_banchi/ripresa_banco_v2_2026-10-04/README.md).
  Stati remoti e quote riletti; sette parti CD4 ancora RUNNING, nessuna duplicata. Output nuovi nella radice dati
  `processed/ripresa_banco_v2_2026-10-04/`. Push e invii non autorizzati; nessun training avviato.
  Aggiornamento delle 19:36: proprietario autorizza «Sì, lancia i cinque banchi CPU»;
  cinque banchi riletti RUNNING, incluso K562 r2 dopo riparazione del controllo di copertura;
  nessun risultato scientifico ancora letto. Tutte le dodici unità CD4 verificate e riconciliate
  alla specifica; integrazione e uso nel training restano aperti. Incidenti D3_Rest e K562 registrati.
  Evidenza, limiti e prossimo passo nello [stato della ripresa](../../reports/generatore_e_banchi/ripresa_banco_v2_2026-10-04/STATO_1936.md).

- **Sottoattività Codex, 4/10 12:28 CEST:** chat `01a10649-0c7f-7551-8bfe-8eca0fe03654`, macchina `LAPTOP-DLG1LHV1`, partenza `1309914`, su mandato del proprietario: audit informativo del prepasso e piano del prossimo ibrido in [prossimo_ibrido_2026-10-04](../../reports/analisi/prossimo_ibrido_2026-10-04/README.md). Riconti e fixture locali completati; piano proposto, da congelare dopo diagnosi di Claude1 e bilancio del corpus ampliato. Perimetro: sola nuova cartella e proprie righe negli indici/scheda; nessun job avviato, nessuna modifica al prepasso altrui. Claude1 mantiene chiusura ufficiale t30, diagnosi banco/export e propri job; [consegna pronta](../../reports/analisi/prossimo_ibrido_2026-10-04/PROMPT_CLAUDE1.md).
- **PASSAGGIO DI CONSEGNE della sessione Claude `ba9b8bcb` a Codex, 4/10 18:08 CEST (ora letta con `date`; da
  leggere per primo; i job si rileggono su Kaggle prima di agire).** Il proprietario ha detto in chat che il lavoro
  passa a Codex. Ultimo commit della sessione: quello che contiene questa nota. 21 commit locali non pubblicati prima
  di questo: **il push non è stato autorizzato** e resta da chiedere.
  - *Chiuso e committato:* t30 ([CP-0064](../checkpoints/0064-t30-ibrido-selettivo-punteggio-ufficiale.md)); confronti
    controllati e taratura del rumore ([CP-0065](../checkpoints/0065-d056-confronti-e-rumore-del-banco.md),
    [esito](../../reports/modelli/diagnosi_t30_2026-10-04/ESITO_CONFRONTI.md)); S-009, ERRORI, PROGETTO §0, AMBITI §2 e
    §5 aggiornati. Da leggere insieme: [resoconto](../../reports/modelli/diagnosi_t30_2026-10-04/README.md),
    [addendum](../../reports/modelli/diagnosi_t30_2026-10-04/ADDENDUM_1451.md) con le due correzioni di Codex accolte.
  - *Che cosa è misurato e serve al prossimo training:* il guadagno di banco D-056 a un seme e 32 cellule aveva
    deviazione standard 0,007–0,045, quanto i guadagni; su 5 semi e 400 cellule vale +0,004…+0,031 (media +0,013),
    risolto in tre linee su cinque su entrambe le baseline; il fold HepG2 (quello del t30) perde PDS, −0,129 ± 0,005;
    la procedura dell'invio dà la stessa correzione del banco sugli stessi bersagli; la quota comune alta dell'invio
    viene dai bersagli del pannello (transfer debole, 5 fonti). La causa della perdita **sul sito** resta un'ipotesi.
  - *Strumento pronto, mai eseguito su dati veri:*
    [banco v2](../../reports/generatore_e_banchi/banco_v2_2026-10-04/README.md) (`bench_v2.py`: bracci come file di
    effetti nel formato dello stadio 100, 400 cellule, 5 semi, un flusso casuale per bersaglio condiviso fra i bracci,
    emissione `t25` o `t28`, differenze appaiate con `--pair`). Non ha ancora un launcher Kaggle: quello delle corsie
    diagnostiche (`reports/modelli/diagnosi_t30_2026-10-04/kaggle_diag.py`) è il modello da cui copiarlo. Proposta
    fatta al proprietario e **non autorizzata**: usarlo sulle cinque reti D-056 esistenti per scegliere il fold con
    guadagno risolto e PDS non in perdita, come base del confronto con il nuovo training.
  - *Job letti su Kaggle alle 18:08, tutti RUNNING, tutti CPU, nessuna GPU usata da questa sessione:*
    - `davideferrante11`: `vcc-cd4-d3-stim48hr-p{0,1}of2-r1`;
    - `davidmaisterx` (token in `~/.kaggle`; codice d'ingestione replicato come dataset privato
      `vcc-ingest-code-cd4-r1`, stesso sha256 `37986c85…`, stage `kaggle_code_cd4_r1_mx`):
      `vcc-cd4-d4-stim48hr-p1of2-r1` (p0 conclusa), `vcc-cd4-d4-stim8hr-p{0,1}of2-r1`, `vcc-cd4-d4-rest-p{0,1}of2-r1`.
    La coda di `fill_sessions.py` è esaurita. Un comando di attesa in background di questa sessione muore con essa:
    non lancia niente da solo.
  - *Verificate oggi:* CD4 `D2_Stim8hr`, `D2_Stim48hr`, `D3_Rest` (p1 rilanciata come r2 dopo l'`IncompleteRead`,
    **incidente ancora da registrare nel registro degli incidenti**), `D3_Stim8hr`
    (`reports/sorgenti/ingestione_completa_2026-10-03/cd4/esito_verifica_*`).
  - *Da fare a parti finite* (dalla cartella `kaggle_cpu`, con il Python del venv e
    `C:/Users/ferra/vcc2026-data/.venv/Scripts` nel PATH, altrimenti `kaggle` non si trova): quattro verifiche con
    `build_parts_verify.py --units cd4_<file>=<righe> --parts <p0> <p1> --slug vcc-cd4-<file>-verify-r1 --launch-log
    lancio_cd4_r1.jsonl`; righe dalla specifica: `D3_Stim48hr` 2.607.532 (account `davideferrante11`); `D4_Rest`
    2.693.903, `D4_Stim8hr` 2.727.254, `D4_Stim48hr` 2.815.784 (account `davidmaisterx`, `--config-dir ~/.kaggle
    --owner davidmaisterx`, perché una verifica monta le parti del proprio account). Poi i gemelli compatti delle
    unità verificate e, per un training che monti D4 da `davideferrante11`, la condivisione fra account.
  - *Vincoli del proprietario detti in chat oggi:* GPU solo su `davidmaisterx` (30 h; l'altro account «non è
    verificato»); «puoi anticipare tutto quello che vuoi» valeva per questa sessione, una sessione nuova lo conferma.
  - *Aperto:* protocollo e codice del nuovo training (piano di Codex: correzione semplice sulla ricetta t28, con e
    senza contesto); pre-passo del corpus ampliato, da profilare; il generatore dello stadio 45 usa ancora un solo
    flusso casuale (un confronto fra due invii contiene un cambio di realizzazione).
- **Sottoattività Claude1, 4/10 13:15–14:10 CEST (ore lette con `date`):** Claude Code, sessione `ba9b8bcb`, macchina
  `LAPTOP-DLG1LHV1`, partenza `a6f7dd2`, su consegna del proprietario
  ([PROMPT_CLAUDE1](../../reports/analisi/prossimo_ibrido_2026-10-04/PROMPT_CLAUDE1.md)). Perimetro: la cartella nuova
  [diagnosi_t30](../../reports/modelli/diagnosi_t30_2026-10-04/README.md), il checkpoint CP-0064 e le proprie righe in
  indici, STRADE, ERRORI, PROGETTO §0, AMBITI §2 e §5.
  - *Fatto:* chiusura del t30 ([CP-0064](../checkpoints/0064-t30-ibrido-selettivo-punteggio-ufficiale.md): 0,135249,
    −0,004989 contro il t25, ramo b, nessuna promozione; il numero 0063 citato nel passaggio delle 12:30 non esiste);
    catena dell'invio riletta e integra; tabella training → banco → esportazione → generazione; difetti riprodotti
    distinti dalle ipotesi (baseline diversa, quota comune 0,62–0,69 all'esportazione, PDS già in perdita sul fold
    esportato, JAC locale di K562, flusso casuale unico, bersagli del pannello assenti dal banco su tre linee).
    La causa della perdita non è isolata.
  - *Pronto e non eseguito:* confronti controllati sulle corsie B
    ([protocollo](../../reports/modelli/diagnosi_t30_2026-10-04/PROTOCOLLO_CONFRONTI.md) congelato a `8f9118c`,
    launcher provato a secco): cinque kernel Kaggle CPU, **serve il via del proprietario**. Il §8 aggiunge il braccio
    fedele: R calcolata dalla procedura di esportazione sui controlli della linea esclusa, stessi bersagli e pesi.
  - *Job riletti su Kaggle alle 13:18, `davideferrante11`, senza lanciare niente:* `vcc-cd4-d3-rest-p0of2-r1` in corsa;
    `vcc-cd4-d3-rest-p1of2-r1` in ERROR (da rilanciare come r2 e da registrare fra gli incidenti); `D2_Stim8hr` e
    `D2_Stim48hr` completi nelle due parti, da verificare. Questa sessione non ha l'autorizzazione autonoma della
    `2b35612c`: rilanci, verifiche su Kaggle, push e invii attendono il via in chat.
  - *Aggiornamento delle 17:55 (via del proprietario in chat: corsie diagnostiche alle 14:53, poi «puoi anticipare
    tutto quello che vuoi»):* confronti eseguiti e letti, [CP-0065](../checkpoints/0065-d056-confronti-e-rumore-del-banco.md)
    ed [esito](../../reports/modelli/diagnosi_t30_2026-10-04/ESITO_CONFRONTI.md): banco a un seme rumoroso quanto i
    guadagni; su 5 semi e 400 cellule +0,013 di media; il fold HepG2 perde PDS; procedura dell'invio fedele.
    Dati: verificate CD4 `D2_Stim8hr`, `D2_Stim48hr` e `D3_Rest` (p1 rilanciata come r2); in corsa alle 17:55 su
    `davideferrante11` `D3_Stim48hr` p0–p1 e la verifica di `D3_Stim8hr`, su `davidmaisterx` (codice replicato come
    dataset privato, stesso sha256) `D4_Stim48hr` p0–p1, `D4_Stim8hr` p0–p1, `D4_Rest` p0; resta `D4_Rest` p1, da
    lanciare su `davidmaisterx` perché l'unità resti su un account. GPU: solo `davidmaisterx` (indicazione del
    proprietario); nessuna usata.
  - *Per Codex:* vincoli per il prossimo protocollo nel §3 e §5 del resoconto; nessun file di
    `prossimo_ibrido_2026-10-04/` è stato toccato.
- **Mandato:** prevedere come rispondono linee mai viste perturbate partendo dai soli controlli, e scegliere il modello
  con prove C/J su linee escluse intere; unico percorso operativo di R-COMP (D-052). **Mandato non negoziabile del
  proprietario (D-053):** tutte le linee e i contesti idonei nel percorso principale, secondo
  [GENERALIZZAZIONE §2.1](../GENERALIZZAZIONE.md#21-copertura-integrale-vincolo-non-negoziabile); i pilot ridotti
  restano dichiarati e non lo sostituiscono.
- **Direzione adottata (D-054, 3/10 sera):** la rete ancorata al transfer, adattamento dell'idea di X (secondo
  classificato 2025): basale dai controlli + effetto trasferito dalle altre linee (l'ancora, dagli aggregati) +
  correzione appresa sulle singole cellule. Il transfer t22/t25 resta il riferimento di produzione e una componente;
  ESM2 è un confronto successivo, a parità di dati. Fonti: [proposta Codex](../../reports/analisi/candidato_ibrido_2026-10-03/README.md),
  [lezioni 2025](../../reports/analisi/lezioni_vcc2025_2026-10-03/README.md),
  [revisione delle ancore](../../reports/analisi/revisione_ancorata_codex_2026-10-03/README.md),
  [diagnosi dei training v3](../../reports/modelli/rete_ancorata_v4_2026-10-03/diagnosi_r1/DIAGNOSI.md).
- **Stato (3/10, 23:15 CEST):** in corso su due binari. Lo stato scritto qui non prova che un job sia vivo: si rilegge
  su Kaggle prima di agire (PIANI §3).
  - **Modello, pilot v4** ([protocollo](../../reports/modelli/rete_ancorata_v4_2026-10-03/PROTOCOLLO.md), congelato a
    `ec580c6`, emendamento §10 a `953eb1e`, entrambi prima dei training): batch bilanciati a ogni passo, gemelli
    compatti degli shard, budget separati, ancore a medie J da tutti gli aggregati del cubo. Training
    `rcell-v4-train-h1-r1` e `rcell-v4-train-hepg2-r1` in esecuzione dalle 23:06
    ([lancio](../../reports/modelli/rete_ancorata_v4_2026-10-03/lancio_train_r1.json)); RPE1 quando una delle due
    sessioni GPU si libera. La v3 r1 è un pilot incompleto (H1 tecnicamente non accettabile), non una bocciatura.
  - **Dati, integrazione di tutti i contesti (D-053), indipendente dall'esito del pilot:** esecuzione in
    [R-LAB](piano-giorno-2026-09-30.md) (le quattro parti Orion che completano HCT116 e HEK293T in corsa dalle 23:08,
    [log di lancio](../../reports/sorgenti/ingestione_completa_2026-10-03/kaggle_cpu/lancio_orion_r2.jsonl));
    inventario riconciliato del catalogo, aggregati mancanti e campioni annidati in [R-DATI](dati-affidabilita.md).
- **Assegnazione:** Claude Code, sessione «Integrazione Codex e piano operativo» (`5eacdf`), macchina
  `LAPTOP-DLG1LHV1`, dal 3/10 21:47 CEST (commit di partenza `8f43310`), su richiesta del proprietario in chat, con
  l'autorizzazione dei job necessari al piano su Colab e Kaggle entro quota. Perimetro: questa scheda, PIANI,
  PROGETTO §0, AMBITI, REGISTRO, `reports/modelli/rete_ancorata_v4_2026-10-03/`, dati in
  `processed/rete_ancorata_v4_2026-10-03/`, regia dei job del binario dati che il piano richiede. Fuori perimetro:
  `adattatori_codex/` e i file non tracciati di altre sessioni. Le sessioni `22d21f` e `c7c07a` risultano inattive.
  **Subentro, 3/10 23:34 CEST:** Claude Code, sessione `d0100a`, stessa macchina, commit di partenza `c86f6ed`, su
  richiesta del proprietario in chat («Continua il compito dell'agente precedente», con il messaggio di passaggio della
  `5eacdf`, chiusa). Stesso perimetro e stesse destinazioni degli output; job riletti su Kaggle alle 23:32 prima di
  agire (cinque in corsa, `vcc-orion-hek293t-p2of8-r3` concluso), quota GPU 12,14 h residue alle 23:34.
- **Prossimo passo:**
  1. Leggere le ricevute tecniche dei training H1 e HepG2 con `fetch_outputs.py`, senza file di valutazione, e
     l'accettazione del §5 del protocollo; lanciare RPE1 con il comando del lancio.
  2. Per ogni linea accettata: generazione delle cellule (`kaggle_gen.py`, CPU), corsia A (`bench_effects.py`) e
     corsia B (`lane_b.py`); poi `decide_anchored.py`, che applica la regola del §7 e il requisito di promozione del
     §10.4 (battere anche `transfer_prod_J`).
  3. Binario dati: verifica di linea di HCT116 e HEK293T a parti finite (`build_orion_verify.py`), poi le parti CD4;
     inventario riconciliato del catalogo e aggregati per le voci senza tabella (R-DATI); campioni annidati
     32/64/128 con perdita d'informazione misurata contro i riassunti completi, letti dai gemelli.
  4. Qualunque sia l'esito del pilot, il corpus ampliato (prima CD4T, HCT116, HEK293T con cellule verificate) entra nel
     protocollo successivo; ESM2 dopo, a parità di dati e di campione.
- **PRIORITÀ DAL 4/10 02:20 (mandato del proprietario alla sessione `2b35612c`): D-056.** Implementare, addestrare e
  valutare l'ibrido selettivo `T + w·R` (transfer congelato, correzione neurale regolarizzata, selettore validato su
  predizioni fuori fold); intanto chiudere il pilot v4 (RPE1, regola §7, checkpoint) e proseguire il binario dati
  D-053. Protocollo, codice e lanci in `reports/modelli/ibrido_selettivo_2026-10-04/` (in scrittura); autorizzazioni
  della notte, compresa la regola degli invii autonomi con banco ≥ 0,100, trascritte in
  [autorizzazioni](../../reports/invii/trial_2026-09-22/autorizzazioni.md#mandato-d-056-e-invii-autonomi-notte-del-4-ottobre-r-lead-sessione-claude-2b35612c).
  - **Subentro, 4/10 02:20 CEST:** Claude Code, sessione `2b35612c`, macchina `LAPTOP-DLG1LHV1`, commit di partenza
    `3758743`. Perimetro: questa scheda, PROGETTO §0, AMBITI §5, STRADE, le proprie righe di REGISTRO, la cartella
    nuova dell'ibrido, la chiusura v4 in `reports/modelli/rete_ancorata_v4_2026-10-03/`, la regia dei job del binario
    dati (ingestione, campioni). Fuori perimetro: `adattatori_codex/`, `libera_spazio_2026-10-04/`,
    `revisione_ancorata_codex_2026-10-03/ADDENDUM_1615.md` (Codex, processo attivo), `t29_keep_awake*.json`.
  - **Job riletti su Kaggle alle 02:23** (non dedotti dal passaggio sotto): in corsa GPU `rcell-v4-train-rpe1-r1`, CPU
    `rcell-v4-fast-hek293t-a-r2`, `vcc-cd4-d1-stim48hr-p{0,1}of2-r1`; conclusi i gemelli KOLF e HCT116, le corsie H1 e
    HepG2, la generazione HepG2, le parti CD4 `D1_Stim8hr`, lo studio `nested-h1-r1`. Quota GPU `davideferrante11`
    8,01 h, altri due account 30 h. Lanciati: `vcc-cd4-d1-stim8hr-verify-r1` (02:26) e `rcell-prepass-jurkat-r1`
    (02:38, pre-passo della linea di conferma dell'ibrido, scelta prima di ogni risultato D-056).
  - **PASSAGGIO DI CONSEGNE della sessione `2b35612c`, 4/10 12:30 CEST (da leggere per primo; i job si rileggono su
    Kaggle prima di agire).** Ultimo commit della sessione al momento della scrittura: `0898ba2`.
    - *Implementato ed eseguito:* ibrido D-056 v1. Protocollo congelato a `817f42a`, emendamenti §12–§14 scritti prima
      delle uscite che toccano; cinque training accettati; righe, corsie, selettore congelato, esportazione A/B/C
      (`reports/modelli/ibrido_selettivo_2026-10-04/`).
    - *Misurato, banco locale:* sviluppo e conferma passano; punteggio del §9 0,134 contro 0,090 del transfer
      ([CP-0062](../checkpoints/0062-d056-ibrido-selettivo-esito-banco.md), S-009). Fonti del transfer: «più fonti
      meglio» su Jurkat e K562, nessun candidato di solo transfer (S-010).
    - *Inviato:* t30 = effetti t25 + w · R della rete del fold HepG2, entry `lDMSYUZU5cFYHcRqI0lq`.
    - *Misurato, ufficiale:* 0,135249 (rango 460).
      - t30 − t25 = −0,004989: ramo b della regola registrata, non conclusivo, al confine del ramo c.
      - t30 − t28 = −0,0096.
      - PDS scalato −0,042 (coseno grezzo 0,763 contro 0,782), FID +0,014, JAC +0,002
        ([comparison.json](../../reports/invii/prediction_t30_2026-10-04/comparison.json)).
      - *Promosso:* nulla.
    - *Diagnostica esplorativa, letta dopo il punteggio (non una regola):*
      - su A/B/C la quota comune ai bersagli di R vale 0,63–0,70, e quella della correzione aggiunta 0,59–0,67; sulle
        righe C delle cinque linee valutate vale 0,13–0,26, negli effetti t25 0,001;
      - R è anche relativamente più ampio (RMS(R)/RMS(T) mediano ≈ 0,70 contro 0,24–0,42);
      - il banco aggiungeva R a `transfer_all_J`, il t30 al t25: è una discrepanza di baseline, un'ipotesi da misurare
        che anche la consegna di Codex segnala.
      - Il meccanismo resta ipotizzato: componente comune come in S-006, dominio dei contesti di gara, baseline.
    - *Chiusura del t30 ancora da fare* (PROCEDURE §2, punto 7): riga nell'indice degli invii, checkpoint CP-0063,
      aggiornamento di S-009, PROGETTO §0, AMBITI §2 e §5.
    - *Job alle 12:26, `davideferrante11`, CPU:*
      - `vcc-cd4-d3-rest-p0of2-r1` in corsa;
      - `vcc-cd4-d3-rest-p1of2-r1` in ERROR dopo 1.735 s per `http.client.IncompleteRead` nella lettura remota. Le
        ricevute arrivano fino a `D3_Rest_001900000_001920000`; il log è in
        `processed/ingestione_completa_2026-10-03/out_vcc-cd4-d3-rest-p1of2-r1_error/`. Va rilanciato come r2, e
        l'incidente va registrato nel registro degli incidenti;
      - complete e da verificare: CD4 `D2_Stim8hr` e `D2_Stim48hr` (entrambe le parti);
      - nessun processo locale attivo; la veglia del portatile è fermata.
      - Quote GPU: `davideferrante11` circa 2 h fino al 10/10; le altre due vanno rilette.
    - *Dati D-053:*
      - gemelli CD4 D1 (tre unità) verificati;
      - un kernel monta almeno 22 sorgenti (137,7 GB) in 5 s
        ([STATO](../../reports/sorgenti/prepasso_ampliato_2026-10-04/STATO.md));
      - il pre-passo pilota ha impiegato 2,9 h: prima lettura 0,6 h, fase globale centrale 1,85 h, seconda lettura
        0,4 h (`processed/rete_cellulare_2026-10-03/out_prepass_hepg2_r1/prepass/train_log.jsonl`). La fase centrale
        va strumentata prima di scegliere fra un pre-passo unico accelerato e quello diviso.
    - *Fuori perimetro, di altri:* `reports/analisi/prossimo_ibrido_2026-10-04/` (Codex: audit del pre-passo, piano
      del prossimo ibrido, consegna `PROMPT_CLAUDE1.md`), `adattatori_codex/`, `ADDENDUM_1615.md`,
      `t29_keep_awake*_stop.json`.
    - *Note:*
      - `submit_t30_raw.json` porta l'email dell'account nel percorso di storage, come i `submit_*_raw.json` già
        pubblici: da valutare dal proprietario;
      - invii del 4/10: 1 su 2;
      - push delle 12:33: `0106571..33c2bb2` pubblicati dopo la verifica dell'intera differenza in uscita. Sono 284
        file; nessun segreto, credenziale, identità di linea o file sopra 1,5 MB. L'unico riscontro è l'email nel
        percorso di storage di `submit_t30_raw.json`.
    - *Attività suggerita, in ordine:*
      1. Chiudere il t30 come sopra.
      2. Diagnosi controllata del t30, secondo `reports/analisi/prossimo_ibrido_2026-10-04/PROMPT_CLAUDE1.md` §2–3.
         - Prima si scrive un protocollo nuovo, con Precedenti S-006 e S-009 e un segnale precoce: quota comune di R
           all'esportazione > 0,5.
         - Poi, sulle corsie B esistenti e a pesi congelati, si confrontano tre bracci:
           a) `transfer_prod_J` + w · R, l'analogo del t30;
           b) `transfer_all_J` + w · R, il caso del banco;
           c) T + w · (R − R̄), con la media sui bersagli tolta per linea.
         - Si misura anche la quota comune di R per linea.
         - Un eventuale t31 (t25 + w · (R − R̄)) si invia solo se la regola passa, con la previsione registrata.
      3. Dati:
         - verifica di CD4 `D2_Stim8hr` e `D2_Stim48hr` (`build_parts_verify.py`);
         - rilancio r2 di `D3_Rest` p1;
         - coda con `fill_sessions.py --max 1` (10 parti) e gemelli delle unità verificate.
      4. Pre-passo del corpus completo: marcatori di tempo per fase, poi la scelta. La scheda suggerita alla sessione
         del 4/10 mattina è il pre-passo diviso; va coordinata con l'audit di Codex.
    - *Prompt di subentro:* «Continua il lavoro della sessione Claude `2b35612c` su VCC 2026 in
      `C:\Users\ferra\OneDrive\Desktop\vcc2026`. Leggi `CLAUDE.md`, `git status --short`, PROGETTO §0 e il passaggio di
      consegne della sessione `2b35612c` nella scheda R-LEAD (`docs/piani/strategia-scientifica.md`); rileggi i job su
      Kaggle prima di agire. Svolgi l'attività suggerita in ordine: chiusura del t30, diagnosi controllata con
      protocollo nuovo prima di leggere, dati D-053, pre-passo. Coordina con Codex
      (`reports/analisi/prossimo_ibrido_2026-10-04/`), non modificare i file di altre sessioni, committa solo i tuoi
      file per nome. Invii, push, nuovi download e calcolo cloud oltre i job già in corso richiedono il via del
      proprietario in chat.»
  - **Stato alle 10:40 (sessione `2b35612c`; i job si rileggono su Kaggle prima di agire).**
    - *Misurato, letto con le regole congelate:* D-056 v1 passa lo sviluppo («contributo neurale nello sviluppo») e la
      conferma («confermato» su Jurkat e K562). Il punteggio di banco del §9 è 0,134 per `ibrido_selettivo` contro
      0,090 del transfer, in scala locale e non uno score VCC
      ([CP-0062](../checkpoints/0062-d056-ibrido-selettivo-esito-banco.md), S-009). Fonti del transfer: «più fonti
      meglio» su Jurkat e K562; nessun candidato di solo transfer è ammesso (S-010).
    - *Invio t30 in preparazione:* il candidato A/B/C del §13–§14 è l'ibrido t25 + w · R, con la rete del fold HepG2 e
      il selettore congelato.
      - Previsione e testi registrati prima della generazione
        ([prediction.json](../../reports/invii/prediction_t30_2026-10-04/prediction.json)).
      - Effetti esportati con parità (`export_abc_r2`).
      - Generazione e pacchetto locali dalle 10:30 (`gen_t30.ps1`), poi l'upload come processo separato
        ([registro](../../reports/invii/trial_2026-10-04/INVIO_T30.md)).
    - *Dati D-053:* spinte le parti CD4 `D2_Stim48hr` p1 e `D3_Rest` p0 (11 in coda) e i gemelli di CD4 `D1_Stim8hr` e
      `D1_Stim48hr`. `D2_Stim8hr` p0 è ancora in corsa, poi va verificata. Cinque sessioni CPU di `davideferrante11`
      occupate.
    - *Prossimi passi:*
      1. stadio 48 finito → `submit_t30.ps1` (upload);
      2. a punteggio arrivato, status, `comparison.json`, checkpoint e riga nell'indice degli invii;
      3. dati: verifica di `D2_Stim8hr`, parti CD4 successive (`fill_sessions.py --max 1`), verifica dei gemelli D1.
  - **Stato alle 07:32 (sessione `2b35612c`, dopo una pausa dalle 04:27 alle 07:22 per il limite d'uso).**
    - *Misurato:* training D-056 H1 e HepG2 **tecnicamente accettati** (§10: 2,0 epoche, nessun arresto per guardia,
      quote effettive entro 0,006, stato esportato al passo 20.000). Sulle coppie di validazione interne delle linee di
      training la correzione migliora il rango di discriminazione (0,34–0,41 contro 0,43–0,47 dell'ancora), resta a
      0,55–0,72 dell'ampiezza dell'ancora, con componente comune 0,12–0,20 e beneficio +0,13 sul coseno. Righe delle
      linee escluse (sviluppo, già lette): correzione nella direzione del residuo nel 86 % (H1) e 67 % (HepG2) delle
      righe, peso ottimo mediano 0,24 e 0,21, errore quadratico +0,8 % e +0,4 % con la miscela fissa, −2,2 % e −6 % con
      peso 1 (`esito/rows_*_r1/` dell'[ibrido](../../reports/modelli/ibrido_selettivo_2026-10-04/PROTOCOLLO.md)).
      Studio dei campioni per fold di H1 letto con la regola congelata: il livello 64 è insufficiente, la decisione
      sul corpus ampliato è corretta ([DECISIONE_AGGIORNATA](../../reports/sorgenti/prepasso_ampliato_2026-10-04/DECISIONE_AGGIORNATA.md)).
    - *In corsa:* GPU `rcell-d056-train-rpe1-r1` (dalle 07:24, `davideferrante11`, quota 3,98 h prima del lancio);
      su `davidmaisterx` ancore `rcell-d056-anchors-conf-r1` (Jurkat e K562) ed estrazione K562; estrazione Jurkat
      conclusa (150 bersagli, 2.048 controlli). CPU di `davideferrante11`: `vcc-sampled-hct116-l64-r3` (prova tecnica
      del costruttore), `vcc-cd4-d2-rest-verify-r1`, `vcc-cd4-d2-stim8hr-p{0,1}of2-r1`.
    - *Prossimi passi:* ancore pronte → training `rcell-d056-train-{jurkat,k562}-r1` su `davidmaisterx` (comandi già
      provati a secco); RPE1 finito (verso le 09:20) → righe RPE1 → `selector.py lolo` e `final` → corsie delle tre
      linee di sviluppo → `decide_hybrid.py`; poi righe e corsie di Jurkat e K562 con il sistema congelato.
  - **Stato alle 03:54 e punto di ripresa (sessione `2b35612c`).**
    - *Fatto:* protocollo D-056 v1 congelato a `817f42a`, emendamento §12 sul selettore prima di ogni uscita;
      codice v5 con test (`cb0f3dc`, 13 + 5 test); pilot v4 chiuso, **non passa**
      ([CP-0061](../checkpoints/0061-pilot-v4-esito-tre-linee.md)); protocollo delle fonti del transfer congelato
      (`810a08d`); scorer 0.18.0 confrontato e suite della repo 290 OK con il venv
      ([report](../../reports/gara/scorer_0_18_2026-10-04/README.md)); CD4 `D1_Stim8hr` e `D1_Stim48hr` verificati;
      E-20261004-001 rev. 2; decisione sul pre-passo ampliato
      ([DECISIONE](../../reports/sorgenti/prepasso_ampliato_2026-10-04/DECISIONE.md)).
    - *In corsa su `davideferrante11`:* GPU `rcell-d056-train-{h1,hepg2}-r1` (dalle 03:00); CPU
      `rcell-prepass-jurkat-r1`, `vcc-cd4-d2-rest-p{0,1}of2-r1`, `rcell-v4-nested-fold-h1-r1`. Su `davidmaisterx`
      (catena replicata, [lancio](../../reports/modelli/ibrido_selettivo_2026-10-04/lancio_replica_r1.json)): gemelli
      `rcell-d056-fast-{a,b,c}-r1`, pre-passi `rcell-prepass-{k562,jurkat}-r1`.
    - *Push del 4/10, 04:10:* 161 commit pubblicati (`1f086cb..0106571`) dopo verifica dell'intera differenza in
      uscita. Esito: nessun segreto, token, URL firmato o file di credenziali; nessuna identità di linea accanto ad
      A/B/C; nessun nome di persona della classifica; nessun file sopra 1,5 MB. I `submit_*_raw.json` portano nel
      percorso di storage l'email dell'account, come gli altri file `vcc` già pubblici dal 13/9 (PROCEDURE §2.6): da
      valutare dal proprietario, non è un'esposizione nuova.
    - *Prossimi passi, in ordine:* (1) a training H1/HepG2 finiti, ricevute senza file di valutazione e accettazione
      (§10), poi `kaggle_hybrid.py --mode rows` per ciascuno e il training RPE1 con gli argomenti di
      `lancio_train_r1.json`; (2) pre-passo Jurkat finito → `kaggle_anchors.py kernel --line Jurkat=…` e
      `kaggle_extract.py`, poi il training Jurkat (GPU di `davideferrante11` se la quota basta, altrimenti la replica);
      (3) con le righe delle tre linee di sviluppo, `selector.py lolo` e `final` (sha256 del sistema congelato prima di
      ogni uscita di conferma), poi `kaggle_hybrid.py --mode lanes` per le tre linee; (4) K562 sulla replica: ancore,
      estrazione, training, righe e corsie con `selector.py apply`; (5) lettura con il §8 del protocollo, checkpoint e
      voce STRADE, ed eventuale invio con la regola del §9.
- **PASSAGGIO DI CONSEGNE della sessione `d0100a`, 4/10 02:02 CEST (da leggere per primo; i blocchi sotto sono la
  cronaca della notte). I job si rileggono su Kaggle prima di agire.**
  - **Esito finora del pilot v4 (misurato, due linee su tre):** la rete ancorata peggiora la propria ancora. Media
    locale dei sei membri, corsia B: H1 0,057 contro 0,272 di `transfer_all_J`; HepG2 0,162 contro 0,212. Corsia A,
    PDS delle righe C: H1 0,547 contro 0,965; HepG2 0,639 contro 0,886. Con due linee negative la primaria del §7 non
    può più passare e la guardia nemmeno. Training tecnicamente accettati (H1, HepG2). Evidenza in `esito/` del
    [report v4](../../reports/modelli/rete_ancorata_v4_2026-10-03/README.md) e voce S-006 di [STRADE](../STRADE.md).
  - **In corsa alle 02:02:** GPU `rcell-v4-train-rpe1-r1` (dalle 00:42; quota 8,36 h residue). CPU:
    `rcell-v4-fast-hek293t-a-r2`, `rcell-v4-fast-kolf-pan-r1` (01:26), `vcc-cd4-d1-stim48hr-p{0,1}of2-r1` (01:52,
    02:00). Una sessione CPU è lasciata libera per la generazione di RPE1.
  - **Per chiudere il pilot** (tutto dalla cartella v4, con il Python del venv, token `~/.kaggle-davideferrante11`):
    1. ricevute di RPE1 senza file di valutazione e accettazione §5 (comando di `fetch_outputs.py` più sotto);
    2. `kaggle_gen.py kernel … --held-group RPE1 --train-kernel rcell-v4-train-rpe1-r1 --prepass-kernel
       rcell-prepass-rpe1-r1 --anchors-kernel rcell-v4-anchors-r1 --anchors-dir anchors_RPE1_all --slug
       rcell-v4-gen-rpe1-r1` (controllare la risposta: la CLI esce 0 anche sul rifiuto);
    3. **corsie su Kaggle, mai sul portatile:** `kaggle_lanes.py --held-group RPE1 --train-kernel
       rcell-v4-train-rpe1-r1 --gen-kernel rcell-v4-gen-rpe1-r1 --real-kernel rcell-gen-rpe1-r3b --prepass-kernel
       rcell-prepass-rpe1-r1 --anchors-dir anchors_RPE1_all --slug rcell-v4-lanes-rpe1-r1 --launch-log
       lancio_lanes_r1.jsonl` (parità con il locale verificata su H1 a 4·10⁻¹⁶);
    4. scaricare nella radice dati i file di valutazione del training (`out_train_rpe1_r1`, come per H1) e le uscite
       delle corsie; `decide_anchored.py --line H1 <out_train_h1_r1/train> <laneA_h1_r1>
       <laneB_h1_r1/bench/scaled_local.csv> --line HepG2 <out_train_hepg2_r1/train> <out_lanes_hepg2_r1_b/laneA>
       <out_lanes_hepg2_r1_b/laneB/bench/scaled_local.csv> --line RPE1 … --out <nuova>` (cartelle in
       `processed/rete_ancorata_v4_2026-10-03/`);
    5. checkpoint con `scripts/30_new_checkpoint.py`, tipo `esperimento`, riga `- **Strade:** S-006`; aggiornare la
       voce S-006 (che deve citare il checkpoint), AMBITI §5 e PROGETTO §0 nello stesso commit. Il controllo dei
       documenti lo pretende (D-055).
  - **Indizio per la produzione, da verificare con una regola sua:** il transfer con più fonti batte quello delle
    quattro fonti della ricetta inviata sulle linee lette (sei membri: H1 0,272 e 0,280 contro 0,248; HepG2 0,212 e
    0,245 contro 0,141, per `transfer_all_J` e `transfer_cells_J` contro `transfer_prod_J`). È la leva più concreta
    sul punteggio ufficiale; un invio resta da autorizzare.
  - **Binario dati:** chiuse e verificate HEK293T, HCT116, CD4 `D1_Rest`. Gemelli conclusi: HEK293T parti 4–7 (111
    shard, 12,95 GB), HCT116 parti 0–1 e 2–3 (55 e 54 shard, 7,95 e 7,83 GB). Misurato: 10,9 GB di picco per
    processo su uno shard Orion da 200 milioni di valori, quindi due processi per kernel (E-20261004-001, da
    aggiornare con questa misura). Da fare: verifica per file di CD4 `D1_Stim8hr` (`build_parts_verify.py --units
    cd4_D1_Stim8hr=2789727 --parts vcc-cd4-d1-stim8hr-p0of2-r1 vcc-cd4-d1-stim8hr-p1of2-r1`), le 18 parti CD4 in coda
    (`fill_sessions.py --max 1` per volta), gemelli della terza ondata scPerturb, studio dei campioni per fold
    (`kaggle_nested.py --dispersion`, slug `rcell-v4-nested-fold-<linea>-r1`); lo studio esplorativo r1 è concluso e
    non letto, e non decide niente.
  - **Regole nuove di stanotte:** ciclo per imparare dagli errori (D-055, [STRADE](../STRADE.md): sezione
    «Precedenti» nei protocolli nuovi, riga «Strade» nei checkpoint); banchi e corsie nel cloud; scelta dei campioni
    per fold. Nessun nuovo training della nostra architettura senza un'ipotesi mirata e il suo protocollo
    (indicazione del proprietario: si attende anche il modello di Alfredo, riferito a circa 0,08 ufficiale, da mettere
    sul banco C/J a sei membri contro il transfer).
  - **Cartella condivisa:** Codex (`01a10414`) sta liberando spazio e ha i suoi file nell'indice git: committare solo
    con `git commit -- <percorsi>`; per `docs/REGISTRO.md` solo le proprie righe (AGENTI §3). 143 commit locali non
    pubblicati: il push va chiesto.
  - **Da riferire al proprietario:** il processo PID 2288 ancora attivo; lo scorer `cell-eval2` 0.18.0 esiste su PyPI
    e noi usiamo la 0.16.0; 30 ore GPU intere su ciascuno degli altri due account, ma gli input sono privati di
    `davideferrante11`; il pre-passo del corpus ampliato richiede prima una scelta su come alleggerirlo (sotto).
- **Stato della sessione `d0100a` (4/10, 00:09 CEST; i job si rileggono su Kaggle prima di agire):**
  - In corsa: i due training GPU (dalle 23:06 del 3/10); su CPU `vcc-orion-hct116-verify-r1` (23:59),
    `vcc-cd4-d1-rest-verify-r1` (00:04), `vcc-cd4-d1-stim8hr-p{0,1}of2-r1` (23:35) e lo studio dei campioni annidati
    `rcell-v4-nested-h1-r1` (23:52, [protocollo](../../reports/modelli/rete_ancorata_v4_2026-10-03/CAMPIONI_ANNIDATI.md)
    con la regola congelata prima dei numeri, [lancio](../../reports/modelli/rete_ancorata_v4_2026-10-03/lancio_nested_r1.json)).
  - Chiusa: HEK293T, 223 shard e 4.534.299 cellule come attese, sha256 riletti da un altro kernel
    ([ricevute](../../reports/sorgenti/ingestione_completa_2026-10-03/orion/esito_verifica_hek293t_r1/line_complete.json)).
  - Pronto e non ancora spinto: gemelli compatti degli shard lasciati negli output dei kernel (`kaggle_fast_units.py`,
    3 test), da lanciare a sessione CPU libera per HEK293T (due kernel da quattro parti), HCT116 dopo la sua verifica
    e KOLF pan-genome; poi le 20 parti CD4 rimaste con `fill_sessions.py`.
  - [Inventario riconciliato](../../reports/sorgenti/inventario_riconciliato_2026-10-04/README.md): cellule di 8 gruppi
    su 21 nel pilot, aggregati di 10 nelle ancore, lacuna e lavoro per ogni altra voce.
  - Quota GPU letta il 3/10 alle 23:58: 11,32 h residue su `davideferrante11` (in consumo), 30 h intere su ciascuno
    degli altri due account; gli input dei training sono kernel e dataset privati di `davideferrante11`.
  - Scostamenti dalla proposta di Codex, detti al proprietario in chat: batch e fonti delle ancore cambiati insieme
    nella v4; Kaggle CPU al posto di Colab CPU per gemelli, campioni e generazione; riassunti delle cellule ammesse
    (R-DATI passo 2) non iniziati.
  - **Aggiornamento delle 00:30.** Chiuse e verificate anche HCT116 (109 shard, 3.409.169 cellule) e CD4 `D1_Rest`
    (154 shard, 1.750.820 cellule idonee su 3.074.496 righe), ricevute in `orion/esito_verifica_hct116_r1/` e
    `cd4/esito_verifica_d1_rest_r1/` dell'ingestione. Gemelli in corsa: `rcell-v4-fast-hek293t-{a,b}-r1` (00:12,
    00:14), `rcell-v4-fast-hct116-a-r1` (00:23); restano HCT116 parti 2–3, KOLF pan-genome, la terza ondata scPerturb.
    Correzione di Codex inoltrata dal proprietario (00:13): la scelta dei campioni è per fold e legge solo le cellule
    di training; lo studio r1 resta esplorativo ([emendamento §10](../../reports/modelli/rete_ancorata_v4_2026-10-03/CAMPIONI_ANNIDATI.md),
    test di invarianza). Da lanciare a sessione libera: `kaggle_nested.py` con `--dispersion` e slug
    `rcell-v4-nested-fold-<linea>-r1`, uno per fold.
  - **Aggiornamento delle 00:53, binario del modello.** H1 concluso alle 00:39 e **tecnicamente accettato** (§5:
    uscita 0, 365 gemelli verificati, nessuna cellula non di training, quote esatte in 60 finestre su 60, salute e
    valutazione complete, ancore a regime J; 2,0 epoche in 4.878 s, 1.579 cellule al secondo, attesa dei dati 0,565;
    [ricevute](../../reports/modelli/rete_ancorata_v4_2026-10-03/esito/train_h1_r1/)). RPE1 spinto alle 00:42
    ([lancio](../../reports/modelli/rete_ancorata_v4_2026-10-03/lancio_train_rpe1_r1.json)); HepG2 ancora in corsa.
    Cellule di H1 generate (`rcell-v4-gen-h1-r1`). **Corsia A di H1 letta (misurato, 72 righe C, una linea su tre):**
    `ancorata` PDS 0,547 contro 0,965 di `transfer_all_J` e 0,963 di `ancora_sola`; coseno −0,031 contro 0,162;
    coseno specifico 0,145 contro 0,183; rapporto MSE 13,9 contro 2,6 (`laneA_h1_r1/summary.json` nella radice dati).
    Con −0,42 su H1 la guardia del §7 (media delle tre linee ≥ −0,02) è aritmeticamente quasi irraggiungibile. La
    corsia B di H1 gira sul portatile dalle 00:50 (PID 28200, `laneB_h1_r1` nella radice dati). Dopo: ricevute,
    generazione e corsie di HepG2 e RPE1, poi `decide_anchored.py` sulle tre linee e il checkpoint.
  - **Indicazione del proprietario in chat, 4/10 01:06:** Alfredo riferisce un modello a «quasi 0,08»; si può
    aspettare che lo pubblichi, seguirlo e migliorarlo «se non c'è nulla di meglio». Non verificato qui: scala e
    provenienza di quel numero (chiesto al proprietario; sul punteggio ufficiale la ricetta t22/t24 vale 0,142, il t28
    0,1448 e l'unica rete inviata, t29, −0,030). Non cambia il piano scritto: il pilot v4 si chiude sulle tre linee
    con la sua regola, il binario dati prosegue; il modello di Alfredo, quando arriva, si mette sul banco C/J a sei
    membri contro il transfer con una regola scritta prima dei numeri. Le 30 ore GPU intere di ciascuno degli altri due
    account restano libere per questo. HepG2 concluso alle 01:01 e tecnicamente accettato
    ([ricevute](../../reports/modelli/rete_ancorata_v4_2026-10-03/esito/train_hepg2_r1/)); la sua generazione attende
    una sessione CPU libera.
  - **Aggiornamento delle 01:37.** Corsia B di H1 conclusa in locale alle 01:10 (media dei sei membri: `ancorata_shift`
    0,057 contro 0,272 di `transfer_all_J`; `esito/laneB_h1_r1/`); corsia A di HepG2: PDS 0,639 contro 0,886
    (`esito/laneA_hepg2_r1/`). Il proprietario ha fermato le corsie sul portatile (regola di `CLAUDE.md`): la corsia B
    di HepG2, partita in locale, è stata interrotta alle 01:31 e **le corsie girano ora su Kaggle CPU**
    (`kaggle_lanes.py`: `rcell-v4-lanes-hepg2-r1` dalle 01:35; da spingere `rcell-v4-lanes-h1-r1` come parità con il
    risultato locale e `rcell-v4-lanes-rpe1-r1` dopo training e generazione di RPE1; registro in
    `lancio_lanes_r1.jsonl`). Gemelli: HEK293T parti 4–7 e HCT116 parti 0–1 conclusi; il kernel HEK293T parti 0–3 è
    caduto a 106 shard su 112 (E-20261004-001) ed è rilanciato come `-a-r2`; HCT116 parti 2–3 e KOLF in corsa.
    Un'altra sessione lavora nel checkout su `reports/sorgenti/libera_spazio_2026-10-04/` (prova a secco, niente
    rimosso): non toccata.
  - **Corpus ampliato, percorso critico (non iniziato):** protocollo con i gruppi adottati; pre-passo sui 365 shard
    del pilot più HCT116, HEK293T e KOLF pan-genome (16,2 milioni di cellule). Stima, non misura: il pre-passo del
    pilot ha impiegato 10.200 s per 5,6 milioni di cellule con 4 processi, quindi circa 8 ore per fold a parità di
    processi; ma gli shard Orion hanno 130–160 milioni di valori l'uno e quattro processi insieme hanno già esaurito
    la memoria nella costruzione dei gemelli (E-20261004-001). Con due processi il tempo supera le 12 ore di un kernel.
    Da decidere prima di lanciare, con il picco di memoria che i kernel dei gemelli ora registrano: pacchetto a
    tetto fisso scelto dai soli metadati prima del pre-passo, lettura a blocchi di righe, oppure pre-passo per
    sorgente con unione. `kaggle_train.py` costruisce l'elenco degli shard solo dai dataset con `files.json`: va
    esteso agli output dei kernel. Le chiavi dei bersagli del pilot (19.814 simboli, dall'inventario P0 che comprende
    Orion e KOLF) coprono già queste sorgenti. Poi campioni per fold e ancore per fold.
- **Riprendere da qui (passaggio ad altro account, 3/10 23:30 CEST; job verificati alle 23:27, tutti RUNNING):**
  - GPU: `rcell-v4-train-h1-r1`, `rcell-v4-train-hepg2-r1` (dalle 23:06). CPU: `vcc-orion-hct116-p3of4-r3`,
    `vcc-orion-hek293t-p{0,1,2}of8-r3` (dalle 23:08). Pronti: dataset `davideferrante11/rcell-v4-code-r1` (training),
    `rcell-v4-gen-r1` (generazione, bersagli r3), kernel `rcell-v4-anchors-r1` e `rcell-v4-fast-{a,b,c}-r1`.
  - Ricevute a training finito, senza i file di valutazione: `python fetch_outputs.py --config-dir
    ~/.kaggle-davideferrante11 --slug rcell-v4-train-<linea>-r1 --pattern "train/*.json" --pattern "train.log"
    --pattern "*kernel_done.json" --exclude "*eval*" --out esito/train_<linea>_r1` nella cartella v4; accettazione
    del §5 (`exposure.json`, `coverage.json` con `timing`, `verify.json`, `health.json`).
  - RPE1: il comando di [lancio_train_r1.json](../../reports/modelli/rete_ancorata_v4_2026-10-03/lancio_train_r1.json)
    con `--anchors-line RPE1 --anchors-dir anchors_RPE1_all --prepass-from rcell-prepass-rpe1-r1`, slug
    `rcell-v4-train-rpe1-r1`, appena una sessione GPU è libera; poi `kaggle quota`.
  - Generazione per linea: `python kaggle_gen.py kernel --config-dir <dir> --owner davideferrante11 --stage <nuova>
    --held-group <LINEA> --train-kernel rcell-v4-train-<linea>-r1 --prepass-kernel rcell-prepass-<linea>-r1
    --anchors-kernel rcell-v4-anchors-r1 --anchors-dir anchors_<LINEA>_all --slug rcell-v4-gen-<linea>-r1`.
    Corsie A/B e regola: comandi nei docstring di `bench_effects.py`, `lane_b.py`, `decide_anchored.py` (cellule vere e
    bersagli da `out_gen_h1_r3`, `out_gen_hepg2_r3b`, `out_gen_rpe1_r3b`; `--splits` da `out_prepass_<linea>_r1`).
  - Binario dati: `nested_samples.py` (studio dei campioni annidati) è scritto e testato, il suo launcher Kaggle no
    (input: gemelli, i dataset `rlab-*` per le colonne obs, `rcell-prepass-h1-r1`). Inventario riconciliato di
    R-DATI non iniziato. Verifiche di linea Orion a parti finite (R-LAB).
  - Da riferire al proprietario: un processo Python bloccato da una sessione chiusa (PID 2288, `C:\\Python314\\python.exe -`,
    padre bash PID 17800, dalle 16:19) occupa circa un core del portatile; terminarlo è stato negato dal controllo dei
    permessi, va fatto a mano.
- **Dipendenze:** [R-LAB](piano-giorno-2026-09-30.md) e [R-DATI](dati-affidabilita.md) per i dati,
  [GENERALIZZAZIONE](../GENERALIZZAZIONE.md), D-050, D-052, D-053, D-054; PROCEDURE §3 ed ERRORI per ogni job.
- **Chiusura:** scelta motivata con prove riproducibili e pipeline finale verificata, oppure esito negativo o
  inconclusivo con il transfer conservato e il limite identificato.
- **Dove stanno gli esiti precedenti:** P3, P4, pilot v2 (r3), miscele, v3 e v4 in
  [AMBITI §5](../AMBITI.md#5-modelli-appresi-e-generalizzazione); le note datate di questa scheda fino al 3/10 sera
  nello [storico del consolidamento](../storico/consolidamento_2026-10-03/INDICE.md).

## 1. Domanda scientifica e perimetro

**Ipotesi da verificare:** a parità di dati e generatore, una correzione della risposta dipendente dai controlli del contesto nuovo migliora il trasferimento degli effetti. Non basta ricostruire il basale, ridurre la loss o riconoscere un'identità di linea.

Il [confronto ufficiale Arc del 1 ottobre](https://arcinstitute.org/news/behind-the-data-virtual-cell-challenge-2026) distingue esempi perturbati nella linea destinataria nel 2025 e soli controlli nelle sei linee del 2026. Il bersaglio può essere già noto in altre linee. Quindi **C e J** sono i regimi rilevanti; T è diagnostico e non promuove un modello per contesti nuovi. La figura chiarisce il compito, non dimostra la causa dei fallimenti locali.

Transfer e cellnet tentano già il trasferimento fra contesti. Ciò che manca è una prova robusta del beneficio appreso dal contesto: l'[audit](../../reports/analisi/lead_audit_2026-10-01/REVISIONE.md) trova r2 inferiore al transfer su HepG2 C in una misura esplorativa. HepG2 già esaminata resta sviluppo. Il [t29](../checkpoints/0055-t29-rete-cellulare-punteggio.md) richiede prima di un altro invio neurale un banco locale a sei membri almeno al livello del transfer. Il collasso `ident` di r3 non identifica la causa del t29, che usa r2 `desc`.

**Cambio rispetto al piano precedente:** costruire prima la prova di trasferimento e il confronto semplice; recuperare la rete solo come candidato motivato. Non si richiede che il bilineare vinca per poter provare una rete: un esito negativo può motivare un'ipotesi non lineare, ma occorrono dati identificabili e un contrasto che possa smentirla.

## 2. Sequenza e contratti di consegna

Gli identificativi P0–P6 sotto hanno questo significato dal 2 ottobre; la [versione precedente](../storico/R-LEAD_pre_contesti_2026-10-02.md) è storia, non una seconda coda.

| Passo | Output minimo | Condizione per avanzare |
|---|---|---|
| P0 — dati e fattibilità | `preflight.json`, `input_manifest.json`, `context_target_study.csv`, `feasibility.md` | Supporto, confondimenti e input disponibili espliciti |
| P1 — esposizione e split | `exposure_manifest.json`, `split_manifest.json`, `reserve_manifest.json` | C/J effettivi, esclusioni globali e storia delle riserve verificati |
| P2 — banco e regola | `PROTOCOLLO.md`, runner, fixture/test, `export_parity.json` | Regola fissata prima dei nuovi risultati; percorso fino allo scorer verificato |
| P3 — confronto semplice | codice, manifest dei fit, sei metriche, `context_ablation.json`, `decision.json` | Beneficio, assenza di beneficio o inconclusività attribuiti al confronto corretto |
| P4 — estensione motivata | `hypothesis.md`, nuova versione, `fix_matrix.json` se applicabile, misure appaiate | Una lacuna precisa motiva rete, dati o distribuzioni; stesso banco |
| P5 — conferma indipendente | candidato congelato, `confirmation.json`, `decision.json` | Regola rispettata su riserva appropriata o indipendenza insufficiente dichiarata |
| P6 — consegna finale | manifest della pipeline, prova a forma piena, verbale | Catena riproducibile e valida, anche se resta il transfer |

Nuovi output in `reports/analisi/generalizzazione_contesti_<data>/` e nuovo codice di ricerca in `reports/modelli/risposta_contesto_<data>/`, con suffisso se già occupati. Sono destinazioni proposte, non risultati esistenti. Indici e registro si aggiornano quando vengono create. Ogni run ha directory nuova, commit, comando, ambiente, input/hash, ruoli, parametri, seed e output/hash; dati e pesi pesanti restano fuori da Git. Distinguere **implementato, eseguito, misurato, adottato**.

## 3. P0 — quale trasferimento possiamo effettivamente imparare

1. Verificare Git, input leggibili, spazio, memoria, interpreter e scorer reale: `cell_eval2.config` e preset `vcc2026`. Per problemi di visibilità seguire [CP-0054](../checkpoints/0054-visibilita-scorer-e-consegna.md) prima di reinstallare. Su altra macchina usare [CONSEGNA_TEAMMATE](../CONSEGNA_TEAMMATE.md).
2. Costruire dal corpus presente una matrice con linea/donatore/stimolo, studio, assay, modalità CRISPRi/a/KO, bersaglio, guide/repliche, controlli, numerosità, geni misurati, unità e disponibilità di cellule o sole DE. Distinguere identità biologiche e alias. Per ogni confronto indicare gli input e il codice che producono le stime.
3. Contare perturbazioni osservate in più contesti, variazione fra contesti e confondimento linea/studio/assay. Se linea e studio coincidono, il confronto non separa le loro cause. Donatori della stessa linea non diventano automaticamente nuove linee indipendenti. Descrivere qualità delle etichette e riproducibilità fra guide/repliche quando misurabili.
4. Riportare efficacia del knockdown, profondità, numerosità e assay come metadati/strati quando disponibili. L'80% di riduzione dichiarato da Arc per la propria curazione non autorizza a filtrare retroattivamente la nostra validazione per efficacia osservata. Valori mancanti restano mancanti. CRISPRi, KO e attivazione hanno ruoli distinti.
5. Dichiarare quali linee permettono training, sviluppo e conferma separati, prima di sceglierle per i punteggi. Priorità ai collegamenti fra contesti, non al conteggio totale di cellule. Sorgenti senza overlap col pannello restano ammesse secondo D-044.

**Esito utile:** una mappa di ciò che è identificabile. Se mancano controlli, repliche o collegamenti, indicare file, locatore, byte e confronto reso possibile; R-DATI colma quella lacuna. L'annuncio dei dati Arc non significa che le risposte della gara siano training scaricabile. Nessun download o job cloud è implicito in questo piano.

## 4. P1 — simulare il 2026 senza cambiare gli split dopo i numeri

- **C:** bersaglio visto, linea nuova. **J:** bersaglio e linea nuovi. **T:** bersaglio nuovo, linea vista, solo diagnosi. Il cambio di pannello non implica automaticamente J.
- Escludere la linea destinataria perturbata da tutti gli studi, stimoli, cache, prior e derivati del fit. In J escludere anche le risposte dei bersagli da tutte le sorgenti, riconciliando alias, guide e repliche. Registrare provenienza del pretraining.
- Usare controlli della linea esclusa soltanto come input al percorso di inferenza preregistrato. Nessuna sua risposta perturbata in preprocessing, selezione di geni, fit, early stopping o tuning. Specificare separazione/incrocio delle librerie dei controlli usati per input basale e contrasto di valutazione.
- Costruire fold di sviluppo con linee intere escluse, ripetuti su più linee se possibile; scegliere iperparametri su ulteriori contesti interni esclusi. Tenere distinta una riserva finale mai consultata. Se il corpus non consente questa separazione, dichiarare il banco esplorativo e cosa manca; non fabbricare indipendenza con split di cellule.
- R2/r3 hanno esposizioni e split diversi: ricostruirli prima di ogni confronto. K562 già nel loro training non è un holdout neurale. Un nuovo fit può escluderla, ma risultati già noti non rendono il contesto una conferma finale intatta. H1 train/val sono nel corpus, H1 test resta chiusa: un test H1 dopo fit H1 non prova C/J.

**Accettazione eseguibile:** fixture con alias e la stessa linea in studi diversi; aggiunta/riordino di shard e QC non cambiano ruoli congelati. Gruppi persi dopo QC sono riportati, non riassegnati. Il controllo di esclusione vale per ogni braccio, compreso il transfer. Un unico contesto escluso o il bootstrap dei suoi target non misura incertezza fra contesti. Il manifest delle riserve registra anche valutazioni e tuning già effettuati.

## 5. P2 — un banco comune e una regola prima dei risultati

Congelare protocollo, bracci, supporti, fold, metrica primaria, aggregazione, miglioramento pratico richiesto, regressioni ammesse, confronti multipli e regola C/J. Motivare le soglie con pilot di sviluppo o informazione indipendente; se si usano risultati per progettarle, quelle osservazioni non sono conferma. Nessuna soglia numerica è inventata da questo piano.

Il runner usa verità, controlli, target, geni misurati, numerosità e seed comuni. Conservare copertura e gruppi esclusi; niente selezione silenziosa dei gruppi più numerosi. Normalizzatori, PCA e rappresentazioni si stimano sul fit ammesso. Un gene non misurato resta mascherato.

Ricostruire t22/t24 dai manifest per la replica; mantenere la correzione dello stimatore t25 nel riferimento corretto, distinguendo l'emissione t28. Fissare riferimento e generatore prima del confronto. Controllare ordine dei geni, log/CPM, maschere, scala, cis, clipping e fallback con una prova piccola di parità effetto → export → generazione; documentare tolleranze. La replica r2 serve se quel checkpoint entra nel banco, non blocca i confronti semplici.

Misurare **PDS, MSE, NMAE, FID, reach e Jaccard**, con scorer e aggregazioni effettivi, per contesto/regime/seed; mantenere numeratori/denominatori della MSE. Macro per contesto e media operativa restano separate. Non convertire le ancore aggregate in uno score VCC esatto. Senza ancore locali indipendenti usare grezzi e una regola esplicita sui sei membri. Coseno top-200, likelihood e metriche sugli effetti servono alla diagnosi, non alla promozione. Sole DE permettono una prova sugli effetti, non il banco completo sulle cellule.

Prevedere almeno tre seed dei finalisti e incertezza appaiata per unità indipendenti, distinguendo variabilità di generazione, fit, target e contesto. Tre seed non sostituiscono nuove linee. D-050 permette adozione nel ramo C con protezione preregistrata di J; per affermare generalizzazione congiunta serve J. Resta il vincolo t29 per nuovi invii neurali.

## 6. P3 — primo esperimento: il contesto migliora la risposta?

Implementare un'interfaccia comune: `fit(train, validation, manifest)` e `predict(target_descriptor, control_context, measured_mask)` → effetto, supporto, fallback. È un contratto proposto, da adattare alle API esistenti senza duplicare il generatore.

| Braccio | Scopo |
|---|---|
| Nullo | Riferimento di nessun effetto |
| Generico addestrato senza identità del bersaglio | Misurare quanto spiega una risposta comune; unknown non addestrato non lo sostituisce |
| Transfer dello stesso bersaglio | Riferimento C; in J nessuna risposta vietata, fallback esplicito |
| Modello del bersaglio senza contesto | Stessi descrittori leciti del candidato; confronto per l'utilità del contesto |
| Modello semplice condizionato | Effetto condiviso del bersaglio più correzione bilineare regolarizzata dai controlli |

Partire da descrittori basali su geni misurati e descrittori trasferibili del target; trasformazioni, rango, shrinkage e ampiezza si scelgono nei fold interni. Il target-ID può essere un confronto C, non la soluzione per J. Per il modello condizionato, il riferimento condiviso può essere il transfer C o il modello senza memoria J: le due strade sono esplicite, con fallback appreso e supporto registrato. Non si impone una nuova famiglia di embedding senza un'ablation che ne motivi l'informazione aggiuntiva.

Se si apprende un residuo rispetto al transfer, calcolare riferimento e residui di training out-of-fold per contesto: togliere ogni linea destinataria anche dalla media di transfer. In J rispettare inoltre le esclusioni globali dei target. Pesi di affidabilità e blending si stimano fuori campione; niente scelta per target del vincitore osservato nel test.

**Prova dell'uso del contesto:** confrontare il modello con contesto corretto, con contesto ignorato (braccio riaddestrato) e con descrittori scambiati secondo permutazioni fissate nel protocollo. Nello scambio mantenere i veri controlli destinatari per basale e generatore, e fissi target, supporto, calibrazione e seed: cambia soltanto il condizionamento dell'effetto. Se codice ed encoder intrecciano basale ed effetto, separare i due percorsi prima del test. Lo scambio da solo può produrre input fuori distribuzione: non dimostra causalità né basta senza il confronto riaddestrato. Permutare anche il target per diagnosticare la specificità.

**Decisione:** distinguere miglioramento della catena e prova del contributo del contesto. Una calibrazione utile ma insensibile al contesto può essere valutata per la produzione senza chiamarla apprendimento della risposta contestuale. Se il candidato perde, salvare la matrice degli errori; il risultato chiude quel confronto, non tutte le reti.

## 7. P4 — rete, dati o distribuzioni solo per un limite identificato

Prima di implementare l'estensione scrivere ipotesi, contrasto, output atteso e regola che la smentisce. Esempi: interazione non lineare non catturata dal bilineare; dati senza collegamenti; verità instabile; perdita introdotta dal generatore a pari effetto medio. Un esito inconclusivo per scarso supporto non motiva automaticamente una rete più grande.

Se si riusa cellnet, copiare il codice in una destinazione nuova; preservare originali e report importati. Usare [NOTA_TRAINING](../../reports/analisi/lead_audit_2026-10-01/NOTA_TRAINING.md) e [AGGIORNAMENTO_R3](../../reports/analisi/lead_audit_2026-10-01/AGGIORNAMENTO_R3.md) per registrare ogni difetto come riprodotto, già corretto, non applicabile o non verificabile.

| Verifica necessaria per il codice riusato | Accettazione |
|---|---|
| Split e prepass | Esclusioni e stabilità P1 anche dopo QC |
| Sampler e pesi globali | Coefficienti aggregati corretti nel replay; niente rinormalizzazione nel batch che annulli i pesi |
| Controlli | Reservoir riproducibile per libreria, nessuna perturbata, fixture con librerie tardive e ordine variato |
| Miscela e gradienti | Log-pesi stabili, gradienti finiti e recupero nel controesempio; monitor per studio |
| Export e resume | Parità, seed ripristinati, smoke e pilot prima del job completo |

`--pi-floor` esiste già: non ricrearlo né scambiarlo per apprendimento dimostrato. Il quarto training datato mescola floor e dati: non riparte automaticamente. Una rete nuova si confronta con P3 sugli stessi fold e input; nessuna promozione da T o dalla likelihood.

Per i dati, ablation annidate a split fisso separano contesti, cellule, qualità e assay; non cambiare corpus e architettura insieme per attribuire il beneficio. R-DATI può aprirsi già da P0/P1 se manca l'informazione per costruire il banco. Per R-SWITCH occorre un limite di popolazione misurato a pari effetto medio e guide/repliche indipendenti; niente coppie cellulari inventate o bistabilità dedotta dalla sola bimodalità.

## 8. P5 — conferma e scelta

Congelare candidato, preprocessore, supporto C/J, adattamento dai controlli, fallback, calibrazione e regola prima di aprire la riserva appropriata di P1. Aprirla una volta; una bocciatura non si sana cambiando la soglia. H1 test non è automaticamente quella riserva. Se non esiste una conferma indipendente al livello di contesto, dichiarare il limite: non rinominare una rivalutazione del banco. Non sostenere generalizzazione robusta da un solo contesto o da target bootstrap sullo stesso contesto.

Conservare il transfer se nessun candidato passa. Un esito negativo produce una scelta del prossimo contrasto motivata da ciò che è misurato, senza espansione automatica del corpus né training senza domanda. La prova finale della pipeline procede comunque.

## 9. P6 — consegna D/E/F

La [prova generale a forma piena](revisione-critica.md) è necessaria anche col transfer: risorse attuali, inferenza completa, nuovi target, assi, maschere, controlli e packaging bitwise. Portare in produzione soltanto componenti adottati con test di parità. Al rilascio del 22 ottobre usare solo input leciti e adattamento preregistrato; registrare supporto C/J e fallback per target. [S-INVII](invii-finale.md) presidia la consegna entro il 5 novembre secondo le autorizzazioni della sessione, senza promessa di punteggio.

## 10. Handoff e lavoro indipendente

Claude consegna commit locali, codice/test/log, manifest, protocollo, misure e decisione; aggiorna scheda, indici e registro. Nessuna misura nasce dalla sola stesura di questo piano. Se manca un input, completare fixture, runner e verifiche indipendenti, poi indicare il minimo necessario per il passo impedito. Non ricreare tutto il disco della macchina origine. Download, cloud, nuovi agenti, invii e push seguono CLAUDE.md e le autorizzazioni della chat. Il piano non assegna tempi né limiti preventivi al lavoro.
