# Risposta proposta ad Alfredo — 4 ottobre sera

**Bozza per Davide, non inviata.** Valutazione del messaggio inoltrato dal proprietario.
Controllato il branch remoto `codex/teammate-rlead`: dopo fetch arriva ancora a
`3d0646f90327c51feee484a397f0e433e749539c`. I risultati successivi (adattatori,
contrastiva e t34) sono quindi riferiti da Alfredo, non ancora verificati dai file.
[Riconti locali](audit_alfredo_r1.json), [codice](audit_alfredo.py).

## 1. Diagnosi: direzione sensata, causalità non ancora dimostrata

Condivido la priorità a dati più vari, CD4 e banchi più rappresentativi. Non possiamo
ancora concludere che i dati siano la causa principale rispetto a obiettivo, baseline,
selezione ed emissione. Il nostro v2, a dati e reti fissi, fa guadagnare PDS a RPE1
contro all (+0,0616) e perderlo contro prod (−0,0701): la coerenza della catena è ancora
decisiva. Fonti: [CP-0066](../../../docs/checkpoints/0066-banco-v2-t28-cinque-linee.md).

Correzioni specifiche:

- «Non nei pannelli essential» non equivale a «geni non essenziali». Inoltre il corpus
  attuale contiene anche K562 genome-wide e altri schermi; descrivere la distribuzione
  effettiva di target e pesi della loss, senza chiamare tutto il training essential.
- Il ponte Flex/3′ è una buona ragione per confrontare le fonti, non una prova causale
  della chimica: cambiano anche laboratorio, guide, tempi e stato cellulare. La metà
  Flex resta poco concorde con l'altra metà. Il report originale lo esplicita;
  la sua vecchia premessa «solo VIPerturb è Flex» è corretta dai metadati CD4.
- Il caso t28 non è dominato dal PDS: contro t25, PDS scalato −0,00126, nMAE −0,06878;
  fedeltà e reach compensano e la media sale +0,00461. Non accomunerei i quattro casi
  dicendo che cede sempre principalmente il PDS.
- Il limite di coseno 0,22 del calcolo MSE è **condizionato al modello e alle assunzioni**,
  non una soglia universale. La vostra nota lo delimita: u0 viene da un altro invio,
  due punti determinano due parametri e t28 cambia anche la dispersione. Un effetto
  quasi nullo non è una misura esatta del generatore a effetto zero.
- La verità rumorosa può attenuare la direzione stimata, ma MSE non implica da sola
  collasso di ampiezza. Il caso S-004 riguarda un cancello di miscela e non basta ad
  attribuirlo a quella loss. Servono confronti a dati, maschere e normalizzazione fissi.

Infine, 400 cellule previste × 5 semi riducono il rumore del generatore; non risolvono
il rumore della verità né l'incertezza fra contesti. Servono letture separate di questi
livelli, senza convertire una media locale in aumento atteso sul sito.

## 2. CD4: cellule pronte, banca per donatore da costruire, accesso da verificare

**Le dodici unità D1–D4 × Rest/Stim8hr/Stim48hr sono tutte acquisite e verificate**:
21.980.517 cellule idonee, 206.002.856.371 byte di shard. Ricevute indipendenti e conteggi
riconciliati nella [copertura CD4](../../generatore_e_banchi/ripresa_banco_v2_2026-10-04/copertura_cd4_r2.json).

Gli shard sono `.h5ad` sparsi con conteggi e metadati del contratto, negli output privati
Kaggle di `davideferrante11` e `davidmaisterx` (D4 sul secondo). Le tre tabelle aggregate
corrette già disponibili distinguono lo stimolo ma uniscono i donatori: copertura del
pannello 293 per Rest, 292 per 8 h e 292 per 48 h, 293 nella miscela. Non assumere 293
in ciascun donatore/stato. [Parità degli aggregati](../../sorgenti/universo_corretto_2026-09-27/RISULTATI.md).

**Non è ancora pronta la nuova banca completa contesto × donatore × bersaglio**, né
sono stati verificati gli accessi di `alfredo2003bit`. Ingestione conclusa non equivale
ad avere il pacchetto del vostro training già montabile. La consegna utile è un
pacchetto privato di pseudobulk, controlli e campioni con manifest/hash, ruoli e assi,
abilitato al lettore corretto e provato dal suo runtime. Non occorre muovere tutti
i 206 GB per allenare la rete sugli effetti. Non abbiamo modificato permessi da questa
valutazione e non prometto una data prima del dimensionamento del pacchetto.

## 3. VIPerturb: aggregati sì, cellule nel corpus no

Sono già presenti somme e stime aggregate VIPerturb, e la tabella `k562_viperturb`
è **già inclusa nella policy all** del nostro cubo. Aggiungerla una seconda volta
duplicherebbe la stessa fonte. La conversione cellulare e la sua integrazione nel
corpus non risultano completate nelle ricevute consultate.

Riconto dell'indice: **124/300 bersagli del pannello presenti; 123 hanno almeno 10
cellule**, soglia dello stimatore; 101 ne hanno almeno 30. Nel vecchio piano del ponte
sono 123 con stima intera e 115 presenti in entrambe le metà. Questi numeri distinguono
presenza nell'indice, numerosità e disponibilità delle metà, non certificano tutte le
coordinate degli effetti. [Indice](../../sorgenti/universo_nuovi_2026-09-27/viperturb_p1/index.csv).

Ha senso il confronto 3′ solo / Flex solo / entrambi, con peso assegnato prima e
gerarchia per linea: due schermi K562 non sono due linee indipendenti. Il solo Flex
lascia molti bersagli senza supporto; conservarli nel banco con fallback esplicito.

## 4. Banco CD4 sul pannello: sì, con due assi di validazione distinti

Usare gli ID del pannello per un banco pubblico è coerente con il regime C: il
bersaglio può essere visto in altre sorgenti. Non è leakage dei conteggi nascosti
di gara, ma ripetere selezione su quel banco lo rende sviluppo, non conferma.
Valutare il pannello intero e dichiarare quelli non giudicabili, senza scegliere a
posteriori solo effetti forti. Un banco sullo stesso assay e pannello è **più vicino**
alla gara; non è lo stesso regime biologico, né certifica le future D/E/F.

Proposta di split da congelare prima di aprire nuove verità:

1. **Donatore escluso:** lasciare fuori tutte e tre le condizioni di quel donatore;
   gli altri tre donatori alimentano il fit. Iterare i quattro fold, macro-media per
   donatore e condizione. È generalizzazione entro CD4, non a una nuova linea.
2. **Condizione esclusa:** lasciare fuori quello stimolo su tutti i donatori.
   Eventuale prova congiunta: il training esclude sia tutto il donatore sia tutta
   la condizione, non soltanto la loro intersezione.
3. **Bersagli C/J separati:** in J nascondere il target in tutte le sorgenti, ancore,
   medie di centrazione e trasformazioni apprese; riconciliare simboli e componenti.
   In C il target resta disponibile in altri contesti, come previsto dal problema.

Le attuali tabelle CD4 mescolano donatori: **non possono entrare nei fold per donatore**
così come sono. Ricostruire le fonti senza il donatore/stimolo escluso anche quando
servono soltanto a centrare un effetto. Non chiamare D4 una riserva indipendente solo
perché è l'ultimo donatore: potrebbe avere già contribuito agli aggregati usati nello
sviluppo precedente. I controlli del contesto escluso entrano solo al momento della
previsione; le sue risposte perturbate non decidono campioni, iperparametri o DE della loss.

Per rappresentatività: pannello dedicato più un insieme ampio, con risultati per
fasce di forza definite dalle sole fonti di training e per supporto. Non eliminare
i geni essential dal training principale. Per qualità: numerosità insieme a guide,
repliche e riproducibilità; non pesi globali proporzionali alle cellule e non selezione
soltanto su H1/KOLF. Tenere uguale peso fra contesti e usare affidabilità dentro il contesto.

## 5. Numerazione

Sì a **main canonico** e a una tabella degli alias ancorata all'entry ID. t32/t33 per
i due invii precedenti di Alfredo e t34 per il terzo sono una proposta ragionevole
da riservare insieme; qui non sono stati assegnati né rinominati file storici.

**Non dopo CP-0063:** su main ci sono CP-0064, CP-0065 e CP-0066; CP-0063 non è mai
stato scritto. Alla lettura attuale il primo nuovo numero è CP-0067. Assegnare il
blocco definitivo durante l'integrazione, preservando vecchi nomi, commit e entry ID
in una mappa di provenienza. Non riscrivere checkpoint già pubblicati per nascondere
la collisione. La quota di due invii del giorno è un'informazione riferita nel messaggio,
non ricertificata qui; nessun altro invio pianificato o avviato.

## 6. Contrastiva e divisione del lavoro

Favorevole a provarla come **ablation separata**, dopo il primo ibrido semplice
concordato con Davide. InfoNCE è un obiettivo surrogato di discriminazione, non il
PDS stesso né una garanzia di beneficio dopo la generazione. Stessi dati, baseline,
semi, capacità, budget e banco; conservare supervisione della media e guardia PDS.

Il termine sui segni deve essere differenziabile, per esempio una softplus del
margine firmato, e ricavare i segni affidabili solo dal training. Una differenza
fra `sign(pred)` e `sign(truth)` può cambiare il valore della loss lasciando invariato
il gradiente: lo abbiamo riprodotto nel codice GEARS
([audit](../../analisi/gears_nella_rete_2026-10-04/audit_upstream_r1.json)).
Costruire negativi fra bersagli distinti nello stesso contesto; non trattare repliche
dello stesso bersaglio come negativi. Verificare casi biologicamente simili e dipendenza
dalla composizione del batch. «Ampiezza fissata» va definita: gain di T fisso e residuo
limitato non equivalgono a norma totale fissa per bersaglio.

La divisione proposta evita duplicazioni: qui dati, ibrido e campioni; Alfredo rete
sugli effetti e banco CD4. È una proposta di coordinamento da confermare fra le persone,
non un messaggio già inviato o un'autorizzazione ad accedere ai loro job. Conviene
condividere un solo manifest di dati/split e un'unica implementazione del banco,
prima di confrontare loss. I nuovi risultati della contrastiva vanno verificati
quando i commit successivi a `3d0646f` saranno disponibili.
