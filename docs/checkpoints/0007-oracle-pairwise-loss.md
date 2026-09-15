# CP-0007 — Primo oracolo numerico: confronto pairwise sulla loss

- **Data:** 2026-09-13
- **Tipo:** osservazione
- **Redatto da:** agente (Grok 4.6)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Si può verificare un'affermazione numerica su due loss — medie, differenza
media e conclusione — ricalcolandola da un CSV, senza un modello linguistico
e senza un vincitore precompilato?

## 2. Cosa è stato fatto

Contratto scritto prima del codice: [`docs/oracle/CONTRATTO.md`](../oracle/CONTRATTO.md).
Implementazione autonoma in `src/oracle/`, senza modifiche a `src/orchestrator/`
né a `src/vcc2026/`. Fixture sintetici in
`src/oracle/fixtures/pairwise_loss/`. Test in
`tests/test_oracle_pairwise_loss.py`. I risultati attesi dei fixture sono
stati calcolati a mano con `decimal.Decimal`, non generati dal verificatore.

```
.\scripts\py.cmd -m unittest tests.test_oracle_pairwise_loss -v
.\scripts\py.cmd -m oracle --csv src\oracle\fixtures\pairwise_loss\example.csv --candidate src\oracle\fixtures\pairwise_loss\correct_candidate.json --config src\oracle\fixtures\pairwise_loss\config_default.json --report reports\oracle\example_pass.json --summary reports\oracle\example_pass.txt
```

CSV di riferimento (tre casi, pesi uguali):

```
case_id,loss_a,loss_b
c1,0.20,0.30
c2,0.40,0.35
c3,0.30,0.40
```

Calcolo a mano, indipendente dal verificatore:

```
mean_a = (0.20 + 0.40 + 0.30) / 3 = 0.90 / 3 = 0.30
mean_b = (0.30 + 0.35 + 0.40) / 3 = 1.05 / 3 = 0.35
delta  = (−0.10 + 0.05 + −0.10) / 3 = −0.15 / 3 = −0.05
```

Con `equivalence_threshold = 0.01`, `|delta| > 0.01` e `delta < 0`, quindi
`A_lower`.

## 3. Cosa si è osservato

**Misura.** `tests.test_oracle_pairwise_loss`: 31 test, tutti ok, 0,047 s.

**Misura.** Esecuzione CLI sull'esempio di riferimento: esito `pass`, 3 casi,
medie `0.30` e `0.35`, differenza `−0.05`, conclusione `A_lower`. Report:
[`reports/oracle/example_pass.json`](../../reports/oracle/example_pass.json),
riepilogo:
[`reports/oracle/example_pass.txt`](../../reports/oracle/example_pass.txt).

**Misura.** SHA-256 dei byte letti in quella esecuzione:

- CSV `b90fb5bfa8e3873c0bea14584dffbda837d87a1ca347568def29564dd0835521`
- candidato `f3dd689051c46c1512d300f05a3352f3b9f92697c0e80f445698151d0136d97d`
- config `afccf4877b1076b8c5648b95bd269ed0ca42a36c2fa3889071f11788c84a7775`

**Misura, sui test (non sulla CLI di esempio).** Candidato con media
dichiarata `0.31` → `fail`. Segno della differenza invertito (`+0.05` al
posto di `−0.05`) → `fail`. Vincitore dichiarato `B_lower` → `fail`.
`|delta| = soglia = 0.05` → equivalenza, non vincitore. `|delta| = 0.05`
con soglia `0.049` → `A_lower`. ID duplicati, NaN, infinito, cella vuota,
CSV vuoto, virgola decimale → `error`, senza ricalcolo. Campo
`mean_loss_a` assente → `unverified`, con ricalcolo comunque prodotto.
Tolleranza imposta dal candidato (`abs_tol: 1.0`) ignorata: non salva
una media sbagliata e non sposta le soglie dell'operatore.

**Non misurato.** Nessun CSV di loss reale della gara. Nessuna chiamata
dall'orchestratore. Nessun test statistico.

## 4. Interpretazione e incertezza

**Interpretazione.** Su tre righe sintetiche il verificatore ricalcola
le stesse medie del conto a mano e rifiuta le affermazioni che le
contraddicono. Il JSON candidato non è riuscito a cambiare le regole.

**Non segue.** Che A sia un modello migliore in generale, né che lo
sia su dati VCC. I tre casi non sono una valutazione. L'oracolo non
ha letto `vcc2026`, non ha letto l'orchestratore, e non ha visto
alcuna loss vera.

**Ipotesi da non promuovere.** Che questo prototipo basti, da solo,
come autorità di verifica per una campagna multiagente. Per ora è un
modulo a un solo tipo di affermazione, collaudato su fixture.

## 5. Spiegazione semplice

Due modelli hanno una loss su tre schede. Qualcuno dichiara: «A è
più basso in media di 0,05». L'oracolo rifà i conti sul foglio e
dice se i numeri e la frase coincidono. Non dice se A è un modello
migliore, e non si fa convincere se il foglio dei risultati prova a
cambiare la soglia.

## 6. Conseguenze

Nuova decisione D-020: l'oracolo numerico è un componente autonomo;
il JSON candidato non è fidato; non valuta ipotesi biologiche.
Nessun allaccio all'orchestratore in questa versione. Il passo
successivo, se lo si vorrà, è un secondo tipo di affermazione o un
contratto esplicito di chiamata dall'orchestratore — non un import
silenzioso.

## 7. Cosa corregge

Nessuna. Non tocca i numeri della gara, le sottomissioni, né i
documenti di strategia.

## 8. Domanda di comprensione

Se il candidato dichiara `A_lower` e nello stesso JSON mette
`equivalence_threshold: 1.0`, mentre l'operatore ha soglia `0.01` e
`delta = −0.05`, l'oracolo accetta l'affermazione?
