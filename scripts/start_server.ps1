# Start Mortgage RAG Evaluator API Server

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Mortgage RAG Evaluator API" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if in project root
if (-not (Test-Path "api\main.py")) {
    Write-Host "Error: Please run this script in zeval-service root directory" -ForegroundColor Red
    exit 1
}

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
    Write-Host "Then install: .venv\Scripts\activate; pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Setup Python paths
Write-Host "Found venv: $VenvPath" -ForegroundColor Green
$pythonExe = Join-Path $VenvPath "Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "Error: python.exe not found in venv" -ForegroundColor Red
    exit 1
}

# Check if dependencies are installed
Write-Host "Checking dependencies..." -ForegroundColor Cyan
$uvicornCheck = & $pythonExe -c "import uvicorn" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Dependencies not installed" -ForegroundColor Red
    Write-Host "Please install dependencies first:" -ForegroundColor Yellow
    Write-Host "  cd zeval-service" -ForegroundColor Yellow
    Write-Host "  $VenvPath\Scripts\activate" -ForegroundColor Yellow
    Write-Host "  pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}
Write-Host "Dependencies OK" -ForegroundColor Green

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
    Write-Host "  Copy .env.example to .env and configure" -ForegroundColor Yellow
}

# Initialize database
Write-Host ""
Write-Host "Initializing database..." -ForegroundColor Cyan
$env:PYTHONPATH = "."
& $pythonExe scripts\init_db.py

# Start API server
Write-Host ""
Write-Host "Starting API server..." -ForegroundColor Cyan
Write-Host "  - API docs: http://localhost:8001/docs" -ForegroundColor Yellow
Write-Host "  - Web UI: http://localhost:8001/ui" -ForegroundColor Yellow
Write-Host "  - Health check: http://localhost:8001/health" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

& $pythonExe -m uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload --reload-dir api --reload-dir database --reload-dir models --reload-dir evaluator --reload-dir worker
