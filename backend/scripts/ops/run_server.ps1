Get-Content d:\SalesBoost\.env | ForEach-Object {
    if ($_ -match '^(\w+)=(.*)$') {
        Set-Item -Path ("Env:" + $matches[1]) -Value $matches[2]
    }
}
uvicorn main:app --host 0.0.0.0 --port 8000
