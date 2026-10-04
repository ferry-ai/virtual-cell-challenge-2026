# Banco v2: effetti in ingresso, differenze appaiate su più semi in uscita

4 ottobre 2026, Claude Code, sessione `ba9b8bcb`, su R-LEAD. **Implementato e provato con test; non ancora eseguito
su dati veri.** Tipo: strumento, nessun risultato.

Nasce dalle misure di [CP-0065](../../../docs/checkpoints/0065-d056-confronti-e-rumore-del-banco.md): a un seme e 32
cellule previste per bersaglio il guadagno appaiato del banco D-056 aveva una deviazione standard di 0,007–0,045 per
linea, quanto i guadagni letti; e il generatore estraeva tutti i blocchi di un braccio da un unico flusso casuale.

| File | Contenuto |
|---|---|
| [bench_v2.py](bench_v2.py) | Stesso scorer e stessa verità delle corsie B; bracci qualunque come file di effetti (formato dello stadio 100); 400 cellule previste per bersaglio; 5 semi; un flusso casuale per (seme, bersaglio) condiviso fra i bracci; emissione `t25` o `t28` (effetti ×1,5 e dispersione per gene); differenze appaiate dichiarate con `--pair`, con media, deviazione standard e «risolto» |
| [test_bench_v2.py](test_bench_v2.py) | 4 test senza scorer: un bersaglio non cambiato dà le stesse cellule quando ne cambia un altro e in qualunque ordine; lettura dei bracci per nome; differenze allo stesso seme |

Che cosa **non** è: non sostituisce le corsie archiviate, non cambia verità, replicato, baseline o scala locale, e non
risolve da solo l'instabilità del JAC locale (i grezzi e i denominatori restano in `bench.json`). Una soglia di
promozione sul banco v2 va scritta in un protocollo prima dei numeri; il costo misurato è di circa un minuto per
valutazione a 400 cellule su una sessione Kaggle CPU.
