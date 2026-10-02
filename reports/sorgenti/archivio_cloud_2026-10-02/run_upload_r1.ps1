# Upload run r1: copy the data root to its Drive mirror in priority tiers, one process per tier, in sequence.
# Resumable (receipts), never overwrites, waits for free space on C: (Drive for desktop caches a file until it is
# uploaded). Create the file STOP in the run folder to stop cleanly before the next file.
param(
    [string]$Py = 'C:\Users\ferra\vcc2026-data\.venv\Scripts\python.exe',
    [string]$Run = 'C:\Users\ferra\vcc2026-data\processed\archivio_cloud_2026-10-02\r1',
    [double]$MinFreeGb = 6
)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$common = @("`"$here\archivio.py`"", 'copy', '--root', 'C:\Users\ferra\vcc2026-data',
            '--dest', "`"G:\Il mio Drive\vcc2026\data`"", '--plan', "`"$Run\plan_r1.json`"",
            '--receipts', "`"$Run\copy_receipts.jsonl`"", '--min-free-gb', "$MinFreeGb", '--stop-file', "`"$Run\STOP`"")
$tiers = @(
    @{ name = 't1_bench_inputs'
       only = @('processed/universe_', 'processed/basal_sources_2026-09-28.csv', 'processed/corpus_basale_2026-09-28', 'external/vcc2025')
       exclude = @('processed/universe_cd4_2026-09-26', 'processed/universe_orion_hct116_2026-09-26', 'processed/universe_orion_hek293t_2026-09-26') },
    @{ name = 't2_originals'
       only = @('external/', 'raw/vcc_2026_controls.zip')
       exclude = @('external/cd4_gw', 'external/vcc2025') },
    @{ name = 't3_processed_kaggle_raw'
       only = @('processed/', 'kaggle/', 'raw/')
       exclude = @('processed/generalizzazione_contesti_2026-10-02', 'processed/archivio_cloud_2026-10-02') },
    @{ name = 't4_artifacts'; only = @('artifacts/'); exclude = @() },
    @{ name = 't5_interim'; only = @('interim/'); exclude = @() }
)
foreach ($t in $tiers) {
    if (Test-Path "$Run\STOP") { "$(Get-Date -Format o) STOP present, not starting $($t.name)" | Add-Content "$Run\runner.log"; break }
    $a = $common + @('--only') + $t.only
    if ($t.exclude.Count -gt 0) { $a += @('--exclude') + $t.exclude }
    "$(Get-Date -Format o) start $($t.name)" | Add-Content "$Run\runner.log"
    # One log pair per start: a restart must not overwrite the logs of an earlier attempt (it did once, at 00:11
    # of 3 October; the append-only copy_receipts.jsonl kept every file of that attempt).
    $stamp = Get-Date -Format 'yyyyMMddTHHmmss'
    $p = Start-Process -FilePath $Py -ArgumentList $a -RedirectStandardOutput "$Run\copy_$($t.name)_$stamp.out.log" `
        -RedirectStandardError "$Run\copy_$($t.name)_$stamp.err.log" -WindowStyle Hidden -PassThru -Wait
    "$(Get-Date -Format o) end $($t.name) exit=$($p.ExitCode)" | Add-Content "$Run\runner.log"
}
"$(Get-Date -Format o) runner finished" | Add-Content "$Run\runner.log"
