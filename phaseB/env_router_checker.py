import os
from typing import Dict


def load_router_config() -> Dict[str, str]:
    # Read from environment; fallback defaults
    return {
        "ROUTER_STRATEGY": os.getenv("ROUTER_STRATEGY", "default"),
        "ENABLE_DETAILED_LOGS": os.getenv("ENABLE_DETAILED_LOGS", "false"),
    }

def validate_config(cfg: Dict[str, str]) -> bool:
    # Minimal validation
    return "ROUTER_STRATEGY" in cfg
