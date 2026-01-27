# Blue/Green Runbook

## Blue/Green Deploy (Docker Compose)
1. Deploy new stack with a different project name:
   - `COMPOSE_PROJECT_NAME=salesboost-green docker compose -f deployment/docker/docker-compose.yml up -d --build`
2. Health check:
   - `curl http://<green-host>:8000/health`
3. Switch traffic at LB / reverse proxy to green.
4. Monitor metrics and logs.

## Rollback
1. Switch traffic back to blue.
2. Stop green stack:
   - `COMPOSE_PROJECT_NAME=salesboost-green docker compose -f deployment/docker/docker-compose.yml down`
