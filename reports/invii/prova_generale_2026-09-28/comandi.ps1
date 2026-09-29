# Dress rehearsal of 22 October (R-REV action 3): the exact commands of steps 2-10 of RISULTATI.md.
#
# NOT a script to run whole. Dot-source it from the repository root to set the variables, then run one
# step at a time, reading each result before the next (LAVORO section 2: one heavy job at a time):
#
#     . .\reports\invii\prova_generale_2026-09-28\comandi.ps1
#
# Every command goes through misura.py, which runs the stage in this same process (runpy) and appends
# argv, UTC start and end, exit code, peak RSS and free disk before and after to tempi.jsonl in this
# folder. Nothing here uploads anything. Written 28/09 before running; the step-5 u26 parity already
# ran (tempi.jsonl, cache_parita_u26.json).

$D = "C:\Users\ferra\vcc2026-data"
$R = "reports\invii\prova_generale_2026-09-28"
$B = "$D\raw\controls_prova_2026-09-28"          # the fake bundle (step 2)
$I = "$D\interim\prova_generale_2026-09-28"      # outputs of steps 3-4: data root, never reports/ (D13)
$M = "$R\misura.py"

# Step 0. Shape: 400 cells per target only with >= 17 GB free; otherwise the reduced shape below.
# Below about 4 GB free, do not start.
$FreeGB = [math]::Round((Get-PSDrive C).Free / 1GB, 2); "free on C: $FreeGB GB"
$Reduced = $FreeGB -lt 17
$Shape45 = if ($Reduced) { @("--cells-per-pert", "40", "--reserve-gib", "1") } else { @() }
$Shape48 = if ($Reduced) { @("--reserve-gib", "1") } else { @() }
$Perts48 = if ($Reduced) { "$R\pert_counts_n40.csv" } else { "$B\pert_counts.csv" }

return   # dot-sourcing stops here: the steps below are run by hand, one at a time

# Step 1 (done 28/09 20:09 UTC+2): estrazione.py wrote bersagli.csv, pert_counts.csv, pert_counts_n40.csv
# and estrazione.json (mapping D=B, E=A, F=C).

# Step 2. The fake bundle: copies of A/B/C relabelled D/E/F (+0.66 GB; sha256 of the originals before
# and after, block-by-block comparison of every dataset). Writes $B and $R\bundle_manifest.json.
.\scripts\py.cmd $M --label "passo2 bundle" -- "$R\bundle_finto.py"

# Step 3. Context identity (stages 85 and 99), outputs in the data root.
.\scripts\py.cmd $M --label "passo3 stadio85" -- scripts\85_identify_contexts.py --controls-dir $B --contexts D E F --out "$I\stadio85"
.\scripts\py.cmd $M --label "passo3 stadio99" -- scripts\99_context_fingerprints.py --controls-dir $B --contexts D E F --out "$I\stadio99"
# Check by hand: stage 99's output reproduces reports\gara\context_fingerprints_2026-09-22\fingerprints.json
# with D, E, F read as B, A, C (dates aside).

# Step 4. Control CPM (mean per-cell CPM, the definition of interim\basal_cpm_by_context.csv). The A/B/C
# run gives R-E the reference libraries and is the D8 parity (A/B/C equal to that file within 1e-9).
.\scripts\py.cmd $M --label "passo4 cpm DEF" -- "$R\cpm_contesti.py" --controls-dir $B --contexts D E F --out "$I\basal_cpm_DEF.csv" --parity-with "$D\interim\basal_cpm_by_context.csv"
.\scripts\py.cmd $M --label "passo4 cpm ABC" -- "$R\cpm_contesti.py" --controls-dir "$D\raw\controls" --contexts A B C --out "$I\basal_cpm_ABC.csv" --parity-with "$D\interim\basal_cpm_by_context.csv"

# Step 5. Panel caches from the universes (about 140 MB each). Rule: 0 differences for k562 and Orion,
# <= 2e-8 for cd4_mix (prediction 3).
# parity u26 against r5: ALREADY RUN 28/09 21:34-21:36 UTC (tempi.jsonl line 1; cache_parita_u26.json)
# .\scripts\py.cmd $M --label "passo5 parita_u26" -- "$R\assembla_cache.py" --preset u26 --targets-csv "$D\raw\controls\pert_counts.csv" --out "$D\processed\multisource_prova_2026-09-28_parita_u26" --compare-to "$D\processed\multisource_2026-09-23_r5" --report-json "$R\cache_parita_u26.json"
.\scripts\py.cmd $M --label "passo5 parita_me1" -- "$R\assembla_cache.py" --preset me1 --targets-csv "$D\raw\controls\pert_counts.csv" --out "$D\processed\multisource_prova_2026-09-28_parita_me1" --compare-to "$D\processed\multisource_2026-09-27_r9" --report-json "$R\cache_parita_me1.json"
.\scripts\py.cmd $M --label "passo5 finto me1" -- "$R\assembla_cache.py" --preset me1 --targets-csv "$B\pert_counts.csv" --out "$D\processed\multisource_prova_2026-09-28_me1" --report-json "$R\cache_me1.json"

# Step 6. Stage 100. Parity runs (rule: max |d lfc| <= 1e-6, observed identical), then the fake run and
# the negative control (prediction 6: exit 0 with about 30 targets covered).
.\scripts\py.cmd $M --label "passo6 parita t22" -- scripts\100_build_context_effects.py --recipe configs\recipes\t22.json --cache "$D\processed\multisource_prova_2026-09-28_parita_u26" --targets-csv "$D\raw\controls\pert_counts.csv" --out "$D\processed\effects_prova_parita_t22_2026-09-28"
.\scripts\py.cmd "$R\confronta_effetti.py" --mine "$D\processed\effects_prova_parita_t22_2026-09-28" --reference "$D\processed\effects_t22_2026-09-26" --out "$R\parita_effetti_t22.json"
.\scripts\py.cmd $M --label "passo6 parita t25" -- scripts\100_build_context_effects.py --recipe configs\recipes\t25.json --cache "$D\processed\multisource_prova_2026-09-28_parita_me1" --targets-csv "$D\raw\controls\pert_counts.csv" --out "$D\processed\effects_prova_parita_t25_2026-09-28"
.\scripts\py.cmd "$R\confronta_effetti.py" --mine "$D\processed\effects_prova_parita_t25_2026-09-28" --reference "$D\processed\effects_t25_2026-09-27" --out "$R\parita_effetti_t25.json"
.\scripts\py.cmd $M --label "passo6 finto" -- scripts\100_build_context_effects.py --recipe "$R\ricetta_t22_DEF.json" --cache "$D\processed\multisource_prova_2026-09-28_me1" --targets-csv "$B\pert_counts.csv" --out "$D\processed\effects_prova_t22_2026-09-28"
.\scripts\py.cmd $M --label "passo6 controllo negativo" -- scripts\100_build_context_effects.py --recipe "$R\ricetta_t22_DEF.json" --cache "$D\processed\multisource_2026-09-27_r9" --targets-csv "$B\pert_counts.csv" --out "$D\processed\effects_prova_controllo_negativo_2026-09-28"

# Step 7. Diagnostics: coverage (prediction 4), gamma G-a/G-b/G-c, P3 against t25, R-B..R-E (prediction 5).
.\scripts\py.cmd $M --label "passo7 diagnostica" -- "$R\diagnostica.py" --effects "$D\processed\effects_prova_t22_2026-09-28" --negative-control "$D\processed\effects_prova_controllo_negativo_2026-09-28" --cache-new "$D\processed\multisource_prova_2026-09-28_me1" --cache-today "$D\processed\multisource_2026-09-27_r9" --universes me1 --reference-p3 "$D\processed\effects_t25_2026-09-27" --reference-effects "$D\processed\effects_t22_2026-09-26" --cpm-new "$I\basal_cpm_DEF.csv" --libraries "$I\basal_cpm_ABC.json" "$I\basal_cpm_DEF.json" --out "$R\diagnostica.json"

# Step 8. Stage 45 (prediction 2: pilot True in the manifest; context_provenance_ok must be true).
$E = "$D\processed\effects_prova_t22_2026-09-28"
.\scripts\py.cmd $M --label "passo8 stadio45" -- scripts\45_generate_prediction.py --run-id pg22gen --trial trial-ext-profile --controls-dir $B --contexts D,E,F --effects "D=$E\effects_D.npz" --effects "E=$E\effects_E.npz" --effects "F=$E\effects_F.npz" @Shape45

# Step 9. Stage 48. (a) Without --contexts, as before the fix: prediction 1, refused with "Unknown context
# label(s)". (b) With --contexts D,E,F (fix D1): validation, packaging and verification must pass.
.\scripts\py.cmd $M --label "passo9 stadio48 senza contexts" -- scripts\48_package_prediction.py --run-id pg22val --prediction "$D\artifacts\pg22gen\prediction.h5ad" --genes "$B\gene_names.csv" --perts $Perts48 --validate-only
# Before (b), the before/after pilot scripts\CLAUDE.md asks of a change to stage 48: HEAD's stage 48 and
# the working tree's on the same small A/B/C prediction (4 targets x 400 cells x 3 contexts, t22's
# effects), without --contexts: the two .vcc must have the same sha256. About 60 MB each, in TEMP.
$P = "$env:TEMP\pilot48_2026-09-28"; New-Item -ItemType Directory $P | Out-Null
cmd /c "git show HEAD:scripts/48_package_prediction.py > `"$P\stage48_before.py`""   # raw bytes, not re-encoded by PowerShell
Get-Content "$D\raw\controls\pert_counts.csv" -TotalCount 5 | Set-Content -Encoding ascii "$P\perts4.csv"
$T = "$D\processed\effects_t22_2026-09-26"
.\scripts\py.cmd scripts\45_generate_prediction.py --run-id pilot48gen --trial trial-ext-profile --n-perts 4 --effects "A=$T\effects_A.npz" --effects "B=$T\effects_B.npz" --effects "C=$T\effects_C.npz" --out "$P\gen" --reserve-gib 1
.\scripts\py.cmd "$P\stage48_before.py" --run-id pilot48_before --prediction "$P\gen\prediction.h5ad" --perts "$P\perts4.csv" --out "$P\before" --reserve-gib 1
.\scripts\py.cmd scripts\48_package_prediction.py --run-id pilot48_after --prediction "$P\gen\prediction.h5ad" --perts "$P\perts4.csv" --out "$P\after" --reserve-gib 1
Get-FileHash "$P\before\prediction.vcc", "$P\after\prediction.vcc"

.\scripts\py.cmd $M --label "passo9 stadio48 contexts DEF" -- scripts\48_package_prediction.py --run-id pg22pack --prediction "$D\artifacts\pg22gen\prediction.h5ad" --genes "$B\gene_names.csv" --perts $Perts48 --contexts D,E,F @Shape48

# Step 10. Records into the report, then the rehearsal's h5ad and .vcc to the Recycle Bin (sha256 and
# sizes kept; the disk is freed when the owner empties the bin).
Copy-Item "$D\artifacts\pg22gen\manifest_45_generate_prediction.json" "$R\pg22_manifest_45_generate_prediction.json"
Copy-Item "$D\artifacts\pg22gen\generation_diagnostics.json" "$R\pg22_generation_diagnostics.json"
Copy-Item "$D\artifacts\pg22val\packaging.json" "$R\pg22val_packaging.json"
Copy-Item "$D\artifacts\pg22pack\packaging.json" "$R\pg22pack_packaging.json"
Copy-Item "$D\artifacts\pg22pack\manifest_48_package_prediction.json" "$R\pg22pack_manifest_48_package_prediction.json"
Get-FileHash -Algorithm SHA256 "$D\artifacts\pg22gen\prediction.h5ad", "$D\artifacts\pg22pack\prediction.vcc" |
    Select-Object Hash, Path, @{n = "Bytes"; e = { (Get-Item $_.Path).Length } } | ConvertTo-Json | Set-Content -Encoding utf8 "$R\artefatti_nel_cestino.json"
Add-Type -AssemblyName Microsoft.VisualBasic
foreach ($f in "$D\artifacts\pg22gen\prediction.h5ad", "$D\artifacts\pg22pack\prediction.vcc") {
    [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($f, "OnlyErrorDialogs", "SendToRecycleBin")
}
