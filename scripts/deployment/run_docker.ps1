$ConfirmPreference = 'None'
docker-compose down
docker-compose up -d --build
Start-Sleep -Seconds 10
docker-compose ps
