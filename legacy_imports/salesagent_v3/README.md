# SalesAgent V3 Legacy Import

This directory preserves useful engineering assets from the retired
`Benjamindaoson/SalesAgent` repository before that standalone repository was
removed.

Status:

- This code is a legacy reference, not the active SalesBoost runtime.
- Old public marketing README files were intentionally not imported because
  they contained unverified conversion and speed claims.
- Runtime integration must happen through normal SalesBoost review, tests, and
  evidence gates.

Preserved assets:

- `salesagent/`: legacy FastAPI/LangGraph service, orchestration nodes,
  memory, guardrails, LLM gateway, WeChat integrations, and flywheel code.
- `platform/`: old React/Vite sales-agent UI prototype.
- `tests/`: unit and integration tests from the source repository.
- `alembic/`, `deployment/`, `scripts/`: schema, deployment, setup, and demo
  utilities.

Source repository:

- GitHub repository: `Benjamindaoson/SalesAgent`
- Last observed source commit: `1838e3d Rescue SalesAgent runnable baseline`
- Consolidated into: `Benjamindaoson/SalesBoost`
