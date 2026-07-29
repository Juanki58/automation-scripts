# Registra arranque automático al iniciar sesión (tarea programada).

$ErrorActionPreference = "Stop"

$TaskName = "PlantServices-Autostart"
$StartScript = Join-Path $PSScriptRoot "start-plant-services.ps1"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

if (-not (Test-Path $StartScript)) {
    throw "No se encuentra $StartScript"
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$StartScript`"" `
    -WorkingDirectory $RepoRoot

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Arranca Home Assistant (Docker), monitor BMS (8501) y Ambiq (8502)." | Out-Null

Write-Host "Tarea registrada: $TaskName"
Write-Host "Se ejecutara al iniciar sesion."
Write-Host "Log: $env:LOCALAPPDATA\plant-services\startup.log"
Write-Host ""
Write-Host "Probar ahora:"
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$StartScript`""
