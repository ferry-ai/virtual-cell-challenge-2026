# AMMI: wrapper biologico e pacchetto di codice

9 ottobre 2026, 16:55 Europe/Rome (orologio letto: 14:55 UTC).
Stato: implementato e verificato su fixture; fit biologico non avviato.
Verdetto: approfondire. Nessun beneficio predittivo nuovo dimostrato.

## Pronto

- `ammi_inputs_v3.py`: pin di file e codice; lettura degli output NTC di DATI;
  controllo di tutte le parti previste e di tutti i contesti; merge globale a
  64 cellule per strato con il codice originale; normalizzazione a profondità
  nativa; ancore annidate con fonti consumate ed esclusioni verificate.
- `training_data` risolve e apre soltanto i chunk dei lignaggi ammessi al fit.
  Seleziona fino a 64 target per contesto dopo disponibilità ESM2 e supporto,
  con hash di soli identificatori. Ogni lacuna resta nell'audit; D-053 incompleto.
- `ammi_guard_v3.py`: codice `metrics.py` indipendente importato per hash;
  disc95 e bootstrap confrontati direttamente con il banco. Le verità interne
  si leggono attraverso un confine distinto dal training. Nessuna verità outer.
- `run_ammi_pilot_v3.py`: richiede CUDA reale, misura risorse, verifica tutti i
  pin, controlla parità nulla prima del fit, conserva il checkpoint e ne prova
  la ricarica. Esporta ogni contesto esterno separatamente e il controllo swapped
  dai checkpoint cells, con residuo nullo quando manca ESM2 e maschere invariate.

Il formato runtime richiesto è dichiarato nel manifest del pacchetto. Le mappe
dei percorsi sono solo locali al runtime: non vi sono URL temporanei nel codice,
nel pacchetto o in questo report. Nessun nuovo trasferimento o lancio eseguito qui.

## Pacchetto corrente

`ammi_code_package_r4/manifest.json`, payload `ammi_code_package_r4/ammi_code.zip`:
37729 byte, SHA256 `7438df781a800b2605badd9c539deab6153ef29ae14be4446e7dfeaf3b562d57`.
Il precedente pacchetto r3 resta conservato. Il manifest dichiara 14 combinazioni:
per ciascuno di C-K562 e C-iPSC, cells/none con semi 17,29,43 e mean con seme17.
Non è una ricevuta di lancio o consumo. Il piano di concorrenza dipende dal preflight
effettivo degli account; nessuna quota si deduce dal solo pacchetto preparato.

`combined_tests_r12.txt`: **64 test PASS**, incluse 22 prove AMMI. Nuove prove su
corruzione di hash, parti NTC mancanti, duplicati cellulari, normalizzazione,
risposte escluse mai risolte, ancore che incorporano il lignaggio della riga,
equivalenza numerica col banco, cache originali con asse separato, review pendente,
checkpoint ricaricato, supporto invariato e rifiuto della CPU per il fit biologico.
Le prime esecuzioni hanno individuato due errori nelle asserzioni delle fixture,
poi corretti; il fallimento salvato in `ammi_tests_r4.txt` resta conservato.
Non erano misure biologiche.

Verifiche generali: `repo_tests_r8.txt`, 290 test in 401,651 secondi, tre errori
per il modulo già mancante `cell_eval2.config` e un fallimento del controllo
documenti durante la creazione concorrente di un file DATI. Nessuno dei tre
errori di dipendenza riguarda il nuovo wrapper. I controlli documentali successivi
`docs_check_r21.txt` e `docs_check_r22.txt` passano. Nessuna dipendenza condivisa
è stata installata o modificata per nascondere questi esiti.

## Dipendenze ancora aperte

1. DATI ha comunicato NTC `davidmaisterx/dt-ntc-inputs-01a11c34-r4` e
   `davideferrante11/dt-ntc-inputs-01a11c34-r5` RUNNING. Le ancore r4 risultano
   COMPLETE secondo DATI, che ne sta recuperando e verificando i 19 NPZ.
   Questi stati sono comunicazioni operative, non una nostra verifica degli array.
2. Manifest numerici completi, hash, localizzazione privata e accesso effettivo
   su davidmaisterx; nessuna dichiarazione di input pronti prima del controllo.
3. Accordo sul routing e sulla guardia, richiesto in `RICHIESTA_GUARDIA_AMMI_r3.md`
   e precisato in `NOTA_ROUTING_AMMI_r4.md`. K562 BULK e controlli GWPS/essential
   appartengono a studi diversi; il confronto non è di campioni abbinati.
   La verifica del controllo positivo dell'ancora annidata può fermare il fold
   prima del training. Nessuna sostituzione post hoc della verità o dell'ancora.
4. Preflight e verifica del consenso applicabile ai fit, quindi esecuzione reale
   CUDA dei bracci congelati. I pacchetti pronti non autorizzano nuovi consumi.

## Per arrivare a un candidato da inviare

Dopo i passaggi sopra: consegna di predizioni con hash, ricevute e controlli a
VALIDAZIONE; lettura per lignaggio, variabilità fra semi e banco a sei membri su
almeno due fold. Solo un esito conforme alla regola congelata giustifica una
proposta di adozione. DATI integra poi il componente senza duplicare scala,
ampiezza o cis; generazione, confezionamento e invio richiedono i rispettivi
controlli e autorizzazioni. Non sono stimate durate non misurate.

I sei fit ESM2 già recuperati restano in `completed_fits_handoff_r1.json` e
`CONSEGNA_SEI_FIT_r1.md`. La lettura C/J-iPSC è di VALIDAZIONE, non viene riaperta
dal wrapper. Il ripiego ESM2 richiede semantica esplicita e conteggio del delta:
copertura completa dei target può renderlo inerte. T3 non sostituisce T0 nel
protocollo AMMI congelato. Nessuna promozione o submission deriva dai test tecnici.
