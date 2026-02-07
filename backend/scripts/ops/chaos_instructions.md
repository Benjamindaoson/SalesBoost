# Fault Injection (Redis / DB)

## Redis outage
1. Stop Redis:
   - `docker stop salesboost_redis`
2. Verify fallback behavior and error handling.
3. Start Redis:
   - `docker start salesboost_redis`

## Postgres outage
1. Stop Postgres:
   - `docker stop salesboost_postgres`
2. Verify API error handling and retries.
3. Start Postgres:
   - `docker start salesboost_postgres`
