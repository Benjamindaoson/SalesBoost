import os
import yaml
from typing import Any

def load_meta_principles() -> list[dict[str, Any]]:
    """Load meta-principles from YAML config."""
    path = os.path.join(os.path.dirname(__file__), "meta_principles.yaml")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        return data.get("meta_principles", [])

META_PRINCIPLES = load_meta_principles()

def get_applicable_principles(persona: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Filter applicable Meta-Principles based on the CustomerPersonaVector (Sales Meta-Principles 1.0).
    """
    trust = persona.get("trust_score", 50)
    urgency = persona.get("urgency", 50)
    friction = str(persona.get("friction_points", [])).lower()
    intent_score = persona.get("intent_score", 50)
    emotion = persona.get("emotion", "neutral")
    is_looping = persona.get("is_looping", False)

    applicable = []
    for mp in META_PRINCIPLES:
        cond = mp.get("condition", "always")
        is_match = False

        if cond == "always":
            is_match = True
        elif "trust_score < 50" in cond and trust < 50:
            is_match = True
        elif "technical_doubt" in cond and ("technical" in friction or "doubt" in friction):
            is_match = True
        elif "friction_points contains 'price'" in cond and "price" in friction:
            is_match = True
        elif "urgency > 80 or urgency < 40" in cond and (urgency > 80 or urgency < 40):
            is_match = True
        elif "price_sensitive" in cond and ("price" in friction or "sensitive" in friction):
            is_match = True
        elif "intent_score > 80" in cond and intent_score > 80 and not persona.get("friction_points"):
            is_match = True
        elif "emotion == 'angry' or is_looping == true" in cond and (emotion == "angry" or is_looping):
            is_match = True

        if is_match:
            applicable.append(mp)

    # Priority: ensure 3-7 principles are selected.
    if len(applicable) < 3:
        remaining = [mp for mp in META_PRINCIPLES if mp not in applicable]
        applicable.extend(remaining[:3 - len(applicable)])
    elif len(applicable) > 7:
        specs = [mp for mp in applicable if mp.get("condition") != "always"]
        always = [mp for mp in applicable if mp.get("condition") == "always"]
        applicable = (specs[:4] + always[:3])

    return applicable
