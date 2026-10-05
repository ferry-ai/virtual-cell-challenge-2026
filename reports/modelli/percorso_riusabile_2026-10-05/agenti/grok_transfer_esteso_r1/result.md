# Transfer lineare esteso — esito del 5 ottobre 2026

Agente: Grok. Cartella di lavoro: `agenti/grok_transfer_esteso_r1`. Nessun commit, push, invio VCC, lancio HIPSCI o fit.

**Esito:** il refit non è stato lanciato. Il gate `run_refit` si ferma prima di leggere matrici. La ricevuta sul pin chiesto è `refusal_r3.json`, da `admission_r3.json` (catalogo r7). Due passaggi precedenti restano nel folder e non vanno letti come conteggi: `admission.json` cercava `bank.state` e ha contato 0 parti HIPSCI; `admission_r2.json` ha marcato come adapter aperti anche le 18 schede `ingested`, che non hanno quel campo.

**Lettura successiva, osservata dopo quel pin.** Sul disco c'è anche `cloud_catalog_r8/manifest.json`, SHA256 calcolato `272fced871671d7ab6295c0e67b29bec94a5275c20fdd67fc2ab3754897b6fb4`, `training_ready` false. Il README di r8 lo dichiara indice di storage, non manifest ammesso al fit. `hipsci_verified_r4/state.json`: fitness 12/12 con stato `remote_complete_union_checked`; nonfitness 11/12 `incomplete`; 23 job `remote_complete_manifest_checked` e 1 `not_complete`; `training_ready` false. Il README di r8 scrive che la parte aperta è p8 su `davideferrante11` ancora RUNNING, e che catalogo, QC, feature, assi, accessi e launcher restano aperti. Il pin del gate non è stato spostato su r8 e quella parte non è stata rilanciata.

## Blocco, osservato

Manifest r7, SHA256 `0c786da9155360e2cbe01604dba37ab5141e71022880be1ab20a4e4fb2f03678`, `training_ready` false. Catalogo `catalogo_r4` ricalcolato sullo stesso hash dichiarato da r7: **100/100 record con `role` unresolved**. `fit_inputs` è vuoto. `required_context_ids` contiene tutti i 100 record.

- Nessun record ha `transfer_source_id`. I 12 `unit_ref` espliciti sono i quattro donatori CD4 per Rest, Stim8hr e Stim48hr. Senza alias esplicito il codice non li attacca a `cd4_mix` e non li aggiunge come dodici fonti nuove.
- Adapter esplicitamente vuoto o ancora richiesto dallo stato di catalogo: 15 record `remote` (lista in `admission_r3.json`). Le schede `ingested` non hanno il campo adapter: sono `adapter_field_absent`, non una seconda scoperta.
- HIPSCI sul pin r7, da `hipsci_verified_r2/state.json`: fitness 7/12 e nonfitness 7/12, stato `incomplete`. 14 job con campioni verificati e `count_sum.npz`; 10 `not_complete`. Sulle 14, `consumer_hashes_verified` è false. La lettura r4 qui sopra è successiva e non sostituisce questo pin. Ledger letti entrambi: `hipsci_partition_r1/launches.jsonl` ha 3 slug accettati, tutti `davidmaisterx`; `hipsci_shared_r1/launches.jsonl` ha 21 slug accettati (8, 8 e 5 sui tre account). In 16 righe del ledger condiviso `original_planned_slug` è diverso dallo slug lanciato, per esempio `davidmaisterx/vcc-derivatives-hipsci-gwnonfit-p1of12-r2` lanciato come `davideferrante11/vcc-derivatives-hipsci-gwnonfit-p1of12-r2`. Nessun nuovo lancio HIPSCI.
- iPSC: dataset privato `davideferante/vcc-tian-ipsc-sample-input-r1`. Il produttore nel manifest resta `davideferante/vcc-derivatives-tian-norman-r1`. SHA della ricevuta originale `1282d5ee30f1dbc216e37e4a038fc5e88153a632c127e6d9d686ecaeda76e5dd`. Accesso fra account non è nel manifest.
- Norman: lo status Kaggle di quel kernel, letto in questo preflight, è `KernelWorkerStatus.ERROR`. r7 conserva comunque la ricevuta della banca `norman2019` con `count_sum.npz`. Lo stato ERROR del kernel non è stato letto come perdita dei file. Il kernel non è stato montato e non è stato ripubblicato.
- In r7 `units`: 37 banche `remote_complete_manifest_checked`; 34 campioni allo stesso stato; 3 unioni `remote_complete_union_checked` (`kolf_pan_genome`, `orion_hct116`, `orion_hek293t`, versioni esplicite nel manifest). Due voci HIPSCI in `units` non sono oggetti banca. `consumer_access` è `not_verified` su 12 voci e assente sulle altre.
- Modalità lette dal catalogo, non fuse: CRISPRi 19, CRISPR 28, CRISPRa 4, KO (Cas9) 1, CRISPR-cas9 6, CRISPR-cas13 1, drug 10, più ORF, citochine e ADT. `jurkat_gse249595` ha nello stato la frase sulle guide assenti. I due HIPSCI genome-wide hanno nello stato la frase sui NTC scarsi. Tahoe non è in `catalogo_r4` e non è stato aggiunto. `rlead-bench-cube-r2` è citato in r7 come pilot aggregato e il consumer lo rifiuta fra gli input.
- La cache locale `processed/multisource_2026-09-27_r9` contiene già `k562.npz`, `cd4_mix.npz`, `orion_hct116.npz`, `orion_hek293t.npz` e le parti CD4. Non è stata ricalcolata.
- Preflight del 5 ottobre, 20 kernel più recenti per account, più lo status Norman. RUNNING osservati: `davideferrante11/vcc-derivatives-rlab-k562-gwps-r3` e `davideferante/vcc-derivatives-hipsci-targeted19-r1`. Nella stessa finestra `davidmaisterx` non ha RUNNING o QUEUED. Una lista da 100 righe non porta una colonna di status, quindi non è un censimento di tutti gli slot. Il fit non è stato rinviato per gli slot: l'input non è ammesso.

## Implementato

`linear_effects.py` stima con `effects_from_pseudobulk`, `min_expected` 1, pseudoconteggio costante 0,5, controlli dello stesso donatore etichettati solo `NTC` → `non-targeting`. Legge `count_sum.npz` e rifiuta `mean_proportion`. Non unisce le condizioni. Azzera le colonne non misurate prima del totale e rimette NaN se la maschera del bersaglio o del controllo è falsa. Toglie dal fit il gruppo tenuto fuori, controlli compresi, e ogni componente compound che interseca un bersaglio nascosto. Componenti illeggibili fermano il run: nessuna separazione su punteggiatura.

`linear_transfer.py` mescola con `mix`, peso 1, ampiezza 1,576, gamma 1, `reliability_scale` 100, poi rifiuta il fit se il manifest non è r7, se un ruolo è unresolved, se manca `transfer_source_id`, se la matrice non è `count_sum`, o se compare `rlead-bench-cube-r2`. L'arm espanso deve contenere le quattro fonti di `configs/recipes/t25.json`. Quattordici fixture in `test_linear_refit.py` passano. Non sono un fit sul corpus.

`trainer_stream_v1` resta il loop di loss su popolazioni e cellule, con le fixture già descritte in `TRAINER_r1.md`. Non chiama lo stimatore t25 né `mix`. `features.verify` non è stato trattato come preparazione delle ancore.

## Protocollo, registrato prima di ogni punteggio

`protocol.json` è stato scritto prima di `admission.json`. Il fattore unico è l'insieme delle fonti. Restano fissi peso, ampiezza, gamma, shrinkage, stimatore e l'emissione t28: 400 cellule, semi del generatore 20260912 con indici 0–4, scala effetti 1,5, dispersione per gene 1. Split `r-lead-2026-10-02`, regimi C e J. «Risolto» è `abs(media) > 2 * sd / sqrt(5)`. Una linea è favorevole solo se il delta dei sei membri è risolto positivo, anche senza Jaccard, il PDS non è risolto negativo, e il punteggio locale dell'arm espanso è almeno 0,100. Sulla prima linea, un delta J risolto negativo ferma le altre. La loss non decide. Un esito negativo non toglie la fonte dal corpus. Non è un punteggio VCC e non promuove un modello. CP-0052 resta la lettura di t28: 0,144845 è il massimo osservato e non ha superato la soglia congelata. S-010 resta il precedente sulle fonti in più.

## In attesa

Il confronto accoppiato, il fit cloud e il banco. Parti HIPSCI ancora aperte: le segue l'altra sessione. Ruoli, QC, alias di transfer, mount iPSC fra account e mount Norman restano da chiudere su un manifest nuovo. Questo percorso non dichiara il corpus completo.

## Ipotesi

Nessuna sull'effetto delle fonti nuove. Il protocollo dice come si leggerà il numero quando il gate sarà aperto.
