---
version: v1
description: FSM stage definitions and transition triggers. Used as configuration reference; loaded into registry for validation and documentation.
---
{
  "stages": [
    {"name": "opening",    "label": "\u5f00\u573a\u7834\u51b0",  "description": "Establish rapport, get basic customer info, gain permission to continue."},
    {"name": "discovery",  "label": "\u9700\u6c42\u6316\u6398",  "description": "Uncover pain points, understand budget, confirm decision makers. Requires 3+ discovery questions."},
    {"name": "pitch",      "label": "\u4ea7\u54c1\u63a8\u4ecb",  "description": "Introduce value based on identified needs, link features to benefits (FAB)."},
    {"name": "objection",  "label": "\u5f02\u8bae\u5904\u7406",  "description": "Identify and handle customer concerns. Use Feel-Felt-Found or SPIN."},
    {"name": "closing",    "label": "\u7f14\u7ed3\u6210\u4ea4",  "description": "Drive for commitment, agree on next steps. Use assumptive close or urgency."},
    {"name": "completed",  "label": "\u5bf9\u8bdd\u5b8c\u6210",  "description": "Terminal success state."},
    {"name": "failed",     "label": "\u5bf9\u8bdd\u5931\u8d25",  "description": "Terminal failure state (hard rejection or conversation ended)."}
  ],
  "triggers": [
    "rapport_established",
    "needs_identified",
    "buying_signal",
    "objection_raised",
    "objection_resolved",
    "interest_confirmed",
    "commitment_made",
    "hard_rejection",
    "conversation_ended",
    "manual_override",
    "discovery_complete"
  ],
  "flow": "opening \u2192 discovery (3+ questions) \u2192 pitch \u2192 objection \u21c4 pitch \u2192 closing \u2192 completed"
}
