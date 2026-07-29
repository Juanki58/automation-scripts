# Detiene monitor BMS y Ambiq (no para Home Assistant Docker).

$ErrorActionPreference = "Continue"

function Stop-StreamlitOnPort {
    param([int]$Port, [string]$Name)

    try {
        $pids = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($pid in $pids) {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Write-Host "Detenido $Name (PID $pid, puerto $Port)"
        }
        if (-not $pids) {
            Write-Host "$Name no estaba en ejecucion (puerto $Port libre)."
        }
    } catch {
        Write-Host "No se pudo detener $Name en puerto $Port: $_"
    }
}

Stop-StreamlitOnPort -Port 8501 -Name "BMS monitor"
Stop-StreamlitOnPort -Port 8502 -Name "Ambiq monitor"

Write-Host "Home Assistant Docker no se detiene (docker stop homeassistant si lo necesitas)."
