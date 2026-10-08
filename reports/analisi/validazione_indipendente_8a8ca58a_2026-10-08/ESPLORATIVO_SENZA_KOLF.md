# Analisi esplorativa: t36 senza KOLF2.1J, e KOLF con un voto solo

8 ottobre 2026, VALIDAZIONE (Claude Code `8a8ca58a`). **Piano scritto prima dei numeri di queste corse**: commit
`5bfb5a7` delle 19:17:38 Europe/Rome; la corsa r3 del livello A è stata spinta alle 19:19:15. È **esplorativa**: l'ipotesi nasce dalla
[scomposizione di K0](TABELLE_SCOMPOSIZIONE_K0_r2.md), cioè dagli stessi lignaggi su cui la si prova. Non è un
candidato del contratto, non può essere promossa da questo banco e non entra nella scelta del freeze; serve a
decidere se vale un contrasto vero, costruito dal proprietario della pipeline.

## Ipotesi

Nella scomposizione H1 migliora le misure primarie dove agisce, mentre l'ingresso di KOLF2.1J le peggiora sui
quattro lignaggi non staminali e i suoi voti ripetuti aggiungono una piccola perdita. Se è così, togliere KOLF dal
t36 (o farlo votare una volta) dovrebbe alzare la discriminazione sui contesti lontani dalle staminali, al prezzo
dell'errore d'ampiezza che KOLF riduceva.

## Bracci

| Braccio | Fonti | Che cos'è |
|---|---|---|
| T0 | le 13 del t36 | riferimento |
| P4h | `k562`, `cd4_mix`, `orion_hct116`, `orion_hek293t`, `h1` | t36 senza le quattro tabelle KOLF |
| P4kh | P4h + `kolf_pan_genome` | t36 con KOLF che vota una volta (già calcolato nella corsa r2) |

Contrasti: X1 = P4h − T0, X2 = P4kh − T0 (= −Q3), X3 = P4h − P4kh (= −Q1 a valle di H1).

## Che cosa si esegue e come si legge

- **Livello A**, sei fold, stesse misure del contratto v2. In C-iPSC le tabelle KOLF sono già escluse, quindi
  P4h = P4kh = T0 a meno delle tabelle senza bersagli: i tre contrasti lì valgono zero per costruzione. In C-H1 è
  esclusa `h1`.
- **Livello B** sul solo fold C-K562 (l'unico non staminale con cellule vere): `bench_v2`, emissione t28, 400
  cellule, cinque semi, coppie `P4h:T0`, `P4kh:T0`, `P4h:P4kh`. Un fold solo: per il §8 non può dare un esito
  favorevole, e non lo si chiede.
- Lettura senza soglia: verso e risoluzione di `disc95`, `r_spec` e dei sei membri, PDS in testa. Se X1 non è
  positivo su `disc95` nei fold non staminali, o se sul fold K562 perde PDS, l'ipotesi cade e lo si scrive.

**Precedenti:** S-010 (fonti aggiunte lette come pacchetto); CP-0050 e CP-0066 (linee già lette non sono
conferma); ERRORI, «scegliere i dati con misure che leggono le risposte della valutazione»: qui l'ipotesi è scelta
proprio così, ed è il motivo per cui resta esplorativa. **Segnale precoce e arresto:** parità di T0 fallita, o
X2 diverso da −Q3 della corsa r2: la corsa non si legge.
