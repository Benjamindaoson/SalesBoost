"""
Tool Reflection and Self-Correction Module

This module provides automatic error correction for tool calls using LLM-based reflection.
When a tool call fails due to validation errors, the reflection agent analyzes the error
and attempts to correct the parameters automatically.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ToolCallCorrection(BaseModel):
    """Result of tool call correction"""

    corrected_payload: Dict[str, Any] = Field(
        description="Corrected tool parameters"
    )
    correction_reasoning: str = Field(
        description="Explanation of what was corrected and why"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the correction (0-1)"
    )


class ReflectionAgent:
    """
    Reflection agent for automatic tool call correction.

    This agent analyzes tool execution errors and attempts to correct
    the parameters automatically using LLM-based reasoning.

    Features:
    - Automatic parameter correction for validation errors
    - Confidence scoring for corrections
    - Detailed reasoning for transparency
    - Support for multiple correction attempts
    """

    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize reflection agent.

        Args:
            llm_client: Optional LLM client for advanced corrections.
                       If None, uses rule-based corrections only.
        """
        self.llm_client = llm_client
        self._correction_rules = self._build_correction_rules()

    def _build_correction_rules(self) -> Dict[str, Any]:
        """Build rule-based correction patterns"""
        return {
            "missing_required_field": self._fix_missing_field,
            "invalid_type": self._fix_type_error,
            "value_error": self._fix_value_error,
            "extra_forbidden": self._fix_extra_fields,
        }

    async def correct_tool_call(
        self,
        tool_name: str,
        original_payload: Dict[str, Any],
        error_message: str,
        tool_schema: Optional[Dict[str, Any]] = None,
        max_confidence: float = 0.9
    ) -> Optional[ToolCallCorrection]:
        """
        Attempt to correct a failed tool call.

        Args:
            tool_name: Name of the tool that failed
            original_payload: Original parameters that caused the error
            error_message: Error message from the failed execution
            tool_schema: Optional tool schema for validation
            max_confidence: Maximum confidence threshold for corrections

        Returns:
            ToolCallCorrection if correction is possible, None otherwise
        """
        logger.info(f"Attempting to correct tool call: {tool_name}")
        logger.debug(f"Original payload: {original_payload}")
        logger.debug(f"Error: {error_message}")

        # Try rule-based correction first (fast and reliable)
        correction = self._apply_rule_based_correction(
            tool_name,
            original_payload,
            error_message,
            tool_schema
        )

        if correction and correction.confidence >= max_confidence:
            logger.info(
                f"Rule-based correction successful (confidence: {correction.confidence:.2f})"
            )
            return correction

        # Fall back to LLM-based correction if available
        if self.llm_client:
            llm_correction = await self._apply_llm_correction(
                tool_name,
                original_payload,
                error_message,
                tool_schema
            )

            if llm_correction and llm_correction.confidence > (correction.confidence if correction else 0):
                logger.info(
                    f"LLM-based correction successful (confidence: {llm_correction.confidence:.2f})"
                )
                return llm_correction

        # Return best correction found
        if correction:
            logger.info(
                f"Returning rule-based correction (confidence: {correction.confidence:.2f})"
            )
        else:
            logger.warning(f"No correction found for tool call: {tool_name}")

        return correction

    def _apply_rule_based_correction(
        self,
        tool_name: str,
        payload: Dict[str, Any],
        error_message: str,
        tool_schema: Optional[Dict[str, Any]]
    ) -> Optional[ToolCallCorrection]:
        """Apply rule-based corrections"""

        error_lower = error_message.lower()

        # Detect error type and apply appropriate rule
        for error_pattern, correction_func in self._correction_rules.items():
            if error_pattern.replace("_", " ") in error_lower:
                try:
                    return correction_func(payload, error_message, tool_schema)
                except Exception as e:
                    logger.warning(f"Rule-based correction failed: {e}")
                    continue

        return None

    def _fix_missing_field(
        self,
        payload: Dict[str, Any],
        error_message: str,
        tool_schema: Optional[Dict[str, Any]]
    ) -> Optional[ToolCallCorrection]:
        """Fix missing required field errors"""

        # Extract field name from error message
        # Example: "Field required [type=missing, input_value={'query': 'test'}]"
        import re

        # Try to find field name in error message
        field_match = re.search(r"field[s]?\s+['\"]?(\w+)['\"]?\s+(?:is\s+)?required", error_message, re.IGNORECASE)
        if not field_match:
            return None

        field_name = field_match.group(1)

        # Try to infer default value from schema
        default_value = None
        if tool_schema and "parameters" in tool_schema:
            properties = tool_schema["parameters"].get("properties", {})
            if field_name in properties:
                field_info = properties[field_name]
                field_type = field_info.get("type", "string")

                # Provide sensible defaults based on type
                if field_type == "string":
                    default_value = ""
                elif field_type == "integer":
                    default_value = 0
                elif field_type == "number":
                    default_value = 0.0
                elif field_type == "boolean":
                    default_value = False
                elif field_type == "array":
                    default_value = []
                elif field_type == "object":
                    default_value = {}

        if default_value is None:
            # No schema available, use generic default
            default_value = ""

        corrected_payload = payload.copy()
        corrected_payload[field_name] = default_value

        return ToolCallCorrection(
            corrected_payload=corrected_payload,
            correction_reasoning=f"Added missing required field '{field_name}' with default value",
            confidence=0.7  # Medium confidence for default values
        )

    def _fix_type_error(
        self,
        payload: Dict[str, Any],
        error_message: str,
        tool_schema: Optional[Dict[str, Any]]
    ) -> Optional[ToolCallCorrection]:
        """Fix type mismatch errors"""

        import re

        # Extract field name and expected type
        # Example: "Input should be a valid integer [type=int_type, input_value='123']"
        type_match = re.search(
            r"(?:field\s+)?['\"]?(\w+)['\"]?.*?should be (?:a valid )?(\w+)",
            error_message,
            re.IGNORECASE
        )

        if not type_match:
            return None

        field_name = type_match.group(1)
        expected_type = type_match.group(2).lower()

        if field_name not in payload:
            return None

        current_value = payload[field_name]
        corrected_value = None

        try:
            # Attempt type conversion
            if expected_type in ["int", "integer"]:
                corrected_value = int(current_value)
            elif expected_type in ["float", "number"]:
                corrected_value = float(current_value)
            elif expected_type in ["str", "string"]:
                corrected_value = str(current_value)
            elif expected_type in ["bool", "boolean"]:
                if isinstance(current_value, str):
                    corrected_value = current_value.lower() in ["true", "1", "yes"]
                else:
                    corrected_value = bool(current_value)
            elif expected_type == "list":
                if not isinstance(current_value, list):
                    corrected_value = [current_value]
            elif expected_type == "dict":
                if isinstance(current_value, str):
                    import json
                    corrected_value = json.loads(current_value)
        except (ValueError, TypeError) as e:
            logger.warning(f"Type conversion failed: {e}")
            return None

        if corrected_value is None:
            return None

        corrected_payload = payload.copy()
        corrected_payload[field_name] = corrected_value

        return ToolCallCorrection(
            corrected_payload=corrected_payload,
            correction_reasoning=f"Converted field '{field_name}' from {type(current_value).__name__} to {expected_type}",
            confidence=0.85  # High confidence for type conversions
        )

    def _fix_value_error(
        self,
        payload: Dict[str, Any],
        error_message: str,
        tool_schema: Optional[Dict[str, Any]]
    ) -> Optional[ToolCallCorrection]:
        """Fix value constraint errors"""

        import re

        # Handle common value errors
        # Example: "Input should be greater than 0"

        if "greater than" in error_message.lower():
            # Extract field and minimum value
            match = re.search(r"['\"]?(\w+)['\"]?.*?greater than (\d+)", error_message, re.IGNORECASE)
            if match:
                field_name = match.group(1)
                min_value = int(match.group(2))

                if field_name in payload:
                    corrected_payload = payload.copy()
                    corrected_payload[field_name] = min_value + 1

                    return ToolCallCorrection(
                        corrected_payload=corrected_payload,
                        correction_reasoning=f"Adjusted '{field_name}' to meet minimum constraint (> {min_value})",
                        confidence=0.8
                    )

        elif "less than" in error_message.lower():
            # Extract field and maximum value
            match = re.search(r"['\"]?(\w+)['\"]?.*?less than (\d+)", error_message, re.IGNORECASE)
            if match:
                field_name = match.group(1)
                max_value = int(match.group(2))

                if field_name in payload:
                    corrected_payload = payload.copy()
                    corrected_payload[field_name] = max_value - 1

                    return ToolCallCorrection(
                        corrected_payload=corrected_payload,
                        correction_reasoning=f"Adjusted '{field_name}' to meet maximum constraint (< {max_value})",
                        confidence=0.8
                    )

        return None

    def _fix_extra_fields(
        self,
        payload: Dict[str, Any],
        error_message: str,
        tool_schema: Optional[Dict[str, Any]]
    ) -> Optional[ToolCallCorrection]:
        """Fix extra forbidden fields errors"""

        import re

        # Extract extra field names
        # Example: "Extra inputs are not permitted [type=extra_forbidden, input={'extra_field': 'value'}]"

        if not tool_schema or "parameters" not in tool_schema:
            return None

        allowed_fields = set(tool_schema["parameters"].get("properties", {}).keys())
        current_fields = set(payload.keys())
        extra_fields = current_fields - allowed_fields

        if not extra_fields:
            # Try to extract from error message
            extra_match = re.findall(r"['\"](\w+)['\"]", error_message)
            if extra_match:
                extra_fields = set(extra_match) & current_fields

        if not extra_fields:
            return None

        # Remove extra fields
        corrected_payload = {k: v for k, v in payload.items() if k not in extra_fields}

        return ToolCallCorrection(
            corrected_payload=corrected_payload,
            correction_reasoning=f"Removed extra forbidden fields: {', '.join(extra_fields)}",
            confidence=0.95  # Very high confidence for removing extra fields
        )

    async def _apply_llm_correction(
        self,
        tool_name: str,
        payload: Dict[str, Any],
        error_message: str,
        tool_schema: Optional[Dict[str, Any]]
    ) -> Optional[ToolCallCorrection]:
        """Apply LLM-based correction (placeholder for future implementation)"""

        # TODO: Implement LLM-based correction using the LLM client
        # This would involve:
        # 1. Constructing a prompt with tool schema, error, and original payload
        # 2. Asking LLM to suggest corrections
        # 3. Parsing and validating the LLM response
        # 4. Returning ToolCallCorrection with appropriate confidence

        logger.debug("LLM-based correction not yet implemented")
        return None
