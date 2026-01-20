## Refactor ComplianceAgent to Fail-Closed

1.  **Define Safety Constants**:
    - Add `SAFE_FALLBACK_RESPONSE` to the `ComplianceAgent` class.
2.  **Rewrite `check_compliance`**:
    - Use a broad `try-except` block to wrap all compliance steps (DB, Regex, LLM).
    - Implement "Fail-Closed" logic: return `is_compliant=False` and `blocked=True` if any step fails.
    - Set reason to "Safety Check Unavailable - System Busy" and return the fallback message.
    - Log stack traces with `logger.exception` at `ERROR` level.
3.  **Rewrite `_call_llm_audit`**:
    - Wrap LLM calls in a `try-except` block and re-raise exceptions to trigger the outer "Fail-Closed" logic.
4.  **Harden Default Rules**:
    - Ensure `HIGH_RISK_PATTERNS` are always available even if DB rules fail to load.
5.  **Maintain Compatibility**:
    - Update `SessionOrchestrator` or provide an alias to ensure existing calls to `check` continue to work.

## Verification
- Verify that simulated LLM timeouts result in a blocked message.
- Verify that sensitive keywords are still blocked even when the DB is unavailable.
