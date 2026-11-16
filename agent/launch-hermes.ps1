# Launch the local AI agent: start LM Studio, load the tuned Gemma model, open Hermes.
$ErrorActionPreference = 'SilentlyContinue'
$lms    = "$env:USERPROFILE\.lmstudio\bin\lms.exe"
$hermes = "$env:USERPROFILE\tools\hermes-agent\.venv\Scripts\hermes.exe"
$model  = "gemma-4-26b-a4b-it-qat-heretic"

function Say($m, $c = 'Cyan') { Write-Host "  $m" -ForegroundColor $c }

Write-Host ""
Say "=== Local AI Agent  (Gemma 4 26B Heretic + Hermes) ===" 'Magenta'
Write-Host ""

# 1) LM Studio server (idempotent)
Say "Starting LM Studio server..." 'Gray'
& $lms server start 2>$null | Out-Null

# 2) Load the model if it isn't already loaded (tuned defaults apply automatically)
$ps = (& $lms ps 2>$null) -join "`n"
if ($ps -match $model) {
    Say "Model already loaded." 'Green'
} else {
    Say "Loading $model  (~20s first time, ~15 GB)..." 'Yellow'
    & $lms load $model -y 2>$null | Out-Null
    $ps = (& $lms ps 2>$null) -join "`n"
    if ($ps -match $model) { Say "Model loaded." 'Green' }
    else { Say "Could not auto-load the model - open LM Studio once, then retry." 'Red' }
}

# 3) Launch Hermes (interactive). Guard hook, memory, skills and MCP come from your config.
Write-Host ""
Say "Launching Hermes. Type a request, or /help for commands. Ctrl+C to quit." 'Cyan'
Write-Host ""
& $hermes
