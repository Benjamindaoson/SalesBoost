"""
Tool Reflection Agent

Provides self-correction capabilities for tool execution failures.

When a tool execution fails due to parameter validation errors, this agent
analyzes the error and generates corrected parameters for retry.

Features:
- Automatic error analysis
- Parameter correction
- Retry with corrected parameters
- Learning from failures

Usage:
    agent = ToolReflectionAgent()
    corrected_call = await agent.correct_tool_call(
        original_call=tool_call,
        error=result.error,
        error_type=result.error_type
    )
"""

from __future__ import annotations

import logging
import json
from dataclasses import dataclass
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Tool call representation."""
    name: str
    arguments: Dict[str, Any]
    tool_call_id: Optional[str] = None


@dataclass
class CorrectionResult:
    """Result of tool call correction."""
    corrected_call: ToolCall
    correction_reasoning: str
    confidence: float  # 0-1
    changes_made: Dict[str, Any]  # parameter -> change description


class ToolReflectionAgent:
    """
    Tool reflection agent for self-correction.

    Analyzes tool execution failures and generates corrected parameters.
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self._correction_history = []

    async def correct_tool_call(
        self,
        original_call: ToolCall,
        error: str,
        error_type: str,
        tool_schema: Optional[Dict] = None,
    ) -> CorrectionResult:
        """
        Correct a failed tool call.

        Args:
            original_call: Original tool call that failed
            error: Error message
            error_type: Error type (validation_error, execution_error, etc.)
            tool_schema: Tool's JSON schema (optional)

        Returns:
            Corrected tool call
        """
        logger.info(f"Reflecting on failed tool call: {original_call.name}")

        # Build reflection prompt
        prompt = self._build_reflection_prompt(
            original_call,
            error,
            error_type,
            tool_schema
        )

        # Call LLM for correction
        try:
            from app.infra.llm import UnifiedLLMClient, LLMProvider

            if self.llm_client is None:
                self.llm_client = UnifiedLLMClient.get_instance()

            response = await self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                provider=LLMProvider.OPENAI,
                model="gpt-4o-mini",
                temperature=0.1,  # Low temperature for precise correction
            )

            # Parse correction
            correction = self._parse_correction(response.content)

            # Create corrected call
            corrected_call = ToolCall(
                name=original_call.name,
                arguments=correction["corrected_arguments"],
                tool_call_id=original_call.tool_call_id,
            )

            result = CorrectionResult(
                corrected_call=corrected_call,
                correction_reasoning=correction["reasoning"],
                confidence=correction["confidence"],
                changes_made=correction["changes"],
            )

            # Record correction history
            self._correction_history.append({
                "original": original_call,
                "corrected": corrected_call,
                "error": error,
                "timestamp": __import__('datetime').datetime.now().isoformat(),
            })

            logger.info(
                f"Generated correction with confidence {result.confidence:.2f}"
            )

            return result

        except Exception as e:
            logger.error(f"Reflection failed: {e}")
            # Return original call as fallback
            return CorrectionResult(
                corrected_call=original_call,
                correction_reasoning=f"Reflection failed: {e}",
                confidence=0.0,
                changes_made={},
            )

    def _build_reflection_prompt(
        self,
        original_call: ToolCall,
        error: str,
        error_type: str,
        tool_schema: Optional[Dict],
    ) -> str:
        """Build reflection prompt for LLM."""
        schema_text = ""
        if tool_schema:
            schema_text = f"\n\nTool Schema:\n{json.dumps(tool_schema, indent=2)}"

        prompt = f"""
You are a tool execution expert. A tool call failed due to parameter validation error.

Tool Name: {original_call.name}
Original Arguments: {json.dumps(original_call.arguments, indent=2)}

Error Type: {error_type}
Error Message: {error}
{schema_text}

Please analyze the error and provide corrected arguments.

Your response should be in JSON format:
{{
    "reasoning": "Explanation of what went wrong and how to fix it",
    "corrected_arguments": {{
        "param1": "corrected_value1",
        "param2": "corrected_value2"
    }},
    "changes": {{
        "param1": "Changed from X to Y because...",
        "param2": "Added missing parameter because..."
    }},
    "confidence": 0.95
}}

Focus on:
1. Type mismatches (e.g., string instead of integer)
2. Missing required parameters
3. Invalid enum values
4. Format issues (e.g., date format)

Provide ONLY the JSON response, no additional text.
"""
        return prompt

    def _parse_correction(self, response_content: str) -> Dict:
        """Parse correction from LLM response."""
        try:
            # Try to parse as JSON
            correction = json.loads(response_content)

            # Validate required fields
            required_fields = ["reasoning", "corrected_arguments", "changes", "confidence"]
            for field in required_fields:
                if field not in correction:
                    raise ValueError(f"Missing required field: {field}")

            return correction

        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError("Failed to parse correction response")

    def get_correction_history(self) -> list:
        """Get correction history for analysis."""
        return self._correction_history.copy()

    def get_correction_stats(self) -> Dict:
        """Get correction statistics."""
        if not self._correction_history:
            return {
                "total_corrections": 0,
                "success_rate": 0.0,
            }

        total = len(self._correction_history)

        return {
            "total_corrections": total,
            "most_common_errors": self._get_common_errors(),
            "most_corrected_tools": self._get_common_tools(),
        }

    def _get_common_errors(self) -> Dict[str, int]:
        """Get most common error types."""
        errors = {}
        for record in self._correction_history:
            error = record["error"]
            errors[error] = errors.get(error, 0) + 1
        return dict(sorted(errors.items(), key=lambda x: x[1], reverse=True)[:5])

    def _get_common_tools(self) -> Dict[str, int]:
        """Get most frequently corrected tools."""
        tools = {}
        for record in self._correction_history:
            tool_name = record["original"].name
            tools[tool_name] = tools.get(tool_name, 0) + 1
        return dict(sorted(tools.items(), key=lambda x: x[1], reverse=True)[:5])
