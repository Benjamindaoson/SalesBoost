"""
Data Masking and Privacy Protection Module

This module provides automatic data masking for sensitive information
in tool results, ensuring compliance with privacy regulations and
protecting user data.

Features:
- Automatic detection of sensitive fields
- Configurable masking strategies
- Support for multiple data types (phone, email, ID, etc.)
- Customizable masking rules per tool
- Audit logging for masked data
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class MaskingStrategy:
    """Base class for masking strategies"""

    def mask(self, value: str) -> str:
        """
        Mask a value.

        Args:
            value: Original value to mask

        Returns:
            Masked value
        """
        raise NotImplementedError


class PartialMaskingStrategy(MaskingStrategy):
    """
    Partial masking strategy that shows first and last N characters.

    Example: "13800138000" -> "138****8000"
    """

    def __init__(self, prefix_len: int = 3, suffix_len: int = 4, mask_char: str = "*"):
        """
        Initialize partial masking strategy.

        Args:
            prefix_len: Number of characters to show at start
            suffix_len: Number of characters to show at end
            mask_char: Character to use for masking
        """
        self.prefix_len = prefix_len
        self.suffix_len = suffix_len
        self.mask_char = mask_char

    def mask(self, value: str) -> str:
        """Mask value with partial visibility"""
        if not value:
            return value

        value_str = str(value)
        length = len(value_str)

        # If value is too short, mask completely
        if length <= self.prefix_len + self.suffix_len:
            return self.mask_char * length

        # Show prefix and suffix, mask middle
        prefix = value_str[:self.prefix_len]
        suffix = value_str[-self.suffix_len:]
        mask_length = length - self.prefix_len - self.suffix_len

        return f"{prefix}{self.mask_char * mask_length}{suffix}"


class FullMaskingStrategy(MaskingStrategy):
    """
    Full masking strategy that replaces entire value.

    Example: "secret123" -> "***"
    """

    def __init__(self, mask_char: str = "*", mask_length: int = 3):
        """
        Initialize full masking strategy.

        Args:
            mask_char: Character to use for masking
            mask_length: Length of masked output
        """
        self.mask_char = mask_char
        self.mask_length = mask_length

    def mask(self, value: str) -> str:
        """Mask value completely"""
        return self.mask_char * self.mask_length


class EmailMaskingStrategy(MaskingStrategy):
    """
    Email masking strategy that preserves domain.

    Example: "user@example.com" -> "u***@example.com"
    """

    def __init__(self, mask_char: str = "*"):
        """
        Initialize email masking strategy.

        Args:
            mask_char: Character to use for masking
        """
        self.mask_char = mask_char

    def mask(self, value: str) -> str:
        """Mask email address"""
        if not value or "@" not in value:
            return value

        local, domain = value.split("@", 1)

        if len(local) <= 1:
            masked_local = self.mask_char
        else:
            masked_local = local[0] + self.mask_char * (len(local) - 1)

        return f"{masked_local}@{domain}"


class DataMasker:
    """
    Data masking engine for automatic sensitive data protection.

    This class provides automatic detection and masking of sensitive
    information in tool results.
    """

    # Default sensitive field patterns
    DEFAULT_SENSITIVE_PATTERNS = {
        "phone": r"^(phone|mobile|tel|telephone|contact_number)$",
        "email": r"^(email|email_address|mail)$",
        "id_card": r"^(id_card|identity|id_number|national_id)$",
        "password": r"^(password|passwd|pwd|secret)$",
        "token": r"^(token|access_token|api_key|secret_key)$",
        "address": r"^(address|home_address|location)$",
        "credit_card": r"^(credit_card|card_number|cc_number)$",
    }

    # Default masking strategies per field type
    DEFAULT_STRATEGIES = {
        "phone": PartialMaskingStrategy(prefix_len=3, suffix_len=4),
        "email": EmailMaskingStrategy(),
        "id_card": PartialMaskingStrategy(prefix_len=4, suffix_len=4),
        "password": FullMaskingStrategy(),
        "token": FullMaskingStrategy(),
        "address": PartialMaskingStrategy(prefix_len=5, suffix_len=0),
        "credit_card": PartialMaskingStrategy(prefix_len=4, suffix_len=4),
    }

    def __init__(
        self,
        sensitive_patterns: Optional[Dict[str, str]] = None,
        strategies: Optional[Dict[str, MaskingStrategy]] = None,
        enabled: bool = True,
    ):
        """
        Initialize data masker.

        Args:
            sensitive_patterns: Custom sensitive field patterns
            strategies: Custom masking strategies
            enabled: Enable/disable masking
        """
        self.sensitive_patterns = sensitive_patterns or self.DEFAULT_SENSITIVE_PATTERNS
        self.strategies = strategies or self.DEFAULT_STRATEGIES
        self.enabled = enabled

        # Compile regex patterns
        self._compiled_patterns = {
            field_type: re.compile(pattern, re.IGNORECASE)
            for field_type, pattern in self.sensitive_patterns.items()
        }

    def mask_result(
        self,
        result: Any,
        additional_fields: Optional[Set[str]] = None,
        skip_fields: Optional[Set[str]] = None,
    ) -> Any:
        """
        Mask sensitive data in tool result.

        Args:
            result: Tool result to mask
            additional_fields: Additional field names to mask
            skip_fields: Field names to skip masking

        Returns:
            Masked result
        """
        if not self.enabled:
            return result

        additional_fields = additional_fields or set()
        skip_fields = skip_fields or set()

        if isinstance(result, dict):
            return self._mask_dict(result, additional_fields, skip_fields)
        elif isinstance(result, list):
            return [self.mask_result(item, additional_fields, skip_fields) for item in result]
        else:
            return result

    def _mask_dict(
        self,
        data: Dict[str, Any],
        additional_fields: Set[str],
        skip_fields: Set[str],
    ) -> Dict[str, Any]:
        """Mask sensitive fields in dictionary"""
        masked_data = {}

        for key, value in data.items():
            # Skip if in skip list
            if key in skip_fields:
                masked_data[key] = value
                continue

            # Check if field should be masked
            field_type = self._detect_sensitive_field(key, additional_fields)

            if field_type:
                # Mask the value
                masked_value = self._mask_value(value, field_type)
                masked_data[key] = masked_value

                # Log masking action
                logger.debug(f"Masked field '{key}' (type: {field_type})")
            elif isinstance(value, dict):
                # Recursively mask nested dicts
                masked_data[key] = self._mask_dict(value, additional_fields, skip_fields)
            elif isinstance(value, list):
                # Recursively mask lists
                masked_data[key] = [
                    self.mask_result(item, additional_fields, skip_fields)
                    for item in value
                ]
            else:
                # Keep value as-is
                masked_data[key] = value

        return masked_data

    def _detect_sensitive_field(
        self,
        field_name: str,
        additional_fields: Set[str],
    ) -> Optional[str]:
        """
        Detect if field is sensitive.

        Args:
            field_name: Field name to check
            additional_fields: Additional sensitive field names

        Returns:
            Field type if sensitive, None otherwise
        """
        # Check additional fields first
        if field_name in additional_fields:
            return "default"

        # Check against patterns
        for field_type, pattern in self._compiled_patterns.items():
            if pattern.match(field_name):
                return field_type

        return None

    def _mask_value(self, value: Any, field_type: str) -> Any:
        """
        Mask a value using appropriate strategy.

        Args:
            value: Value to mask
            field_type: Type of sensitive field

        Returns:
            Masked value
        """
        if value is None:
            return None

        # Get masking strategy
        strategy = self.strategies.get(field_type)
        if not strategy:
            # Use default strategy
            strategy = PartialMaskingStrategy()

        # Convert to string and mask
        value_str = str(value)
        masked_str = strategy.mask(value_str)

        return masked_str


# Global data masker instance
_masker = DataMasker()


def get_data_masker() -> DataMasker:
    """Get global data masker instance"""
    return _masker


def configure_data_masker(
    sensitive_patterns: Optional[Dict[str, str]] = None,
    strategies: Optional[Dict[str, MaskingStrategy]] = None,
    enabled: bool = True,
) -> None:
    """
    Configure global data masker.

    Args:
        sensitive_patterns: Custom sensitive field patterns
        strategies: Custom masking strategies
        enabled: Enable/disable masking
    """
    global _masker
    _masker = DataMasker(
        sensitive_patterns=sensitive_patterns,
        strategies=strategies,
        enabled=enabled,
    )
