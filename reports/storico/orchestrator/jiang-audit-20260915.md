# Campagna Jiang — esito 15 settembre 2026

Run: `20260915T115742Z-vcc2026-jiang-audit-v1-a81104`
Percorso completo (fuori dal repo, D-001):
`C:/Users/ferra/vcc2026-data/orchestrator/runs/20260915T115742Z-vcc2026-jiang-audit-v1-a81104/`

**Esito:** `stopped` / `service_unavailable`. Kimi non ha risposto in fase 2 né in fase 3
(timeout dopo invio). DeepSeek ha consegnato le tre fasi. Nessuna sintesi consensuale:
il rapporto dell'orchestratore raccoglie, non concilia.
Fonte: `ricerca-20260915T123112Z.md` in quella cartella.

## Cosa coincide con la misura locale (script 61)

Dimensioni dei cinque RDS, mapping blocco→stimolo, licenza CC BY 4.0, assenza di
una target list nel listing Zenodo, default Mixscale (`labels='gene'`,
`nt.class.name='NT'`, `slot='counts'` come *default del pacchetto*, non come
schema dei RDS). Copertura M1 ∩ Jiang **non calcolata**.

I file piccoli che DeepSeek chiedeva di scaricare (`A_readme.txt`,
`Pathway_genelist.rds` e affini) sono già in `reports/jiang_2026-09-15/small_files/`.
Restano RDS: senza R non sono stati aperti.

## Cosa resta aperto (dichiarato, non chiuso)

Schema `meta.data`, counts grezzi vs normalizzati, RAM di `readRDS`, incrocio
linea×stimolo×batch×NTC, elenco target. H1 resta **open**.

## Cosa non fare adesso

Non `orch resume` su questo run finché Kimi non risponde: la ricerca scientifica
non ha `stand_in`, e due timeout di fila hanno già fermato il ciclo. Non
scaricare un RDS su questa macchina (D-005, 11,3 GiB liberi).
`DE_results_all_pathway.zip` (324 MB) è il prossimo file *candidato* per i nomi
dei regolatori, non una feature per target unseen.
