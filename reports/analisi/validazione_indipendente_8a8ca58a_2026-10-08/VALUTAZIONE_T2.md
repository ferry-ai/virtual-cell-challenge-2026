# Valutazione di T2: la centratura su tutti i bersagli, sui fold a lignaggio escluso

8 ottobre 2026, VALIDAZIONE (Claude Code `8a8ca58a`). **Piano scritto prima dei numeri di queste corse**: vale
l'orario del commit che lo introduce; le corse sono lanciate dopo quel commit e i loro orari stanno nei
`launch.json`. La regola di lettura è il §8 del [contratto](PROTOCOLLO_v1.md) con la misura del
[v2](PROTOCOLLO_v2.md), **invariata**.

## Che cosa è arrivato, e quando

DATI-TRANSFER ha consegnato i **vettori comuni congelati** di T2, non gli effetti di T2:
`reports/modelli/dati_transfer_2026-10-08_01a11c34/HANDOFF_T2_MEDIE_r1.md` (file scritto alle 21:00:34, letto con
`ls --time-style=full-iso`), manifest `common_release_production_r1.json` (20:55:52). Il mio messaggio delle 19:06
chiedeva i vettori entro le 21:15 circa: **sono arrivati in tempo**. Li ho letti alle 21:27, mentre chiudevo i
documenti; la [raccomandazione](RACCOMANDAZIONE.md) delle 21:01 scrive «T2 non valutato», che era vero per gli
effetti e non teneva conto di questa consegna, sul disco da 26 secondi. Questo piano rimedia.

Il candidato T2 di produzione **non esiste ancora**: il fit finale di DATI-TRANSFER è preparato e attende il
consenso del proprietario (`STATO_r4.md`). Qui si valuta lo **stimatore**, nel solo modo possibile a lignaggio
escluso: rieseguendo lo stadio 100 di produzione sulla cache di ogni fold, con i vettori consegnati.

## Che cos'è T2

La release T1 (16 fonti), con le stesse tabelle, pesi, gamma 1, ampiezza e testa cis. Cambia **una** chiave della
ricetta: `common` passa da `panel` (a ogni tabella si toglie la media delle sue righe sul pannello) a un file con un
vettore per fonte, la media su **tutti** i bersagli di quella fonte. È la stessa modifica che fa il fit finale di
DATI-TRANSFER (`final_t2_driver.py`: `recipe.update(common=…)`), che ho letto e non modificato.

**Ammissibilità nei fold C.** Il vettore di una fonte dipende solo da quella fonte: nei fold si tolgono dalla cache
le tabelle del lignaggio escluso e i loro vettori non sono letti. Non vale per T e J, che richiedono la release
`T`. **Il regime J non si esegue:** tolti i bersagli nascosti da ogni tabella, il transfer prevede la sola testa
cis qualunque sia la centratura (per costruzione; misurato per gli altri bracci nella corsa r4).

## Verificato prima del lancio

[banco/t2_vettori_r1/verifica.json](banco/t2_vettori_r1/verifica.json): `common.npz` e `support.npz` hanno
dimensione e sha256 della consegna (`80103235…8b02`, `7481c9e0…ec89`); 16 fonti, le stesse del braccio T1; asse
ufficiale; valori finiti e nulli dove nessun bersaglio sostiene la media.

| Fonte | Bersagli dietro il vettore | | Fonte | Bersagli dietro il vettore |
|---|---:|---|---|---:|
| `orion_hek293t` | 18.080 | | `kolf_strong` | 1.641 |
| `orion_hct116` | 17.963 | | `hipsci_targeted_19` | 435 |
| `cd4_mix` | 11.593 | | `xu2023` | 200 |
| `kolf_pan_genome` | 11.498 | | `h1` | 199 |
| `k562` | 9.866 | | `tian2021_crispri` | 176 |
| `rpe1` | 2.282 | | `kolf_metabolic` | 97 |
| `jurkat_nadig` | 2.280 | | `kolf_chromatin` | 95 |
| `hepg2_nadig` | 2.274 | | | |
| `k562_essential` | 1.983 | | | |

Il minimo è quello scritto come segnale precoce nella strada S-011 prima di leggere questi vettori: venti bersagli.
Nessuna fonte è sotto; la quota dell'effetto proprio tolta dalla centratura scende dal 17–20 % delle tabelle
piccole di T1 a meno dell'1,1 %. La segnalazione DT-1 è soddisfatta **per costruzione**; che questo migliori la
previsione è ciò che si misura.

## Bracci, contrasti, controlli (corsa r5 del livello A)

| Che cosa | Come | Se fallisce |
|---|---|---|
| Braccio **T2** | ricetta di T1 con `common` = file consegnato, trovato nel kernel per dimensione e sha256 | — |
| **K2 = T2 − T1** | il contrasto del contratto: sola centratura, stessa banca | — |
| **T2 − T0** | contro la consegna: è il contrasto che la regola legge per una promozione | — |
| Parità di produzione | T0, R1 e T1 riproducono gli sha256 registrati, come in ogni corsa | la corsa non si legge |
| **Parità a gamma 0** | bracci `T2g0` e `T1g0`: senza sottrazione il file non deve cambiare nulla; ogni misura identica su ogni bersaglio | **invalido** |
| **Sostegno** | nel kernel: nessun gene votato da una tabella ha media non stimata nel suo vettore (lo stesso controllo del fit finale) | il kernel si ferma |
| Bersagli scambiati | `T2~shuffle`: `disc95` deve tornare a 0,5 | il banco non vede la specificità di T2: invalido |

## Come si legge

- **Livello A**, sei fold, bootstrap appaiato sui bersagli: `disc95` (primaria), `r_spec`, `sign50`, `reach`,
  `nmae_conf`, errore quadratico, per fold e in macro, per T2 − T0 e T2 − T1. Da solo può fermare, non promuovere:
  macro di `disc95` risolta negativa contro T0 = **sfavorevole**.
- **Livello B**, come in [LIVELLO_B.md](LIVELLO_B.md): `bench_v2` non modificato, emissione t28, 400 cellule,
  cinque semi, fold C-iPSC e C-K562, coppie `T2:T0`, `T2:T1`, `T1:T0`. `T1:T0` è già stata misurata nella corsa
  r1: deve ridare gli stessi numeri, ed è il controllo di riproducibilità del banco. Si lancia appena il livello A
  ha scritto gli effetti dei fold, se la corsa è valida.
- **Favorevole** solo con tutte le condizioni del §8 su T2 − T0: macro dei sei membri positiva e risolta su due
  fold, stesso segno senza Jaccard, nessun fold con media o PDS risolti in perdita, livello A senza `disc95`
  risolto negativo.

**Alla scadenza delle 23:00.** Il banco a sei membri sul fold K562 è durato 109 e 107 minuti nelle due corse di
oggi: lanciato dopo le 21:50 non può finire prima del freeze. Per la regola un livello B mancante alla scadenza è
**inconcludente**: stanotte T2 non può essere promosso, qualunque cosa dica il livello A, e comunque non c'è un
suo effetto di produzione né un invio autorizzato. L'esito completo si legge quando arriva il fold K562, e serve
alla decisione successiva (autorizzare o no il fit finale, e che cosa confrontare dopo).

## Precedenti

- **S-011** (voti di fonti piccole sotto la centratura sul pannello). T2 è ciò che quella strada indica come
  riapertura. Differenza di meccanismo: il vettore comune non è più stimato su 5–6 righe ma su almeno 95.
  Segnale precoce: i bersagli dietro ogni vettore, letti sopra prima del fit.
- **S-010** (composizione delle fonti). T2 non cambia chi vota: KOLF2.1J resta con quattro tabelle. Se il costo
  misurato oggi sui lignaggi non staminali viene dalla risposta comune di KOLF sottratta male, T2 lo riduce; se
  viene dallo specifico di KOLF, resta. Segnale precoce: `r_spec` e `disc95` per fold sui quattro non staminali.
- **S-006** (membri d'ampiezza trascinati dalla parte comune). Un guadagno del solo errore quadratico o dell'NMAE
  senza `disc95` né PDS si legge come ampiezza, non come specificità.
- ERRORI, errori di metodo: la soglia non si sposta dopo il numero; lignaggi già letti sono sviluppo, non conferma.

**Arresto:** parità fallita, sostegno mancante o `T2~shuffle` lontano da 0,5: la corsa non si legge e la
riproduzione minima va a DATI-TRANSFER.
