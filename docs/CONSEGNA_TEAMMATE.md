# Portare R-LEAD sulla macchina del teammate

Questa pagina integra il [prompt unico per Claude](PROMPT_CLAUDE.md) e il
[piano R-LEAD](piani/strategia-scientifica.md) soltanto per il trasferimento di ambiente.
Il t29 è concluso. Non esiste qui una seconda coda di training o invii.

## Git e presa in carico

Repository: [ferry-ai/virtual-cell-challenge-2026](https://github.com/ferry-ai/virtual-cell-challenge-2026).
Verificare remoto, branch, commit e modifiche locali prima di aggiornare senza force/reset.
La presenza dell'audit `53d17fe` non prova di avere il rinnovo: devono esserci
`docs/PROMPT_CLAUDE.md` e R-LEAD con P0–P6. Il commit esatto di consegna si confronta
con quello comunicato dal proprietario; nessun push futuro è implicito in questo documento.

Nel clone separato usare un branch di lavoro `codex/teammate-rlead`, registrando la presa
in carico in R-LEAD. Claude e teammate erano fermi al rinnovo; coordinare eventuali riprese
successive per non eseguire due versioni sugli stessi file o sulla stessa quota.

## Runtime e percorsi

Configurare `VCC2026_DATA_ROOT` fuori dal clone; verificare il valore risolto da
`vcc2026.config.paths()`. Non copiare percorsi `C:/Users/ferra`, mount `G:` o credenziali.
I wrapper `.cmd` sono Windows; su Linux/macOS usare il Python del venv ed esporre `src/`
su `PYTHONPATH`. Ricreare l'ambiente dai requisiti, registrando versioni effettive:
i requisiti hanno intervalli, non un lock esatto; il training richiede anche PyTorch.

Il [preflight portabile](../reports/analisi/handoff_teammate_2026-10-01/preflight_handoff.py)
scrive un inventario con la libreria standard. Exit code 0 significa «inventario scritto»,
non readiness completa. Usare anche `validate_runtime.py` del corpus per il runtime
effettivo, H5AD e risorse. Verificare `cell_eval2.config`, preset e API usate dal banco.
[CP-0054](checkpoints/0054-visibilita-scorer-e-consegna.md) distingue visibilità sandbox
da pacchetto rotto: confrontare il terminale nativo prima di reinstallare.

## Input che Git non trasferisce

| Materiale | Verifica necessaria |
|---|---|
| Codice, ricette, protocolli, eval e diagnostiche | Revisioni e hash; distinguere LF/CRLF da modifiche del codice |
| Conteggi, controlli ufficiali, asse e pannello | Copia lecita, unità, nomi/ordine, maschere e checksum |
| Shard e descrittori | Accesso proprio a Drive/Kaggle, revisione e manifest; presenza nel catalogo non significa presenza sul disco |
| `model.pt`, checkpoint, prepass pesanti | Percorso leggibile e hash; gli eval versionati non li contengono |
| H1 test | Solo provenienza e ruolo dai manifest: non aprire la riserva per onboarding |
| Venv, credenziali, GPU, sessioni cloud, `.claude/`, agent-hub e worktree | Non trasferiti dal clone; nessuna dipendenza privata implicita |

Inventariare con percorsi locali; usare `inventory.py --no-drive` se il mount non è
configurato. Conservare i manifest originali, creando una mappatura nuova degli input.
Per ciascun dato mancante indicare locatore, byte, accesso e fase impedita; proseguire
con fixture CPU e output versionati dove bastano. Il preflight sul portatile non certifica
il runtime GPU remoto: ripeterlo lì prima del job autorizzato.

La consegna scientifica e i test sono specificati soltanto in R-LEAD.
[Consegna precedente integrale](storico/rinnovo_2026-10-01/docs/CONSEGNA_TEAMMATE.md).
