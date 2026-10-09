# Vecchio e nuovo banco messi alla prova: che cosa prevedono per i sei membri del riempimento

9 ottobre 2026, committato alle 22:44:16 (`f373fd5f`), VALIDAZIONE (Claude Code `eace4d03`). **Scritto mentre i due
kernel a sei membri giravano e prima di raccoglierne un'uscita** (nessun file dei kernel `…-eace4d03-e1` era stato
letto; la prima raccolta, del fold C-iPSC, è delle 22:44:42, come scrive la sua ricevuta `provider_status.json`). Serve a confrontare la
convenzione vecchia del livello A (ogni braccio sul proprio supporto, banco B4) con quella nuova (supporto definito
dalla verità, coppia non prevista a zero, banco B5) **su un dato che non è servito a scegliere la correzione**: i sei
membri con lo scorer vero per `E2f` − `T0`.

La corrispondenza fra misure del livello A e membri è un'ipotesi dichiarata, non una taratura: `disc95` ↔ PDS;
`nmae_conf` ↔ NMAE; `sign50` ↔ fedeltà (FID); `reach` ↔ REACH. La MSE scalata locale è tosata a zero per ogni
braccio e non si prevede. Un contrasto di livello A non risolto prevede «indistinto»; risolto prevede il verso.
I membri scalati sono «più alto è meglio» anche dove il grezzo è un errore.

| Fold | Membro | Convenzione vecchia (supporto proprio) | Convenzione nuova (vista del generatore) | Le due differiscono? |
|---|---|---|---|---|
| C-K562 | PDS | indistinto (`disc95` +0,0003, non risolto) | indistinto (`disc95g` +0,0002, non risolto) | no |
| C-K562 | NMAE | **peggiora** (`nmae_conf` +0,0022, risolto) | indistinto (+0,0008, non risolto) | **sì** |
| C-K562 | FID | indistinto (`sign50` +0,0018, non risolto) | **migliora** (`sign50` +0,0226, risolto; uguale a bersagli scambiati) | **sì** |
| C-K562 | REACH | indistinto (−0,0055, non risolto) | indistinto (−0,0004, non risolto) | no |
| C-iPSC | PDS | indistinto (`disc95` +0,0002, non risolto) | non leggibile (controllo non superato) | — |
| C-iPSC | NMAE | **migliora** (`nmae_conf` −0,0021, risolto) | **migliora** (−0,0015, risolto) | no |
| C-iPSC | FID | **migliora** (`sign50` +0,0058, risolto) | **migliora** (+0,0058, risolto) | no |
| C-iPSC | REACH | indistinto (+0,0004, non risolto) | **migliora** (`reach` +0,0011, risolto) | **sì** |

**Come si leggerà.** Per ogni riga, il membro a sei membri di `E2f:T0` risolto positivo conta «migliora», risolto
negativo «peggiora», altrimenti «indistinto». Una previsione è giusta se coincide; una previsione di verso contro
un esito indistinto è «non confermata», non sbagliata. Si contano le righe giuste, non confermate e sbagliate per
ciascuna convenzione, e a parte le tre righe in cui differiscono. Otto righe e due lignaggi non bastano a dire che
una convenzione è migliore in generale: se le tre righe discordanti danno ragione alla nuova lo si riporta come
osservazione, e la stessa prova si ripete al prossimo candidato con copertura diversa.

In più, dalla vista del generatore con il braccio scambiato: **la nuova convenzione prevede che dove `E2f:T0`
migliora un membro lo migliori uguale `E2swap:T0`**, cioè che `E2f:E2swap` non sia risolto su nessun membro. La
convenzione vecchia non ha questa previsione.

Fonti dei numeri: [C-K562](../esm2/cloud_r1/completion/supporto_C-K562.json),
[C-iPSC](../esm2/cloud_r1/completion/supporto_C-iPSC.json), chiavi `own_support_as_published` e `generator_view`.
