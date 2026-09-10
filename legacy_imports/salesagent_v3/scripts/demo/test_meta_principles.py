import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from salesagent.reasoning.meta_principles import get_applicable_principles

def test_principles():
    test_cases = [
        {
            "name": "Low Trust (Trust First)",
            "vector": {
                "trust_score": 30,
                "urgency": 50,
                "friction_points": [],
            }
        },
        {
            "name": "Technical Doubt (Asymmetric Info)",
            "vector": {
                "trust_score": 75,
                "urgency": 50,
                "friction_points": ["technical_doubt", "architecture"],
            }
        },
        {
            "name": "Price Sensitivity (Value Before Price)",
            "vector": {
                "trust_score": 60,
                "urgency": 50,
                "friction_points": ["price", "budget_tight"],
            }
        },
        {
            "name": "High Urgency (Urgency Match)",
            "vector": {
                "trust_score": 80,
                "urgency": 90,
                "friction_points": [],
            }
        },
        {
            "name": "Ready to Close (Closing Capture)",
            "vector": {
                "trust_score": 90,
                "urgency": 85,
                "friction_points": [],
                "intent_score": 85
            }
        },
        {
            "name": "Angry Customer (Human Handover)",
            "vector": {
                "trust_score": 20,
                "urgency": 60,
                "friction_points": ["service_failure"],
                "emotion": "angry"
            }
        }
    ]

    print("=== Sales Meta-Principles 1.0 Activation Test ===\n")
    for case in test_cases:
        print(f"Test: {case['name']}")
        print(f"Vector: {case['vector']}")
        applicable = get_applicable_principles(case['vector'])
        ids = [mp['id'] for mp in applicable]
        names = [mp['name'] for mp in applicable]
        print(f"Activated IDs: {ids}")
        print(f"Activated Names: {names}")
        print("-" * 40)

if __name__ == "__main__":
    test_principles()
