$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class T34Awake {
    [DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint flags);
}
'@
$stopFile = Join-Path $PSScriptRoot 't34_keep_awake_stop.json'
$expires = [DateTime]::UtcNow.AddHours(9)
if ([T34Awake]::SetThreadExecutionState(2147483649) -eq 0) { throw 'Cannot inhibit sleep' }
try {
    @{started_utc=[DateTime]::UtcNow.ToString('o');expires_utc=$expires.ToString('o');pid=$PID;system_sleep_inhibited=$true;display_sleep_allowed=$true} | ConvertTo-Json | Set-Content (Join-Path $PSScriptRoot 't34_keep_awake_started.json') -Encoding UTF8
    while ([DateTime]::UtcNow -lt $expires -and -not (Test-Path -LiteralPath $stopFile)) { Start-Sleep -Seconds 15 }
} finally {
    [void][T34Awake]::SetThreadExecutionState(2147483648)
}
