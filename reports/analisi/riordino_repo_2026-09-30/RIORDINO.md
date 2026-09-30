# Riordino della repo, notte del 30 settembre

Claude, sessione `dcf3a1b9`, dalle 02:07 del 30/09 (orari letti con `date`, CEST). Il proprietario
aveva chiesto alle 00:40, prima di andare a dormire, di agire senza chiedere: agenti che si
orientano senza perdersi, scoperte del 29/09 in evidenza, una direzione generale, informazioni
ritrovabili per ambito, dimensioni ridotte, errori da cui imparare, nessuna informazione persa.
Le regole che ne seguono sono la decisione D-048. Qui c'è che cosa è stato fatto, con le
verifiche, e che cosa aspetta il proprietario. Il manifest di ciò che è uscito dall'albero è
[fuori_repo.json](fuori_repo.json).

## 1. Niente più lavoro fuori dai commit

Alle 02:07 la sessione lead di Codex (`01a0ee03`) aveva chiuso il suo ultimo turno alle 01:13, e la
sessione Claude `f4f38e58` non era più attiva. Circa 1.160 file loro erano fuori dai commit, in una
cartella condivisa. Sono stati committati in locale così come erano, dopo una scansione di tutti i
file: nessun nome di linea accanto ai contesti, nessun nome dalla classifica, nessuna credenziale.

| Commit | Che cosa | Controllo prima |
|---|---|---|
| `29446ce` | Il codice vivo di Codex: opzioni dello stadio 45 (scala della dispersione, classi di profondità), `depth_generator.py`, due test | Suite: 282 test, 280 passano. Le due failure chiedevano solo che due cartelle citate dagli indici fossero committate |
| `09ac053` | 1.155 file: la cartella della revisione lead, gli invii del t28, i checkpoint 0046–0052, `ERRORI.md`, la scheda R-COMP, le righe dei registri; e il report `basali_asse_2026-09-29/` di `f4f38e58` | Checker verde; privacy come sopra |

## 2. Orientamento

- **[docs/AMBITI.md](../../../docs/AMBITI.md)**, nuovo: una sezione per ambito (gara, invii,
  generatore, dati, modelli, set finale, operazioni, metodo), con stato, letture prime,
  evidenza e scheda. In testa, le scoperte del 29–30/09.
- **L'indice della revisione lead**, [lead_scientist_2026-09-29/README.md](../lead_scientist_2026-09-29/README.md):
  circa 1.070 file ordinati per ambito, con che cosa leggere prima e che cosa è codice riusabile.
- **PROGETTO §0** ha una «Direzione generale», proposta e con le fonti; la voce del t28 è scesa da
  29 a 16 righe, con i dettagli operativi nei report che cita.
- **CLAUDE.md, «Start here»**: lo stato al 30/09 al posto del passaggio di consegne del 28/09;
  AMBITI ed ERRORI fra le letture iniziali; una riga nella tabella dei compiti; due regole nuove
  su commit e peso dei file. `AGENTS.md` rimanda alle stesse porte d'ingresso.
- **reports/README.md**: «da leggere per primi» aggiornato al 30/09 con le correzioni
  dell'audit, conteggi delle cartelle, righe di codice di ricerca (circa 60.000, di cui 28.000
  del 29/09), e gli strumenti riusabili `learning/preflight.py` e `ledger.py`.
- **Rimandi incrociati** nei README di generatore e banchi, modelli, trasferimento e sorgenti
  verso le parti giuste della revisione lead, che sta in `analisi/`.
- **Il controllo documentale** verifica ora anche i link di `AMBITI.md` ed `ERRORI.md`.

## 3. Imparare dagli errori

`docs/ERRORI.md` copriva i guasti dei job. Ora ha anche:
- **undici errori di metodo già commessi**, ciascuno con come si è visto, la regola che lo evita
  e la fonte: dalla catena di CP-0002 alla premessa falsa su CD4, dal plateau letto come
  saturazione all'indice locale letto come guadagno atteso;
- **undici lezioni operative**: Colab, Drive, orari, processi lunghi, disco, cartella condivisa,
  scratchpad, identità dei contesti. Alcune stavano solo nella memoria privata di un agente.

## 4. Dimensioni

| Parte | Prima | Dopo | Come |
|---|---|---|---|
| `.git` | 106 MB: 6.070 oggetti sciolti (80,6 MB) e 8,3 MB di scarto | 59 MB, un solo pack | `git gc`; la storia non è stata riscritta |
| `.runtime-deps/` | 62,6 MB, 858 file: una copia della repo del 24/09 che inquinava le ricerche | fuori dall'albero | nella radice dati, hash verificati dopo lo spostamento |
| 34 cartelle `__pycache__` | 6,3 MB | 0 | Cestino |
| File sparsi in radice | `C`, `ids.txt`, `tmpzg7h1jcl/` | 0 | `ids.txt` nella radice dati, gli altri due nel Cestino |

Misure: `.git` con `du`, da 106 a 59 MB; l'albero di lavoro, come somma delle dimensioni dei file,
da circa 278 a 209 MB.

**Non fatto, di proposito:**
- la cartella della revisione lead (58 MB, circa 10 MB compressi in git) è entrata intera: i
  manifest dei fold e le tabelle grezze dei kernel sono la catena di verifica dei verdetti di
  CP-0048 e CP-0049, e i suoi script li rileggono da lì;
- i circa 38 MB di `.npz`, `.zip` e `.h5ad` ignorati in `reports/storico/` restano: non sono in
  git, e portarli fuori da OneDrive toglierebbe loro una copia di sicurezza;
- nessuna riscrittura della storia git: servirebbe un push forzato sulla repo pubblica.

## 5. Che cosa aspetta il proprietario

1. **Il push** dei commit locali di questa notte. La repo è pubblica; la scansione della privacy è
   descritta nel §1.
2. **Gli scratchpad di undici sessioni chiuse**, circa 4,8 GB in una cartella temporanea di
   Windows che una pulizia automatica può svuotare. Lo spostamento nella radice dati è stato
   rifiutato dal controllo automatico dei permessi, come interferenza con gli spazi di lavoro di
   altre sessioni; anche la copia di loro file nella repo. Restano dove sono; l'elenco dei file di
   dieci di loro è nella radice dati (manifest, `inventoried_not_moved`). Quello della sessione
   `76a3a45e` del 26/09 contiene risultati verificati mai trascritti nella repo: un'analisi
   dell'interazione bersaglio × contesto sugli schermi essenziali, controlli sulla risposta p53
   del pannello e il pannello di architetture di quel giorno. Trascriverli richiede il via del
   proprietario. Lo scratchpad `db2d3e63` può contenere materiale riservato sulle identità dei
   contesti: in ogni caso non va nella repo.
3. **Svuotare il Cestino**: circa 6,3 MB di cache e due file senza contenuto.
4. **Lo spazio su C:**, 3,8 GB liberi alle 02:30 e dopo il riordino: la forma piena della prova
   generale ne chiede circa 17.
5. **Il pilota non committato di Codex del 19/09**, nel suo worktree
   `C:/Users/ferra/.codex/worktrees/atlas-transfer-pilot/vcc2026`: già indicato in `docs/ARCHIVIO.md`
   come decisione del proprietario.
6. **Cinque metadati di worktree vecchi** in `.git/worktrees/` (`wt_check`…`wt_check3`,
   `wt_f19e447`) che `git gc` non ha potuto cancellare per accesso negato: innocui; si può ripetere
   `git worktree prune`.

## 6. Come tornare indietro

- `.runtime-deps/` e `ids.txt`: si riportano dalla radice dati ai percorsi del manifest; l'elenco
  degli hash permette di verificarli.
- Cestino: si ripristina finché il proprietario non lo svuota.
- I commit sono locali: `git revert` li annulla senza toccare GitHub.
