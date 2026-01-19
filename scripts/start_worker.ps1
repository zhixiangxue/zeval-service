# Start Evaluation Worker

$ErrorActionPreference = "Stop"

Write-Host "Starting Evaluation Worker..." -ForegroundColor Cyan

# Find virtual environment (search up to 3 levels)
$VenvPath = $null
for ($i = 0; $i -le 3; $i++) {
    if ($i -eq 0) {
        $testPath = ".venv"
    } else {
        $parts = @()
        for ($j = 0; $j -lt $i; $j++) {
            $parts += ".."
        }
        $testPath = Join-Path ($parts -join "\") ".venv"
    }
    
    if (Test-Path $testPath) {
        $VenvPath = (Resolve-Path $testPath).Path
        break
    }
}

if (-not $VenvPath) {
    Write-Host "Error: Virtual environment .venv not found" -ForegroundColor Red
    Write-Host "Please create: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

Write-Host "Found venv: $VenvPath" -ForegroundColor Green

# Python executable path
$pythonExe = Join-Path $VenvPath "Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "Error: python.exe not found in venv" -ForegroundColor Red
    exit 1
}

# Check if dependencies are installed
Write-Host "Checking dependencies..." -ForegroundColor Cyan
$depsCheck = & $pythonExe -c "import fastapi, schedule" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Dependencies not installed" -ForegroundColor Red
    Write-Host "Please install dependencies first:" -ForegroundColor Yellow
    Write-Host "  cd zeval-service" -ForegroundColor Yellow
    Write-Host "  $VenvPath\Scripts\activate" -ForegroundColor Yellow
    Write-Host "  pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}
Write-Host "Dependencies OK" -ForegroundColor Green

# Change to zeval-service directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$serviceDir = Split-Path -Parent $scriptDir
Set-Location $serviceDir

# Load environment variables
if (Test-Path ".env") {
    Write-Host "Loading .env file" -ForegroundColor Green
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*?)\s*=\s*(.*)$') {
            $name = $matches[1]
            $value = $matches[2]
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
} else {
    Write-Host "Warning: .env file not found" -ForegroundColor Yellow
}

# Initialize database
Write-Host "Initializing database..." -ForegroundColor Green
$env:PYTHONPATH = "."
& $pythonExe scripts\init_db.py

# Start Worker
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "  Evaluation Worker Starting..." -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

& $pythonExe -m worker.worker

Write-Host ""
Write-Host "Worker stopped" -ForegroundColor Yellow
