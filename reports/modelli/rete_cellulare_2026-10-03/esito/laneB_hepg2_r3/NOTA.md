# Corsia B, generazione

Le cellule della rete r3 sono quelle del kernel `rcell-gen-<linea>-r3b`, che usa `pi` = 1 per i modelli senza miscela.
La prima generazione (`rcell-gen-<linea>-r3`) usava per errore `pi` ≈ 0,5, la testa del gate mai addestrata: metà delle
cellule non portava lo spostamento. È scartata, con gli output nella radice dati. Le cellule vere estratte dalle due
generazioni sono identiche (stesso sha256 in `real_cells.json`).
