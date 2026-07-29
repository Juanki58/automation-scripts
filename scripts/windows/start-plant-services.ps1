# Arranca servicios de planta al iniciar sesión en Windows.
# Home Assistant (Docker) + monitor BMS (8501) + Ambiq (8502).

$ErrorActionPreference = "Continue"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$SolarTelemetryRoot = if ($env:SOLAR_TELEMETRY_ROOT) {
    $env:SOLAR_TELEMETRY_ROOT
} else {
    (Resolve-Path (Join-Path $RepoRoot "..\solar-telemetry")).Path
}
$LogDir = Join-Path $env:LOCALAPPDATA "plant-services"
$LogFile = Join-Path $LogDir "startup.log"

function Write-Log {
    param([string]$Message)
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$stamp] $Message"
    if (-not (Test-Path $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    }
    Add-Content -Path $LogFile -Value $line
}

function Get-PythonCommand {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @{ Exe = "py"; Args = @("-3") }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @{ Exe = "python"; Args = @() }
    }
    return $null
}

function Test-PortListening {
    param([int]$Port)
    try {
        return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    } catch {
        return $false
    }
}

function Start-DockerService {
    Write-Log "Comprobando Docker..."
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Log "Docker no encontrado en PATH."
        return
    }

    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Docker no responde; intentando iniciar Docker Desktop..."
        $dockerDesktop = "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
        if (Test-Path $dockerDesktop) {
            Start-Process -FilePath $dockerDesktop | Out-Null
            $deadline = (Get-Date).AddMinutes(3)
            while ((Get-Date) -lt $deadline) {
                Start-Sleep -Seconds 5
                docker info 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) { break }
            }
        } else {
            Write-Log "Docker Desktop no instalado en ruta habitual."
            return
        }
    }

    $ha = docker ps -a --filter "name=^homeassistant$" --format "{{.Names}}" 2>$null
    if ($ha -eq "homeassistant") {
        $running = docker ps --filter "name=^homeassistant$" --format "{{.Names}}" 2>$null
        if ($running -ne "homeassistant") {
            Write-Log "Iniciando contenedor homeassistant..."
            docker start homeassistant 2>&1 | Out-Null
        } else {
            Write-Log "Home Assistant ya en ejecución."
        }
        docker update --restart unless-stopped homeassistant 2>&1 | Out-Null
    } else {
        Write-Log "Contenedor homeassistant no encontrado; omitido."
    }
}

function Start-StreamlitApp {
    param(
        [string]$Name,
        [string]$ScriptPath,
        [int]$Port,
        [string]$Address = "0.0.0.0",
        [string]$WorkingDirectory = $RepoRoot
    )

    if (Test-PortListening -Port $Port) {
        Write-Log "$Name ya escucha en puerto $Port."
        return
    }

    $python = Get-PythonCommand
    if (-not $python) {
        Write-Log "Python no encontrado; no se inicia $Name."
        return
    }

    if (-not (Test-Path $ScriptPath)) {
        Write-Log "No existe script $ScriptPath"
        return
    }

    $streamlitArgs = @(
        "-m", "streamlit", "run", $ScriptPath,
        "--server.port", "$Port",
        "--server.address", $Address,
        "--server.headless", "true"
    )

    $allArgs = @($python.Args + $streamlitArgs) -join " "
    Write-Log "Iniciando $Name en :$Port ($ScriptPath)"

    Start-Process `
        -FilePath $python.Exe `
        -ArgumentList $allArgs `
        -WorkingDirectory $WorkingDirectory `
        -WindowStyle Hidden `
        | Out-Null
}

Write-Log "=== Arranque servicios planta ==="
Write-Log "Repo: $RepoRoot"
Write-Log "Solar telemetry: $SolarTelemetryRoot"

Start-DockerService

Start-StreamlitApp `
    -Name "BMS monitor" `
    -ScriptPath (Join-Path $SolarTelemetryRoot "bms_web_monitor.py") `
    -Port 8501 `
    -Address "0.0.0.0" `
    -WorkingDirectory $SolarTelemetryRoot

Start-StreamlitApp `
    -Name "Ambiq monitor" `
    -ScriptPath (Join-Path $RepoRoot "market-analysis\ambiq_monitor.py") `
    -Port 8502 `
    -Address "127.0.0.1"

Write-Log "Arranque completado."
Write-Log "URLs: HA http://127.0.0.1:8123 | BMS http://127.0.0.1:8501 | Ambiq http://127.0.0.1:8502"
