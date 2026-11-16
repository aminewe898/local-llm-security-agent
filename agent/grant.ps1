# Open a timed window in which the Hermes guard lets "needs approval" actions run
# (git push, gh PR/issue writes, publishing, POST requests, recursive deletes, installs, system changes).
# Usage:  pwsh grant.ps1 [minutes]   (default 15)      Revoke early:  pwsh grant.ps1 0
param([int]$Minutes = 15)
$file = Join-Path $PSScriptRoot "grant.json"
if ($Minutes -le 0) { Remove-Item $file -ErrorAction SilentlyContinue; "Grant revoked."; exit }
$until = [DateTimeOffset]::UtcNow.AddMinutes($Minutes).ToUnixTimeSeconds()
@{ until = $until } | ConvertTo-Json | Set-Content $file -Encoding utf8
"Approval window open for $Minutes minutes (until $([DateTimeOffset]::FromUnixTimeSeconds($until).LocalDateTime.ToString('HH:mm')))."
"Hard blocks (secrets, ~/.codex, ~/.agents, piped installers, force-push to main) still apply."
