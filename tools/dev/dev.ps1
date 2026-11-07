#Requires -Version 5.1
<#
.SYNOPSIS
  NISAR SAR local development environment on Windows: database (Docker), Spring Boot
  server and hot-reloading frontend (VS Code Go Live or live-server in Docker).

.DESCRIPTION
  Called by the root Makefile (make <target>) or by dev.cmd when the machine has no make.
  Works with Windows PowerShell 5.1 (bundled with Windows) and PowerShell 7.

  Configuration through environment variables (or make <target> VAR=value):
    DB_PORT         MySQL port on localhost                           (3306)
    DB_PASSWORD     MySQL root password                               (root)
    SERVER_PORT     Spring Boot server port                           (8080)
    FRONT_PORT      Frontend port                                     (5500)
    SERVER_MODE     auto | local (this machine's JDK 21) | docker     (auto)
    FRONT_MODE      auto | vscode (Go Live) | docker (live-server)    (auto)
    SERVER_TIMEOUT  Maximum seconds to wait for the server to start   (180)
    FRONT_WAIT      Seconds to wait for Go Live to be clicked         (120)
    OPEN            1 opens the browser, 0 does not                   (1)
    YES             1 skips confirmation of destructive actions       (0)
    FORCE           1 allows stopping unrelated processes that hold the server port (0)
#>
param(
    [Parameter(Position = 0)][string]$Action = 'help'
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # the progress bar makes Invoke-WebRequest very slow on 5.1
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch { }

# ----------------------------------------------------------------------------------------------
# Paths and configuration
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
        throw "The variable $Name='$v' is not a valid number."
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

if (@('auto', 'local', 'docker') -notcontains $ServerMode) { throw "SERVER_MODE must be auto, local or docker (it is '$ServerMode')." }
if (@('auto', 'vscode', 'docker') -notcontains $FrontMode) { throw "FRONT_MODE must be auto, vscode or docker (it is '$FrontMode')." }

$DbUrl     = "jdbc:mysql://localhost:$DbPort/$DbName"
$ServerUrl = "http://127.0.0.1:$ServerPort"
$HealthUrl = "$ServerUrl/api/sites"
$FrontUrl  = "http://127.0.0.1:$FrontPort/"

# Read by docker compose (interpolation in compose.dev.yml) and by the server (Spring reads
# SERVER_PORT, DB_URL, DB_USER and DB_PASSWORD in application.properties).
$env:DB_PORT     = "$DbPort"
$env:DB_PASSWORD = $DbPassword
$env:SERVER_PORT = "$ServerPort"
$env:FRONT_PORT  = "$FrontPort"

# ----------------------------------------------------------------------------------------------
# Output
# ----------------------------------------------------------------------------------------------
function Say([string]$m)  { Write-Host "==> $m" -ForegroundColor Cyan }
function Ok([string]$m)   { Write-Host "  [ok] $m" -ForegroundColor Green }
function Warn([string]$m) { Write-Host "  [!]  $m" -ForegroundColor Yellow }
function Bad([string]$m)  { Write-Host "  [x]  $m" -ForegroundColor Red }
function Info([string]$m) { Write-Host "       $m" }

function Confirm-Action([string]$Question) {
    if ($AssumeYes) { return $true }
    $a = Read-Host "$Question [y/N]"
    return ($a -match '^(y|yes)$')
}

# ----------------------------------------------------------------------------------------------
# Running external programs
# On PowerShell 5.1 with ErrorActionPreference=Stop, any line a program writes to stderr
# becomes an exception: it is lowered to Continue while they run.
# ----------------------------------------------------------------------------------------------
function Invoke-Native([string]$Exe, [string[]]$Arguments) {
    # Shows the output as it arrives and returns the exit code.
    $old = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $Exe @Arguments 2>&1 | ForEach-Object { Write-Host "$_" }
        return $LASTEXITCODE
    } finally { $ErrorActionPreference = $old }
}

function Get-NativeOutput([string]$Exe, [string[]]$Arguments) {
    # Captures the output (stdout + stderr) without showing it.
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
    # For commands that need a TTY or follow output (-it, -f): no redirection.
    $old = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & $Exe @Arguments } finally { $ErrorActionPreference = $old }
}

function Test-Command([string]$Name) { return [bool](Get-Command $Name -ErrorAction SilentlyContinue) }

function Ensure-StateDir {
    if (-not (Test-Path $StateDir)) { New-Item -ItemType Directory -Path $StateDir | Out-Null }
}

# ----------------------------------------------------------------------------------------------
# Ports and processes
# ----------------------------------------------------------------------------------------------
function Get-PortPids([int]$Port) {
    # PIDs listening on the TCP port (IPv4 or IPv6).
    $ids = @()
    if (Test-Command 'Get-NetTCPConnection') {
        try {
            $ids = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop |
                     Select-Object -ExpandProperty OwningProcess)
        } catch { $ids = @() }   # no connections: the cmdlet throws ObjectNotFound
    } else {
        # netstat: the state is localized (LISTENING/ESCUCHANDO...), so listening sockets are
        # recognized by the remote address having port 0
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
    if ([string]::IsNullOrWhiteSpace($CommandLine)) { return '(command line not available: process of another user or elevated)' }
    $c = $CommandLine -replace '\s+', ' '
    if ($c.Length -gt $Max) { $c = $c.Substring(0, $Max) + '...' }
    return $c
}

function Test-DockerProcessName([string]$Name) {
    return ($Name -match '^(com\.docker\.|docker|wslrelay|vpnkit|dockerd)' )
}

function Test-Http([string]$Url) {
    # Any HTTP response (including 4xx/5xx) means the server is listening.
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
        $env:PATH = "$bin;$env:PATH"   # installed but not on this console's PATH
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

function Get-DockerEngine {
    # Docker engine state: Up, Os (linux | windows), Version and Text (output, including the
    # error when it does not respond). 'docker info --format' is not used: with the daemon
    # stopped it exits 0 and prints the error, which also contains 'dockerDesktopLinuxEngine'
    # and so matched 'linux'. 'docker version' does fail, and its output is validated anyway.
    $r = Get-NativeOutput 'docker' @('version', '--format', '{{.Server.Os}}|{{.Server.Version}}')
    $up = ($r.Code -eq 0 -and $r.Text -match '^(linux|windows)\|(\S+)$')
    return [pscustomobject]@{
        Up      = $up
        Os      = $(if ($up) { $Matches[1] } else { '' })
        Version = $(if ($up) { $Matches[2] } else { '' })
        Text    = $r.Text
    }
}

$script:DaemonUp = $false
function Test-DockerDaemon {
    if ($script:DaemonUp) { return $true }   # only 'yes' is cached
    if (-not (Find-DockerCli)) { return $false }
    $script:DaemonUp = (Get-DockerEngine).Up
    return $script:DaemonUp
}

function Ensure-Docker {
    if ($script:DockerReady) { return }

    if (-not (Find-DockerCli)) {
        throw ("Docker is not installed. Install Docker Desktop and run the command again:`n" +
               "         winget install -e --id Docker.DockerDesktop   (requires a restart; uses the WSL 2 backend)")
    }

    $info = Get-DockerEngine
    if (-not $info.Up) {
        $desktop = Find-DockerDesktop
        if (-not $desktop) {
            throw "The Docker daemon is not responding and Docker Desktop cannot be found to start it.`n$($info.Text)"
        }
        Say 'Docker Desktop is not running: starting it (this can take 2-3 minutes)...'
        Start-Process -FilePath $desktop | Out-Null
        $deadline = (Get-Date).AddSeconds(240)
        do {
            Start-Sleep -Seconds 3
            Write-Host '.' -NoNewline
            $info = Get-DockerEngine
        } while (-not $info.Up -and (Get-Date) -lt $deadline)
        Write-Host ''
        if (-not $info.Up) {
            throw "Docker Desktop has not finished starting. Open it, wait until it says 'Engine running' and retry.`n$($info.Text)"
        }
    }

    if ($info.Os -eq 'windows') {
        $cli = Join-Path $env:ProgramFiles 'Docker\Docker\DockerCli.exe'
        if (-not (Test-Path $cli)) {
            throw 'Docker is in Windows containers mode. Switch it: Docker icon > Switch to Linux containers.'
        }
        Say 'Docker is in Windows containers mode: switching to Linux containers...'
        Invoke-Native $cli @('-SwitchLinuxEngine') | Out-Null
        Start-Sleep -Seconds 10
        $info = Get-DockerEngine
        if ($info.Os -ne 'linux') { throw 'Could not switch Docker to Linux containers. Do it from the Docker icon.' }
    }

    if ((Get-NativeOutput 'docker' @('compose', 'version')).Code -ne 0) {
        throw "'docker compose' (v2) is missing. Update Docker Desktop: winget upgrade -e --id Docker.DockerDesktop"
    }
    $script:DockerReady = $true
}

function Invoke-Compose([string[]]$Arguments, [string[]]$Profiles = @()) {
    Ensure-Docker
    # Target of the /api proxy of live-server in Docker: through the compose network if the
    # server is also in Docker; otherwise the host (IntelliJ or make with a local JDK)
    if ((Get-ContainerState $ServerContainer) -eq 'running') { $env:API_TARGET = 'http://server:8080/api' }
    else { $env:API_TARGET = "http://host.docker.internal:$ServerPort/api" }
    $a = @('compose', '-f', $ComposeFile, '-p', $ComposeProject)
    foreach ($p in $Profiles) { $a += @('--profile', $p) }
    return (Invoke-Native 'docker' ($a + $Arguments))
}

function Get-ContainerState([string]$Name) {
    # running | exited | created | ... ; '' if it does not exist or Docker is not available.
    # Never starts Docker Desktop: it is also used by status.
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
    # Every JDK (with javac) found on the machine, newest first.
    $homes = New-Object System.Collections.Generic.List[string]
    if ($env:JAVA_HOME) { $homes.Add($env:JAVA_HOME.TrimEnd('\')) }
    $java = Get-Command java -ErrorAction SilentlyContinue
    if ($java) {
        $o = Get-NativeOutput $java.Source @('-XshowSettings:properties', '-version')
        $m = [regex]::Match($o.Text, 'java\.home = (.+)')
        if ($m.Success) { $homes.Add($m.Groups[1].Value.Trim()) }
    }
    $patterns = @(
        (Join-Path $HOME '.jdks\*'),                         # JDKs downloaded from IntelliJ
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
    # The project uses Lombok 1.18.30, which does not compile on JDK 22 or later: a 21 is needed.
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
        return [pscustomobject]@{ Exe = $wrapper; Source = "the project's Maven Wrapper (server\mvnw.cmd)" }
    }
    $mvn = Get-Command mvn -ErrorAction SilentlyContinue
    if ($mvn) { return [pscustomobject]@{ Exe = $mvn.Source; Source = "mvn on PATH ($($mvn.Source))" } }
    foreach ($idea in Find-IntelliJHomes) {
        $bundled = Join-Path $idea 'plugins\maven\lib\maven3\bin\mvn.cmd'
        if (Test-Path $bundled) { return [pscustomobject]@{ Exe = $bundled; Source = "Maven bundled with IntelliJ ($bundled)" } }
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
# Database
# ----------------------------------------------------------------------------------------------
function Start-Db {
    Say "MySQL database ($DbContainer on localhost:$DbPort)"
    Ensure-Docker

    $state = Get-ContainerState $DbContainer
    if ($state -ne 'running') {
        # Guard: another MySQL (Windows service, XAMPP...) already holds the port
        $pids = Get-PortPids $DbPort
        if ($pids.Count -gt 0) {
            $p = Get-ProcInfo $pids[0]
            $who = $(if ($p) { "$($p.Name) (PID $($p.Id))" } else { "PID $($pids[0])" })
            if (-not ($p -and (Test-DockerProcessName $p.Name))) {
                throw ("Port $DbPort is already used by $who, probably a MySQL installed on Windows.`n" +
                       "         Options: stop it (e.g. 'net stop MySQL80' as administrator) or use another port:`n" +
                       "         make up DB_PORT=3307   (and in IntelliJ add the variable DB_URL=jdbc:mysql://localhost:3307/$DbName)")
            }
        }
    }

    $code = Invoke-Compose @('up', '-d', '--wait', 'mysql')
    if ($code -ne 0) {
        Invoke-Native 'docker' @('logs', '--tail', '30', $DbContainer) | Out-Null
        throw 'MySQL did not start (output above).'
    }
    Ok "MySQL ready: $DbUrl  (user $DbUser / $DbPassword)"
}

function Stop-Db {
    Say 'Stopping MySQL (data is kept)'
    if (-not (Test-DockerDaemon)) { Ok 'Docker is not running: nothing to stop.'; return }
    if ((Get-ContainerState $DbContainer) -eq '') { Ok 'The MySQL container does not exist.'; return }
    Invoke-Compose @('stop', 'mysql') | Out-Null
    Ok 'MySQL stopped.'
}

function Reset-Db {
    if (-not (Confirm-Action "ALL data in the development database will be deleted. Are you sure?")) { Warn 'Cancelled.'; return }
    Stop-Server -Quiet
    Ensure-Docker
    Invoke-Compose @('rm', '-s', '-f', 'mysql') | Out-Null
    Invoke-Native 'docker' @('volume', 'rm', '-f', "${ComposeProject}_mysql_data") | Out-Null
    Ok 'Data volume deleted.'
    Start-Db
    Info 'Flyway migrations are applied when the server starts: make server'
}

# ----------------------------------------------------------------------------------------------
# Server
# ----------------------------------------------------------------------------------------------
function Read-ServerState {
    if (-not (Test-Path $ServerState)) { return $null }
    try { return (Get-Content $ServerState -Raw | ConvertFrom-Json) } catch { return $null }
}

function Get-ServerOwner {
    # Who holds the server port:
    #   make     -> launched by this script (local process)
    #   docker   -> nisarsar-dev-server container
    #   project  -> another instance of this project (IntelliJ, mvn spring-boot:run, java -jar...)
    #   foreign  -> any other program
    #   none     -> free
    if ((Get-ContainerState $ServerContainer) -eq 'running') {
        return [pscustomobject]@{ Kind = 'docker'; Proc = $null; Text = "Docker container $ServerContainer" }
    }
    $pids = Get-PortPids $ServerPort
    if ($pids.Count -eq 0) { return [pscustomobject]@{ Kind = 'none'; Proc = $null; Text = 'free' } }

    $state = Read-ServerState
    $p = Get-ProcInfo $pids[0]
    if (-not $p) { return [pscustomobject]@{ Kind = 'foreign'; Proc = $null; Text = "PID $($pids[0])" } }

    if ($state -and ($p.Id -eq [int]$state.javaPid -or $p.ParentId -eq [int]$state.launcherPid)) {
        return [pscustomobject]@{ Kind = 'make'; Proc = $p; Text = "launched by make (PID $($p.Id))" }
    }
    if (Test-DockerProcessName $p.Name) {
        return [pscustomobject]@{ Kind = 'foreign'; Proc = $p; Text = "a Docker container outside this environment ($($p.Name), PID $($p.Id))" }
    }
    $isJava = $p.Name -match '^javaw?\.exe$'
    $fromIdea = $p.ParentName -match '^idea(64)?\.exe$'
    $isProject = ($p.CommandLine -match '(?i)nisarsar|NisarSARApplication') -or
                 ($p.CommandLine.IndexOf((Join-Path $StateDir 'server.jar'), [StringComparison]::OrdinalIgnoreCase) -ge 0)
    if ($isJava -and ($fromIdea -or $isProject)) {
        $origin = $(if ($fromIdea) { 'IntelliJ' } else { "$($p.ParentName)" })
        return [pscustomobject]@{ Kind = 'project'; Proc = $p; Text = "server of this project launched from $origin (PID $($p.Id))" }
    }
    return [pscustomobject]@{ Kind = 'foreign'; Proc = $p; Text = "$($p.Name) (PID $($p.Id))" }
}

function Resolve-ServerMode {
    if ($ServerMode -eq 'docker') { return [pscustomobject]@{ Mode = 'docker'; Jdk = $null } }
    $jdk = Find-Jdk21
    if ($jdk) { return [pscustomobject]@{ Mode = 'local'; Jdk = $jdk } }
    if ($ServerMode -eq 'local') {
        throw ("SERVER_MODE=local but no JDK 21 is installed (the project uses Lombok 1.18.30, which does not compile on 22+).`n" +
               "         Install it with: winget install -e --id EclipseAdoptium.Temurin.21.JDK`n" +
               "         or from IntelliJ: File > Project Structure > SDKs > + > Download JDK > version 21.")
    }
    Warn 'No JDK 21 on this machine: the server will run in Docker (maven + temurin 21).'
    Info 'To run it from IntelliJ you will need a JDK 21: winget install -e --id EclipseAdoptium.Temurin.21.JDK'
    return [pscustomobject]@{ Mode = 'docker'; Jdk = $null }
}

function Build-Server($Jdk) {
    $mvn = Find-Maven
    if (-not $mvn) {
        throw 'Maven not found (no server\mvnw.cmd with .mvn\wrapper, no mvn on PATH, no Maven bundled with IntelliJ).'
    }
    Say "Building the server with JDK $($Jdk.Major) ($($Jdk.Home))"
    Info "Maven: $($mvn.Source)"
    $env:JAVA_HOME = $Jdk.Home
    $env:PATH = "$(Join-Path $Jdk.Home 'bin');$env:PATH"
    Push-Location $ServerDir
    try {
        $code = Invoke-Native $mvn.Exe @('-B', '-ntp', '-q', '-DskipTests', 'package')
    } finally { Pop-Location }
    if ($code -ne 0) { throw 'The server build failed (output above).' }

    $jar = Get-ChildItem -Path (Join-Path $ServerDir 'target') -Filter '*.jar' -ErrorAction SilentlyContinue |
           Where-Object { $_.Name -notmatch '(-plain|-sources|-javadoc)\.jar$' } |
           Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $jar) { throw 'Maven finished but there is no .jar in server\target.' }
    Ok "Built: $($jar.Name)"
    return $jar.FullName
}

function Show-ServerLogTail([int]$Lines = 40) {
    if (Test-Path $ServerLog) {
        Write-Host "------ last $Lines lines of $ServerLog ------" -ForegroundColor DarkGray
        Get-Content $ServerLog -Tail $Lines | ForEach-Object { Write-Host $_ }
        Write-Host '------------------------------------------------------------' -ForegroundColor DarkGray
    }
}

function Wait-ServerReady([scriptblock]$IsAlive) {
    Info "Waiting for $HealthUrl to respond (max. $ServerTimeout s)..."
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
    # A copy is run: Windows locks the .jar in use, which would break the next
    # 'mvn package' (or the IntelliJ build) while the server is still running.
    $runJar = Join-Path $StateDir 'server.jar'
    Copy-Item $jar $runJar -Force

    $env:DB_URL      = $DbUrl
    $env:DB_USER     = $DbUser
    $env:DB_PASSWORD = $DbPassword
    $java = Join-Path $Jdk.Home 'bin\java.exe'
    if (Test-Path $ServerLog) { Remove-Item $ServerLog -Force -ErrorAction SilentlyContinue }

    # cmd.exe redirects stdout and stderr to the same log; hidden window, independent of this
    # console: the server keeps running when the terminal is closed and is stopped with 'make server-stop'.
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

    Ok "Server launched in the background (PID $javaPid). Log: $ServerLog"
    # No GetNewClosure: the block is evaluated inside this function and sees $launcher and $javaPid
    $alive = { (Test-ProcessAlive $launcher.Id) -or (Test-ProcessAlive $javaPid) }
    if (-not (Wait-ServerReady $alive)) {
        Show-ServerLogTail 60
        if (-not (& $alive)) {
            Remove-Item $ServerState -Force -ErrorAction SilentlyContinue
            throw 'The server exited during startup (log above).'
        }
        throw "The server is not responding after $ServerTimeout s. It is still running: check 'make server-logs' or stop it with 'make server-stop'."
    }
    Ok "Server ready: $ServerUrl"
}

function Start-ServerDocker {
    Say 'Starting the server in Docker (the first time it downloads Maven and the dependencies)'
    $code = Invoke-Compose @('up', '-d', 'server') @('server')
    if ($code -ne 0) { throw 'Could not create the server container.' }
    $alive = { (Get-ContainerState $ServerContainer) -eq 'running' }
    if (-not (Wait-ServerReady $alive)) {
        Invoke-Native 'docker' @('logs', '--tail', '60', $ServerContainer) | Out-Null
        throw "The server in Docker is not responding (log above). More detail: make server-logs"
    }
    Ok "Server ready: $ServerUrl (Docker)"
    Sync-FrontProxy
}

function Sync-FrontProxy {
    # If live-server runs in Docker, recreate it when the server location changes
    # (compose only recreates it if API_TARGET has changed)
    if ((Get-ContainerState $FrontContainer) -eq 'running') {
        Invoke-Compose @('up', '-d', 'front') @('front') | Out-Null
    }
}

function Start-Server {
    Say "Spring Boot server ($ServerUrl)"
    $owner = Get-ServerOwner
    switch ($owner.Kind) {
        'make'    { Ok "Already running: $($owner.Text). To rebuild with your changes: make server-restart"; return }
        'docker'  { Ok "Already running: $($owner.Text)."; return }
        'project' {
            Ok "There is already a $($owner.Text): reusing it."
            Info 'If you want make to manage it: make server-stop && make server'
            return
        }
        'foreign' {
            $cmd = $(if ($owner.Proc) { Format-Cmd $owner.Proc.CommandLine } else { '' })
            throw ("Port $ServerPort is held by $($owner.Text), which is not this server.`n         $cmd`n" +
                   "         Free it with 'make server-stop FORCE=1' or use another port: make up SERVER_PORT=8081")
        }
    }

    if ((Get-ContainerState $DbContainer) -ne 'running') { Start-Db }

    $m = Resolve-ServerMode
    if ($m.Mode -eq 'local') { Start-ServerLocal $m.Jdk } else { Start-ServerDocker }
}

function Stop-Server([switch]$Quiet) {
    if (-not $Quiet) { Say "Stopping the server (port $ServerPort)" }
    $did = $false

    $state = Read-ServerState
    if ($state) {
        foreach ($id in @([int]$state.launcherPid, [int]$state.javaPid)) {
            if (Test-ProcessAlive $id) { Stop-ProcessTree $id; $did = $true }
        }
        Remove-Item $ServerState -Force -ErrorAction SilentlyContinue
        if ($did) { Ok 'Stopped the server launched by make.' }
    }

    if ((Get-ContainerState $ServerContainer) -ne '') {
        Invoke-Compose @('rm', '-s', '-f', 'server') @('server') | Out-Null
        Ok 'Stopped the server container.'
        $did = $true
        Sync-FrontProxy
    }

    # Whatever is still listening: another instance of the project (e.g. launched from IntelliJ)
    # is always stopped, because the goal is to free the port; an unrelated process, only with FORCE=1.
    $owner = Get-ServerOwner
    if ($owner.Kind -eq 'project' -or $owner.Kind -eq 'make') {
        Stop-ProcessTree $owner.Proc.Id
        Ok "Stopped the $($owner.Text)."
        $did = $true
    } elseif ($owner.Kind -eq 'foreign') {
        if ($Force -and $owner.Proc -and -not (Test-DockerProcessName $owner.Proc.Name)) {
            Stop-ProcessTree $owner.Proc.Id
            Ok "Stopped (FORCE=1) $($owner.Text)."
            $did = $true
        } else {
            Warn "Port $ServerPort is held by $($owner.Text), unrelated to this project: leaving it alone."
            if ($owner.Proc) { Info (Format-Cmd $owner.Proc.CommandLine) }
            Info 'To stop it anyway: make server-stop FORCE=1'
        }
    }

    for ($i = 0; $i -lt 10 -and (Get-PortPids $ServerPort).Count -gt 0 -and $did; $i++) { Start-Sleep -Milliseconds 500 }
    if (-not $Quiet) {
        if ((Get-PortPids $ServerPort).Count -eq 0) { Ok "Port $ServerPort is free: you can now launch the server from IntelliJ." }
        elseif (-not $did) { Warn 'There was no server of this project to stop.' }
    }
}

function Show-ServerStatus {
    $owner = Get-ServerOwner
    if ($owner.Kind -eq 'none') { Write-Host "  Server   : stopped (port $ServerPort free)"; return }
    $color = $(if ($owner.Kind -eq 'foreign') { 'Yellow' } else { 'Green' })
    $up = Test-Http $HealthUrl
    Write-Host "  Server   : $($owner.Text) - $(if ($up) { "responding on $ServerUrl" } else { 'not responding (starting?)' })" -ForegroundColor $color
    if ($owner.Proc) {
        Info "Process  : $($owner.Proc.Name), PID $($owner.Proc.Id), parent $($owner.Proc.ParentName) ($($owner.Proc.ParentId)), since $($owner.Proc.Started)"
        Info "Command  : $(Format-Cmd $owner.Proc.CommandLine 110)"
    }
    if ($owner.Kind -eq 'make') { Info "Log      : $ServerLog   (make server-logs)" }
    if ($owner.Kind -eq 'docker') { Info 'Log      : make server-logs' }
    if ($owner.Kind -eq 'project') { Info 'Log      : IntelliJ console and server\logs\app.log. To stop it: make server-stop' }
}

function Show-ServerLogs {
    $owner = Get-ServerOwner
    if ($owner.Kind -eq 'docker') { Invoke-Interactive 'docker' @('logs', '-f', '--tail', '100', $ServerContainer); return }
    $file = $ServerLog
    if ($owner.Kind -ne 'make' -or -not (Test-Path $file)) {
        $file = Join-Path $ServerDir 'logs\app.log'   # log4j2 file, written by any instance
        Warn "The server was not launched by make: showing $file"
    }
    if (-not (Test-Path $file)) { throw "There is no log at $file. Is the server running? (make status)" }
    Info "Following $file (Ctrl+C to exit; the server keeps running)"
    Get-Content $file -Tail 100 -Wait
}

# ----------------------------------------------------------------------------------------------
# Frontend
# ----------------------------------------------------------------------------------------------
function Set-JsonSettings([string]$File, [hashtable]$Values) {
    # Merges keys into a VS Code settings.json without losing the existing ones.
    $dir = Split-Path $File -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
    $obj = New-Object psobject
    if (Test-Path $File) {
        $raw = Get-Content $File -Raw
        if (-not [string]::IsNullOrWhiteSpace($raw)) {
            try { $obj = $raw | ConvertFrom-Json }
            catch {
                # Comments or trailing commas (JSONC): PowerShell 5.1 does not understand them
                $backup = "$File.bak-$(Get-Date -Format yyyyMMddHHmmss)"
                Copy-Item $File $backup
                Warn "$File is not strict JSON: backup saved to $backup and the file is regenerated."
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
    # Repository root opened in VS Code -> serves /frontend
    $rootValues = $common.Clone(); $rootValues['liveServer.settings.root'] = '/frontend'
    Set-JsonSettings (Join-Path $Root '.vscode\settings.json') $rootValues
    # In case the frontend folder is opened directly
    $frontValues = $common.Clone(); $frontValues['liveServer.settings.root'] = '/'
    Set-JsonSettings (Join-Path $FrontDir '.vscode\settings.json') $frontValues
    Ok "Go Live configured: port $FrontPort, /api -> $ServerUrl/api (.vscode\settings.json)"
}

function Get-FrontOwner {
    if ((Get-ContainerState $FrontContainer) -eq 'running') {
        return [pscustomobject]@{ Kind = 'docker'; Proc = $null; Text = "live-server in Docker ($FrontContainer)" }
    }
    $pids = Get-PortPids $FrontPort
    if ($pids.Count -eq 0) { return [pscustomobject]@{ Kind = 'none'; Proc = $null; Text = 'free' } }
    $p = Get-ProcInfo $pids[0]
    if ($p -and $p.Name -match '^Code(\s-\sInsiders)?\.exe$') {
        return [pscustomobject]@{ Kind = 'vscode'; Proc = $p; Text = "VS Code Go Live (PID $($p.Id))" }
    }
    $name = $(if ($p) { "$($p.Name) (PID $($p.Id))" } else { "PID $($pids[0])" })
    return [pscustomobject]@{ Kind = 'foreign'; Proc = $p; Text = $name }
}

function Resolve-FrontMode {
    if ($FrontMode -eq 'docker') { return 'docker' }
    $code = Find-VSCode
    if (-not $code) {
        if ($FrontMode -eq 'vscode') { throw 'FRONT_MODE=vscode but VS Code cannot be found. Install it: winget install -e --id Microsoft.VisualStudioCode' }
        Warn 'VS Code is not installed: the frontend will be served by live-server in Docker.'
        return 'docker'
    }
    if (-not (Test-LiveServerExtension $code)) {
        Say "Installing the Live Server (Go Live) extension in VS Code"
        $r = Invoke-Native $code @('--install-extension', $LiveServerExt, '--force')
        if ($r -ne 0 -or -not (Test-LiveServerExtension $code)) {
            if ($FrontMode -eq 'vscode') { throw "Could not install $LiveServerExt." }
            Warn "Could not install ${LiveServerExt}: live-server in Docker will be used."
            return 'docker'
        }
        Ok 'Live Server installed.'
    }
    return 'vscode'
}

function Start-Front {
    Say "Hot-reloading frontend ($FrontUrl)"
    $owner = Get-FrontOwner
    if ($owner.Kind -eq 'docker' -or $owner.Kind -eq 'vscode') {
        Ok "Already being served: $($owner.Text) on $FrontUrl"
        if ($owner.Kind -eq 'vscode') { Write-LiveServerSettings }
        return
    }
    if ($owner.Kind -eq 'foreign') {
        throw "Port $FrontPort is held by $($owner.Text). Close it or use another one: make front FRONT_PORT=5501"
    }

    $mode = Resolve-FrontMode
    if ($mode -eq 'vscode') {
        Write-LiveServerSettings
        $code = Find-VSCode
        Invoke-Native $code @($Root) | Out-Null   # opens the repo, or focuses its window if already open
        Ok 'VS Code opened at the repository root.'
        Write-Host ''
        Write-Host "  >> Click 'Go Live' in the VS Code status bar (bottom right)" -ForegroundColor Magenta
        Write-Host "     or press Alt+L Alt+O. Live Server cannot be started from the command line." -ForegroundColor Magenta
        Write-Host ''
        Info "Waiting for port $FrontPort to be active (max. $FrontWait s, Ctrl+C to stop waiting)..."
        if (Wait-Port $FrontPort $FrontWait) { Ok "Frontend served by Go Live on $FrontUrl" }
        else { Warn "Go Live is not active yet. Once you click it the frontend will be on $FrontUrl" }
        return
    }

    $code = Invoke-Compose @('up', '-d', 'front') @('front')
    if ($code -ne 0) { throw 'Could not start the frontend container.' }
    Info 'Waiting for live-server (the first time it downloads the package)...'
    $deadline = (Get-Date).AddSeconds(120)
    while ((Get-Date) -lt $deadline -and -not (Test-Http $FrontUrl)) { Start-Sleep -Seconds 2 }
    if (-not (Test-Http $FrontUrl)) {
        Invoke-Native 'docker' @('logs', '--tail', '40', $FrontContainer) | Out-Null
        throw 'live-server is not responding (log above).'
    }
    Ok "Frontend served by live-server in Docker: $FrontUrl (reloads when saving in frontend\)"
    Open-Url $FrontUrl
}

function Stop-Front {
    Say 'Stopping the frontend'
    if ((Get-ContainerState $FrontContainer) -ne '') {
        Invoke-Compose @('rm', '-s', '-f', 'front') @('front') | Out-Null
        Ok 'Stopped live-server (Docker).'
    }
    $owner = Get-FrontOwner
    switch ($owner.Kind) {
        'none'    { Ok "Port $FrontPort is free." }
        'vscode'  { Warn "Go Live is still active: stop it by clicking 'Port : $FrontPort' in the VS Code status bar (VS Code is not closed from here)." }
        'foreign' { Warn "Port $FrontPort is held by $($owner.Text): leaving it alone." }
    }
}

function Show-FrontStatus {
    $owner = Get-FrontOwner
    switch ($owner.Kind) {
        'none'    { Write-Host "  Frontend : stopped (port $FrontPort free)" }
        'foreign' { Write-Host "  Frontend : port $FrontPort held by $($owner.Text)" -ForegroundColor Yellow }
        default   { Write-Host "  Frontend : $($owner.Text) on $FrontUrl" -ForegroundColor Green }
    }
}

# ----------------------------------------------------------------------------------------------
# Model lab (C TUI with ncurses: Linux only, built and run in a container)
# ----------------------------------------------------------------------------------------------
function Build-Lab {
    Say 'Building fractal_model_lab in Docker'
    Ensure-Docker
    $code = Invoke-Native 'docker' @('build', '-f', $LabFile, '-t', $LabImage, $LabDir)
    if ($code -ne 0) { throw 'The model lab build failed.' }
    Ok "Image $LabImage ready."
}

# ----------------------------------------------------------------------------------------------
# Diagnostics and status
# ----------------------------------------------------------------------------------------------
function Show-Doctor {
    Say 'Checking the environment'
    $problems = 0

    Ok "PowerShell $($PSVersionTable.PSVersion)"
    if (Test-Command 'make') { Ok 'make installed' }
    else { Warn 'make is not on PATH: use dev.cmd <target> or install it with: dev install-make' }

    if (Find-DockerCli) {
        $engine = Get-DockerEngine
        if ($engine.Up) {
            $script:DaemonUp = $true
            if ($engine.Os -eq 'linux') { Ok "Docker $($engine.Version) (Linux containers)" }
            else { Warn "Docker in $($engine.Os) containers mode: make up will switch it to Linux" }
            if ((Get-NativeOutput 'docker' @('compose', 'version', '--short')).Code -eq 0) { Ok "docker compose $((Get-NativeOutput 'docker' @('compose','version','--short')).Text)" }
            else { Bad 'docker compose v2 is missing: winget upgrade -e --id Docker.DockerDesktop'; $problems++ }
        } elseif (Find-DockerDesktop) { Warn 'Docker Desktop is installed but stopped: make up starts it.' }
        else { Bad 'Docker is installed but the daemon is not responding.'; $problems++ }
    } else { Bad 'Docker is not installed: winget install -e --id Docker.DockerDesktop'; $problems++ }

    $jdks = Find-Jdks
    $jdk21 = $jdks | Where-Object { $_.Major -eq 21 } | Select-Object -First 1
    if ($jdk21) { Ok "JDK 21: $($jdk21.Home)" }
    else {
        $others = ($jdks | ForEach-Object { "$($_.Major)" }) -join ', '
        Warn "No JDK 21$(if ($others) { " (found: $others)" }): the server will run in Docker."
        Info 'Install: winget install -e --id EclipseAdoptium.Temurin.21.JDK  (or download it from IntelliJ)'
    }
    $mvn = Find-Maven
    if ($mvn) { Ok "Maven: $($mvn.Source)" } else { Warn 'No local Maven (only affects SERVER_MODE=local).' }

    $idea = Find-IntelliJHomes
    if ($idea.Count -gt 0) { Ok "IntelliJ: $($idea[0])" } else { Warn 'IntelliJ IDEA not found in the usual paths (optional for make).' }

    $code = Find-VSCode
    if ($code) {
        Ok "VS Code: $code"
        if (Test-LiveServerExtension $code) { Ok 'Live Server (Go Live) extension installed' }
        else { Warn 'The Live Server extension is missing: make front installs it.' }
    } else { Warn 'VS Code is not installed: the frontend will be served by live-server in Docker.' }

    foreach ($pp in @(@($DbPort, 'MySQL'), @($ServerPort, 'server'), @($FrontPort, 'frontend'))) {
        $pids = Get-PortPids $pp[0]
        if ($pids.Count -eq 0) { Ok "Port $($pp[0]) ($($pp[1])) free" }
        else {
            $p = Get-ProcInfo $pids[0]
            Info "Port $($pp[0]) ($($pp[1])) in use by $(if ($p) { "$($p.Name) (PID $($p.Id))" } else { "PID $($pids[0])" })"
        }
    }

    Write-Host ''
    if ($problems -eq 0) { Ok 'Environment ready: make up' } else { Bad "$problems problem(s) preventing the environment from starting." }
}

function Show-Status {
    Say 'Development environment status'
    if (-not (Find-DockerCli)) { Write-Host '  Docker   : not installed' -ForegroundColor Yellow }
    elseif (-not (Test-DockerDaemon)) { Write-Host '  Docker   : stopped' -ForegroundColor Yellow }
    else {
        $s = Get-ContainerState $DbContainer
        if ($s -eq '') { Write-Host '  MySQL    : not created (make db)' }
        else {
            $h = Get-ContainerHealth $DbContainer
            $color = $(if ($s -eq 'running' -and $h -eq 'healthy') { 'Green' } else { 'Yellow' })
            Write-Host "  MySQL    : $s$(if ($h) { " ($h)" }) on localhost:$DbPort - $DbUrl" -ForegroundColor $color
        }
    }
    Show-ServerStatus
    Show-FrontStatus
}

function Show-Help {
    @"

  NISAR SAR development environment (Windows)        make <target> [VAR=value ...]
                                                     (without make: dev <target>)
  General
    up               Starts everything: MySQL (Docker) + server (unless already running) + hot-reloading frontend
    down             Stops frontend, server and MySQL (data is kept)
    restart          down + up
    status           What is running, with PID, origin (make/IntelliJ/Docker) and URLs
    doctor           Checks Docker, JDK 21, Maven, VS Code + Live Server, IntelliJ and ports
    open             Opens the frontend in the browser

  Database (MySQL 8 in Docker, root/root, NisarSar database on localhost:3306)
    db               Starts MySQL and waits until it is healthy
    db-stop          Stops MySQL
    db-logs          Follows the MySQL log
    db-shell         mysql console inside the container
    db-reset         Deletes the data (asks for confirmation; YES=1 to skip it)

  Server (Spring Boot on $ServerUrl)
    server           Builds and starts it in the background, unless one is already listening
    server-stop      Stops this project's server (including one launched from IntelliJ)
                     and frees the port. FORCE=1 to also stop unrelated processes
    server-restart   Rebuilds and relaunches with your changes
    server-status    Details of the process holding the port
    server-logs      Follows the server log
    server-build     Only builds (mvnw package)

  Frontend (hot reload on $FrontUrl, /api forwarded to the server)
    front            VS Code Go Live (configures it and installs the extension) or live-server in Docker
    front-stop       Stops live-server (Go Live is stopped from the VS Code status bar)
    front-config     Only writes the Go Live settings to .vscode\settings.json

  Model lab (C TUI, in Docker)
    lab-build        Builds fractal_model_lab
    lab-test         Runs its tests
    lab-run          Runs the TUI in this console

  Cleanup
    clean            Deletes .dev\ and server\target
    purge            down + deletes containers, volumes (data, caches) and the lab image

  Variables: DB_PORT=3306 DB_PASSWORD=root SERVER_PORT=8080 FRONT_PORT=5500
             SERVER_MODE=auto|local|docker FRONT_MODE=auto|vscode|docker
             SERVER_TIMEOUT=180 FRONT_WAIT=120 OPEN=1 YES=0 FORCE=0

  IntelliJ workflow: make up  ->  make server-stop  ->  Run in IntelliJ (connects to the same DB)

"@ | Write-Host
}

# ----------------------------------------------------------------------------------------------
# Actions
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
            Info 'To run the server from IntelliJ with your changes: make server-stop, then Run.'
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
            if (-not $jdk) { throw 'No JDK 21 to build locally: winget install -e --id EclipseAdoptium.Temurin.21.JDK' }
            Build-Server $jdk | Out-Null
        }

        'front'          { Start-Front }
        'front-start'    { Start-Front }
        'front-stop'     { Stop-Front }
        'front-config'   { Write-LiveServerSettings }

        'lab-build'      { Build-Lab }
        'lab-test'       { Build-Lab; if ((Invoke-Native 'docker' @('run', '--rm', $LabImage, 'make', 'test')) -ne 0) { throw 'The model lab tests failed.' } }
        'lab-run'        { Build-Lab; Invoke-Interactive 'docker' @('run', '--rm', '-it', '-e', 'TERM=xterm-256color', $LabImage) }

        'clean' {
            Stop-Server -Quiet
            foreach ($d in @($StateDir, (Join-Path $ServerDir 'target'))) {
                if (Test-Path $d) { Remove-Item $d -Recurse -Force; Ok "Deleted $d" }
            }
        }
        'purge' {
            if (-not (Confirm-Action 'Containers, MySQL data and the Maven/npm caches of the environment will be deleted. Are you sure?')) { Warn 'Cancelled.'; return }
            Stop-Front; Stop-Server
            Ensure-Docker
            Invoke-Native 'docker' @('compose', '-f', $ComposeFile, '-p', $ComposeProject, '--profile', 'server', '--profile', 'front', 'down', '-v', '--remove-orphans') | Out-Null
            Invoke-Native 'docker' @('image', 'rm', '-f', $LabImage) | Out-Null
            if (Test-Path $StateDir) { Remove-Item $StateDir -Recurse -Force }
            Ok 'Development environment removed.'
        }

        'install-make' {
            if (Test-Command 'make') { Ok 'make is already installed.'; return }
            if (-not (Test-Command 'winget')) { throw 'winget is not available. Install make with Chocolatey (choco install make) or Scoop (scoop install make).' }
            Invoke-Native 'winget' @('install', '-e', '--id', 'ezwinports.make', '--accept-source-agreements', '--accept-package-agreements') | Out-Null
            Ok 'make installed. Open a new console so that it is on PATH.'
        }

        default { Show-Help; throw "Unknown target: '$Name'" }
    }
}

try {
    if ($env:OS -ne 'Windows_NT') { throw 'This script is for Windows.' }
    Invoke-Action $Action.ToLowerInvariant()
    exit 0
} catch {
    Write-Host ''
    Bad $_.Exception.Message
    exit 1
}
