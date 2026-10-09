# Validazione, banco e registro delle previsioni — sessione eace4d03, dal 9 ottobre 2026

Claude Code, sessione `eace4d03`, incarico del proprietario in chat: riprendere il ruolo VALIDAZIONE della sessione
`8a8ca58a`, allargare il banco con i dati acquisiti e costruire un processo che impari dagli errori di previsione
dopo ogni invio. Binario [R-LEAD](../../../docs/piani/strategia-scientifica.md). Questa cartella possiede
protocollo, misure, controlli e lettura; **non** possiede banca e pipeline (DATI-TRANSFER, `01a11c34`) né modelli
e training (MODELLI-ESTERNI, `01a11c35`). La cartella dell'8 ottobre,
[validazione_indipendente](../validazione_indipendente_8a8ca58a_2026-10-08/README.md), resta com'è: il suo banco è
usato da qui senza modifiche, con `metrics.py` verificato per sha256.

Tutti i numeri dei banchi sono **locali e di sviluppo**: non sono punteggi VCC. I punteggi ufficiali stanno solo
nell'[indice degli invii](../../invii/README.md).

## Che cosa leggere prima

1. [PROTOCOLLO_v3.md](PROTOCOLLO_v3.md): che cosa cambia rispetto a v2, e perché. Congelato alle 20:50 del 9/10,
   prima dei numeri che legge. [ADDENDUM_v3_1.md](ADDENDUM_v3_1.md): due diagnosi in più, registrate prima del
   fold C-iPSC.
2. [RISULTATI_ESM2_FALLBACK.md](RISULTATI_ESM2_FALLBACK.md): i cinque punti dell'audit del Lead verificati, e che
   cosa fa davvero il riempimento ([CP-0075](../../../docs/checkpoints/0075-fallback-esm2-supporto-e-vista-del-generatore.md)).
3. [invii/RAPPORTO_INVII_r1.md](invii/RAPPORTO_INVII_r1.md): ogni previsione registrata contro i sei membri
   ufficiali, t38 compreso ([CP-0074](../../../docs/checkpoints/0074-t38-crispri-piu-ko-punteggio-ufficiale.md)).
4. [inventario/INVENTARIO_r1.md](inventario/INVENTARIO_r1.md): che cosa la banca offre alla valutazione, per
   lignaggio e per unità, e quali checkpoint si possono leggere come contesto nuovo.

## Indice

| Area | File | Che cosa fa |
|---|---|---|
| **Contratto** | [PROTOCOLLO_v3.md](PROTOCOLLO_v3.md), [ADDENDUM_v3_1.md](ADDENDUM_v3_1.md) | copertura separata dall'accuratezza e vista del generatore; diagnosi del fallback; estensione dei fold; registro previsione → punteggio |
| **Supporto del fallback** | [esm2/supporto_fallback.py](esm2/supporto_fallback.py), [test](esm2/test_supporto_fallback.py) ([esito](esm2/test_supporto_fallback_r1.txt)) | conteggi di supporto, quattro bracci con maschera e scala identiche, parità con il banco congelato prima di ogni lettura |
| | [esm2/prepara_spec.py](esm2/prepara_spec.py), [esm2/prepara_cloud.py](esm2/prepara_cloud.py) | gli sha256 attesi vengono dalle ricevute di chi ha prodotto i file; un kernel CPU privato con gli input già montati |
| | [esm2/supporto_C-K562_r1.json](esm2/supporto_C-K562_r1.json), [r2](esm2/supporto_C-K562_r2.json) | C-K562 sul portatile: r1 con la regola congelata, r2 con le due diagnosi aggiunte dopo |
| | [esm2/cloud_r1/](esm2/cloud_r1/prepared.json) | pacchetto, preflight, lancio, uscite del kernel `davideferrante11/vcc-validazione-supporto-eace4d03-r1` per i due fold |
| **Registro degli invii** | [invii/registro.py](invii/registro.py), [test](invii/test_registro.py) ([esito](invii/test_registro_r1.txt)) | `costruisci`, `rapporto`, `dopo-invio`, `confronto`, `leggi-stato` |
| | [invii/previsioni_di_banco.json](invii/previsioni_di_banco.json), [invii/banchi.json](invii/banchi.json), [invii/spiegazioni.json](invii/spiegazioni.json) | puntatori, non numeri: dove sta scritta ogni previsione di banco, le versioni del banco, le spiegazioni con il loro stato di prova |
| | [invii/registro_previsioni_r1.json](invii/registro_previsioni_r1.json), [invii/RAPPORTO_INVII_r1.md](invii/RAPPORTO_INVII_r1.md), [invii/stati/](invii/stati/status_LJmnhqqh1WTrx1JcoRlr_20261009T190948Z.json) | il registro e il rapporto del 9/10; lo stato ufficiale del t38 letto alle 21:09 |
| **Quale misura vale dove** | [banco/validita_misure.py](banco/validita_misure.py), [banco/VALIDITA_MISURE_r1.md](banco/VALIDITA_MISURE_r1.md) | per ogni fold e misura del livello A: T0 si distingue da previsioni scambiate, generiche, nulle? Dai risultati congelati, senza nuovi calcoli |
| **Sei membri per il fallback** | [LIVELLO_B_ESM2.md](LIVELLO_B_ESM2.md), [esm2/costruisci_bracci.py](esm2/costruisci_bracci.py), [banco/livello_b_esm2.py](banco/livello_b_esm2.py) | piano scritto prima dei numeri; i tre bracci di riempimento con una sola maschera; dataset privato e due kernel CPU su `davidmaisterx` (`banco/livello_b_k562_e1/`, `banco/livello_b_ipsc_e1/`) |
| | [banco/PREVISIONI_LIVELLO_B_e1.md](banco/PREVISIONI_LIVELLO_B_e1.md), [banco/leggi_livello_b_esm2.py](banco/leggi_livello_b_esm2.py) | che cosa prevedono per i sei membri la convenzione vecchia e la nuova del livello A, registrato prima di raccogliere un'uscita; lettore con l'esito del §8 e le frasi fissate |
| **Sei membri su lignaggi nuovi** | [LIVELLO_B_NUOVI_FOLD.md](LIVELLO_B_NUOVI_FOLD.md) | piano per C-HCT116, C-HEK293 e C-CD4T scritto prima che esistano le cellule: bracci, coppie, e la regola con cui si leggerà l'ipotesi sulla composizione delle fonti |
| **AMMI `none`** | [LETTURA_AMMI_NONE.md](LETTURA_AMMI_NONE.md), [ammi/lettura_esterni.py](ammi/lettura_esterni.py), [test](ammi/test_lettura_esterni.py) ([esito](ammi/test_lettura_esterni_r1.txt)) | piano scritto prima di aprire gli export; lettore di bracci esterni con il banco congelato, copertura e vista del generatore |
| | [ammi/prepara_spec_ammi.py](ammi/prepara_spec_ammi.py), [ammi/prepara_cloud_ammi.py](ammi/prepara_cloud_ammi.py), [ammi/ammi_none_download_r2.json](ammi/ammi_none_download_r2.json) | pin dalle ricevute; scarico verificato dei due export, dataset privato e kernel CPU su `davideferrante11` |
| | [ammi/ammi_none_C-K562_r1.json](ammi/ammi_none_C-K562_r1.json), `ammi/cloud_r2/` | C-K562 sul portatile; i due fold nel kernel (`cloud_r1/` conserva un push rifiutato dal provider) |
| **Autorizzazioni** | [AUTORIZZAZIONI_r1.json](AUTORIZZAZIONI_r1.json) | le tre decisioni del proprietario delle 21:42 del 9/10, con che cosa coprono e che cosa no |
| **Inventario** | [inventario/inventario.py](inventario/inventario.py), [inventario/esposizione.json](inventario/esposizione.json) | la regola del ruolo applicata ai numeri di ogni unità; che cosa ogni lignaggio ha già visto del progetto |
| | [inventario/INVENTARIO_r1.md](inventario/INVENTARIO_r1.md), [inventario/inventario_r1.json](inventario/inventario_r1.json) | tabelle per lignaggio, per unità, e dei checkpoint leggibili come regime C |
| **Coordinamento** | [MESSAGGI.md](MESSAGGI.md) | chi esegue che cosa, esito del t38, richieste precise a DATI-TRANSFER |

## Dopo ogni invio

```bash
.\scripts\py.cmd reports/analisi/validazione_banco_eace4d03_2026-10-09/invii/registro.py leggi-stato <entry> <cartella degli stati>
.\scripts\py.cmd reports/analisi/validazione_banco_eace4d03_2026-10-09/invii/registro.py costruisci <registro nuovo.json> --stati <cartella degli stati>
.\scripts\py.cmd reports/analisi/validazione_banco_eace4d03_2026-10-09/invii/registro.py dopo-invio <registro.json> <tNN>
.\scripts\py.cmd reports/analisi/validazione_banco_eace4d03_2026-10-09/invii/registro.py confronto <registro.json> <tNN> reports/invii/prediction_<tNN>_<data>/comparison.json
.\scripts\py.cmd reports/analisi/validazione_banco_eace4d03_2026-10-09/invii/registro.py rapporto <registro.json> <rapporto nuovo.md>
```

Prima dell'invio: la previsione nel suo `prediction.json`, e se un banco ha un numero per quel candidato una riga
in `previsioni_di_banco.json` che dice dove sta scritto. Ogni uscita è un file nuovo; il comando non sovrascrive.

## Regole di questa cartella

- Un numero comparativo si legge con la regola che era congelata quando è stato prodotto; una lettura aggiunta dopo
  i numeri è dichiarata come tale.
- Copertura e accuratezza non si sommano: un gene che la verità non misura resta fuori dai conteggi di accuratezza,
  e una coppia che un braccio non prevede vale zero solo nella vista del generatore.
- Nessun file di un altro incarico è modificato da qui. Nessun lignaggio è conferma indipendente.
