# Verifiche della sessione

- [Audit upstream](audit_upstream_r1.json): SHA degli otto sorgenti verificati;
  loss originale eseguita su una fixture CPU, differenza di gradiente zero con
  `direction_lambda` 0 contro 10. Inventario statico di `x`, non esecuzione completa GEARS.
- [Sette test del prototipo](test_adapter_r1.txt): tutti passati. Parità esatta col
  vero `build_model` D-056 a messaggio nullo anche con residuo non nullo; ancora invariata
  all'inizializzazione; contesto con gradiente; invarianti di batch, rinomina dei nodi,
  fallback e serializzazione. Nessuna prova di miglioramento predittivo.
- [Suite generale](test_suite_r1.txt): 290 test in 441 s, 289 passati. L'unico fallimento
  era l'indice della ripresa del banco: il collegamento puntava a `STATO_1936.md` anziché
  alla cartella richiesta dall'indice. Corretto il collegamento mantenendo lo stato a fianco;
  [rieseguiti tutti gli 11 test dell'albero](test_live_tree_r2.txt), passati. Non è un difetto
  del modulo a grafo. La suite completa non è stata ripetuta dopo questa sola correzione Markdown.
- `scripts/31_check_docs.py`: passato dopo la stabilizzazione dei file. Un primo controllo
  eseguito mentre nasceva il log della suite aveva osservato quel file fra le due scansioni;
  la riga di registro della cartella era già presente. Nessuna modifica al checker.
- [Input locali](audit_local_inputs_r1.json): matrice dei descrittori e asse verificati;
  sorgenti storiche mancanti ai cinque percorsi controllati, come dettagliato nelle
  [note](NOTE_INPUTS.md). Nessun grafo reale o dataset acquisito per aggirare la lacuna.

Restano da verificare: grafo reale e provenienza, integrazione nel trainer e nel caricamento
dei checkpoint di produzione, parità end-to-end con export/scoring, prestazioni sul corpus,
utilità biologica C/J e conferma indipendente. Nessun nuovo job, training, invio o push Git.
