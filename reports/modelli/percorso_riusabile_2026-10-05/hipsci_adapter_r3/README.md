# HIPSCI: consumer della banca persistente, ricetta originale

6 ottobre 2026. [Pacchetto](prepared_r2.json) e [lancio](launch.json) del derivato CPU
su `davideferante`, con mount del producer già chiuso. Nessuna nuova ingestion,
trasferimento di grezzi o matrice locale. Non è il fit completo né un invio VCC.

[policy.py](policy.py) dichiara la chimica non riportata in un namespace isolato
al solo studio; non inventa una chimica né la fonde con altri studi. Le identità
target seguono il campo gene della `Guide_Call` nel converter originale
`reports/sorgenti/corpus_cellulare_2026-09-30/adapters.py` (_hipsci_blocks).
Solo corrispondenze esatte al pannello originale congelato; nessun alias dedotto
o esclusione per asse di espressione. Tutti gli altri target restano inventariati,
insieme a UNASSIGNED (ruolo ausiliario aperto) e NO_METADATA (identità irrisolta).

Sul pannello t25/t28 sono presenti cinque label native: EZH2, GIGYF2, NT5DC1,
STT3A, ZNF526; 7.583 cellule di target e 8.241 NTC nella banca. Questo conteggio
precede min_cells10 e le maschere: non equivale a cinque effetti già verificati.
Le 19 linee/cloni condividono un voto di fonte, pooling donatori prima dello
shrink, stessi pseudo0,5/min_expected1/phi0,2. I target fuori pannello non sono
esclusi dal catalogo né dichiarati risolti per futuri modelli.

**Verificato localmente:** due [fixture](test_policy.py), equivalenza esatta
con lo stimatore originale, mantenimento del clone con soli controlli e dei ruoli
non supervisionati; nessun pooling con altro studio. Bootstrap contiene input
e codice con hash; runtime verifica receipt/count_sum/rows/mask/asse/pannello,
RAM e disco prima di stimare gli effetti.

**Attendere output reale:** `fit_receipt.json` e NPZ con hash, donatori/righe
effettivi. Provider RUNNING non certifica consumo o risultato. Output produzione
con hidden vuoto non è validazione C/J. Dopo verifica servirà integrare la fonte
in una nuova release del mixer; t36 rimane immutato e non viene reinviato.
