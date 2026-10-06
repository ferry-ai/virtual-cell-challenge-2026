# HIPSCI: pooling congiunto prima dello shrink e cellule per ruolo

6 ottobre 2026. [adapter.py](adapter.py) copia r1 in una versione distinta,
conserva anche cloni con soli controlli e aggiunge `estimate_joint`: una chiamata
allo stimatore originale su tutti i donatori, prima dello shrink. Nessun voto
indipendente per ciascun clone. Si rifiutano pooling non autorizzati fra studi,
condizioni, modalità/chimiche e assi incompatibili; BIO ignoti restano un blocco.

**Verificato:** due [test piccoli](test_joint.py) passati, uguaglianza esatta
raw/SE/shrunk/n_cells/control_mean con il pooling originale. Il controllo-only
del terzo clone influenza la frazione di controllo e non può essere omesso.
La r1 conservava quei controlli solo quando nello stesso blocco di un target:
le sue quattro fixture restano valide nel loro perimetro, ma insufficienti
per il pooling congiunto fra cloni. Nessun fit reale o t36 usava questo adapter.

**Metadata reali verificati per hash:** [qualificazione](metadata_qualification_r1.json),
1.161.865 cellule totali: 626.781 con label di target assegnata, 8.241 NTC,
526.842 senza guida assegnata, una senza metadata. Il precedente totale catalogo
526.843 non supervisionate comprende le ultime due categorie, non due conteggi
in contraddizione. Le cellule senza guida rimangono nella banca per un eventuale
ruolo ausiliario; non ricevono un target inventato.

**Aperto:** label assegnata non prova ammissione/QC/crosswalk. Chimica ignota,
asse/count_sum/mask verificati nel consumer, confronto con input nativi, split
e integrazione nel mixer sono da completare. Nessun nuovo job o invio; la banca
reale non è stata consumata da questa fixture. [Metadata](../hipsci_adapter_r1/real_rows_r1/README.md).
