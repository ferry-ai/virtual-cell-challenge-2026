# Protocollo — derivazioni dalla banca e ammissione alla release

Scritto il 7 ottobre 2026 alle 01:35 (Europe/Rome, letto con `date`), **prima** di lanciare
le derivazioni e di leggerne le uscite. Sessione Claude `6cf149d8`. Tipo: proposta operativa
con regole registrate; nessun numero di esito è noto mentre si scrive.

## Che cosa si fa

Per ogni unità di banca `count_sum` già persistente e verificata, non ancora collegata al
transfer, un job CPU su Kaggle legge **solo** `count_sum.npz`, `mask.npz`, `rows.csv` e la
ricevuta della banca, ne verifica gli hash nel runtime e stima gli effetti sui bersagli del
pannello con lo stimatore originale (pseudo 0,5, min_expected 1, min_cells 10, phi 0,2).
Adapter e stimatore sono copie byte-identiche di quelli del consumer HIPSCI già verificato
(`hipsci_adapter_r3`). Nessuna ingestione, nessun grezzo riletto, nessuna matrice scaricata.

Il piano dei metadati, calcolato dalle righe verificate **senza leggere conteggi**, è in
[piano_r1.json](piano_r1.json); le specifiche in [derivazioni.json](derivazioni.json).

## Ruoli dichiarati prima degli esiti

| Braccio | Fonti | Destinazione |
|---|---|---|
| `crispri` | xu2023, tian2021_crispri, tian2019_ipsc, tian2019_neuron, HIPSCI mirato (già derivato) | candidate al voto dello stesso bersaglio nel transfer t25, peso 1 come ogni fonte |
| `crispri_same_study_as_k562_bulk` | k562_gwps_sc (blocchi a+b sommati) | **mai** un secondo voto: è lo stesso esperimento della tabella K562 BULK storica che già vota. Si deriva per leggere l'equivalenza fra le due derivazioni |
| `ko` | a549_ko, frangieh2021, sunshine2023, dixit2016, shifrut2018 | derivate e conservate come braccio separato. Non entrano nel voto CRISPRi di questa release: unire KO e CRISPRi è una scelta di modello, non di banca (GENERALIZZAZIONE §2.1, «uso coerente») |
| `crispra` | norman2019, tian2021_crispra | derivate e conservate; direzione opposta al knockdown, mai nel voto |
| non lanciate | HIPSCI genome-wide (2 unità), papalexi2021_arrayed, datlinger2017, datlinger2021 | il piano mostra perché lo stimatore originale non può girare; restano in banca come lavoro aperto |

## Regola di ammissione al voto (braccio `crispri`)

Una fonte entra nella release del transfer se, e solo se:

1. il job è COMPLETE, il codice salvato coincide con il pacchetto lanciato e gli hash di banca,
   asse e pannello sono stati verificati nel runtime;
2. almeno un bersaglio del pannello è stimato con controlli abbinati;
3. **verso del knockdown:** fra i bersagli stimati il cui trascritto è misurato, la mediana del
   log-rapporto grezzo sul proprio gene è **negativa**. Nessuna soglia di ampiezza.

Una fonte che non passa il punto 3 resta in banca e nel registro come «derivata, non ammessa»,
con il numero letto; non si rimuovono cloni, contesti o bersagli per farla passare. La regola non
si sposta dopo la lettura. Per HIPSCI mirato il punto 3 si legge sulla
[diagnostica già conclusa](../percorso_riusabile_2026-10-05/hipsci_qc_r1/completion_r1/qc_receipt.json).

L'equivalenza K562 (coseno per bersaglio fra tabella nuova e storica) è **descrittiva**: non
ammette e non sostituisce nulla. Gli effetti del braccio `ko` si leggono solo come inventario.

## Che cosa questa prova non è

- Non è una validazione C/J: produzione con bersagli nascosti vuoti e nessuna linea esclusa.
- Non misura un punteggio VCC e non autorizza un invio.
- Il fit della release è il transfer t25 invariato (media a peso 1, shrunk, ampiezza 1,576, testa
  cis): cambia la banca, non il modello. Nessuna aspettativa di miglioramento è registrata.
- Le derivazioni coprono i bersagli del pannello. La banca `count_sum` resta completa su tutti
  i bersagli nativi: lo stesso ingresso deriva altri insiemi senza reingestione.

## Precedenti

- **S-010** (fonti in più nel transfer): banco storico positivo ma non ammesso, t36 +0,0024
  descrittivo, meccanismo ipotizzato. Qui il disegno non cambia: si aggiungono fonti allo stesso
  transfer. Differenza: ogni fonte nuova ha la sua ricevuta di consumo e il verso del knockdown
  letto prima dell'ammissione; nessuna attribuzione del punteggio a una fonte.
- **Errori di metodo già registrati** (ERRORI): manifest non consumati scambiati per training;
  `p2` letto come pseudocount (R-026). Guardie: il fit verifica byte per byte ogni tabella e
  scrive quali fonti hanno davvero votato per ogni bersaglio; lo stimatore rifiuta una ricetta
  diversa dall'originale.
- **Segnale precoce d'arresto:** un job che fallisce sul controllo di hash, asse o controlli
  abbinati si ferma prima di ogni stima; si diagnostica e non si rilancia alla cieca. Una mediana
  del proprio gene non negativa ferma l'ammissione di quella fonte, non le altre.
