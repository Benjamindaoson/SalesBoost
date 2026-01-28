Get-Content d:\SalesBoost\.env | ForEach-Object {
    if ($_ -match '^(\w+)=(.*)$') {
        Set-Item -Path ("Env:" + $matches[1]) -Value $matches[2]
    }
}
# Override for local run
$env:ENV_STATE = "development"
$env:ADMIN_PASSWORD_HASH = ""
$env:ADMIN_PASSWORD = "ChangeMe_123!"
$env:ALLOW_INSECURE_ADMIN_PASSWORD = "true"
$env:DATABASE_URL = "sqlite+aiosqlite:///d:/SalesBoost/storage/databases/salesboost_local.db"
$env:PORT = "8001"
uvicorn main:app --host 0.0.0.0 --port 8001
