[CmdletBinding()]
param([switch]$SkipEngine, [switch]$LibraryOnly)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))

function Get-DharoharPython {
    $candidate = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    $pointer = Join-Path $ProjectRoot 'runtime\python-path.txt'
    if (Test-Path -LiteralPath $pointer -PathType Leaf) {
        $candidate = (Get-Content -LiteralPath $pointer -Raw).Trim()
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return [IO.Path]::GetFullPath($candidate) }
    }
    throw 'Python environment not found. Run scripts\Setup-DHAROHAR.ps1 first.'
}

function Get-DharoharSetting([string]$Name, [string]$Default) {
    $value = [Environment]::GetEnvironmentVariable($Name, 'Process')
    if ($null -ne $value) { return $value }
    $envFile = Join-Path $ProjectRoot '.env'
    if (Test-Path -LiteralPath $envFile) {
        foreach ($line in Get-Content -LiteralPath $envFile) {
            if ($line -match ('^\s*' + [regex]::Escape($Name) + '\s*=\s*(.*?)\s*$')) {
                return $Matches[1].Trim().Trim('"').Trim("'")
            }
        }
    }
    return $Default
}

function Enter-DharoharLaunchLock {
    $hash = [Security.Cryptography.SHA256]::Create()
    try { $id = [BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($ProjectRoot.ToLowerInvariant()))).Replace('-', '').Substring(0, 20) }
    finally { $hash.Dispose() }
    $mutex = [Threading.Mutex]::new($false, ('Local\DHAROHAR-' + $id))
    try { $acquired = $mutex.WaitOne(10000) }
    catch [Threading.AbandonedMutexException] { $acquired = $true }
    if (-not $acquired) { $mutex.Dispose(); throw 'Another DHAROHAR launcher is running. Try again when it finishes.' }
    return $mutex
}

function ConvertTo-DharoharArgument([string]$Value) {
    if ($Value.Length -gt 0 -and $Value -notmatch '[\s"]') { return $Value }
    $escaped = [regex]::Replace($Value, '(\\*)"', '$1$1\"')
    $escaped = [regex]::Replace($escaped, '(\\+)$', '$1$1')
    return '"' + $escaped + '"'
}

function Start-DharoharProcess([string]$Name, [string]$Executable, [string[]]$Arguments) {
    $logs = Join-Path $ProjectRoot 'data\logs'
    $records = Join-Path $ProjectRoot 'runtime\processes'
    [void](New-Item -ItemType Directory -Force -Path $logs, $records)
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $stdout = Join-Path $logs "$Name-$stamp.stdout.log"
    $stderr = Join-Path $logs "$Name-$stamp.stderr.log"
    $argumentLine = ($Arguments | ForEach-Object { ConvertTo-DharoharArgument $_ }) -join ' '
    $process = Start-Process -FilePath $Executable -ArgumentList $argumentLine -WorkingDirectory $ProjectRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
    @{ pid = $process.Id; executable = $Executable; arguments = $Arguments; started = (Get-Date).ToString('o'); stdout = $stdout; stderr = $stderr } |
        ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $records "$Name.json") -Encoding UTF8
    Write-Host "$Name started (PID $($process.Id)); logs: $logs"
    return $process
}

function Find-DharoharWorker([string]$ScriptName, [string]$PythonPath) {
    $absolute = Join-Path $ProjectRoot ('scripts\' + $ScriptName)
    foreach ($process in Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'pythonw.exe'") {
        $command = [string]$process.CommandLine
        if (-not $command) { continue }
        # Absolute paths identify this project. For legacy relative launches,
        # match the configured interpreter and the exact script basename.
        $fullMatch = $command.IndexOf($absolute, [StringComparison]::OrdinalIgnoreCase) -ge 0
        $scriptMatch = $command -match ('(?:^|[\\/\s"''])' + [regex]::Escape($ScriptName) + '(?:[\s"'']|$)')
        $pythonMatch = ([string]$process.ExecutablePath -eq $PythonPath) -or ($command.IndexOf($PythonPath, [StringComparison]::OrdinalIgnoreCase) -ge 0)
        if ($fullMatch -or ($scriptMatch -and $pythonMatch)) { return $process }
    }
    return $null
}

function Test-DharoharPort([int]$Port) {
    return @([Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() | Where-Object { $_.Port -eq $Port }).Count -gt 0
}

function Test-DharoharHealth([string]$Kind, [string]$Url) {
    try {
        if ($Kind -eq 'api') {
            $schema = Invoke-RestMethod -Uri ($Url + '/openapi.json') -TimeoutSec 4
            if ($schema.info.title -ne 'DHAROHAR') { return $false }
            $result = Invoke-RestMethod -Uri ($Url + '/api/status') -TimeoutSec 12
            return $null -ne $result.documents
        }
        $result = Invoke-RestMethod -Uri ($Url + '/health') -TimeoutSec 3
        return $result.status -eq 'ok'
    } catch { return $false }
}

function Wait-DharoharHealth([string]$Kind, [string]$Url, [int]$Seconds = 120) {
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    do {
        if (Test-DharoharHealth $Kind $Url) { return }
        Start-Sleep -Milliseconds 750
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "$Kind did not become ready at $Url. Read data\logs; no process was stopped."
}

function Start-DharoharEngine {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker Desktop is not installed or is not on PATH.' }
    $null = & docker info --format '{{.OSType}}' 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop with Linux containers, then run this command again.' }
    $inspection = & docker inspect --format '{{.State.Running}}' dharohar-ocr 2>$null
    if ($LASTEXITCODE -eq 0) {
        if (($inspection | Out-String).Trim() -eq 'true') { Write-Host 'Using the running dharohar-ocr speech/OCR engine.'; return }
        $null = & docker start dharohar-ocr
        if ($LASTEXITCODE -ne 0) { throw 'The existing speech/OCR engine could not be started.' }
        Write-Host 'Started the existing dharohar-ocr speech/OCR engine.'
        return
    }
    $null = & docker image inspect dharohar-ai:engine 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'Engine image is missing. Run scripts\Setup-DHAROHAR.ps1, or docker build -f Dockerfile.engine -t dharohar-ai:engine .' }
    $null = & docker run -d --name dharohar-ocr --restart unless-stopped --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,size=128m --memory 1200m --cpus 3 dharohar-ai:engine
    if ($LASTEXITCODE -ne 0) { throw 'The speech/OCR engine could not be created.' }
    Write-Host 'Started the isolated local speech/OCR engine.'
}

if ($LibraryOnly) { return }
$launchLock = Enter-DharoharLaunchLock
try {
    $pythonPath = Get-DharoharPython
    if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot 'frontend\dist\index.html'))) { throw 'The built frontend is missing. Run Setup-DHAROHAR.ps1 or npm run build in frontend.' }
    if (-not $SkipEngine) {
        try { Start-DharoharEngine } catch { Write-Warning "$($_.Exception.Message) OCR needs the engine. Reading, chat and neural narration can still run." }
    }
    if ((Get-DharoharSetting 'AI_PROVIDER' 'local') -eq 'local') {
        $llmUrl = (Get-DharoharSetting 'LOCAL_LLM_URL' 'http://127.0.0.1:8011').TrimEnd('/')
        if (Test-DharoharHealth 'llm' $llmUrl) { Write-Host "Using the healthy local language model at $llmUrl." }
        elseif ($llmUrl -notin @('http://127.0.0.1:8011', 'http://localhost:8011')) { Write-Warning "The configured language model at $llmUrl is unavailable. Start that service separately." }
        else {
            $llama = Join-Path $ProjectRoot 'runtime\llama\llama-server.exe'
            $model = Join-Path $ProjectRoot 'data\models\Qwen3.5-4B-Q4_K_M.gguf'
            if (-not (Test-Path -LiteralPath $llama) -or -not (Test-Path -LiteralPath $model)) { Write-Warning 'The local language model/runtime is missing. Run Setup-DHAROHAR.ps1; the archive remains readable.' }
            elseif (Test-DharoharPort 8011) { Wait-DharoharHealth 'llm' $llmUrl }
            else {
                $existing = @(Get-CimInstance Win32_Process -Filter "Name = 'llama-server.exe'" | Where-Object { ([string]$_.ExecutablePath -eq $llama) -and ([string]$_.CommandLine -match '(?:--port[ =]+|--port"?\s+"?)8011(?:\s|"|$)') })
                if ($existing.Count -eq 0) {
                    $null = Start-DharoharProcess 'llama' $llama @('-m', $model, '--host', '127.0.0.1', '--port', '8011', '-c', '8192', '-np', '1', '-t', '6', '-tb', '8', '--no-webui', '--reasoning', 'off', '--jinja')
                }
                Wait-DharoharHealth 'llm' $llmUrl
            }
        }
    }
    $apiUrl = 'http://127.0.0.1:8010'
    if (Test-DharoharHealth 'api' $apiUrl) { Write-Host "Using the healthy DHAROHAR server at $apiUrl." }
    elseif (Test-DharoharPort 8010) { Wait-DharoharHealth 'api' $apiUrl 30 }
    else {
        $existing = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'pythonw.exe'" | Where-Object { ([string]$_.CommandLine -match '(?:^|\s)uvicorn\s+app\.main:app\b') -and ([string]$_.CommandLine -match '--port\s+8010(?:\s|$)') })
        if ($existing.Count -eq 0) { $null = Start-DharoharProcess 'api' $pythonPath @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8010') }
        Wait-DharoharHealth 'api' $apiUrl
    }
    Write-Host "Open $apiUrl in your browser. Background processing: scripts\Resume-Processing.ps1"
} finally { $launchLock.ReleaseMutex(); $launchLock.Dispose() }
