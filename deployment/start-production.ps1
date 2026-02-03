# SalesBoost Production Deployment Script
# 100% Automated Go-Live

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting SalesBoost Production Deployment..." -ForegroundColor Cyan

# 1. Environment Check
if (-not (Test-Path .env)) {
    Write-Host "❌ .env file not found! Please create it from .env.example" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Environment file found." -ForegroundColor Green

# 2. Docker Check
try {
    docker info > $null
} catch {
    Write-Host "❌ Docker is not running! Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Docker is running." -ForegroundColor Green

# 3. Build and Launch
Write-Host "🏗️  Building and launching containers..." -ForegroundColor Yellow
docker-compose up -d --build

# 4. Wait for services to be ready
Write-Host "⏳ Waiting for services to initialize (this may take 1-2 minutes)..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# 5. Health Check
$maxRetries = 10
$retryCount = 0
$healthy = $false

while ($retryCount -lt $maxRetries -and -not $healthy) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
        if ($response.status -eq "ok") {
            $healthy = $true
        } else {
            Write-Host "⚠️  System status: $($response.status). Retrying..." -ForegroundColor Gray
        }
    } catch {
        Write-Host "⏳ API not ready yet... ($($retryCount + 1)/$maxRetries)" -ForegroundColor Gray
    }
    
    if (-not $healthy) {
        $retryCount++
        Start-Sleep -Seconds 10
    }
}

if ($healthy) {
    Write-Host "`n✨ SalesBoost is now LIVE and 100% Operational!" -ForegroundColor Green
    Write-Host "------------------------------------------------"
    Write-Host "🌍 Frontend: http://localhost" -ForegroundColor White
    Write-Host "⚙️  Backend API: http://localhost:8000" -ForegroundColor White
    Write-Host "📊 Monitoring (Grafana): http://localhost:3001" -ForegroundColor White
    Write-Host "📈 Metrics (Prometheus): http://localhost:9090" -ForegroundColor White
    Write-Host "------------------------------------------------"
    Write-Host "Enjoy your AI-powered sales coaching platform!" -ForegroundColor Cyan
} else {
    Write-Host "`n❌ Deployment timed out or health check failed." -ForegroundColor Red
    Write-Host "Please check logs with: docker-compose logs api" -ForegroundColor Yellow
}
