# Remove only the nine named archived copies after a complete, locked recheck.
# Without -Apply this is a read-only dry run, apart from its audit receipt.
param(
    [Parameter(Mandatory=$true)][string]$PlanPath,
    [Parameter(Mandatory=$true)][string]$PlanSha256,
    [Parameter(Mandatory=$true)][string]$ReceiptPath,
    [switch]$Apply
)
$ErrorActionPreference = 'Stop'
$expectedRoot = [IO.Path]::GetFullPath('C:\Users\ferra\vcc2026-data')
$receiptFull = [IO.Path]::GetFullPath($ReceiptPath)
if (-not $receiptFull.StartsWith($PSScriptRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Receipt must be in this report directory'
}
if ((Test-Path -LiteralPath $receiptFull) -or (Test-Path -LiteralPath ($receiptFull + '.jsonl'))) { throw 'Receipt already exists' }
if ((Get-FileHash -LiteralPath $PlanPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $PlanSha256.ToLowerInvariant()) { throw 'Plan hash mismatch' }
$plan = Get-Content -LiteralPath $PlanPath -Raw | ConvertFrom-Json
if ([IO.Path]::GetFullPath($plan.root) -ne $expectedRoot) { throw 'Unexpected data root' }
if ((Get-FileHash -LiteralPath $plan.proof_path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $plan.proof_sha256) { throw 'Remote proof changed' }
$allowed = @{}
foreach ($folder in @('kaggle/rete_data_r1','processed/rete_contesti_r1','processed/rete_contesti_r2')) {
    foreach ($name in @('raw','se','shrunk')) { $allowed["$folder/$name.npy"] = $true }
}
if (@($plan.rows).Count -ne 9) { throw 'Expected exactly nine paths' }
$seen = @{}
$handles = [Collections.Generic.List[IDisposable]]::new()
$verified = @{}
$removed = [Collections.Generic.List[string]]::new()
$before = [IO.DriveInfo]::new('C').AvailableFreeSpace
$started = (Get-Date).ToUniversalTime().ToString('o')
try {
    foreach ($row in $plan.rows) {
        if (-not $allowed.ContainsKey($row.rel) -or $seen.ContainsKey($row.rel)) { throw "Unexpected or repeated path $($row.rel)" }
        $seen[$row.rel] = $true
        $path = [IO.Path]::GetFullPath((Join-Path $expectedRoot $row.rel))
        if ($path -ne [IO.Path]::GetFullPath($row.path) -or -not $path.StartsWith($expectedRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Path escaped the data root' }
        $item = Get-Item -LiteralPath $path -Force
        if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Not an ordinary file: $path" }
        $ancestor = $item.Directory
        while ($ancestor.FullName -ne $expectedRoot) {
            if (($ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint) -or -not $ancestor.FullName.StartsWith($expectedRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe ancestor' }
            $ancestor = $ancestor.Parent
        }
        $remote = @($row.remote_proofs | Where-Object { $_.status -eq 'match' -and $_.sha256_kaggle -eq $row.sha256 -and [long]$_.bytes -eq [long]$row.bytes })
        if ($remote.Count -eq 0) { throw "Missing remote proof: $path" }
        # Deny writers for the complete check/removal phase; allow all aliases to be read.
        $stream = [IO.File]::Open($path, [IO.FileMode]::Open, [IO.FileAccess]::Read, ([IO.FileShare]::Read -bor [IO.FileShare]::Delete))
        $handles.Add($stream)
        if ($stream.Length -ne [long]$row.bytes) { throw "Size changed: $path" }
        $hash = [Security.Cryptography.SHA256]::Create()
        try { $actual = [Convert]::ToHexString($hash.ComputeHash($stream)).ToLowerInvariant() } finally { $hash.Dispose() }
        if ($actual -ne $row.sha256) { throw "Hash changed: $path" }
        $verified[$row.file_id] = $true
        Write-Output "Verified $($row.rel)"
    }
    if ($Apply) {
        foreach ($row in $plan.rows) {
            Remove-Item -LiteralPath ([IO.Path]::GetFullPath($row.path)) -ErrorAction Stop
            $removed.Add($row.rel)
            @{rel=$row.rel;sha256=$row.sha256;removed_utc=(Get-Date).ToUniversalTime().ToString('o')} | ConvertTo-Json -Compress | Add-Content -LiteralPath ($receiptFull + '.jsonl') -Encoding utf8
        }
    }
} finally {
    foreach ($handle in $handles) { $handle.Dispose() }
    $after = [IO.DriveInfo]::new('C').AvailableFreeSpace
    [ordered]@{started_utc=$started;finished_utc=(Get-Date).ToUniversalTime().ToString('o');apply=[bool]$Apply;
        plan_sha256=$PlanSha256;verified_physical_files=$verified.Count;removed_paths=@($removed.ToArray());
        free_bytes_before=$before;free_bytes_after=$after;free_bytes_delta=($after-$before);
        expected_unique_bytes=$plan.unique_bytes} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $receiptFull -Encoding utf8
}
