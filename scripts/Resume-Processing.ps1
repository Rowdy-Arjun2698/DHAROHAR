[CmdletBinding()]
param([switch]$OcrOnly, [switch]$EmbeddingsOnly)
if ($OcrOnly -and $EmbeddingsOnly) { throw 'Choose at most one of -OcrOnly and -EmbeddingsOnly, or omit both.' }
. (Join-Path $PSScriptRoot 'Start-DHAROHAR.ps1') -LibraryOnly
$launchLock = Enter-DharoharLaunchLock
try {
    $pythonPath = Get-DharoharPython
    if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot 'data\archive.sqlite3'))) { throw 'Import the supplied archive first; see docs\SETUP.md.' }
    if (-not $EmbeddingsOnly) {
        $worker = Find-DharoharWorker 'ocr_archive.py' $pythonPath
        if ($null -ne $worker) { Write-Host "OCR is already running (PID $($worker.ProcessId)); keeping that worker." }
        else {
            Start-DharoharEngine
            $null = Start-DharoharProcess 'ocr' $pythonPath @('-u', (Join-Path $ProjectRoot 'scripts\ocr_archive.py'))
        }
    }
    if (-not $OcrOnly) {
        $worker = Find-DharoharWorker 'build_embeddings.py' $pythonPath
        if ($null -ne $worker) { Write-Host "Embedding indexing is already running (PID $($worker.ProcessId)); keeping that worker." }
        else {
            if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot 'data\models\multilingual-minilm\model.onnx'))) { throw 'The multilingual search model is missing. Run Setup-DHAROHAR.ps1 first.' }
            $null = Start-DharoharProcess 'embeddings' $pythonPath @('-u', (Join-Path $ProjectRoot 'scripts\build_embeddings.py'))
        }
    }
    Write-Host 'Processing is resumable and may take hours. Check the app status or data\logs for progress.'
} finally { $launchLock.ReleaseMutex(); $launchLock.Dispose() }
