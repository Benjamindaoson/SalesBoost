"""
Enterprise AI Memory System - Core Module

This module provides the foundational abstractions for the three-tier
memory architecture:
- Short-term (Redis): Millisecond access, session state
- Medium-term (Vector DB): Semantic retrieval, user preferences
- Long-term (Graph DB): Knowledge graph, relationship reasoning
"""

from .schemas import (
    MemoryTier,
    MemoryType,
    MemoryPriority,
    ConflictResolutionStrategy,
    VectorClock,
    MemoryMetadata,
    MemoryEntry,
    MemoryRelation,
    UserProfile,
    ProfileUpdate,
    MemoryQuery,
    MemoryQueryResult,
)

from .interfaces import (
    MemoryStore,
    ShortTermMemoryStore,
    MediumTermMemoryStore,
    LongTermMemoryStore,
    ProfileStore,
    SyncEngine,
)

from .exceptions import (
    MemorySystemError,
    MemoryNotFoundError,
    MemoryConflictError,
    MemoryCapacityError,
    MemorySyncError,
    MemorySerializationError,
    MemoryAccessDeniedError,
    MemoryValidationError,
)

__all__ = [
    # Enums
    "MemoryTier",
    "MemoryType",
    "MemoryPriority",
    "ConflictResolutionStrategy",
    # Data Classes
    "VectorClock",
    "MemoryMetadata",
    "MemoryEntry",
    "MemoryRelation",
    "UserProfile",
    "ProfileUpdate",
    "MemoryQuery",
    "MemoryQueryResult",
    # Interfaces
    "MemoryStore",
    "ShortTermMemoryStore",
    "MediumTermMemoryStore",
    "LongTermMemoryStore",
    "ProfileStore",
    "SyncEngine",
    # Exceptions
    "MemorySystemError",
    "MemoryNotFoundError",
    "MemoryConflictError",
    "MemoryCapacityError",
    "MemorySyncError",
    "MemorySerializationError",
    "MemoryAccessDeniedError",
    "MemoryValidationError",
]
