# Adapter di produzione Stack: implementato, non eseguito

29 settembre 2026. `stack_production_infer.py` legge il bundle preparato da
`stack_production_pack.py` e riusa le funzioni scientifiche del pilot congelato.
Non legge verità perturbata destinataria, non campiona cellule finali, non
impacchetta e non invia. Non è una prova di miglioramento né un modello adottato.

Richiede il confronto di conferma positivo e verificato per SHA, con tutte le
soglie numeriche ricontrollate. Richiede inoltre una decisione concreta, verificata
per SHA, che autorizzi l'inferenza su quel bundle e su quella versione dell'adapter
e riconosca il cambiamento di regime verso A/B/C. Questo documento non è quella
decisione. I risultati del pilot e della conferma non erano ancora disponibili
quando il codice è stato scritto.

La baseline è t25 senza ulteriore moltiplicazione. Per i 254 bersagli ammessi,
stesso seed Stack, stessa cache del controllo sintetico per numerosità, stessa
formula di correzione entro il supporto comune. Fuori dal supporto la baseline
è identica; per i 46 bersagli non ammessi è identica su tutti i geni. Gli input
dei contesti sono diversi, quindi la cache si ricrea per ciascun contesto.
Non si sovrappone questa modifica all'ampiezza di t28 senza una prova distinta.

I controlli completi vengono riassunti a blocchi per limitare la RAM. I 512
controlli preparati alimentano il modello. Per ogni bersaglio si salva subito
un NPZ senza pickle contenente i profili transfer e Stack esatti in float64,
seguito dalla ricevuta con SHA; ogni contesto completato ha una ricevuta propria.
Un output parziale non è una previsione pronta né autorizza a eliminare bersagli.
La revisione incrociata ha evidenziato il costo delle 35 matrici di controllo
sintetico. La cache ora conserva soltanto la loro somma per gene, eseguita con
lo stesso dtype prima della conversione float64 del helper. La formula usa
soltanto quella somma: un test con valori grandi float32 ne verifica la parità
bit per bit con la matrice completa. Ogni diagnostica misura i byte della cache.

Quattro test sintetici passati: integrazione a 600 geni con due target ammessi e uno
di fallback, parità esatta con la formula congelata e riuso corretto del controllo;
soglie della conferma e autorizzazione distinta; rifiuto di percorsi fuori bundle.
I test non caricano i pesi reali. Revisione incrociata del contratto del bundle
completata, con la correzione di memoria appena descritta; resta richiesta verifica
del runtime prima di una eventuale esecuzione.

`stack_profiles_to_cells.py` implementa ora il passaggio successivo: legge i
profili completi verificati per SHA e li campiona con l'identico percorso IID
Poisson del pilot, 400 cellule per target, seed 20260929 e librerie dei controlli
ufficiali completi. Scrive a blocchi con `SubmissionWriter`, usando il nome
parziale fino alla chiusura. Due test passati verificano parità bit per bit del
campionamento, asse/etichette del file e rifiuto di input alterati prima di creare
l'output. Non è stato eseguito su profili reali. La CLI richiede una previsione
concreta registrata che leghi SHA di codice, profili e conferma; questa previsione
non esiste ancora. Restano inoltre il packaging con lo stadio 48 e il consenso
distinto per l'invio VCC.

La selezione prospettica A/B del `PROTOCOLLO_STACK_AB.md` precede qualunque
promozione. L'adapter di produzione qui descritto usa l'input A; se fosse scelto B
servirebbe una versione distinta con il relativo input e la provenienza della
conferma B. L'esistenza del codice A non autorizza a ignorare quella selezione.
