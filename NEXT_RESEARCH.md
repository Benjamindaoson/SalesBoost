# Future Research Directions

**Date**: 2026-01-18

## 1. Reinforcement Learning (RL)
### Contextual Bandits for Curriculum
-   **Current**: Rule-based `CurriculumPlanner` (If weak -> recommend).
-   **Proposal**: Use Contextual Bandits (e.g., LinUCB).
-   **Context**: User Profile (Skill levels, History).
-   **Action**: Recommended Scenario.
-   **Reward**: `effectiveness_score` of next turn.
-   **Goal**: Maximize learning rate, not just engagement.

## 2. Dynamic NPC Evolution
-   **Current**: Static Persona Traits ("Price Sensitive").
-   **Proposal**: Generative Agents (Park et al., 2023).
-   **Idea**: NPC "remembers" previous sales attempts and builds "Immunities".
-   **Impact**: Prevents users from memorizing "winning scripts".

## 3. Multimodal Analysis
-   **Current**: Text-only.
-   **Proposal**: Audio/Video processing.
-   **Tech**: OpenAI Whisper + Tone Analysis.
-   **Metric**: Detect "Confidence" via voice jitter/pace, not just text semantics.

## 4. Causal Inference in Sales
-   **Problem**: Did the user sell because of the *strategy* or just *luck*?
-   **Proposal**: A/B Testing Simulator.
-   **Method**: Run shadow simulations where the same user input is tested against different NPC randomness seeds to determine "True Skill".

## 5. Automated Golden Strategy Mining
-   **Current**: Hardcoded `STRATEGY_TAXONOMY`.
-   **Proposal**: Unsupervised Clustering on top-performing logs.
-   **Goal**: Discover *new* strategies that humans haven't labeled yet.
