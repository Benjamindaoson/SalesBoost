# Repository Consolidation - 2026-09-10

This document records repository governance changes for SalesBoost.

## SalesAgent -> SalesBoost

Decision: `SalesAgent` is a predecessor of `SalesBoost`, not a separate public
portfolio project.

Reasoning:

- `SalesBoost` is the canonical sales enablement platform.
- `SalesAgent` had useful implementation assets: FastAPI service code,
  LangGraph-style orchestration, WeChat workers, memory, guardrails, synthetic
  data/flywheel code, a React/Vite prototype, deployment files, and tests.
- The old public `SalesAgent` README contained unverified claims such as
  conversion uplift, speed multipliers, placeholder demo links, and template
  repository URLs, so those marketing files were not retained.

Preserved assets:

- `legacy_imports/salesagent_v3/salesagent/`
- `legacy_imports/salesagent_v3/platform/`
- `legacy_imports/salesagent_v3/tests/`
- `legacy_imports/salesagent_v3/alembic/`
- `legacy_imports/salesagent_v3/deployment/`
- `legacy_imports/salesagent_v3/scripts/`
- `legacy_imports/salesagent_v3/.env.example`
- `legacy_imports/salesagent_v3/pyproject.toml`
- `legacy_imports/salesagent_v3/requirements*.txt`

Boundary:

`legacy_imports/salesagent_v3/` is reference code only. It must not be treated
as active runtime without targeted integration, tests, and updated evidence.
