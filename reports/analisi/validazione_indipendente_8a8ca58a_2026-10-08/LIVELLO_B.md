# Livello B del contratto v1: come si esegue sul fold C-K562

8 ottobre 2026, VALIDAZIONE (Claude Code `8a8ca58a`). **Scritto prima che esista un numero del livello B** (orologio
letto con `date`: 18:33 Europe/Rome; il kernel di estrazione era in corsa, nessun banco a sei membri lanciato).
Non cambia il [contratto v1](PROTOCOLLO_v1.md): ne fissa i dettagli di esecuzione che il §5 lasciava al banco, e
dichiara che cosa manca.

## Che cosa si è trovato (misurato)

Le cellule vere estratte per i banchi a sei membri del 4 ottobre seguivano una regola di hash su 150 bersagli per
linea. Contate oggi sui file locali verificati (`processed/ripresa_banco_v2_2026-10-04/inputs/`):

| Linea | Bersagli nel file | Di cui del pannello | Cellule per bersaglio | Bersagli con voti nuovi in T1 |
|---|---:|---:|---:|---|
| K562 | 150 | **6** | 64 | AP2A2, KMT2A |
| H1 | 70 | **15** | 64 | ACLY, MTA1 |

Con 6 e 15 bersagli il livello B sul pannello non era eseguibile con gli ingressi esistenti (il «72 su K562» di
STRADE S-009 non riguarda questi file). Per questo si estraggono cellule nuove.

## Che cosa si esegue

1. **Estrazione** ([prepara_estrazione.py](banco/prepara_estrazione.py), kernel
   `davidmaisterx/vcc-validazione-celle-k562-8a8ca58a-r1`, CPU, privato): lo script archiviato `extract_cells.py`
   del corpus cellulare, senza modifiche, sullo stato di prepass di K562, per i **272 bersagli del pannello** su cui
   la tabella `k562` vota (elenco preso dalla ricevuta di consumo della release r1, non da un effetto). Fino a 128
   cellule per bersaglio e 2.048 controlli, seme 2026. Nessun effetto è letto.
2. **Banco** `bench_v2.py` senza modifiche (sha256 `06966c0b…0c08`), emissione t28, 400 cellule previste per
   bersaglio, scorer `cell-eval2` 0.16.0, tre corse nello stesso kernel:
   - *intero*: bracci T0, T1, P4 sui bersagli estratti, cinque semi; coppie `T1:T0` (K1) e `T0:P4` (K0);
   - *cambiati*: bracci T0, T1, R1 sui soli bersagli con voti nuovi presenti nel file, cinque semi; coppie `T1:T0`,
     `R1:T0`, `R1:T1`;
   - *controllo*: T0 contro T0 con le righe scambiate fra i bersagli (permutazione senza punti fissi, seme
     20261008), un seme: il PDS locale del braccio scambiato deve cadere, altrimenti il banco non vede la
     specificità.
   Gli effetti dei bracci sono i file scritti dal banco di livello A per il fold C-K562 (stadio 100 con la cache
   priva di ogni tabella K562), verificati per sha256 nel runtime.

## Secondo fold: C-iPSC sulla libreria «strong» di KOLF2.1J

Aggiunto alle 18:40, **prima di ogni numero del livello B** (nessun banco a sei membri era stato lanciato; del
livello A erano già letti i risultati, che non scelgono né il fold né i suoi bersagli). Il corpus cellulare del
pilot contiene le cellule della libreria `kolf_strong`: 55 bersagli del pannello. Stessa estrazione (kernel
`davidmaisterx/vcc-validazione-celle-ipsc-8a8ca58a-r1`, chiave risolta sul runtime come l'unica che contiene
`kolf_strong`), stesso banco e stesse tre corse, con gli effetti del fold C-iPSC del livello A: cache priva di ogni
tabella iPSC, comprese HIPSCI e Tian iPSC. Nel manifest `kolf_strong` è la «seconda libreria» del fold: la verità
primaria del livello A resta `kolf_pan_genome`, le cui cellule non sono nel corpus del pilot.

## Come si legge, e che cosa non può dire

Vale il §8 del contratto, senza modifiche: per un esito «valido e favorevole» servono almeno due fold di livello
B. Con C-K562 e C-iPSC la condizione sul numero di fold è raggiungibile; se uno dei due non si completa, un
candidato può risultare solo sfavorevole o inconcludente. Gli altri lignaggi del pannello (CD4T, HCT116, HEK293)
non hanno cellule vere estratte per il banco: lacuna nominata, non scelta. H1 ha 17 bersagli nella tabella e 15
nel file esistente, con 64 cellule: non è un fold utile. Due fold su sei lignaggi, uno dei quali di 55 bersagli:
la macro del livello B è una media su due contesti, non una stima di generalizzazione.

La metà delle cellule vere fa da verità e l'altra da replicato (come nei banchi del 4/10): scale locali, non
punteggi VCC. K562 è una linea di sviluppo, letta più volte; la testa cis viene da coppie di K562 e l'ampiezza è
nata anche su banchi di K562: i livelli assoluti non sono stime pulite, i contrasti appaiati sì nella misura in cui
le costanti sono comuni ai bracci.
