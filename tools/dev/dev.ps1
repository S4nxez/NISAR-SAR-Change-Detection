#Requires -Version 5.1
<#
.SYNOPSIS
  Entorno de desarrollo local de NISAR SAR en Windows: base de datos (Docker), servidor
  Spring Boot y frontend con recarga en caliente (Go Live de VS Code o live-server en Docker).

.DESCRIPTION
  Lo invoca el Makefile de la raíz (make <objetivo>) o dev.cmd si la máquina no tiene make.
  Compatible con Windows PowerShell 5.1 (viene con Windows) y PowerShell 7.

  Configuración por variables de entorno (o make <objetivo> VAR=valor):
    DB_PORT         Puerto de MySQL en localhost                    (3306)
    DB_PASSWORD     Contraseña de root de MySQL                     (root)
    SERVER_PORT     Puerto del servidor Spring Boot                 (8080)
    FRONT_PORT      Puerto del frontend                             (5500)
    SERVER_MODE     auto | local (JDK 21 de la máquina) | docker    (auto)
    FRONT_MODE      auto | vscode (Go Live) | docker (live-server)  (auto)
    SERVER_TIMEOUT  Segundos máximos esperando a que arranque       (180)
    FRONT_WAIT      Segundos esperando a que se pulse Go Live       (120)
    OPEN            1 abre el navegador, 0 no                       (1)
    YES             1 no pide confirmación en acciones destructivas (0)
    FORCE           1 permite parar procesos ajenos que ocupen el puerto del servidor (0)
#>
param(
    [Parameter(Position = 0)][string]$Action = 'help'
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # Invoke-WebRequest es muy lento en 5.1 con la barra
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch { }

# ----------------------------------------------------------------------------------------------
# Rutas y configuración
# ----------------------------------------------------------------------------------------------
$Root        = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$ServerDir   = Join-Path $Root 'server'
$FrontDir    = Join-Path $Root 'frontend'
$LabDir      = Join-Path $Root 'fractal_model_lab'
$StateDir    = Join-Path $Root '.dev'
$ComposeFile = Join-Path $PSScriptRoot 'compose.dev.yml'
$LabFile     = Join-Path $PSScriptRoot 'lab.Containerfile'
$ServerState = Join-Path $StateDir 'server.json'
$ServerLog   = Join-Path $StateDir 'server.log'

$ComposeProject  = 'nisarsar-dev'
$DbContainer     = 'nisarsar-dev-mysql'
$ServerContainer = 'nisarsar-dev-server'
$FrontContainer  = 'nisarsar-dev-front'
$LabImage        = 'nisarsar-lab:dev'
$LiveServerExt   = 'ritwickdey.LiveServer'
$DbName          = 'NisarSar'
$DbUser          = 'root'

function Get-Setting([string]$Name, $Default) {
    $v = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($v)) { return $Default }
    return $v.Trim()
}
function Get-IntSetting([string]$Name, [int]$Default) {
    $v = Get-Setting $Name "$Default"
    $n = 0
    if (-not [int]::TryParse($v, [ref]$n) -or $n -le 0) {
        throw "La variable $Name='$v' no es un número válido."
    }
    return $n
}

$DbPort        = Get-IntSetting 'DB_PORT' 3306
$DbPassword    = Get-Setting 'DB_PASSWORD' 'root'
$ServerPort    = Get-IntSetting 'SERVER_PORT' 8080
$FrontPort     = Get-IntSetting 'FRONT_PORT' 5500
$ServerMode    = (Get-Setting 'SERVER_MODE' 'auto').ToLowerInvariant()
$FrontMode     = (Get-Setting 'FRONT_MODE' 'auto').ToLowerInvariant()
$ServerTimeout = Get-IntSetting 'SERVER_TIMEOUT' 180
$FrontWait     = Get-IntSetting 'FRONT_WAIT' 120
$OpenBrowser   = (Get-Setting 'OPEN' '1') -ne '0'
$AssumeYes     = (Get-Setting 'YES' '0') -eq '1'
$Force         = (Get-Setting 'FORCE' '0') -eq '1'

if (@('auto', 'local', 'docker') -notcontains $ServerMode) { throw "SERVER_MODE debe ser auto, local o docker (es '$ServerMode')." }
if (@('auto', 'vscode', 'docker') -notcontains $FrontMode) { throw "FRONT_MODE debe ser auto, vscode o docker (es '$FrontMode')." }

$DbUrl     = "jdbc:mysql://localhost:$DbPort/$DbName"
$ServerUrl = "http://127.0.0.1:$ServerPort"
$HealthUrl = "$ServerUrl/api/sites"
$FrontUrl  = "http://127.0.0.1:$FrontPort/"

# Lo leen docker compose (interpolación de compose.dev.yml) y el servidor (Spring lee
# SERVER_PORT, DB_URL, DB_USER y DB_PASSWORD de application.properties).
$env:DB_PORT     = "$DbPort"
$env:DB_PASSWORD = $DbPassword
$env:SERVER_PORT = "$ServerPort"
$env:FRONT_PORT  = "$FrontPort"

# ----------------------------------------------------------------------------------------------
# Salida
# ----------------------------------------------------------------------------------------------
function Say([string]$m)  { Write-Host "==> $m" -ForegroundColor Cyan }
function Ok([string]$m)   { Write-Host "  [ok] $m" -ForegroundColor Green }
function Warn([string]$m) { Write-Host "  [!]  $m" -ForegroundColor Yellow }
function Bad([string]$m)  { Write-Host "  [x]  $m" -ForegroundColor Red }
function Info([string]$m) { Write-Host "       $m" }

function Confirm-Action([string]$Question) {
    if ($AssumeYes) { return $true }
    $a = Read-Host "$Question [s/N]"
    return ($a -match '^(s|si|sí|y|yes)$')
}

# ----------------------------------------------------------------------------------------------
# Ejecución de programas externos
# En PowerShell 5.1, con ErrorActionPreference=Stop, cualquier línea que un programa escriba
# en stderr se convierte en excepción: se baja a Continue mientras se ejecutan.
# ----------------------------------------------------------------------------------------------
function Invoke-Native([string]$Exe, [string[]]$Arguments) {
    # Muestra la salida según llega y devuelve el código de salida.
    $old = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $Exe @Arguments 2>&1 | ForEach-Object { Write-Host "$_" }
        return $LASTEXITCODE
    } finally { $ErrorActionPreference = $old }
}

function Get-NativeOutput([string]$Exe, [string[]]$Arguments) {
    # Captura la salida (stdout + stderr) sin mostrarla.
    $old = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $lines = @(& $Exe @Arguments 2>&1 | ForEach-Object { "$_" })
        return [pscustomobject]@{ Code = $LASTEXITCODE; Text = ($lines -join "`n").Trim() }
    } catch {
        return [pscustomobject]@{ Code = 1; Text = $_.Exception.Message }
    } finally { $ErrorActionPreference = $old }
}

function Invoke-Interactive([string]$Exe, [string[]]$Arguments) {
    # Para comandos con TTY o que siguen la salida (-it, -f): sin redirecciones.
    $old = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & $Exe @Arguments } finally { $ErrorActionPreference = $old }
}

function Test-Command([string]$Name) { return [bool](Get-Command $Name -ErrorAction SilentlyContinue) }

function Ensure-StateDir {
    if (-not (Test-Path $StateDir)) { New-Item -ItemType Directory -Path $StateDir | Out-Null }
}

# ----------------------------------------------------------------------------------------------
# Puertos y procesos
# ----------------------------------------------------------------------------------------------
function Get-PortPids([int]$Port) {
    # PIDs que escuchan en el puerto TCP (IPv4 o IPv6).
    $ids = @()
    if (Test-Command 'Get-NetTCPConnection') {
        try {
            $ids = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop |
                     Select-Object -ExpandProperty OwningProcess)
        } catch { $ids = @() }   # sin conexiones: el cmdlet lanza ObjectNotFound
    } else {
        # netstat: el estado sale traducido (LISTENING/ESCUCHANDO), así que se reconoce la
        # escucha por la dirección remota con puerto 0
        $rx = '^\s*TCP\s+\S+:(\d+)\s+\S+:0\s+\S+\s+(\d+)\s*$'
        foreach ($line in (netstat -ano -p TCP) + (netstat -ano -p TCPv6)) {
            $m = [regex]::Match("$line", $rx)
            if ($m.Success -and [int]$m.Groups[1].Value -eq $Port) { $ids += [int]$m.Groups[2].Value }
        }
    }
    return @($ids | Where-Object { $_ -gt 0 } | Sort-Object -Unique)
}

function Get-ProcInfo([int]$Id) {
    $p = Get-CimInstance Win32_Process -Filter "ProcessId=$Id" -ErrorAction SilentlyContinue
    if (-not $p) { return $null }
    $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($p.ParentProcessId)" -ErrorAction SilentlyContinue
    return [pscustomobject]@{
        Id          = $Id
        Name        = "$($p.Name)"
        CommandLine = "$($p.CommandLine)"
        ParentId    = [int]$p.ParentProcessId
        ParentName  = $(if ($parent) { "$($parent.Name)" } else { '' })
        Started     = $p.CreationDate
    }
}

function Test-ProcessAlive([int]$Id) {
    if ($Id -le 0) { return $false }
    return [bool](Get-Process -Id $Id -ErrorAction SilentlyContinue)
}

function Stop-ProcessTree([int]$Id) {
    if (-not (Test-ProcessAlive $Id)) { return }
    $r = Get-NativeOutput 'taskkill.exe' @('/PID', "$Id", '/T', '/F')
    if ($r.Code -ne 0 -and (Test-ProcessAlive $Id)) {
        Stop-Process -Id $Id -Force -ErrorAction SilentlyContinue
    }
}

function Format-Cmd([string]$CommandLine, [int]$Max = 150) {
    if ([string]::IsNullOrWhiteSpace($CommandLine)) { return '(línea de comandos no disponible: proceso de otro usuario o elevado)' }
    $c = $CommandLine -replace '\s+', ' '
    if ($c.Length -gt $Max) { $c = $c.Substring(0, $Max) + '...' }
    return $c
}

function Test-DockerProcessName([string]$Name) {
    return ($Name -match '^(com\.docker\.|docker|wslrelay|vpnkit|dockerd)' )
}

function Test-Http([string]$Url) {
    # Cualquier respuesta HTTP (incluidos 4xx/5xx) significa que el servidor escucha.
    try {
        Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 4 -Method Get | Out-Null
        return $true
    } catch {
        if ($_.Exception.Response) { return $true }
        return $false
    }
}

function Wait-Port([int]$Port, [int]$Seconds) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if ((Get-PortPids $Port).Count -gt 0) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Open-Url([string]$Url) {
    if ($OpenBrowser) { Start-Process $Url | Out-Null }
}

# ----------------------------------------------------------------------------------------------
# Docker
# ----------------------------------------------------------------------------------------------
$script:DockerReady = $false

function Find-DockerCli {
    if (Test-Command 'docker') { return $true }
    $bin = Join-Path $env:ProgramFiles 'Docker\Docker\resources\bin'
    if (Test-Path (Join-Path $bin 'docker.exe')) {
        $env:PATH = "$bin;$env:PATH"   # instalado pero fuera del PATH de esta consola
        return $true
    }
    return $false
}

function Find-DockerDesktop {
    foreach ($p in @(
            (Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'),
            (Join-Path $env:LOCALAPPDATA 'Programs\Docker\Docker\Docker Desktop.exe'))) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

$script:DaemonUp = $false
function Test-DockerDaemon {
    if ($script:DaemonUp) { return $true }   # 'docker info' tarda: solo se cachea el 'sí'
    if (-not (Find-DockerCli)) { return $false }
    $script:DaemonUp = ((Get-NativeOutput 'docker' @('info', '--format', '{{.OSType}}')).Code -eq 0)
    return $script:DaemonUp
}

function Ensure-Docker {
    if ($script:DockerReady) { return }

    if (-not (Find-DockerCli)) {
        throw ("Docker no está instalado. Instala Docker Desktop y vuelve a lanzar el comando:`n" +
               "         winget install -e --id Docker.DockerDesktop   (pide reiniciar; usa el backend WSL 2)")
    }

    $info = Get-NativeOutput 'docker' @('info', '--format', '{{.OSType}}')
    if ($info.Code -ne 0) {
        $desktop = Find-DockerDesktop
        if (-not $desktop) {
            throw "El demonio de Docker no responde y no se encuentra Docker Desktop para arrancarlo.`n$($info.Text)"
        }
        Say 'Docker Desktop no está arrancado: arrancándolo (puede tardar hasta 2-3 minutos)...'
        Start-Process -FilePath $desktop | Out-Null
        $deadline = (Get-Date).AddSeconds(240)
        do {
            Start-Sleep -Seconds 3
            Write-Host '.' -NoNewline
            $info = Get-NativeOutput 'docker' @('info', '--format', '{{.OSType}}')
        } while ($info.Code -ne 0 -and (Get-Date) -lt $deadline)
        Write-Host ''
        if ($info.Code -ne 0) {
            throw "Docker Desktop no ha terminado de arrancar. Ábrelo, espera a que diga 'Engine running' y repite.`n$($info.Text)"
        }
    }

    if ($info.Text -match 'windows') {
        $cli = Join-Path $env:ProgramFiles 'Docker\Docker\DockerCli.exe'
        if (-not (Test-Path $cli)) {
            throw 'Docker está en modo contenedores Windows. Cámbialo: icono de Docker > Switch to Linux containers.'
        }
        Say 'Docker está en modo contenedores Windows: cambiando a contenedores Linux...'
        Invoke-Native $cli @('-SwitchLinuxEngine') | Out-Null
        Start-Sleep -Seconds 10
        $info = Get-NativeOutput 'docker' @('info', '--format', '{{.OSType}}')
        if ($info.Text -notmatch 'linux') { throw 'No se ha podido cambiar Docker a contenedores Linux. Hazlo desde el icono de Docker.' }
    }

    if ((Get-NativeOutput 'docker' @('compose', 'version')).Code -ne 0) {
        throw "Falta 'docker compose' (v2). Actualiza Docker Desktop: winget upgrade -e --id Docker.DockerDesktop"
    }
    $script:DockerReady = $true
}

function Invoke-Compose([string[]]$Arguments, [string[]]$Profiles = @()) {
    Ensure-Docker
    # Destino del proxy /api de live-server en Docker: por la red de compose si el servidor
    # también está en Docker; si no, el host (IntelliJ o make con JDK local)
    if ((Get-ContainerState $ServerContainer) -eq 'running') { $env:API_TARGET = 'http://server:8080/api' }
    else { $env:API_TARGET = "http://host.docker.internal:$ServerPort/api" }
    $a = @('compose', '-f', $ComposeFile, '-p', $ComposeProject)
    foreach ($p in $Profiles) { $a += @('--profile', $p) }
    return (Invoke-Native 'docker' ($a + $Arguments))
}

function Get-ContainerState([string]$Name) {
    # running | exited | created | ... ; '' si no existe o Docker no está disponible.
    # Nunca arranca Docker Desktop: se usa también desde status.
    if (-not (Test-DockerDaemon)) { return '' }
    $r = Get-NativeOutput 'docker' @('inspect', '-f', '{{.State.Status}}', $Name)
    if ($r.Code -ne 0) { return '' }
    return $r.Text
}

function Get-ContainerHealth([string]$Name) {
    $r = Get-NativeOutput 'docker' @('inspect', '-f', '{{if .State.Health}}{{.State.Health.Status}}{{end}}', $Name)
    if ($r.Code -ne 0) { return '' }
    return $r.Text
}

# ----------------------------------------------------------------------------------------------
# Java, Maven, VS Code, IntelliJ
# ----------------------------------------------------------------------------------------------
function Get-JdkMajor([string]$JavaHome) {
    $release = Join-Path $JavaHome 'release'
    if (-not (Test-Path $release)) { return 0 }
    $m = Select-String -Path $release -Pattern '^JAVA_VERSION="([^"]+)"' | Select-Object -First 1
    if (-not $m) { return 0 }
    $parts = $m.Matches[0].Groups[1].Value.Split('.')
    if ($parts[0] -eq '1' -and $parts.Count -gt 1) { return [int]$parts[1] }   # 1.8 -> 8
    return [int]($parts[0] -replace '\D.*$', '')
}

function Find-Jdks {
    # Todos los JDK (con javac) que se encuentran en la máquina, el más nuevo primero.
    $homes = New-Object System.Collections.Generic.List[string]
    if ($env:JAVA_HOME) { $homes.Add($env:JAVA_HOME.TrimEnd('\')) }
    $java = Get-Command java -ErrorAction SilentlyContinue
    if ($java) {
        $o = Get-NativeOutput $java.Source @('-XshowSettings:properties', '-version')
        $m = [regex]::Match($o.Text, 'java\.home = (.+)')
        if ($m.Success) { $homes.Add($m.Groups[1].Value.Trim()) }
    }
    $patterns = @(
        (Join-Path $HOME '.jdks\*'),                         # JDKs descargados desde IntelliJ
        (Join-Path $env:ProgramFiles 'Java\*'),
        (Join-Path $env:ProgramFiles 'Eclipse Adoptium\*'),
        (Join-Path $env:ProgramFiles 'Microsoft\jdk-*'),
        (Join-Path $env:ProgramFiles 'Zulu\*'),
        (Join-Path $env:ProgramFiles 'Amazon Corretto\*'),
        (Join-Path $env:ProgramFiles 'BellSoft\*'),
        (Join-Path $env:ProgramFiles 'OpenJDK\*'),
        (Join-Path $HOME 'scoop\apps\*jdk*\current')
    )
    foreach ($p in $patterns) {
        Get-ChildItem -Path $p -Directory -ErrorAction SilentlyContinue | ForEach-Object { $homes.Add($_.FullName) }
    }
    $seen = @{}
    $found = @()
    foreach ($h in $homes) {
        $key = $h.ToLowerInvariant()
        if ($seen.ContainsKey($key)) { continue }
        $seen[$key] = $true
        if (-not (Test-Path (Join-Path $h 'bin\javac.exe'))) { continue }
        $found += [pscustomobject]@{ Home = $h; Major = (Get-JdkMajor $h) }
    }
    return @($found | Sort-Object Major -Descending)
}

function Find-Jdk21 {
    # El proyecto usa Lombok 1.18.30, que no compila con JDK 22 o superior: hace falta un 21.
    return (Find-Jdks | Where-Object { $_.Major -eq 21 } | Select-Object -First 1)
}

function Find-IntelliJHomes {
    $patterns = @(
        (Join-Path $env:ProgramFiles 'JetBrains\IntelliJ*'),
        (Join-Path $env:LOCALAPPDATA 'Programs\IntelliJ*'),
        (Join-Path $env:LOCALAPPDATA 'JetBrains\Toolbox\apps\IDEA-*\ch-*\*'),
        (Join-Path $env:LOCALAPPDATA 'JetBrains\Toolbox\apps\intellij-idea*')
    )
    $r = @()
    foreach ($p in $patterns) {
        Get-ChildItem -Path $p -Directory -ErrorAction SilentlyContinue |
            Where-Object { Test-Path (Join-Path $_.FullName 'bin\idea64.exe') } |
            ForEach-Object { $r += $_.FullName }
    }
    return @($r)
}

function Find-Maven {
    $wrapper = Join-Path $ServerDir 'mvnw.cmd'
    if ((Test-Path $wrapper) -and (Test-Path (Join-Path $ServerDir '.mvn\wrapper\maven-wrapper.properties'))) {
        return [pscustomobject]@{ Exe = $wrapper; Source = 'Maven Wrapper del proyecto (server\mvnw.cmd)' }
    }
    $mvn = Get-Command mvn -ErrorAction SilentlyContinue
    if ($mvn) { return [pscustomobject]@{ Exe = $mvn.Source; Source = "mvn del PATH ($($mvn.Source))" } }
    foreach ($idea in Find-IntelliJHomes) {
        $bundled = Join-Path $idea 'plugins\maven\lib\maven3\bin\mvn.cmd'
        if (Test-Path $bundled) { return [pscustomobject]@{ Exe = $bundled; Source = "Maven incluido en IntelliJ ($bundled)" } }
    }
    return $null
}

function Find-VSCode {
    $c = Get-Command code -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    foreach ($p in @(
            (Join-Path $env:LOCALAPPDATA 'Programs\Microsoft VS Code\bin\code.cmd'),
            (Join-Path $env:ProgramFiles 'Microsoft VS Code\bin\code.cmd'))) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

function Test-LiveServerExtension([string]$Code) {
    $dir = Join-Path $HOME '.vscode\extensions'
    if (Get-ChildItem -Path $dir -Directory -Filter 'ritwickdey.liveserver-*' -ErrorAction SilentlyContinue) { return $true }
    $r = Get-NativeOutput $Code @('--list-extensions')
    return ($r.Text -match '(?im)^ritwickdey\.liveserver$')
}

# ----------------------------------------------------------------------------------------------
# Base de datos
# ----------------------------------------------------------------------------------------------
function Start-Db {
    Say "Base de datos MySQL ($DbContainer en localhost:$DbPort)"
    Ensure-Docker

    $state = Get-ContainerState $DbContainer
    if ($state -ne 'running') {
        # Guard: otro MySQL (servicio de Windows, XAMPP...) ya ocupa el puerto
        $pids = Get-PortPids $DbPort
        if ($pids.Count -gt 0) {
            $p = Get-ProcInfo $pids[0]
            $who = $(if ($p) { "$($p.Name) (PID $($p.Id))" } else { "PID $($pids[0])" })
            if (-not ($p -and (Test-DockerProcessName $p.Name))) {
                throw ("El puerto $DbPort ya lo usa $who, probablemente un MySQL instalado en Windows.`n" +
                       "         Opciones: pararlo (p. ej. 'net stop MySQL80' como administrador) o usar otro puerto:`n" +
                       "         make up DB_PORT=3307   (y en IntelliJ añade la variable DB_URL=jdbc:mysql://localhost:3307/$DbName)")
            }
        }
    }

    $code = Invoke-Compose @('up', '-d', '--wait', 'mysql')
    if ($code -ne 0) {
        Invoke-Native 'docker' @('logs', '--tail', '30', $DbContainer) | Out-Null
        throw 'MySQL no ha arrancado (salida arriba).'
    }
    Ok "MySQL listo: $DbUrl  (usuario $DbUser / $DbPassword)"
}

function Stop-Db {
    Say 'Parando MySQL (los datos se conservan)'
    if (-not (Test-DockerDaemon)) { Ok 'Docker no está arrancado: nada que parar.'; return }
    if ((Get-ContainerState $DbContainer) -eq '') { Ok 'El contenedor de MySQL no existe.'; return }
    Invoke-Compose @('stop', 'mysql') | Out-Null
    Ok 'MySQL parado.'
}

function Reset-Db {
    if (-not (Confirm-Action "Se borrarán TODOS los datos de la base de datos de desarrollo. ¿Seguro?")) { Warn 'Cancelado.'; return }
    Stop-Server -Quiet
    Ensure-Docker
    Invoke-Compose @('rm', '-s', '-f', 'mysql') | Out-Null
    Invoke-Native 'docker' @('volume', 'rm', '-f', "${ComposeProject}_mysql_data") | Out-Null
    Ok 'Volumen de datos borrado.'
    Start-Db
    Info 'Las migraciones de Flyway se aplican al arrancar el servidor: make server'
}

# ----------------------------------------------------------------------------------------------
# Servidor
# ----------------------------------------------------------------------------------------------
function Read-ServerState {
    if (-not (Test-Path $ServerState)) { return $null }
    try { return (Get-Content $ServerState -Raw | ConvertFrom-Json) } catch { return $null }
}

function Get-ServerOwner {
    # Quién ocupa el puerto del servidor:
    #   make     -> lanzado por este script (proceso local)
    #   docker   -> contenedor nisarsar-dev-server
    #   project  -> otra instancia de este proyecto (IntelliJ, mvn spring-boot:run, java -jar...)
    #   foreign  -> cualquier otro programa
    #   none     -> libre
    if ((Get-ContainerState $ServerContainer) -eq 'running') {
        return [pscustomobject]@{ Kind = 'docker'; Proc = $null; Text = "contenedor Docker $ServerContainer" }
    }
    $pids = Get-PortPids $ServerPort
    if ($pids.Count -eq 0) { return [pscustomobject]@{ Kind = 'none'; Proc = $null; Text = 'libre' } }

    $state = Read-ServerState
    $p = Get-ProcInfo $pids[0]
    if (-not $p) { return [pscustomobject]@{ Kind = 'foreign'; Proc = $null; Text = "PID $($pids[0])" } }

    if ($state -and ($p.Id -eq [int]$state.javaPid -or $p.ParentId -eq [int]$state.launcherPid)) {
        return [pscustomobject]@{ Kind = 'make'; Proc = $p; Text = "lanzado con make (PID $($p.Id))" }
    }
    if (Test-DockerProcessName $p.Name) {
        return [pscustomobject]@{ Kind = 'foreign'; Proc = $p; Text = "un contenedor Docker ajeno a este entorno ($($p.Name), PID $($p.Id))" }
    }
    $isJava = $p.Name -match '^javaw?\.exe$'
    $fromIdea = $p.ParentName -match '^idea(64)?\.exe$'
    $isProject = ($p.CommandLine -match '(?i)nisarsar|NisarSARApplication') -or
                 ($p.CommandLine.IndexOf((Join-Path $StateDir 'server.jar'), [StringComparison]::OrdinalIgnoreCase) -ge 0)
    if ($isJava -and ($fromIdea -or $isProject)) {
        $origin = $(if ($fromIdea) { 'IntelliJ' } else { "$($p.ParentName)" })
        return [pscustomobject]@{ Kind = 'project'; Proc = $p; Text = "servidor de este proyecto lanzado desde $origin (PID $($p.Id))" }
    }
    return [pscustomobject]@{ Kind = 'foreign'; Proc = $p; Text = "$($p.Name) (PID $($p.Id))" }
}

function Resolve-ServerMode {
    if ($ServerMode -eq 'docker') { return [pscustomobject]@{ Mode = 'docker'; Jdk = $null } }
    $jdk = Find-Jdk21
    if ($jdk) { return [pscustomobject]@{ Mode = 'local'; Jdk = $jdk } }
    if ($ServerMode -eq 'local') {
        throw ("SERVER_MODE=local pero no hay ningún JDK 21 instalado (el proyecto usa Lombok 1.18.30, que no compila con 22+).`n" +
               "         Instálalo con: winget install -e --id EclipseAdoptium.Temurin.21.JDK`n" +
               "         o desde IntelliJ: File > Project Structure > SDKs > + > Download JDK > versión 21.")
    }
    Warn 'No hay JDK 21 en esta máquina: el servidor se ejecutará en Docker (maven + temurin 21).'
    Info 'Para ejecutarlo desde IntelliJ necesitarás un JDK 21: winget install -e --id EclipseAdoptium.Temurin.21.JDK'
    return [pscustomobject]@{ Mode = 'docker'; Jdk = $null }
}

function Build-Server($Jdk) {
    $mvn = Find-Maven
    if (-not $mvn) {
        throw 'No se encuentra Maven (ni server\mvnw.cmd con .mvn\wrapper, ni mvn en el PATH, ni el incluido en IntelliJ).'
    }
    Say "Compilando el servidor con JDK $($Jdk.Major) ($($Jdk.Home))"
    Info "Maven: $($mvn.Source)"
    $env:JAVA_HOME = $Jdk.Home
    $env:PATH = "$(Join-Path $Jdk.Home 'bin');$env:PATH"
    Push-Location $ServerDir
    try {
        $code = Invoke-Native $mvn.Exe @('-B', '-ntp', '-q', '-DskipTests', 'package')
    } finally { Pop-Location }
    if ($code -ne 0) { throw 'La compilación del servidor ha fallado (salida arriba).' }

    $jar = Get-ChildItem -Path (Join-Path $ServerDir 'target') -Filter '*.jar' -ErrorAction SilentlyContinue |
           Where-Object { $_.Name -notmatch '(-plain|-sources|-javadoc)\.jar$' } |
           Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $jar) { throw 'Maven ha terminado pero no hay ningún .jar en server\target.' }
    Ok "Compilado: $($jar.Name)"
    return $jar.FullName
}

function Show-ServerLogTail([int]$Lines = 40) {
    if (Test-Path $ServerLog) {
        Write-Host "------ últimas $Lines líneas de $ServerLog ------" -ForegroundColor DarkGray
        Get-Content $ServerLog -Tail $Lines | ForEach-Object { Write-Host $_ }
        Write-Host '------------------------------------------------------------' -ForegroundColor DarkGray
    }
}

function Wait-ServerReady([scriptblock]$IsAlive) {
    Info "Esperando a que responda $HealthUrl (máx. $ServerTimeout s)..."
    $deadline = (Get-Date).AddSeconds($ServerTimeout)
    while ((Get-Date) -lt $deadline) {
        if (-not (& $IsAlive)) { return $false }
        if (Test-Http $HealthUrl) { Write-Host ''; return $true }
        Write-Host '.' -NoNewline
        Start-Sleep -Seconds 2
    }
    Write-Host ''
    return $false
}

function Start-ServerLocal($Jdk) {
    $jar = Build-Server $Jdk
    Ensure-StateDir
    # Se ejecuta una copia: Windows bloquea el .jar en uso y eso rompería el siguiente
    # 'mvn package' (o el build de IntelliJ) mientras el servidor sigue arrancado.
    $runJar = Join-Path $StateDir 'server.jar'
    Copy-Item $jar $runJar -Force

    $env:DB_URL      = $DbUrl
    $env:DB_USER     = $DbUser
    $env:DB_PASSWORD = $DbPassword
    $java = Join-Path $Jdk.Home 'bin\java.exe'
    if (Test-Path $ServerLog) { Remove-Item $ServerLog -Force -ErrorAction SilentlyContinue }

    # cmd.exe redirige stdout y stderr al mismo log; ventana oculta e independiente de esta
    # consola: el servidor sigue vivo al cerrar el terminal y se para con 'make server-stop'.
    $cmdArgs = "/d /s /c `"`"$java`" -jar `"$runJar`" > `"$ServerLog`" 2>&1`""
    $launcher = Start-Process -FilePath $env:ComSpec -ArgumentList $cmdArgs -WorkingDirectory $ServerDir `
                              -WindowStyle Hidden -PassThru

    $javaPid = 0
    for ($i = 0; $i -lt 20 -and $javaPid -eq 0; $i++) {
        Start-Sleep -Milliseconds 500
        $child = Get-CimInstance Win32_Process -Filter "ParentProcessId=$($launcher.Id)" -ErrorAction SilentlyContinue |
                 Where-Object { $_.Name -eq 'java.exe' } | Select-Object -First 1
        if ($child) { $javaPid = [int]$child.ProcessId }
    }
    [pscustomobject]@{
        mode        = 'local'
        launcherPid = $launcher.Id
        javaPid     = $javaPid
        port        = $ServerPort
        jdk         = $Jdk.Home
        log         = $ServerLog
        started     = (Get-Date).ToString('s')
    } | ConvertTo-Json | Set-Content -Path $ServerState -Encoding UTF8

    Ok "Servidor lanzado en segundo plano (PID $javaPid). Log: $ServerLog"
    # Sin GetNewClosure: el bloque se evalúa dentro de esta función y ve $launcher y $javaPid
    $alive = { (Test-ProcessAlive $launcher.Id) -or (Test-ProcessAlive $javaPid) }
    if (-not (Wait-ServerReady $alive)) {
        Show-ServerLogTail 60
        if (-not (& $alive)) {
            Remove-Item $ServerState -Force -ErrorAction SilentlyContinue
            throw 'El servidor se ha cerrado durante el arranque (log arriba).'
        }
        throw "El servidor no responde tras $ServerTimeout s. Sigue arrancado: revisa 'make server-logs' o páralo con 'make server-stop'."
    }
    Ok "Servidor listo: $ServerUrl"
}

function Start-ServerDocker {
    Say 'Arrancando el servidor en Docker (la primera vez descarga Maven y las dependencias)'
    $code = Invoke-Compose @('up', '-d', 'server') @('server')
    if ($code -ne 0) { throw 'No se ha podido crear el contenedor del servidor.' }
    $alive = { (Get-ContainerState $ServerContainer) -eq 'running' }
    if (-not (Wait-ServerReady $alive)) {
        Invoke-Native 'docker' @('logs', '--tail', '60', $ServerContainer) | Out-Null
        throw "El servidor en Docker no responde (log arriba). Más detalle: make server-logs"
    }
    Ok "Servidor listo: $ServerUrl (Docker)"
    Sync-FrontProxy
}

function Sync-FrontProxy {
    # Si live-server corre en Docker, lo recrea cuando cambia dónde está el servidor
    # (compose solo lo recrea si API_TARGET ha cambiado)
    if ((Get-ContainerState $FrontContainer) -eq 'running') {
        Invoke-Compose @('up', '-d', 'front') @('front') | Out-Null
    }
}

function Start-Server {
    Say "Servidor Spring Boot ($ServerUrl)"
    $owner = Get-ServerOwner
    switch ($owner.Kind) {
        'make'    { Ok "Ya está arrancado: $($owner.Text). Para recompilar con tus cambios: make server-restart"; return }
        'docker'  { Ok "Ya está arrancado: $($owner.Text)."; return }
        'project' {
            Ok "Ya hay un $($owner.Text): se reutiliza."
            Info 'Si quieres que lo gestione make: make server-stop && make server'
            return
        }
        'foreign' {
            $cmd = $(if ($owner.Proc) { Format-Cmd $owner.Proc.CommandLine } else { '' })
            throw ("El puerto $ServerPort lo ocupa $($owner.Text), que no es este servidor.`n         $cmd`n" +
                   "         Libéralo con 'make server-stop FORCE=1' o usa otro puerto: make up SERVER_PORT=8081")
        }
    }

    if ((Get-ContainerState $DbContainer) -ne 'running') { Start-Db }

    $m = Resolve-ServerMode
    if ($m.Mode -eq 'local') { Start-ServerLocal $m.Jdk } else { Start-ServerDocker }
}

function Stop-Server([switch]$Quiet) {
    if (-not $Quiet) { Say "Parando el servidor (puerto $ServerPort)" }
    $did = $false

    $state = Read-ServerState
    if ($state) {
        foreach ($id in @([int]$state.launcherPid, [int]$state.javaPid)) {
            if (Test-ProcessAlive $id) { Stop-ProcessTree $id; $did = $true }
        }
        Remove-Item $ServerState -Force -ErrorAction SilentlyContinue
        if ($did) { Ok 'Parado el servidor lanzado con make.' }
    }

    if ((Get-ContainerState $ServerContainer) -ne '') {
        Invoke-Compose @('rm', '-s', '-f', 'server') @('server') | Out-Null
        Ok 'Parado el contenedor del servidor.'
        $did = $true
        Sync-FrontProxy
    }

    # Lo que quede escuchando: otra instancia del proyecto (p. ej. lanzada desde IntelliJ)
    # se para siempre, porque el objetivo es liberar el puerto; un proceso ajeno, solo con FORCE=1.
    $owner = Get-ServerOwner
    if ($owner.Kind -eq 'project' -or $owner.Kind -eq 'make') {
        Stop-ProcessTree $owner.Proc.Id
        Ok "Parado el $($owner.Text)."
        $did = $true
    } elseif ($owner.Kind -eq 'foreign') {
        if ($Force -and $owner.Proc -and -not (Test-DockerProcessName $owner.Proc.Name)) {
            Stop-ProcessTree $owner.Proc.Id
            Ok "Parado (FORCE=1) $($owner.Text)."
            $did = $true
        } else {
            Warn "El puerto $ServerPort lo ocupa $($owner.Text), ajeno a este proyecto: no se toca."
            if ($owner.Proc) { Info (Format-Cmd $owner.Proc.CommandLine) }
            Info 'Para pararlo igualmente: make server-stop FORCE=1'
        }
    }

    for ($i = 0; $i -lt 10 -and (Get-PortPids $ServerPort).Count -gt 0 -and $did; $i++) { Start-Sleep -Milliseconds 500 }
    if (-not $Quiet) {
        if ((Get-PortPids $ServerPort).Count -eq 0) { Ok "Puerto $ServerPort libre: ya puedes lanzar el servidor desde IntelliJ." }
        elseif (-not $did) { Warn 'No había ningún servidor de este proyecto que parar.' }
    }
}

function Show-ServerStatus {
    $owner = Get-ServerOwner
    if ($owner.Kind -eq 'none') { Write-Host "  Servidor : parado (puerto $ServerPort libre)"; return }
    $color = $(if ($owner.Kind -eq 'foreign') { 'Yellow' } else { 'Green' })
    $up = Test-Http $HealthUrl
    Write-Host "  Servidor : $($owner.Text) - $(if ($up) { "responde en $ServerUrl" } else { 'no responde (¿arrancando?)' })" -ForegroundColor $color
    if ($owner.Proc) {
        Info "Proceso  : $($owner.Proc.Name), PID $($owner.Proc.Id), padre $($owner.Proc.ParentName) ($($owner.Proc.ParentId)), desde $($owner.Proc.Started)"
        Info "Comando  : $(Format-Cmd $owner.Proc.CommandLine 110)"
    }
    if ($owner.Kind -eq 'make') { Info "Log      : $ServerLog   (make server-logs)" }
    if ($owner.Kind -eq 'docker') { Info 'Log      : make server-logs' }
    if ($owner.Kind -eq 'project') { Info 'Log      : consola de IntelliJ y server\logs\app.log. Para pararlo: make server-stop' }
}

function Show-ServerLogs {
    $owner = Get-ServerOwner
    if ($owner.Kind -eq 'docker') { Invoke-Interactive 'docker' @('logs', '-f', '--tail', '100', $ServerContainer); return }
    $file = $ServerLog
    if ($owner.Kind -ne 'make' -or -not (Test-Path $file)) {
        $file = Join-Path $ServerDir 'logs\app.log'   # fichero de log4j2, lo escribe cualquier instancia
        Warn "El servidor no lo ha lanzado make: se muestra $file"
    }
    if (-not (Test-Path $file)) { throw "No hay log en $file. ¿Está arrancado el servidor? (make status)" }
    Info "Siguiendo $file (Ctrl+C para salir; el servidor sigue arrancado)"
    Get-Content $file -Tail 100 -Wait
}

# ----------------------------------------------------------------------------------------------
# Frontend
# ----------------------------------------------------------------------------------------------
function Set-JsonSettings([string]$File, [hashtable]$Values) {
    # Fusiona claves en un settings.json de VS Code sin perder las que ya tuviera.
    $dir = Split-Path $File -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
    $obj = New-Object psobject
    if (Test-Path $File) {
        $raw = Get-Content $File -Raw
        if (-not [string]::IsNullOrWhiteSpace($raw)) {
            try { $obj = $raw | ConvertFrom-Json }
            catch {
                # Comentarios o comas finales (JSONC): PowerShell 5.1 no los entiende
                $backup = "$File.bak-$(Get-Date -Format yyyyMMddHHmmss)"
                Copy-Item $File $backup
                Warn "$File no es JSON estricto: copia guardada en $backup y se regenera."
                $obj = New-Object psobject
            }
        }
    }
    foreach ($k in $Values.Keys) {
        $obj | Add-Member -NotePropertyName $k -NotePropertyValue $Values[$k] -Force
    }
    $json = $obj | ConvertTo-Json -Depth 20
    [IO.File]::WriteAllText($File, $json, (New-Object Text.UTF8Encoding($false)))
}

function Write-LiveServerSettings {
    $proxy = [ordered]@{ enable = $true; baseUri = '/api'; proxyUri = "http://127.0.0.1:$ServerPort/api" }
    $common = @{
        'liveServer.settings.port'        = $FrontPort
        'liveServer.settings.host'        = '127.0.0.1'
        'liveServer.settings.proxy'       = $proxy
        'liveServer.settings.NoBrowser'   = (-not $OpenBrowser)
        'liveServer.settings.ignoreFiles' = @('.vscode/**', '.dev/**', 'server/**', 'fractal_model_lab/**', 'tools/**', 'data/**')
    }
    # Carpeta raíz del repositorio abierta en VS Code -> sirve /frontend
    $rootValues = $common.Clone(); $rootValues['liveServer.settings.root'] = '/frontend'
    Set-JsonSettings (Join-Path $Root '.vscode\settings.json') $rootValues
    # Por si se abre directamente la carpeta frontend
    $frontValues = $common.Clone(); $frontValues['liveServer.settings.root'] = '/'
    Set-JsonSettings (Join-Path $FrontDir '.vscode\settings.json') $frontValues
    Ok "Go Live configurado: puerto $FrontPort, /api -> $ServerUrl/api (.vscode\settings.json)"
}

function Get-FrontOwner {
    if ((Get-ContainerState $FrontContainer) -eq 'running') {
        return [pscustomobject]@{ Kind = 'docker'; Proc = $null; Text = "live-server en Docker ($FrontContainer)" }
    }
    $pids = Get-PortPids $FrontPort
    if ($pids.Count -eq 0) { return [pscustomobject]@{ Kind = 'none'; Proc = $null; Text = 'libre' } }
    $p = Get-ProcInfo $pids[0]
    if ($p -and $p.Name -match '^Code(\s-\sInsiders)?\.exe$') {
        return [pscustomobject]@{ Kind = 'vscode'; Proc = $p; Text = "Go Live de VS Code (PID $($p.Id))" }
    }
    $name = $(if ($p) { "$($p.Name) (PID $($p.Id))" } else { "PID $($pids[0])" })
    return [pscustomobject]@{ Kind = 'foreign'; Proc = $p; Text = $name }
}

function Resolve-FrontMode {
    if ($FrontMode -eq 'docker') { return 'docker' }
    $code = Find-VSCode
    if (-not $code) {
        if ($FrontMode -eq 'vscode') { throw 'FRONT_MODE=vscode pero no se encuentra VS Code. Instálalo: winget install -e --id Microsoft.VisualStudioCode' }
        Warn 'VS Code no está instalado: el frontend se servirá con live-server en Docker.'
        return 'docker'
    }
    if (-not (Test-LiveServerExtension $code)) {
        Say "Instalando la extensión Live Server (Go Live) en VS Code"
        $r = Invoke-Native $code @('--install-extension', $LiveServerExt, '--force')
        if ($r -ne 0 -or -not (Test-LiveServerExtension $code)) {
            if ($FrontMode -eq 'vscode') { throw "No se ha podido instalar $LiveServerExt." }
            Warn "No se ha podido instalar ${LiveServerExt}: se usará live-server en Docker."
            return 'docker'
        }
        Ok 'Live Server instalado.'
    }
    return 'vscode'
}

function Start-Front {
    Say "Frontend con recarga en caliente ($FrontUrl)"
    $owner = Get-FrontOwner
    if ($owner.Kind -eq 'docker' -or $owner.Kind -eq 'vscode') {
        Ok "Ya está sirviéndose: $($owner.Text) en $FrontUrl"
        if ($owner.Kind -eq 'vscode') { Write-LiveServerSettings }
        return
    }
    if ($owner.Kind -eq 'foreign') {
        throw "El puerto $FrontPort lo ocupa $($owner.Text). Ciérralo o usa otro: make front FRONT_PORT=5501"
    }

    $mode = Resolve-FrontMode
    if ($mode -eq 'vscode') {
        Write-LiveServerSettings
        $code = Find-VSCode
        Invoke-Native $code @($Root) | Out-Null   # abre el repo o enfoca la ventana si ya lo está
        Ok 'VS Code abierto en la raíz del repositorio.'
        Write-Host ''
        Write-Host "  >> Pulsa 'Go Live' en la barra de estado de VS Code (abajo a la derecha)" -ForegroundColor Magenta
        Write-Host "     o Alt+L Alt+O. Live Server no se puede arrancar desde la línea de comandos." -ForegroundColor Magenta
        Write-Host ''
        Info "Esperando a que el puerto $FrontPort esté activo (máx. $FrontWait s, Ctrl+C para no esperar)..."
        if (Wait-Port $FrontPort $FrontWait) { Ok "Frontend servido por Go Live en $FrontUrl" }
        else { Warn "Go Live aún no está activo. Cuando lo pulses tendrás el frontend en $FrontUrl" }
        return
    }

    $code = Invoke-Compose @('up', '-d', 'front') @('front')
    if ($code -ne 0) { throw 'No se ha podido arrancar el contenedor del frontend.' }
    Info 'Esperando a live-server (la primera vez descarga el paquete)...'
    $deadline = (Get-Date).AddSeconds(120)
    while ((Get-Date) -lt $deadline -and -not (Test-Http $FrontUrl)) { Start-Sleep -Seconds 2 }
    if (-not (Test-Http $FrontUrl)) {
        Invoke-Native 'docker' @('logs', '--tail', '40', $FrontContainer) | Out-Null
        throw 'live-server no responde (log arriba).'
    }
    Ok "Frontend servido por live-server en Docker: $FrontUrl (recarga al guardar en frontend\)"
    Open-Url $FrontUrl
}

function Stop-Front {
    Say 'Parando el frontend'
    if ((Get-ContainerState $FrontContainer) -ne '') {
        Invoke-Compose @('rm', '-s', '-f', 'front') @('front') | Out-Null
        Ok 'Parado live-server (Docker).'
    }
    $owner = Get-FrontOwner
    switch ($owner.Kind) {
        'none'    { Ok "Puerto $FrontPort libre." }
        'vscode'  { Warn "Go Live sigue activo: páralo pulsando 'Port : $FrontPort' en la barra de estado de VS Code (no se cierra VS Code desde aquí)." }
        'foreign' { Warn "El puerto $FrontPort lo ocupa $($owner.Text): no se toca." }
    }
}

function Show-FrontStatus {
    $owner = Get-FrontOwner
    switch ($owner.Kind) {
        'none'    { Write-Host "  Frontend : parado (puerto $FrontPort libre)" }
        'foreign' { Write-Host "  Frontend : puerto $FrontPort ocupado por $($owner.Text)" -ForegroundColor Yellow }
        default   { Write-Host "  Frontend : $($owner.Text) en $FrontUrl" -ForegroundColor Green }
    }
}

# ----------------------------------------------------------------------------------------------
# Model lab (TUI en C con ncurses: solo Linux, se compila y ejecuta en un contenedor)
# ----------------------------------------------------------------------------------------------
function Build-Lab {
    Say 'Compilando fractal_model_lab en Docker'
    Ensure-Docker
    $code = Invoke-Native 'docker' @('build', '-f', $LabFile, '-t', $LabImage, $LabDir)
    if ($code -ne 0) { throw 'La compilación del model lab ha fallado.' }
    Ok "Imagen $LabImage lista."
}

# ----------------------------------------------------------------------------------------------
# Diagnóstico y estado
# ----------------------------------------------------------------------------------------------
function Show-Doctor {
    Say 'Comprobando el entorno'
    $problems = 0

    Ok "PowerShell $($PSVersionTable.PSVersion)"
    if (Test-Command 'make') { Ok 'make instalado' }
    else { Warn 'make no está en el PATH: usa dev.cmd <objetivo> o instálalo con: dev install-make' }

    if (Find-DockerCli) {
        if (Test-DockerDaemon) {
            $os = (Get-NativeOutput 'docker' @('info', '--format', '{{.OSType}}')).Text
            $ver = (Get-NativeOutput 'docker' @('version', '--format', '{{.Server.Version}}')).Text
            if ($os -match 'linux') { Ok "Docker $ver (contenedores Linux)" } else { Warn "Docker en modo contenedores ${os}: make up lo cambiará a Linux"; }
            if ((Get-NativeOutput 'docker' @('compose', 'version', '--short')).Code -eq 0) { Ok "docker compose $((Get-NativeOutput 'docker' @('compose','version','--short')).Text)" }
            else { Bad 'Falta docker compose v2: winget upgrade -e --id Docker.DockerDesktop'; $problems++ }
        } elseif (Find-DockerDesktop) { Warn 'Docker Desktop instalado pero parado: make up lo arranca.' }
        else { Bad 'Docker instalado pero el demonio no responde.'; $problems++ }
    } else { Bad 'Docker no instalado: winget install -e --id Docker.DockerDesktop'; $problems++ }

    $jdks = Find-Jdks
    $jdk21 = $jdks | Where-Object { $_.Major -eq 21 } | Select-Object -First 1
    if ($jdk21) { Ok "JDK 21: $($jdk21.Home)" }
    else {
        $others = ($jdks | ForEach-Object { "$($_.Major)" }) -join ', '
        Warn "No hay JDK 21$(if ($others) { " (encontrados: $others)" }): el servidor correrá en Docker."
        Info 'Instalar: winget install -e --id EclipseAdoptium.Temurin.21.JDK  (o descargarlo desde IntelliJ)'
    }
    $mvn = Find-Maven
    if ($mvn) { Ok "Maven: $($mvn.Source)" } else { Warn 'Sin Maven local (solo afecta a SERVER_MODE=local).' }

    $idea = Find-IntelliJHomes
    if ($idea.Count -gt 0) { Ok "IntelliJ: $($idea[0])" } else { Warn 'IntelliJ IDEA no encontrado en las rutas habituales (opcional para make).' }

    $code = Find-VSCode
    if ($code) {
        Ok "VS Code: $code"
        if (Test-LiveServerExtension $code) { Ok 'Extensión Live Server (Go Live) instalada' }
        else { Warn 'Falta la extensión Live Server: make front la instala sola.' }
    } else { Warn 'VS Code no instalado: el frontend se servirá con live-server en Docker.' }

    foreach ($pp in @(@($DbPort, 'MySQL'), @($ServerPort, 'servidor'), @($FrontPort, 'frontend'))) {
        $pids = Get-PortPids $pp[0]
        if ($pids.Count -eq 0) { Ok "Puerto $($pp[0]) ($($pp[1])) libre" }
        else {
            $p = Get-ProcInfo $pids[0]
            Info "Puerto $($pp[0]) ($($pp[1])) en uso por $(if ($p) { "$($p.Name) (PID $($p.Id))" } else { "PID $($pids[0])" })"
        }
    }

    Write-Host ''
    if ($problems -eq 0) { Ok 'Entorno listo: make up' } else { Bad "$problems problema(s) que impiden levantar el entorno." }
}

function Show-Status {
    Say 'Estado del entorno de desarrollo'
    if (-not (Find-DockerCli)) { Write-Host '  Docker   : no instalado' -ForegroundColor Yellow }
    elseif (-not (Test-DockerDaemon)) { Write-Host '  Docker   : parado' -ForegroundColor Yellow }
    else {
        $s = Get-ContainerState $DbContainer
        if ($s -eq '') { Write-Host '  MySQL    : sin crear (make db)' }
        else {
            $h = Get-ContainerHealth $DbContainer
            $color = $(if ($s -eq 'running' -and $h -eq 'healthy') { 'Green' } else { 'Yellow' })
            Write-Host "  MySQL    : $s$(if ($h) { " ($h)" }) en localhost:$DbPort - $DbUrl" -ForegroundColor $color
        }
    }
    Show-ServerStatus
    Show-FrontStatus
}

function Show-Help {
    @"

  Entorno de desarrollo de NISAR SAR (Windows)        make <objetivo> [VAR=valor ...]
                                                     (sin make: dev <objetivo>)
  General
    up               Levanta todo: MySQL (Docker) + servidor (si no está ya) + frontend con recarga
    down             Para frontend, servidor y MySQL (los datos se conservan)
    restart          down + up
    status           Qué está arrancado, con PID, origen (make/IntelliJ/Docker) y URLs
    doctor           Comprueba Docker, JDK 21, Maven, VS Code + Live Server, IntelliJ y puertos
    open             Abre el frontend en el navegador

  Base de datos (MySQL 8 en Docker, root/root, base NisarSar en localhost:3306)
    db               Arranca MySQL y espera a que esté sano
    db-stop          Para MySQL
    db-logs          Sigue el log de MySQL
    db-shell         Consola mysql dentro del contenedor
    db-reset         Borra los datos (pide confirmación; YES=1 para no preguntar)

  Servidor (Spring Boot en $ServerUrl)
    server           Compila y arranca en segundo plano, salvo que ya haya uno escuchando
    server-stop      Para el servidor de este proyecto (también el lanzado desde IntelliJ)
                     y deja libre el puerto. FORCE=1 para también procesos ajenos
    server-restart   Recompila y relanza con tus cambios
    server-status    Detalle del proceso que ocupa el puerto
    server-logs      Sigue el log del servidor
    server-build     Solo compila (mvnw package)

  Frontend (recarga en caliente en $FrontUrl, /api redirigido al servidor)
    front            Go Live de VS Code (configura e instala la extensión) o live-server en Docker
    front-stop       Para live-server (Go Live se para desde la barra de estado de VS Code)
    front-config     Solo escribe la configuración de Go Live en .vscode\settings.json

  Model lab (TUI en C, en Docker)
    lab-build        Compila fractal_model_lab
    lab-test         Ejecuta sus pruebas
    lab-run          Ejecuta la TUI en esta consola

  Limpieza
    clean            Borra .dev\ y server\target
    purge            down + borra contenedores, volúmenes (datos, cachés) e imagen del lab

  Variables: DB_PORT=3306 DB_PASSWORD=root SERVER_PORT=8080 FRONT_PORT=5500
             SERVER_MODE=auto|local|docker FRONT_MODE=auto|vscode|docker
             SERVER_TIMEOUT=180 FRONT_WAIT=120 OPEN=1 YES=0 FORCE=0

  Flujo con IntelliJ: make up  ->  make server-stop  ->  Run en IntelliJ (conecta a la misma BD)

"@ | Write-Host
}

# ----------------------------------------------------------------------------------------------
# Acciones
# ----------------------------------------------------------------------------------------------
function Invoke-Action([string]$Name) {
    switch ($Name) {
        'help'           { Show-Help }
        'doctor'         { Show-Doctor }
        'status'         { Show-Status }
        'up' {
            Ensure-Docker
            Start-Db
            Start-Server
            Start-Front
            Write-Host ''
            Show-Status
            Write-Host ''
            Info 'Para ejecutar el servidor desde IntelliJ con tus cambios: make server-stop y Run.'
        }
        'down'           { Stop-Front; Stop-Server; Stop-Db }
        'restart'        { Invoke-Action 'down'; Invoke-Action 'up' }
        'open'           { $script:OpenBrowser = $true; Start-Process $FrontUrl | Out-Null }

        'db'             { Start-Db }
        'db-start'       { Start-Db }
        'db-stop'        { Stop-Db }
        'db-logs'        { Ensure-Docker; Invoke-Interactive 'docker' @('logs', '-f', '--tail', '100', $DbContainer) }
        'db-shell' {
            Ensure-Docker
            if ((Get-ContainerState $DbContainer) -ne 'running') { Start-Db }
            Invoke-Interactive 'docker' @('exec', '-it', $DbContainer, 'mysql', "-u$DbUser", "-p$DbPassword", $DbName)
        }
        'db-reset'       { Reset-Db }

        'server'         { Start-Server }
        'server-start'   { Start-Server }
        'server-stop'    { Stop-Server }
        'server-restart' { Stop-Server; Start-Server }
        'server-status'  { Show-ServerStatus }
        'server-logs'    { Show-ServerLogs }
        'server-build' {
            $jdk = Find-Jdk21
            if (-not $jdk) { throw 'No hay JDK 21 para compilar localmente: winget install -e --id EclipseAdoptium.Temurin.21.JDK' }
            Build-Server $jdk | Out-Null
        }

        'front'          { Start-Front }
        'front-start'    { Start-Front }
        'front-stop'     { Stop-Front }
        'front-config'   { Write-LiveServerSettings }

        'lab-build'      { Build-Lab }
        'lab-test'       { Build-Lab; if ((Invoke-Native 'docker' @('run', '--rm', $LabImage, 'make', 'test')) -ne 0) { throw 'Las pruebas del model lab han fallado.' } }
        'lab-run'        { Build-Lab; Invoke-Interactive 'docker' @('run', '--rm', '-it', '-e', 'TERM=xterm-256color', $LabImage) }

        'clean' {
            Stop-Server -Quiet
            foreach ($d in @($StateDir, (Join-Path $ServerDir 'target'))) {
                if (Test-Path $d) { Remove-Item $d -Recurse -Force; Ok "Borrado $d" }
            }
        }
        'purge' {
            if (-not (Confirm-Action 'Se borrarán contenedores, datos de MySQL y cachés de Maven/npm del entorno. ¿Seguro?')) { Warn 'Cancelado.'; return }
            Stop-Front; Stop-Server
            Ensure-Docker
            Invoke-Native 'docker' @('compose', '-f', $ComposeFile, '-p', $ComposeProject, '--profile', 'server', '--profile', 'front', 'down', '-v', '--remove-orphans') | Out-Null
            Invoke-Native 'docker' @('image', 'rm', '-f', $LabImage) | Out-Null
            if (Test-Path $StateDir) { Remove-Item $StateDir -Recurse -Force }
            Ok 'Entorno de desarrollo eliminado.'
        }

        'install-make' {
            if (Test-Command 'make') { Ok 'make ya está instalado.'; return }
            if (-not (Test-Command 'winget')) { throw 'No hay winget. Instala make con Chocolatey (choco install make) o Scoop (scoop install make).' }
            Invoke-Native 'winget' @('install', '-e', '--id', 'ezwinports.make', '--accept-source-agreements', '--accept-package-agreements') | Out-Null
            Ok 'make instalado. Abre una consola nueva para que esté en el PATH.'
        }

        default { Show-Help; throw "Objetivo desconocido: '$Name'" }
    }
}

try {
    if ($env:OS -ne 'Windows_NT') { throw 'Este script es para Windows.' }
    Invoke-Action $Action.ToLowerInvariant()
    exit 0
} catch {
    Write-Host ''
    Bad $_.Exception.Message
    exit 1
}
