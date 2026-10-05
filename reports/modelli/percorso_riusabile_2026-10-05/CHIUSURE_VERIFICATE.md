# Chiusure verificate il 5 ottobre, circa 12:23 CEST

`snapshot_samples_r5/state.json`: dodici campionamenti CD4 completi e persistenti,
106.829.811.245 byte, con versioni private, codice e ricevute riconciliati.
Le dodici banche CD4 erano già verificate in `snapshot_r11`. Nuova release
`release_cd4_r5.json`, senza modificare le precedenti. Nessuna matrice riscaricata.

`snapshot_other_r2/state.json`: KOLF, HCT116 e HEK293T completi e persistenti,
cellule, provenienza, codice salvato e file attesi riconciliati. Nessun guasto.
Complessivamente le quindici unità di banca contengono 32.583.194 cellule ammesse
e 26.997.423.795 byte di artefatti. Non rappresentano ancora l'intero catalogo.

Per i tre nuovi banchi, selezioni al livello 128 già definite:
KOLF 1.425.550 cellule, HCT116 1.928.264, HEK293T 2.329.024. Questi sono ancora
locatori, non matrici campionate autonome: materializzarle senza ricampionare,
dimensionando e se necessario partizionando gli output, senza tagliare cellule
per rientrare nel disco. Mantenere indici globali e verificare la ricomposizione.

I quattro job seguiti sono conclusi. Il prossimo lavoro non è aspettarli o
rilanciarli: completare i campioni delle nuove sorgenti, la copertura delle altre
linee del catalogo e l'integrazione effettiva nel trainer, con release, hash,
asse, split e ricevute di uso nella loss/resume. Training esteso non avviato;
i 18 fit precedenti restano preliminari, con valutazione t28 ancora da fare.
Automazione attiva; nessuna pubblicazione, cancellazione o push Git.
