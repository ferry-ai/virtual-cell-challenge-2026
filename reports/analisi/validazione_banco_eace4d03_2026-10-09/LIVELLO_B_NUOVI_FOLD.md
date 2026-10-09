# Sei membri su tre lignaggi nuovi per il banco: che cosa si leggerà, scritto prima che esistano le cellule

9 ottobre 2026, 22:55, VALIDAZIONE (Claude Code `eace4d03`). **Nessuna cellula vera di HCT116, HEK293T o CD4T è
stata estratta per il banco**: l'estrazione è chiesta a DATI-TRANSFER ([messaggi](MESSAGGI.md), 21:30) per
decisione del proprietario. Questo piano fissa ora bracci, coppie e regole, così che la prima lettura a sei membri
su quei lignaggi sia un confronto registrato e non un'esplorazione. Vale il §3 del [contratto v3](PROTOCOLLO_v3.md);
il §8 del contratto v1 non cambia.

## Perché questi fold contano

Il banco a sei membri esiste oggi su K562 e su iPSC. Due conclusioni dell'8 ottobre poggiano su quei due soli
lignaggi, e una è nata proprio su uno di essi:

1. **L'ampliamento delle fonti da quattro linee a t36** costa PDS al fold K562 (−0,10, risolto) e ne dà al fold
   iPSC (+0,07): «KOLF2.1J costa ai lignaggi non staminali» (CP-0069, S-010).
2. **Togliere le tabelle KOLF** dà sul fold K562 +0,030 di media e +0,117 di PDS, risolti: è un'ipotesi, perché
   quel fold è lo stesso su cui è nata.

HCT116, HEK293 e CD4T sono lignaggi non staminali che **non hanno contribuito a formulare l'ipotesi a sei membri**
(nel livello A erano già stati letti, in modo esplorativo). Sono fonti di ogni ricetta da settembre: restano
sviluppo, non conferma indipendente. Ma sono il dato più vicino a un test dell'ipotesi che la banca offra.

## Che cosa si esegue, per ciascun fold nuovo

`bench_v2.py` senza modifiche, emissione t28, 400 cellule per bersaglio, cinque semi, scorer `cell-eval2` 0.16.0,
sul conto dove stanno le cellule estratte. Bracci, tutti già scritti dal livello A per quel fold (corse r1 e r3 del
banco dell'8 ottobre, sha256 nelle loro ricevute di consumo):

| Braccio | Fonti |
|---|---|
| `T0` | t36 senza il lignaggio del fold |
| `P4` | le quattro linee della ricetta t22/t28, senza il lignaggio del fold |
| `P4h` | le quattro linee più H1, senza KOLF2.1J, senza il lignaggio del fold |
| `T1` | T1 senza il lignaggio del fold |

Corse: *controllo* (T0 contro T0 a righe scambiate, un seme: il PDS deve cadere, altrimenti il fold è invalido);
*intero*, coppie `T0:P4` (K0), `P4h:T0` (composizione), `T1:T0` (K1). Per CD4T la verità primaria è `Rest` con i
quattro donatori; `Stim8hr` e `Stim48hr` sono strati, letti a parte e mai contati come fold.

## Come si leggerà

| Domanda | Regola, fissata ora |
|---|---|
| L'ampliamento costa ai lignaggi non staminali? | «Confermato sui lignaggi nuovi» se `T0:P4` è risolto negativo sul PDS o sulla media dei sei in almeno due dei tre fold e in nessuno risolto positivo. «Smentito» se è risolto positivo in almeno due e in nessuno negativo. Altrimenti «non risolto» |
| Togliere KOLF aiuta i lignaggi non staminali? | «Confermato» se `P4h:T0` è risolto positivo sulla media dei sei in almeno due dei tre fold e in nessuno risolto negativo, PDS compreso. «Smentito» se risolto negativo in almeno due. Altrimenti «non risolto» |
| T1 si distingue da t36? | Il §8 com'è, con la macro a peso uguale per lignaggio su tutti i fold di livello B disponibili |

Un'ipotesi confermata qui diventa un **candidato da proporre al Lead** (una ricetta a cinque fonti, da generare e
inviare con una previsione registrata): non è una promozione, perché nessun lignaggio in banca è conferma
indipendente, e il fold iPSC resta a dire quanto si perde dove KOLF aiutava. Un'ipotesi smentita si scrive in
STRADE con lo stesso rilievo.

## Che cosa serve per partire

Le estrazioni chieste a DATI-TRANSFER (formato, selezione delle cellule e conto nei [messaggi](MESSAGGI.md)). Gli
effetti dei bracci sono già uscite private del conto `davideferrante11`
(`vcc-validazione-logo-8a8ca58a-r1` e `-r3`, file `effects/<braccio>__<fold>.npz`): nessun passaggio fra account.
Il lanciatore è quello di [banco/livello_b_esm2.py](banco/livello_b_esm2.py) con i bracci presi per percorso
dall'uscita del livello A; va adattato e provato quando esistono il nome e lo sha256 delle estrazioni.

## Precedenti

- **S-010** (fonti del transfer): la scomposizione dell'ampliamento è stata letta a sei membri su due lignaggi; qui
  si legge su tre lignaggi che non hanno scelto l'ipotesi, con la regola scritta prima.
- **S-009**, CP-0065 (rumore del banco): cinque semi, 400 cellule, differenza che conta solo se risolta; guardia
  sul PDS per fold.
- **S-011**, **S-012** (T1, T2): gli stessi bracci si rileggono sui fold nuovi senza cambiare regola; un esito
  inconcludente su due fold può restare tale su cinque.
- ERRORI: una riserva già valutata chiamata indipendente (CP-0050): questi lignaggi sono sviluppo e lo si dice.

**Segnale precoce e arresto:** se il controllo non abbassa il PDS locale il fold è invalido e non entra in nessun
conteggio. Se le cellule estratte per bersaglio sono meno di quattro il banco scarta il bersaglio; un fold che
resta con meno di 30 bersagli si legge solo come descrittivo.
