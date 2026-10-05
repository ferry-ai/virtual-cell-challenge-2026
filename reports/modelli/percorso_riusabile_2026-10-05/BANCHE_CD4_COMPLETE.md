# Dodici banche CD4 persistenti

Heartbeat 5 ottobre, dalle 03:23 CEST. Evidenza tecnica, non esito di training.

`snapshot_r11/state.json` verifica tutte le dodici unità CD4: **21.980.517
cellule ammesse, 19.160.769.062 byte di banca**. Le versioni private Kaggle,
codice, ricevute e file attesi sono riconciliati. Il log dell'ultima unità
(`bank_stim8hr_live_r1.json`) mostra D3 Stim8hr completo, 1.691.290 cellule;
il periodo dopo l'ultimo shard comprendeva la finalizzazione degli output.
Non era una nuova ingestione o un rilancio. Le matrici restano sul cloud.

`snapshot_samples_r3/state.json` verifica sei campioni persistenti: Rest D1–D4
e tutti gli stati D4, senza contare D4 Rest due volte. Totale 52.964.362.982
byte. Stim48hr D1–D3 continua nei tre job già accettati.

Avviati e da seguire `vcc-samples-cd4-d1-stim8hr-r1` e
`vcc-samples-cd4-d2-stim8hr-r1` su davideferrante11. Preflight r4 sui tre account,
ricevute in `sample_launches.jsonl`, avanzamento in `samples_live_r4.json`.
D3 Stim8hr resta da lanciare: cinque sessioni impegnate sull'account proprietario.
Usare `launch_samples_r2.py` con snapshot r11 e un nuovo preflight quando si
libera uno slot; non duplicare gli undici campionamenti già accettati.

**Ostacolo al terzo account misurato:** `third_input_access_r1.json` registra
HTTP 403 per la banca Stim8hr e per entrambe le parti KOLF da davideferante.
È un limite di accesso agli output privati, non una stima della sua RAM o quota.
Il probe non scarica file né modifica condivisioni. Non duplicare i dati per
aggirarlo; una futura condivisione privata richiede verifica sul consumatore.

Release CD4 aggiornata in `release_cd4_r3.json`, SHA256
`f01a22dbf17c5608e67aff94d46be27725a39ad86a2c87bcc6c39f19da87d816`.
R1 e r2 restano intatte; la release r3 è completa per i pseudobulk CD4,
incompleta per i campioni e non rappresenta l'intero corpus D-053.

**Oltre CD4:** rilette le ricevute KOLF già esistenti
(`reports/sorgenti/ingestione_completa_2026-10-03/kolf/esito_verifica_r1/source_complete.json`):
2.659.209 cellule, 133 shard in due parti verificate; non rifare ingestione.
Il produttore CD4 non va applicato invariato: scrive `line_group=CD4T` e richiede
shard omogenei per identità biologica. Per il successivo adattatore KOLF servono
gruppo iPSC coerente con gli split, verifica di tutte le identità e input
congelati. Non è stato lanciato un banco KOLF con etichette CD4.

Ancora aperti: ultimo lancio CD4 e completamento campioni, banche delle altre
sorgenti e catalogo completo, collegamento reale al trainer di release/asse/
maschere/split/ancore/loss e ricevute dopo resume, export e valutazione t28.
La lettura congiunta D1 Rest verificata nel turno precedente resta una prova
di consumo senza fit. Nessun nuovo training, invio, pubblicazione o push.
