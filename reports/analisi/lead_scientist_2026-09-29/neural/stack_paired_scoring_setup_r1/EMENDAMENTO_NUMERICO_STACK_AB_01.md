# Stack A/B: verifica meccanica della riproducibilità numerica

29 settembre 2026. **Emendamento operativo prima del job085**, dopo i risultati
completi A/B e il fallimento del selettore congelato. Non è una nuova ipotesi
scientifica, non modifica `PROTOCOLLO_STACK_AB.md` o le sue soglie e non amplia
alcuna tolleranza. Tutti i tentativi e gli esiti precedenti restano conservati.

## Difetto misurato e limite della diagnosi

Il selettore si arresta su `Transfer per-target scores are not exactly identical`.
Fra i 105 valori transfer dei CSV completi, una sola stringa cambia:
SETD1A/NMAE, A `0.9526270737227032`, B `0.9526270737227044`.
Differenza float64 `1.2212453270876722e-15`, 11 ULP. Non è solo parsing del CSV.
I sei aggregati transfer JSON, configurazioni e versioni registrate sono identici;
gli input transfer hanno lo stesso hash. Evidenza:
`stack_ab_numerical_diagnostic_r1/csv_difference.json`.

Nel codice installato di cell-eval2 0.16.0, `metrics/de.py` righe 737–740 e
765–769, il NMAE usa join e medie per gruppo Polars. La causa esatta dei 11 ULP
non è ancora identificata. La fixture locale su Polars 1.44.2 cambia ordine dei
gruppi con più thread ma non i valori in 64 ripetizioni; il runtime originale usa
Polars 1.35.2. Questa prova non dimostra il meccanismo del guasto remoto.

## Un solo ricontrollo fissato

Job085 esegue sequenzialmente A e B sullo stesso ambiente CPU già usato, con
gli stessi H5AD, controlli, truth development, assi, ancore e sorgenti dello scorer.
Si riusa lo snapshot `6e216f900a606656c182bb7f520e351bb7805358a0e2943a226ce3a105071dcb`,
contenente entrambi gli scorer congelati. Nessuna inferenza, rigenerazione di
cellule, modifica del modello, nuova truth o lettura della riserva.

Prima di qualunque import: `PYTHONHASHSEED=0`; `POLARS_MAX_THREADS`,
`OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, `NUMEXPR_NUM_THREADS`
e `NUMBA_NUM_THREADS` uguali a 1. Le versioni scientifiche devono coincidere con
quelle della ricevuta084 e del suo pip freeze. Output nuovi, A e B separati.
Il preflight locale e quello remoto verificano l'inventario completo prima dello
scoring; una ricevuta locale non prova disponibilità nel runtime.

Si riportano entrambi i risultati e le differenze rispetto agli originali,
anche se sfavorevoli. **Non si sceglie il migliore tra vecchio e nuovo run.**
I due output deterministici servono insieme al selettore originale, byte per byte
immutato, che richiede ancora baseline esattamente uguale e identiche maschere.
La regola resta D > 0 e PDS >= 0, massimo D fra ammissibili, parità esatta ad A.
Nessun risultato o soglia di conferma cambia.

Se la guardia fallisce ancora, non si forza un verdetto: si conserva il fallimento
e si riporta la selezione non disponibile. Nessuna catena di retry con scelta
del tentativo favorevole. La riduzione dei thread è una verifica di riproducibilità,
non una dimostrazione anticipata della causa né della qualità di Stack.
