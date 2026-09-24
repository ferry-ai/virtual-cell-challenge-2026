# Audit dello stato e delle interpretazioni — 24 settembre 2026

**Tipo:** misure esplorative, interpretazioni e proposte, separate sotto.
**Autore:** Codex. **Revisione umana:** no.

Il trasferimento dello stesso bersaglio ha un segnale reale, ma la diagnostica attuale
confonde in parte specificità, prevalenza dei segni e incertezza del riferimento.
La priorità proposta è rendere queste tre componenti distinguibili prima di aumentare
la complessità del predittore. Nessuna ricetta o regola di invio è cambiata.

## Stato verificato negli artefatti

- **Misurato:** il migliore documentato è t15, +0,107533, rango 436 al momento dello status
  salvato, da `reports/trial_2026-09-24/status_U1K3SZuq7w5cef9lBKsn.json`.
  Non è una verifica della classifica online attuale.
- **Misurato:** t16 e t17 sono già impacchettati e validati, secondo
  `reports/trial_2026-09-24/t16_packaging.json` e `reports/trial_2026-09-24/t17_packaging.json`.
  La mappa li descrive ancora come in generazione. Il packaging non prova un invio.
- **Misurato:** t15 migliora cinque metriche ma peggiora la MSE grezza da 1,129 a 1,579.
  Il suo punteggio MSE resta zero. È un miglioramento dell'obiettivo di gara, non un
  miglioramento uniforme dell'accuratezza biologica (comparison del t15).

## 1. Il 50% non basta come riferimento per i segni

**Misurato ex novo:** `measurements.json`, sezione `direction`; riproduzione in `audit.py`.
Cache r5, effetti raw, media con affidabilità n/(n+100), una sorgente esclusa alla volta.
Per bersaglio: primi 100 geni per effetto previsto assoluto, escluso il gene bersaglio;
50 scorrimenti casuali non nulli delle identità dei bersagli per il controllo negativo.
Le colonne sono medie per bersaglio, non le mediane dello stadio 103.

| Riferimento escluso | γ | Segni corretti | Bersagli scambiati | Sempre aumento, stessi geni |
|---|---:|---:|---:|---:|
| K562 | 0 | 52,25% | 50,01% | 49,04% |
| CD4 mix | 0 | 52,40% | 51,77% | 51,41% |
| HCT116 | 0 | 56,60% | 53,85% | 63,58% |
| HEK293T | 0 | 56,63% | 54,37% | 54,93% |
| K562 | 1 | 52,47% | 50,16% | 48,83% |
| CD4 mix | 1 | 50,57% | 49,56% | 51,13% |
| HCT116 | 1 | 49,27% | 46,35% | 62,66% |
| HEK293T | 1 | 53,21% | 49,61% | 52,27% |

**Interpretazione:** esiste informazione specifica del bersaglio, ma è più piccola della
distanza ingenua dal 50% in diversi confronti. In HCT116 γ=0 il vantaggio sul controllo è
2,75 punti percentuali, IC bootstrap per bersaglio [2,07; 3,45]. In CD4 γ=0 è 0,63 punti,
IC [−0,35; 1,55]: questo confronto non separa chiaramente il segnale dal controllo.
La centratura può abbassare l'accordo assoluto mantenendo informazione specifica:
su HCT116 γ=1 il vantaggio sul controllo rimane 2,91 punti.

**Limite:** il controllo «sempre aumento» usa i geni scelti dal predittore, non è una
pipeline alternativa né una raccomandazione per un invio. Gli intervalli sono condizionati
a queste sorgenti; non includono incertezza su nuovi contesti, e non sono intervalli VCC.
Gli scorrimenti non sono stratificati per numerosità cellulare. L'analisi è esplorativa.

## 2. Il riferimento stesso è debole; il 51–56% non è un tetto biologico

**Misurato:** con CD4 halfA che predice halfB, stessa condizione Stim48hr ma donatori
diversi, γ=0, l'accordo medio è 57,23%, contro 53,04% scambiando i bersagli.
La mediana è 58%. Questo confronto non è una replica tecnica pura: comprende differenze
fra donatori e una numerosità inferiore alla miscela completa.

**Misurato:** limitandosi, entro gli stessi primi 100 geni, a quelli con |effetto vero|/SE ≥ 2,
l'accordo aggregato γ=0 diventa 62,31% su K562 (2.765 coppie), 62,53% su HCT116 (2.466),
66,22% su HEK293T (2.469), 61,70% fra le due metà CD4 (7.018).

**Interpretazione:** c'è spazio per distinguere segno incerto da segno non trasferibile.
Non possiamo separare rumore e differenze biologiche da questi soli numeri. La selezione
usa la risposta vera, indisponibile nei contesti ufficiali: NON è un filtro applicabile
alla previsione e NON dimostra che un filtro predittivo raggiungerà il 66%.
Gli SE sono quelli quasi-Poisson del codice, non un'incertezza completa fra donatori.

**Misurato nel codice e nella cache:** `cd4_mix.se` è interamente NaN, intenzionalmente
nello stadio 98. Non si può quindi fare lo stesso controllo di affidabilità sulla miscela.
Il peso n/(n+100) usa il numero di cellule; non incorpora il disaccordo fra condizioni,
donatori o guide. A parità di pesi nominali, le sorgenti non hanno pesi effettivi uguali
(funzione `mix` in `src/vcc2026/multisource.py`).

## 3. Il t17 è confrontabile globalmente, ma non isola perfettamente la sorgente

**Misurato:** ricostruendo gli effetti con le ricette t15 e t17:

- mediana del q99 assoluto: 0,229091 contro 0,229116, quindi compensazione riuscita;
- rapporto del q99 per bersaglio, percentili 10/50/90: 0,918 / 0,992 / 1,088;
- 22 bersagli su 300 hanno un rapporto fuori da [0,8; 1,2];
- somma dei quadrati degli effetti: +6,67%;
- coseno fra i due vettori di effetti per bersaglio, percentili 10/50/90:
  0,714 / 0,815 / 0,882.

**Interpretazione:** non è una semplice riscalatura. HEK293T modifica direzioni e copertura,
mentre la compensazione globale lascia variazioni locali di ampiezza. Il risultato dirà
se conviene il pacchetto «HEK293T + nuova miscela + compensazione»; attribuirlo soltanto
all'informazione aggiunta dalla sorgente richiede un'ablazione ulteriore.
La previsione registrata rimane immutata; questa è una nota antecedente al suo punteggio.

## 4. Fedeltà, precisione dei segni e PDS sono oggetti diversi

**Verificato nel codice:** `src/vcc2026/bench.py:direction_components` espone
FID = k / max(n_pred, n_conf). Aumentare FID può significare maggiore copertura a precisione
invariata; non basta per dire «sbagliamo meno spesso il segno».
Il miglioramento t15 è reale, la sua attribuzione a maggiore precisione resta aperta.
Le percentuali nello spazio degli effetti dello stadio 103 non sono FID ufficiali.

**Ipotesi da testare:** se amplificare gli stessi effetti migliora PDS, parte del beneficio
può venire dal rapporto fra segnale e distorsione del generatore. Un coseno su vettori
riscalati positivamente sarebbe invariato; il percorso reale comprende composizione,
generazione e trasformazioni. Questo non dimostra un difetto nello scorer né individua
da solo quale passaggio causi il guadagno.

**Correzione logica:** se t16 perde rispetto a t15, non segue che l'ottimo sia necessariamente
fra 0,394 e 0,788. Il punto medio è un esperimento sensato, ma il confinamento dell'ottimo
richiederebbe ipotesi sulla forma della curva e sulla variabilità che non abbiamo verificato.

## 5. Il trasferimento al set finale non è ancora interamente parametrizzato

**Verificato nel codice:** gli stadi 45, 76, 98 e 100 chiamano `official_axis()` senza un
percorso. Il default è `raw/controls/gene_names.csv`, anche quando si cambia `--controls-dir`
o `--targets-csv`. D/E/F funzionano con questa parte del percorso se l'asse resta quello
attuale; un asse nuovo richiederà interventi. Il controllo che si ferma su un ordine diverso
evita errori silenziosi, ma non rende il percorso pronto ad accettare il nuovo asse.

**Verificato nel codice:** la centratura `AxisTable.common()` usa i bersagli presenti nella
cache. Cambiare pannello cambia quindi anche il riferimento sottratto, oltre ai bersagli
previsti. Il parametro γ=1 non conserva necessariamente lo stesso significato quantitativo
fra validazione e finale. Non è leakage di risposte ufficiali: è dipendenza dal pannello
pubblico usato per stimare la componente comune. Il suo impatto resta da misurare.

## Implementazioni future proposte, in ordine

| Priorità | Implementazione | Criterio per giudicarla |
|---|---|---|
| 1 | Estendere la diagnostica dei segni con controlli a bersagli scambiati, prevalenza dei segni, accordo fra repliche e numerosità per bersaglio | Vantaggio rispetto al controllo, stabile fra sorgenti e per fasce di numerosità; separare precisione e copertura nei banchi con verità nota |
| 2 | Piccolo esperimento incrociato ampiezza × generatore sui banchi esistenti, con stessi effetti e più semi; misurare effetti realizzati, n_pred, n_conf e k | Stabilire se l'ampiezza corregge attenuazione o compensa distorsioni; usare tutte le sei metriche, non promuovere il banco a previsione ufficiale |
| 3 | Parametro esplicito per l'asse genico lungo 98 → 100 → 45/76 → 48, con hash dell'asse nelle cache | Prova D/E/F con un asse riordinato e test negativo di cache incompatibile; parità su A/B/C |
| 4 | Conservare in CD4 mix la variabilità fra condizioni/donatori; valutare pesi che riflettano anche coerenza e precisione | Battere n/(n+100) su contesti e bersagli tenuti fuori, senza scegliere usando la risposta del contesto escluso |
| 5 | Ablazioni di HEK293T e dei pesi a scale controllate; sensibilità della centratura a sottopannelli | Separare beneficio della sorgente, scala e composizione del pannello; eventuali invii restano soggetti alla quota |

Queste sono proposte, non decisioni adottate. Non emerge dai dati una giustificazione
per un nuovo modello neurale prima di queste verifiche. Un generatore non va scartato
in generale dal solo t14, dove cambia anche l'ampiezza e mancano gli effetti Orion.

## Riproducibilità e limiti

`audit.py` produce `measurements.json`, con hash SHA256 delle sei cache, seme e risultati
per bersaglio. Per ripetere usare `--out` nuovo. Legge solo cache esistenti, senza generare
cellule, consumare quota o modificare dati esterni. Non sono stati letti di nuovo tutti
i grezzi a singola cellula, né verificati gli endpoint esterni.

Le misure nuove valutano effetti pubblici, non la verità nascosta A/B/C. Nessun risultato
qui dimostra da solo un miglioramento del punteggio ufficiale o la generalizzazione a D/E/F.
