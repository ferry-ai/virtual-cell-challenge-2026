# Scostamenti dal protocollo del secondo training, decisi prima di ogni suo numero

1 ottobre 2026, 03:35 CEST, Claude Code (sessione `07ebf08b`). Il [protocollo](PROTOCOLLO.md), scritto alle 02:40,
resta com'è. Questi scostamenti vengono dopo l'[esito del primo training](../cellnet_tecnico_2026-10-01/ESITO.md)
(03:20) e dopo la [profilazione del caricatore](caricatore/README.md) (03:31). Precedono il pre-passo e il lancio del
secondo training: quando sono scritti, del secondo training non esiste alcun numero.

1. **Dati (incidente `E-20260930-004`).** I tre dataset di K562 e RPE1 del protocollo (`rlab-k562-gwps-r2`,
   `rlab-k562-essential`, `rlab-rpe1`) hanno gli ID Ensembl al posto dei simboli e nessun gene sull'asse. Al loro posto
   entrano le riletture con `gene_name`:
   - `rlab-k562-essential-r2` e `rlab-rpe1-r2`, dal job 121;
   - `rlab-k562-gwps-r3`, dal job 122.

   Il pre-passo diventa `rlab-prepass-r5`, con gli argomenti del protocollo §2 e quattro processi; r4 resta come
   diagnosi.
2. **Codice (incidente `E-20261001-001`).** Il kernel `rlab-cellnet-r2` lancia un solo processo di training con
   `--arm desc=descriptors@cuda:0 --arm ident=identity@cuda:1 --workers 3 --eval-workers 3`. Il protocollo diceva due
   processi, uno per braccio, ciascuno con `--workers 2`. Con lo stesso codice:
   - i due bracci ricevono gli stessi lotti;
   - `read_csr` filtra il CSR direttamente;
   - la valutazione legge gli shard con tre processi;
   - la riserva della valutazione separa le letture dal resto;
   - il piano misura il throughput a regime.

   Il pre-passo r5 usa lo stesso codice: il nuovo `read_csr` dà la stessa matrice, e le impronte delle cellule ordinano
   da sé gli indici (`test_read_csr.py`).
3. **Ciclo di ripresa.** Il protocollo §3 lo escludeva perché il primo training lo aveva verificato su CUDA. Ma il
   checkpoint ora tiene modelli e ottimizzatori per braccio, quindi il ciclo si rifà, nello stesso kernel e prima del
   training: passi 50 e 100, entrambi i bracci, senza il controllo degli hash nelle tre corse brevi. Il training vero
   gli hash li controlla. Se il ciclo non passa, il training non parte.
4. **Budget:** invariato, 150 minuti per il training con valutazione ed esportazione. Il ciclo aggiunge qualche minuto
   di quota.
5. **Regola di lettura:** invariata (§4). In A si riportano, accanto a quelli del primo training, il throughput a
   regime (`plan.json`) e la frazione di attesa dei dati (`coverage.json`, `throughput`). Nessuna soglia nuova.
6. **La seconda ondata resta fuori**, come dice il §2. A549, Tian e Norman sono già pubblicati; KOLF e Southard sono
   in coda (job 124-126). Entreranno in un training successivo, con un suo protocollo scritto prima.
