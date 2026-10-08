# Risultati della valutazione di T2 (centratura su tutti i bersagli)

8 ottobre 2026, VALIDAZIONE (Claude Code `8a8ca58a`). [Piano scritto prima](VALUTAZIONE_T2.md): commit `34984c39`
delle 21:36:52; il livello A (corsa r5, kernel `davideferrante11/vcc-validazione-logo-8a8ca58a-r5`) è stato
lanciato alle 21:40:43 e si è concluso alle 21:51; 63 esecuzioni dello stadio 100, 553 secondi.

**Che cosa è valutato.** Lo stimatore T2, cioè la release T1 con il vettore comune congelato di ogni fonte
consegnato da DATI-TRANSFER, rieseguito sulla cache di ogni fold senza il lignaggio escluso. **Non** è valutato un
effetto di produzione di T2: non esiste, il fit finale attende il consenso del proprietario. I numeri sono proxy e
punteggi **locali** su lignaggi di sviluppo, non punteggi VCC.

Tabelle scritte dai lettori: [contrasti di T2](TABELLE_T2_r5.md), lettura con la regola
([`disc95`](TABELLE_LIVELLO_A_r5_v2.md), [`disc` del v1](TABELLE_LIVELLO_A_r5_v1.md)).

## 1. La corsa è valida (misurato)

| Controllo del piano | Esito | Dove |
|---|---|---|
| Parità di produzione | T0, R1 e T1 ridanno gli sha256 registrati; il codice salvato da Kaggle è il pacchetto | [verification.json](banco/r5/completion/verification.json) |
| Identità dei vettori | il kernel li trova per dimensione e sha256 (`80103235…8b02`); ogni esecuzione di T2 dichiara `common: frozen` con quello sha256 | [analysis_data_files.json](banco/r5/completion_extra/analysis_data_files.json), [descrizione](banco/r5/descrizione_t2_r5.json) |
| Esclusione nei fold | i vettori del lignaggio escluso non sono letti: in C-K562 restano inutilizzati `k562` e `k562_essential`, in C-HEK293 `orion_hek293t` e `xu2023`, in C-iPSC le quattro tabelle KOLF e HIPSCI, in C-CD4T `cd4_mix`, in C-HCT116 e C-H1 la tabella omonima | stessa descrizione, `frozen_common` |
| Sostegno | nessun gene votato da una tabella ha media non stimata; il minimo di bersagli dietro un gene votato è 74 (Xu 2023), poi 93 e 96 (le due tabelle KOLF piccole): sopra il minimo di venti | [common_support.json](banco/r5/completion_extra/common_support.json) |
| **Parità a gamma 0** | gli effetti di `T2g0` e `T1g0` hanno lo stesso sha256 nei sei fold e in produzione; il contrasto vale zero su ogni bersaglio | descrizione, `gamma0_parity_sha256` |
| Bersagli scambiati | `disc95` di T2 scambiato fra 0,470 e 0,526 (T1 scambiato: 0,471–0,537); la differenza da T2 è risolta in ogni fold | [tabelle](TABELLE_T2_r5.md) |
| Riproducibilità | K1 ridà i numeri della corsa r1: macro `disc95` +0,0004 [−0,0005; +0,0013] | [tabelle](TABELLE_T2_r5.md) |

`hepg2_nadig`, `jurkat_nadig`, `rpe1` e `k562_essential` non votano su nessun gene: le loro tabelle non hanno
bersagli del pannello. I loro vettori esistono ma non entrano in nessuna previsione.

## 2. Che cosa cambia negli effetti (misurato, senza leggere la verità)

Sui due fold di cui tengo gli effetti nella radice dati ([descrizione](banco/r5/descrizione_t2_r5.json),
[parte comune](banco/r5/comune_t2_r5.json)):

| | C-K562 | C-iPSC |
|---|---:|---:|
| Copertura delle risposte, T2 contro T1 | identica | identica |
| Distanza di T2 da T1, in norma, rispetto alla norma di T1 | 10,1 % | 8,3 % |
| Quota degli effetti comune a tutti i bersagli, T1 | 0,02 % | 0,01 % |
| Quota degli effetti comune a tutti i bersagli, T2 | 0,63 % | 0,35 % |
| Norma di P, la risposta comune che la centratura sul pannello toglie | 8,47 | 8,82 |
| Norma di D, la riga media che T2 rimette | 3,34 | 3,85 |
| Pendenza di D su P | 0,11 | 0,19 |
| Coseno fra D e P | 0,29 | 0,44 |

**Misurato.** T2 non è «T1 con una media stimata meglio»: aggiunge a ogni bersaglio una stessa riga D, che contiene
l'11–19 % della risposta comune del pannello e, per il resto, una direzione diversa da quella.

**Interpretazione.** La media su tutti i bersagli di una fonte è la risposta comune di un'**altra popolazione** di
perturbazioni (migliaia di geni, in gran parte fuori dal pannello), non una stima più precisa della risposta
comune dei 300 bersagli di gara. Toglierla lascia nelle previsioni una parte comune che la centratura sul pannello
azzerava.

## 3. Livello A: sei fold, contro T1 e contro la consegna

Macro su sei fold, bootstrap appaiato sui bersagli, intervallo al 95 %; in grassetto i valori il cui intervallo
esclude zero.

| Misura (verso migliore) | K2 = T2 − T1 | T2 − T0 (la consegna) | per confronto, T0 − T0 senza centratura |
|---|---|---|---|
| `disc95` (alto), primaria | −0,0009 [−0,0032; +0,0015] | −0,0005 [−0,0030; +0,0020] | **+0,0080** [+0,0012; +0,0163] |
| `r_spec` (alto) | +0,0000 [−0,0002; +0,0003] | −0,0003 [−0,0006; +0,0000] | **−0,0005** [−0,0008; −0,0002] |
| `sign50` (alto) | **−0,0039** [−0,0062; −0,0018] | **−0,0042** [−0,0065; −0,0020] | **−0,0177** [−0,0212; −0,0141] |
| `reach` (alto) | −0,0003 [−0,0012; +0,0005] | −0,0003 [−0,0012; +0,0006] | **−0,0022** [−0,0034; −0,0011] |
| `nmae_conf` (basso) | **+0,0025** [+0,0013; +0,0035] | **+0,0026** [+0,0014; +0,0037] | **+0,0040** [+0,0024; +0,0053] |
| errore quadratico (basso) | **+0,0059** [+0,0002; +0,0111] | +0,0014 [−0,0043; +0,0068] | **−0,0252** [−0,0330; −0,0188] |

Per fold, `disc95` di T2 − T0: C-CD4T −0,0029, C-HCT116 −0,0014, C-HEK293 −0,0028, C-K562 +0,0003, C-iPSC +0,0038,
C-H1 0 (17 bersagli): **nessuno risolto**. La profondità di segno scende in modo risolto in C-CD4T, C-HCT116,
C-HEK293 e C-K562 (da −0,005 a −0,009); l'errore sui geni confidenti peggiora in modo risolto negli stessi quattro.

**Le due letture della discriminazione**, come promesso dal contratto v2:

| Misura | K2, macro | T2 − T0, macro | Lettura del §8 dal solo livello A |
|---|---|---|---|
| `disc95`, in vigore dal v2 (18:50) | −0,0009 [−0,0032; +0,0015] | −0,0005 [−0,0030; +0,0020] | nessun arresto; il livello A non promuove |
| `disc` stretta del v1, sei fold | **−0,0039** [−0,0073; −0,0006] | **−0,0035** [−0,0069; −0,0001] | arresto |
| `disc` stretta, i cinque fold dove è utilizzabile | −0,0026 [−0,0058; +0,0005] | −0,0020 [−0,0053; +0,0011] | nessun arresto |

La misura stretta su C-K562 usa **un** gene (è il motivo dell'emendamento v2) e quel fold dà il contributo più
negativo (−0,011): tolto, la macro non è più risolta ([ricalcolo](banco/r5/sensibilita_disc_t2_r5.json), che
riproduce al decimale le macro del kernel). **Vale la regola in vigore: nessun arresto dal livello A.** Le tre
letture hanno però lo stesso verso, negativo, e nessuna è a favore.

**Misurato.** T2 non migliora nessuna misura del livello A rispetto a T1 o a t36. La discriminazione non si
distingue; profondità di segno ed errore sui geni confidenti peggiorano di poco, in modo risolto, sui quattro
lignaggi non staminali.

**Interpretazione.** Coerente con il §2: la riga comune che T2 rimette non somiglia alla risposta del lignaggio
escluso. Non è un passo verso «nessuna centratura»: senza centratura la profondità di segno *sale* (ultima
colonna, letta al contrario), con T2 scende.

**Che cosa non dice.** Il livello A è un proxy nello spazio degli effetti; i sei membri possono muoversi in altro
modo (l'NMAE e la fedeltà del sito premiano anche la parte comune, S-006). Per questo il §8 chiede il livello B.
