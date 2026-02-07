"""
Enterprise AI Memory System - Core Data Models

Unified data models supporting three-tier storage architecture:
- Short-term (Redis): Session state, real-time context
- Medium-term (Vector DB): Semantic retrieval, user preferences
- Long-term (Graph DB): Knowledge graph, relationship reasoning

Designed for:
- 10M+ concurrent users
- 99.99% data consistency
- GDPR compliance
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import UUID, uuid4

if TYPE_CHECKING:
    pass


class MemoryTier(str, Enum):
    """Memory tier enumeration"""
    SHORT_TERM = "short_term"    # Redis - millisecond access
    MEDIUM_TERM = "medium_term"  # Vector DB - semantic retrieval
    LONG_TERM = "long_term"      # Graph DB - relationship reasoning


class MemoryType(str, Enum):
    """Memory type enumeration"""
    EPISODIC = "episodic"        # Episodic memory - specific events
    SEMANTIC = "semantic"        # Semantic memory - conceptual knowledge
    PROCEDURAL = "procedural"    # Procedural memory - skill patterns
    CONTEXTUAL = "contextual"    # Contextual memory - session state


class MemoryPriority(int, Enum):
    """Memory priority levels"""
    CRITICAL = 100   # Critical memory - never forget
    HIGH = 75        # High priority - long-term retention
    MEDIUM = 50      # Medium priority - normal decay
    LOW = 25         # Low priority - fast decay
    VOLATILE = 0     # Volatile memory - delete after session


class ConflictResolutionStrategy(str, Enum):
    """Conflict resolution strategies for distributed memory"""
    LAST_WRITE_WINS = "lww"           # Last write wins (timestamp-based)
    FIRST_WRITE_WINS = "fww"          # First write wins
    MERGE = "merge"                   # Intelligent merge
    MANUAL = "manual"                 # Mark for manual review
    VERSION_VECTOR = "version_vector" # Vector clock based


@dataclass
class VectorClock:
    """
    Vector Clock for distributed version control.

    Used for detecting causality and conflicts in distributed memory systems.
    Each node maintains its own counter, allowing detection of concurrent writes.
    """
    node_id: str
    counters: Dict[str, int] = field(default_factory=dict)

    def increment(self) -> None:
        """Increment this node's counter"""
        self.counters[self.node_id] = self.counters.get(self.node_id, 0) + 1

    def merge(self, other: "VectorClock") -> "VectorClock":
        """Merge with another vector clock, taking max of each counter"""
        merged = VectorClock(node_id=self.node_id)
        all_nodes = set(self.counters.keys()) | set(other.counters.keys())
        for node in all_nodes:
            merged.counters[node] = max(
                self.counters.get(node, 0),
                other.counters.get(node, 0)
            )
        return merged

    def happens_before(self, other: "VectorClock") -> bool:
        """
        Check if this clock happens-before another clock.

        Returns True if this clock is strictly less than the other,
        indicating a causal relationship.
        """
        all_nodes = set(self.counters.keys()) | set(other.counters.keys())

        all_less_or_equal = all(
            self.counters.get(node, 0) <= other.counters.get(node, 0)
            for node in all_nodes
        )
        any_less = any(
            self.counters.get(node, 0) < other.counters.get(node, 0)
            for node in all_nodes
        )
        return all_less_or_equal and any_less

    def is_concurrent_with(self, other: "VectorClock") -> bool:
        """Check if this clock is concurrent with another (no causal relationship)"""
        return not self.happens_before(other) and not other.happens_before(self)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "node_id": self.node_id,
            "counters": self.counters.copy()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VectorClock":
        """Deserialize from dictionary"""
        return cls(
            node_id=data["node_id"],
            counters=data.get("counters", {})
        )


@dataclass
class MemoryMetadata:
    """
    Memory entry metadata for lifecycle and relevance management.

    Tracks access patterns, decay, importance, and version control.
    """
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    decay_factor: float = 1.0       # Decay factor [0, 1]
    importance_score: float = 0.5   # Importance score [0, 1]
    emotional_valence: float = 0.0  # Emotional polarity [-1, 1]
    confidence: float = 1.0         # Confidence level [0, 1]
    source: str = "user_interaction"
    version: int = 1
    vector_clock: Optional[VectorClock] = None
    checksum: Optional[str] = None

    def calculate_relevance(self, recency_weight: float = 0.4) -> float:
        """
        Calculate composite relevance score.

        Combines recency, frequency, importance, decay, and confidence.

        Args:
            recency_weight: Weight for recency vs other factors [0, 1]

        Returns:
            Relevance score [0, 1]
        """
        now = datetime.utcnow()
        age_hours = (now - self.accessed_at).total_seconds() / 3600
        recency_score = 1.0 / (1.0 + age_hours * 0.1)

        frequency_score = min(1.0, self.access_count / 100)

        return (
            recency_weight * recency_score +
            (1 - recency_weight) * 0.5 * (self.importance_score + frequency_score)
        ) * self.decay_factor * self.confidence

    def record_access(self) -> None:
        """Record an access event"""
        self.accessed_at = datetime.utcnow()
        self.access_count += 1

    def apply_decay(self, decay_rate: float = 0.01) -> None:
        """Apply time-based decay"""
        age_hours = (datetime.utcnow() - self.accessed_at).total_seconds() / 3600
        self.decay_factor = max(0.1, self.decay_factor - decay_rate * age_hours)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "access_count": self.access_count,
            "decay_factor": self.decay_factor,
            "importance_score": self.importance_score,
            "emotional_valence": self.emotional_valence,
            "confidence": self.confidence,
            "source": self.source,
            "version": self.version,
            "vector_clock": self.vector_clock.to_dict() if self.vector_clock else None,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryMetadata":
        """Deserialize from dictionary"""
        vector_clock = None
        if data.get("vector_clock"):
            vector_clock = VectorClock.from_dict(data["vector_clock"])

        return cls(
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.utcnow()),
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data.get("updated_at"), str) else data.get("updated_at", datetime.utcnow()),
            accessed_at=datetime.fromisoformat(data["accessed_at"]) if isinstance(data.get("accessed_at"), str) else data.get("accessed_at", datetime.utcnow()),
            access_count=data.get("access_count", 0),
            decay_factor=data.get("decay_factor", 1.0),
            importance_score=data.get("importance_score", 0.5),
            emotional_valence=data.get("emotional_valence", 0.0),
            confidence=data.get("confidence", 1.0),
            source=data.get("source", "user_interaction"),
            version=data.get("version", 1),
            vector_clock=vector_clock,
            checksum=data.get("checksum"),
        )


@dataclass
class MemoryRelation:
    """
    Memory relationship for knowledge graph.

    Represents directed edges between memory nodes with typed relationships.
    """
    id: UUID = field(default_factory=uuid4)
    source_id: UUID = field(default_factory=uuid4)
    target_id: UUID = field(default_factory=uuid4)
    relation_type: str = ""          # e.g., "related_to", "caused_by", "part_of"
    weight: float = 1.0              # Relationship strength [0, 1]
    bidirectional: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "id": str(self.id),
            "source_id": str(self.source_id),
            "target_id": str(self.target_id),
            "relation_type": self.relation_type,
            "weight": self.weight,
            "bidirectional": self.bidirectional,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryRelation":
        """Deserialize from dictionary"""
        return cls(
            id=UUID(data["id"]) if isinstance(data.get("id"), str) else data.get("id", uuid4()),
            source_id=UUID(data["source_id"]) if isinstance(data.get("source_id"), str) else data.get("source_id", uuid4()),
            target_id=UUID(data["target_id"]) if isinstance(data.get("target_id"), str) else data.get("target_id", uuid4()),
            relation_type=data.get("relation_type", ""),
            weight=data.get("weight", 1.0),
            bidirectional=data.get("bidirectional", False),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.utcnow()),
        )


@dataclass
class MemoryEntry:
    """
    Unified memory entry for all storage tiers.

    Represents a single piece of memory that can be stored in any tier,
    with full support for semantic search, graph relationships, and TTL.
    """
    id: UUID = field(default_factory=uuid4)
    user_id: str = ""
    tenant_id: str = ""
    session_id: Optional[str] = None

    # Memory content
    content: str = ""
    content_type: str = "text"
    embedding: Optional[List[float]] = None

    # Classification
    tier: MemoryTier = MemoryTier.SHORT_TERM
    memory_type: MemoryType = MemoryType.CONTEXTUAL
    priority: MemoryPriority = MemoryPriority.MEDIUM

    # Semantic tags
    tags: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)

    # Relationships (for graph database)
    relations: List[MemoryRelation] = field(default_factory=list)

    # Metadata
    metadata: MemoryMetadata = field(default_factory=MemoryMetadata)
    extra: Dict[str, Any] = field(default_factory=dict)

    # TTL management
    ttl_seconds: Optional[int] = None
    expires_at: Optional[datetime] = None

    def compute_checksum(self) -> str:
        """Compute content checksum for integrity verification"""
        content_hash = hashlib.sha256(
            json.dumps({
                "content": self.content,
                "tags": sorted(self.tags),
                "entities": sorted(self.entities),
            }, sort_keys=True).encode()
        ).hexdigest()
        self.metadata.checksum = content_hash
        return content_hash

    def should_promote(self) -> bool:
        """Determine if memory should be promoted to higher tier"""
        if self.tier == MemoryTier.LONG_TERM:
            return False
        return (
            self.metadata.access_count >= 5 and
            self.metadata.importance_score >= 0.7 and
            self.priority.value >= MemoryPriority.HIGH.value
        )

    def should_demote(self) -> bool:
        """Determine if memory should be demoted to lower tier"""
        if self.tier == MemoryTier.SHORT_TERM:
            return False
        return (
            self.metadata.decay_factor < 0.3 and
            self.metadata.calculate_relevance() < 0.2
        )

    def is_expired(self) -> bool:
        """Check if memory has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def set_ttl(self, seconds: int) -> None:
        """Set TTL in seconds"""
        self.ttl_seconds = seconds
        self.expires_at = datetime.utcnow().replace(microsecond=0)
        from datetime import timedelta
        self.expires_at += timedelta(seconds=seconds)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "session_id": self.session_id,
            "content": self.content,
            "content_type": self.content_type,
            "embedding": self.embedding,
            "tier": self.tier.value,
            "memory_type": self.memory_type.value,
            "priority": self.priority.value,
            "tags": self.tags,
            "entities": self.entities,
            "relations": [r.to_dict() for r in self.relations],
            "metadata": self.metadata.to_dict(),
            "extra": self.extra,
            "ttl_seconds": self.ttl_seconds,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """Deserialize from dictionary"""
        relations = [
            MemoryRelation.from_dict(r) for r in data.get("relations", [])
        ]

        expires_at = None
        if data.get("expires_at"):
            expires_at = datetime.fromisoformat(data["expires_at"]) if isinstance(data["expires_at"], str) else data["expires_at"]

        return cls(
            id=UUID(data["id"]) if isinstance(data.get("id"), str) else data.get("id", uuid4()),
            user_id=data.get("user_id", ""),
            tenant_id=data.get("tenant_id", ""),
            session_id=data.get("session_id"),
            content=data.get("content", ""),
            content_type=data.get("content_type", "text"),
            embedding=data.get("embedding"),
            tier=MemoryTier(data.get("tier", "short_term")),
            memory_type=MemoryType(data.get("memory_type", "contextual")),
            priority=MemoryPriority(data.get("priority", 50)),
            tags=data.get("tags", []),
            entities=data.get("entities", []),
            relations=relations,
            metadata=MemoryMetadata.from_dict(data.get("metadata", {})),
            extra=data.get("extra", {}),
            ttl_seconds=data.get("ttl_seconds"),
            expires_at=expires_at,
        )


@dataclass
class UserProfile:
    """
    User profile model for behavioral analysis and personalization.

    Tracks user preferences, behaviors, skills, and emotional states
    with support for incremental updates and GDPR compliance.
    """
    user_id: str = ""
    tenant_id: str = ""

    # Basic profile
    demographics: Dict[str, Any] = field(default_factory=dict)

    # Behavioral characteristics
    behavior_patterns: Dict[str, float] = field(default_factory=dict)
    interaction_history: List[Dict[str, Any]] = field(default_factory=list)

    # Preference model
    preferences: Dict[str, float] = field(default_factory=dict)
    topics_of_interest: Dict[str, float] = field(default_factory=dict)

    # Skill assessment
    skill_levels: Dict[str, float] = field(default_factory=dict)
    learning_progress: Dict[str, float] = field(default_factory=dict)

    # Emotional state
    emotional_baseline: Dict[str, float] = field(default_factory=dict)
    recent_sentiment: float = 0.0

    # Meta information
    profile_version: int = 1
    last_updated: datetime = field(default_factory=datetime.utcnow)
    confidence_scores: Dict[str, float] = field(default_factory=dict)

    # Privacy settings (GDPR)
    privacy_settings: Dict[str, bool] = field(default_factory=dict)
    consent_flags: Dict[str, bool] = field(default_factory=dict)
    data_retention_days: int = 90

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "demographics": self.demographics,
            "behavior_patterns": self.behavior_patterns,
            "interaction_history": self.interaction_history[-100:],  # Limit history
            "preferences": self.preferences,
            "topics_of_interest": self.topics_of_interest,
            "skill_levels": self.skill_levels,
            "learning_progress": self.learning_progress,
            "emotional_baseline": self.emotional_baseline,
            "recent_sentiment": self.recent_sentiment,
            "profile_version": self.profile_version,
            "last_updated": self.last_updated.isoformat(),
            "confidence_scores": self.confidence_scores,
            "privacy_settings": self.privacy_settings,
            "consent_flags": self.consent_flags,
            "data_retention_days": self.data_retention_days,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        """Deserialize from dictionary"""
        last_updated = data.get("last_updated", datetime.utcnow())
        if isinstance(last_updated, str):
            last_updated = datetime.fromisoformat(last_updated)

        return cls(
            user_id=data.get("user_id", ""),
            tenant_id=data.get("tenant_id", ""),
            demographics=data.get("demographics", {}),
            behavior_patterns=data.get("behavior_patterns", {}),
            interaction_history=data.get("interaction_history", []),
            preferences=data.get("preferences", {}),
            topics_of_interest=data.get("topics_of_interest", {}),
            skill_levels=data.get("skill_levels", {}),
            learning_progress=data.get("learning_progress", {}),
            emotional_baseline=data.get("emotional_baseline", {}),
            recent_sentiment=data.get("recent_sentiment", 0.0),
            profile_version=data.get("profile_version", 1),
            last_updated=last_updated,
            confidence_scores=data.get("confidence_scores", {}),
            privacy_settings=data.get("privacy_settings", {}),
            consent_flags=data.get("consent_flags", {}),
            data_retention_days=data.get("data_retention_days", 90),
        )


@dataclass
class ProfileUpdate:
    """
    Incremental profile update.

    Supports three update types:
    - increment: Add delta to current value
    - replace: Replace current value
    - merge: Deep merge dictionaries
    """
    user_id: str
    tenant_id: str
    update_type: str              # "increment", "replace", "merge"
    field_path: str               # Dot-separated path, e.g., "preferences.sales_style"
    old_value: Any = None
    new_value: Any = None
    delta: Optional[float] = None  # Increment value
    weight: float = 1.0            # Update weight
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "system"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "update_type": self.update_type,
            "field_path": self.field_path,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "delta": self.delta,
            "weight": self.weight,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProfileUpdate":
        """Deserialize from dictionary"""
        timestamp = data.get("timestamp", datetime.utcnow())
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return cls(
            user_id=data["user_id"],
            tenant_id=data["tenant_id"],
            update_type=data["update_type"],
            field_path=data["field_path"],
            old_value=data.get("old_value"),
            new_value=data.get("new_value"),
            delta=data.get("delta"),
            weight=data.get("weight", 1.0),
            timestamp=timestamp,
            source=data.get("source", "system"),
        )


@dataclass
class MemoryQuery:
    """
    Memory query request.

    Supports multi-tier queries with semantic search,
    graph traversal, and filtering.
    """
    user_id: str
    tenant_id: str

    # Query conditions
    query_text: Optional[str] = None
    query_embedding: Optional[List[float]] = None

    # Filters
    tiers: List[MemoryTier] = field(default_factory=lambda: list(MemoryTier))
    memory_types: List[MemoryType] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    session_id: Optional[str] = None

    # Time range
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # Pagination and limits
    limit: int = 10
    offset: int = 0
    min_relevance: float = 0.0

    # Search options
    use_semantic_search: bool = True
    use_graph_traversal: bool = False
    traversal_depth: int = 2
    include_expired: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "query_text": self.query_text,
            "query_embedding": self.query_embedding,
            "tiers": [t.value for t in self.tiers],
            "memory_types": [t.value for t in self.memory_types],
            "tags": self.tags,
            "entities": self.entities,
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "limit": self.limit,
            "offset": self.offset,
            "min_relevance": self.min_relevance,
            "use_semantic_search": self.use_semantic_search,
            "use_graph_traversal": self.use_graph_traversal,
            "traversal_depth": self.traversal_depth,
            "include_expired": self.include_expired,
        }


@dataclass
class MemoryQueryResult:
    """
    Memory query result.

    Contains matched entries along with search metadata.
    """
    entries: List[MemoryEntry] = field(default_factory=list)
    total_count: int = 0
    query_time_ms: float = 0.0
    tiers_searched: List[MemoryTier] = field(default_factory=list)
    semantic_scores: Dict[str, float] = field(default_factory=dict)
    graph_paths: List[List[str]] = field(default_factory=list)
    has_more: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "entries": [e.to_dict() for e in self.entries],
            "total_count": self.total_count,
            "query_time_ms": self.query_time_ms,
            "tiers_searched": [t.value for t in self.tiers_searched],
            "semantic_scores": self.semantic_scores,
            "graph_paths": self.graph_paths,
            "has_more": self.has_more,
        }
