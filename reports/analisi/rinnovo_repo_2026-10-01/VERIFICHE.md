# Verifiche del rinnovo

2 ottobre 2026, Europe/Rome. Verifiche completate prima del commit.
Nessuna nuova verifica biologica.

- Conservazione: `verify_renewal.py` verifica le 18 copie contro il commit di partenza,
  i loro hash e il corpo runtime dello stadio 84. Prima esecuzione passata.
- Controllo documentale: prima esecuzione individua un'ancora di PROCEDURE errata nella
  nuova R-REV; collegamento corretto prima della verifica finale.
- Suite completa nell'interprete nativo, come CP-0054:
  `.\scripts\py.cmd -m unittest discover -s tests` — **287 test passati**, exit code 0,
  438,159 secondi misurati. [Log integrale](unittest_native.log). Nessuna reinstallazione
  o sostituzione dello scorer; gli avvisi nel log appartengono alle fixture dei test.

## Percorsi verificati manualmente

Questa è una verifica dei rimandi, non il test multi-agente di orientamento del 30/09.
Nessun altro agente è stato lanciato per il rinnovo.

| Domanda di chi riprende | Risposta e fonte corrente |
|---|---|
| Quale piano devo eseguire? | README → PROGETTO §0 → PIANI §2 → R-LEAD P0–P6; il prompt unico segue lo stesso percorso |
| Che cosa faccio prima di un altro training? | R-LEAD P0/P1/P3: disponibilità, esposizione, difetti applicabili e test; P2 export con pesi reali quando disponibili |
| R4 deve partire appena torna quota? | No: R-LAB e `--status` del protocollo indicano verifica tecnica senza esito, subordinata alla scelta del nuovo esperimento |
| Quale baseline e quali sei metriche? | R-LEAD §1/P4 distingue replica t22, correzione t25 ed emissione t28; sei grezzi espliciti e regola preregistrata |
| K562 e H1 sono contesti mai visti dalle reti esistenti? | No: P1 ricostruisce l'esposizione; H1 test resta chiusa e non sana l'uso H1 train/val |
| È ancora valido convertire i grezzi con le vecchie ancore? | CP-0050/R-022, D-038 qualificata e PROCEDURE §4: metodo approssimato, non scala ufficiale esatta |
| Quali lavori precedenti sono davvero da fare? | R-REV distingue azioni concluse e residui; S-INVII presidia il finale; R-V2/R-DATI/R-SWITCH hanno condizioni esplicite |
| Dove recupero un incarico o testo precedente? | INDICE storico → copia; manifest con hash e tag locale su 3de6cd0 |

## Controlli aggiuntivi

`verify_renewal.py` conferma 18 copie identiche al contenuto di partenza salvo la
trasformazione dichiarata dei link, 33 collegamenti locali aggiuntivi risolti, nessuna
modifica fuori dal perimetro autorizzato e corpo runtime dello stadio 84 invariato.
L'elenco di file ammessi comprende esplicitamente la cartella del rinnovo: la prima
versione del controllo non la includeva e segnalava i nuovi file dopo lo staging;
la verifica delle copie e del runtime era già positiva. L'elenco è stato corretto.

Il checker strutturale passa: 55 checkpoint, registro, decisioni e link coerenti.
Nessun checkpoint è stato modificato o aggiunto per un semplice riordino documentale.
Gli stati del prompt, di R-LEAD, del protocollo R4 e della copia storica R-LAB sono stati
letti anche con `31_check_docs.py --status`: guida corrente e storia risultano distinti.

`git diff --check` passa. Le due ricevute di stop preesistenti sono file vuoti e restano
non tracciate; `.claude/` resta sul disco ed è ignorata. Nessun push eseguito.
