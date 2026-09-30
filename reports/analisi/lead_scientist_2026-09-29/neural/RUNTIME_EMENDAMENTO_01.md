# Stack: Python managed e verifiche aggiuntive

29 settembre 2026. **Emendamento tecnico prima dei pesi e degli score.** Il
coordinatore ha verificato Python 3.13.15 nel runtime Colab. I pin scientifici
congelati richiedono Python precedente; cambiare NumPy/Torch per adattarli a 3.13
avrebbe cambiato il runtime senza verifica. La soluzione implementata aggiunge
CPython **3.11.13 isolato**, senza sostituire l'interprete di Colab.

`stack_remote_runner.py` crea una venv bootstrap con il Python ospite, installa
`uv==0.8.22`, quindi usa il suo catalogo congelato per Python 3.11.13. La
[distribuzione ufficiale Astral](https://github.com/astral-sh/uv/blob/0.8.22/crates/uv-python/download-metadata.json)
contiene la release python-build-standalone 20250918; per Linux x86_64 il tar ha
SHA256 `511ceceeff184ad742a35583755f5070c0274cc0f0bb5c9218abd939240a2146`.
uv verifica i checksum del catalogo. Directory Python, bin e cache sono nello
scratch; il launcher verifica il percorso risolto e registra versione e hash
dell'eseguibile effettivo. Il Python scientifico è una seconda venv derivata da
quel 3.11.13. Nessun pin di `requirements_stack.txt` è stato cambiato.

`colab_stack_dependencies_r2.sh` prova questo percorso e il dry-run pip senza
checkpoint. r1 è conservato; la sua verifica di versione lo ferma correttamente
su Python 3.13. Il runner esegue anche gli import Stack/scvi prima dei pesi.
Queste verifiche sono implementate, non vanno confuse con un'installazione o una
generazione già riuscita.

La revisione indipendente ha aggiunto due controlli allo scorer: identità di
adapter/checkpoint/lista geni nel manifest, e uguaglianza esatta del pannello con
PDS finito per tutti i 12 bersagli. NMAE e altri membri mantengono la propria
eleggibilità. Il file `genelist_metadata_r1.json` verifica sui metadati pubblici
congelati che tutti i 15.012 geni sono maiuscoli e unici anche dopo uppercase.
Nessun peso è stato scaricato localmente.

**Chiarimento del nullo appaiato, nessuna modifica alla formula:** `d_g=0` sul
supporto condiviso significa rapporto Stack nullo. La massa complessiva di quel
supporto resta quella della baseline transfer. Con basale `[10,20,7]`, baseline
`[15,17,5]` e primi due geni condivisi, prompt identici producono
`[10.6667,21.3333,5]`, non tutto il basale. È l'effetto della massa transfer
conservata, già prevista dalla formula; il test aggiunto lo rende esplicito.
La frase «drift nullo» non va estesa alla composizione globale dell'ibrido.
