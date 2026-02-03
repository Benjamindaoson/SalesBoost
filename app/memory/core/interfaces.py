"""
Enterprise AI Memory System - Storage Layer Interfaces

Abstract interfaces defining the contract for three-tier storage:
- ShortTermMemoryStore: Redis-based fast access
- MediumTermMemoryStore: Vector DB for semantic search
- LongTermMemoryStore: Graph DB for relationship reasoning

All implementations must adhere to these interfaces for
consistent behavior across the memory system.
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple
from uuid import UUID

from .schemas import (
    MemoryEntry,
    MemoryQuery,
    MemoryQueryResult,
    MemoryTier,
    UserProfile,
    ProfileUpdate,
)


class MemoryStore(ABC):
    """
    Abstract base class for memory storage.

    Defines the common interface for all storage tiers.
    """

    @property
    @abstractmethod
    def tier(self) -> MemoryTier:
        """Return the storage tier"""
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize storage connection"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown storage connection"""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Health check for the storage.

        Returns:
            Dict containing health status and metrics
        """
        pass

    # CRUD Operations
    @abstractmethod
    async def store(self, entry: MemoryEntry) -> UUID:
        """
        Store a memory entry.

        Args:
            entry: The memory entry to store

        Returns:
            UUID of the stored entry
        """
        pass

    @abstractmethod
    async def retrieve(self, memory_id: UUID) -> Optional[MemoryEntry]:
        """
        Retrieve a single memory by ID.

        Args:
            memory_id: UUID of the memory to retrieve

        Returns:
            The memory entry if found, None otherwise
        """
        pass

    @abstractmethod
    async def update(self, entry: MemoryEntry) -> bool:
        """
        Update an existing memory entry.

        Args:
            entry: The updated memory entry

        Returns:
            True if update successful, False otherwise
        """
        pass

    @abstractmethod
    async def delete(self, memory_id: UUID) -> bool:
        """
        Delete a memory by ID.

        Args:
            memory_id: UUID of the memory to delete

        Returns:
            True if deletion successful, False otherwise
        """
        pass

    @abstractmethod
    async def query(self, query: MemoryQuery) -> MemoryQueryResult:
        """
        Query memories based on criteria.

        Args:
            query: Query parameters

        Returns:
            Query result with matching entries
        """
        pass

    @abstractmethod
    async def batch_store(self, entries: List[MemoryEntry]) -> List[UUID]:
        """
        Store multiple memory entries.

        Args:
            entries: List of entries to store

        Returns:
            List of UUIDs for stored entries
        """
        pass

    @abstractmethod
    async def batch_delete(self, memory_ids: List[UUID]) -> int:
        """
        Delete multiple memories by ID.

        Args:
            memory_ids: List of UUIDs to delete

        Returns:
            Number of successfully deleted entries
        """
        pass

    # Lifecycle Management
    @abstractmethod
    async def cleanup_expired(self) -> int:
        """
        Clean up expired memories.

        Returns:
            Number of cleaned up entries
        """
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dict containing storage metrics
        """
        pass

    async def exists(self, memory_id: UUID) -> bool:
        """
        Check if a memory exists.

        Args:
            memory_id: UUID of the memory

        Returns:
            True if exists, False otherwise
        """
        entry = await self.retrieve(memory_id)
        return entry is not None


class ShortTermMemoryStore(MemoryStore):
    """
    Short-term memory storage interface (Redis).

    Optimized for:
    - Millisecond access latency
    - Session state management
    - TTL-based expiration
    - Real-time context
    """

    @property
    def tier(self) -> MemoryTier:
        return MemoryTier.SHORT_TERM

    @abstractmethod
    async def get_session_context(
        self,
        user_id: str,
        session_id: str,
        limit: int = 50,
    ) -> List[MemoryEntry]:
        """
        Get session context memories.

        Args:
            user_id: User identifier
            session_id: Session identifier
            limit: Maximum number of entries

        Returns:
            List of memory entries for the session
        """
        pass

    @abstractmethod
    async def update_session_context(
        self,
        user_id: str,
        session_id: str,
        entries: List[MemoryEntry],
        max_entries: int = 50,
    ) -> None:
        """
        Update session context with new entries.

        Args:
            user_id: User identifier
            session_id: Session identifier
            entries: New entries to add
            max_entries: Maximum entries to retain
        """
        pass

    @abstractmethod
    async def set_with_ttl(
        self,
        key: str,
        value: Any,
        ttl_seconds: int,
    ) -> None:
        """
        Set a value with TTL.

        Args:
            key: Cache key
            value: Value to store
            ttl_seconds: Time-to-live in seconds
        """
        pass

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value by key.

        Args:
            key: Cache key

        Returns:
            The value if found, None otherwise
        """
        pass

    @abstractmethod
    async def extend_ttl(self, key: str, ttl_seconds: int) -> bool:
        """
        Extend TTL for a key.

        Args:
            key: Cache key
            ttl_seconds: New TTL in seconds

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def get_ttl(self, key: str) -> Optional[int]:
        """
        Get remaining TTL for a key.

        Args:
            key: Cache key

        Returns:
            Remaining TTL in seconds, None if key doesn't exist
        """
        pass

    @abstractmethod
    async def increment(
        self,
        key: str,
        amount: int = 1,
    ) -> int:
        """
        Increment a counter.

        Args:
            key: Counter key
            amount: Increment amount

        Returns:
            New counter value
        """
        pass


class MediumTermMemoryStore(MemoryStore):
    """
    Medium-term memory storage interface (Vector DB).

    Optimized for:
    - Semantic similarity search
    - Hybrid search (vector + keyword)
    - User preference matching
    - Content-based retrieval
    """

    @property
    def tier(self) -> MemoryTier:
        return MemoryTier.MEDIUM_TERM

    @abstractmethod
    async def semantic_search(
        self,
        query_embedding: List[float],
        user_id: str,
        tenant_id: str,
        limit: int = 10,
        min_similarity: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[MemoryEntry, float]]:
        """
        Semantic similarity search.

        Args:
            query_embedding: Query vector embedding
            user_id: User identifier
            tenant_id: Tenant identifier
            limit: Maximum results
            min_similarity: Minimum similarity threshold
            filters: Additional filters

        Returns:
            List of (entry, similarity_score) tuples
        """
        pass

    @abstractmethod
    async def hybrid_search(
        self,
        query_text: str,
        query_embedding: List[float],
        user_id: str,
        tenant_id: str,
        limit: int = 10,
        alpha: float = 0.5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[MemoryEntry, float]]:
        """
        Hybrid search combining vector and keyword search.

        Args:
            query_text: Text query for keyword search
            query_embedding: Query vector embedding
            user_id: User identifier
            tenant_id: Tenant identifier
            limit: Maximum results
            alpha: Weight for vector search (0=keyword only, 1=vector only)
            filters: Additional filters

        Returns:
            List of (entry, combined_score) tuples
        """
        pass

    @abstractmethod
    async def update_embedding(
        self,
        memory_id: UUID,
        new_embedding: List[float],
    ) -> bool:
        """
        Update vector embedding for a memory.

        Args:
            memory_id: UUID of the memory
            new_embedding: New embedding vector

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def find_similar(
        self,
        memory_id: UUID,
        limit: int = 5,
        min_similarity: float = 0.7,
    ) -> List[Tuple[MemoryEntry, float]]:
        """
        Find similar memories to a given memory.

        Args:
            memory_id: UUID of the reference memory
            limit: Maximum results
            min_similarity: Minimum similarity threshold

        Returns:
            List of (entry, similarity_score) tuples
        """
        pass

    @abstractmethod
    async def get_embeddings(
        self,
        memory_ids: List[UUID],
    ) -> Dict[UUID, List[float]]:
        """
        Get embeddings for multiple memories.

        Args:
            memory_ids: List of memory UUIDs

        Returns:
            Dict mapping UUID to embedding
        """
        pass

    @abstractmethod
    async def reindex(
        self,
        user_id: str,
        tenant_id: str,
    ) -> int:
        """
        Reindex all memories for a user.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier

        Returns:
            Number of reindexed entries
        """
        pass


class LongTermMemoryStore(MemoryStore):
    """
    Long-term memory storage interface (Graph DB).

    Optimized for:
    - Knowledge graph storage
    - Relationship reasoning
    - Path finding
    - Subgraph queries
    """

    @property
    def tier(self) -> MemoryTier:
        return MemoryTier.LONG_TERM

    @abstractmethod
    async def create_node(self, entry: MemoryEntry) -> UUID:
        """
        Create a knowledge graph node.

        Args:
            entry: Memory entry to store as node

        Returns:
            UUID of the created node
        """
        pass

    @abstractmethod
    async def create_relationship(
        self,
        source_id: UUID,
        target_id: UUID,
        relation_type: str,
        properties: Optional[Dict[str, Any]] = None,
        weight: float = 1.0,
    ) -> UUID:
        """
        Create a relationship between nodes.

        Args:
            source_id: Source node UUID
            target_id: Target node UUID
            relation_type: Type of relationship
            properties: Additional properties
            weight: Relationship strength [0, 1]

        Returns:
            UUID of the created relationship
        """
        pass

    @abstractmethod
    async def delete_relationship(
        self,
        source_id: UUID,
        target_id: UUID,
        relation_type: Optional[str] = None,
    ) -> bool:
        """
        Delete a relationship between nodes.

        Args:
            source_id: Source node UUID
            target_id: Target node UUID
            relation_type: Type of relationship (None = all)

        Returns:
            True if deleted, False otherwise
        """
        pass

    @abstractmethod
    async def traverse(
        self,
        start_id: UUID,
        relation_types: Optional[List[str]] = None,
        direction: str = "outgoing",  # outgoing, incoming, both
        max_depth: int = 3,
        limit: int = 100,
    ) -> List[List[MemoryEntry]]:
        """
        Traverse the graph from a starting node.

        Args:
            start_id: Starting node UUID
            relation_types: Filter by relationship types
            direction: Traversal direction
            max_depth: Maximum traversal depth
            limit: Maximum paths to return

        Returns:
            List of paths (each path is a list of entries)
        """
        pass

    @abstractmethod
    async def find_paths(
        self,
        source_id: UUID,
        target_id: UUID,
        max_length: int = 5,
        relation_types: Optional[List[str]] = None,
    ) -> List[List[MemoryEntry]]:
        """
        Find paths between two nodes.

        Args:
            source_id: Source node UUID
            target_id: Target node UUID
            max_length: Maximum path length
            relation_types: Filter by relationship types

        Returns:
            List of paths connecting source to target
        """
        pass

    @abstractmethod
    async def get_neighbors(
        self,
        node_id: UUID,
        relation_type: Optional[str] = None,
        direction: str = "both",
        limit: int = 20,
    ) -> List[Tuple[MemoryEntry, str, float]]:
        """
        Get neighboring nodes.

        Args:
            node_id: Node UUID
            relation_type: Filter by relationship type
            direction: Relationship direction
            limit: Maximum neighbors

        Returns:
            List of (entry, relation_type, weight) tuples
        """
        pass

    @abstractmethod
    async def infer_relations(
        self,
        user_id: str,
        tenant_id: str,
        min_confidence: float = 0.7,
    ) -> List[Tuple[UUID, UUID, str, float]]:
        """
        Infer potential relationships.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            min_confidence: Minimum confidence threshold

        Returns:
            List of (source_id, target_id, relation_type, confidence) tuples
        """
        pass

    @abstractmethod
    async def get_subgraph(
        self,
        center_id: UUID,
        radius: int = 2,
    ) -> Tuple[List[MemoryEntry], List[Tuple[UUID, UUID, str, float]]]:
        """
        Get a subgraph centered on a node.

        Args:
            center_id: Center node UUID
            radius: Subgraph radius (hops)

        Returns:
            Tuple of (nodes, edges) where edges are (src, tgt, type, weight)
        """
        pass


class ProfileStore(ABC):
    """
    User profile storage interface.

    Manages user profiles with support for:
    - Incremental updates
    - Version history
    - Rollback capabilities
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the profile store"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the profile store"""
        pass

    @abstractmethod
    async def get_profile(
        self,
        user_id: str,
        tenant_id: str,
    ) -> Optional[UserProfile]:
        """
        Get user profile.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier

        Returns:
            User profile if found, None otherwise
        """
        pass

    @abstractmethod
    async def save_profile(self, profile: UserProfile) -> bool:
        """
        Save user profile.

        Args:
            profile: Profile to save

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def delete_profile(
        self,
        user_id: str,
        tenant_id: str,
    ) -> bool:
        """
        Delete user profile (GDPR compliance).

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier

        Returns:
            True if deleted, False otherwise
        """
        pass

    @abstractmethod
    async def apply_update(self, update: ProfileUpdate) -> UserProfile:
        """
        Apply incremental update to profile.

        Args:
            update: Profile update to apply

        Returns:
            Updated profile
        """
        pass

    @abstractmethod
    async def apply_batch_updates(
        self,
        updates: List[ProfileUpdate],
    ) -> UserProfile:
        """
        Apply batch of updates to profile.

        Args:
            updates: List of updates to apply

        Returns:
            Updated profile
        """
        pass

    @abstractmethod
    async def get_profile_history(
        self,
        user_id: str,
        tenant_id: str,
        limit: int = 10,
    ) -> List[ProfileUpdate]:
        """
        Get profile change history.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            limit: Maximum history entries

        Returns:
            List of profile updates
        """
        pass

    @abstractmethod
    async def rollback_to_version(
        self,
        user_id: str,
        tenant_id: str,
        version: int,
    ) -> UserProfile:
        """
        Rollback profile to a specific version.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            version: Target version

        Returns:
            Rolled back profile
        """
        pass

    @abstractmethod
    async def list_profiles(
        self,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[UserProfile]:
        """
        List profiles for a tenant.

        Args:
            tenant_id: Tenant identifier
            limit: Maximum profiles
            offset: Pagination offset

        Returns:
            List of user profiles
        """
        pass


class SyncEngine(ABC):
    """
    Synchronization engine interface.

    Manages data synchronization between tiers and regions.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the sync engine"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the sync engine"""
        pass

    @abstractmethod
    async def sync_to_tier(
        self,
        entry: MemoryEntry,
        target_tier: MemoryTier,
    ) -> bool:
        """
        Sync memory to a specific tier.

        Args:
            entry: Memory entry to sync
            target_tier: Target storage tier

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def promote_entry(self, memory_id: UUID) -> bool:
        """
        Promote memory to higher tier.

        Args:
            memory_id: UUID of memory to promote

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def demote_entry(self, memory_id: UUID) -> bool:
        """
        Demote memory to lower tier.

        Args:
            memory_id: UUID of memory to demote

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def resolve_conflict(
        self,
        local_entry: MemoryEntry,
        remote_entry: MemoryEntry,
    ) -> MemoryEntry:
        """
        Resolve conflict between entries.

        Args:
            local_entry: Local memory entry
            remote_entry: Remote memory entry

        Returns:
            Resolved memory entry
        """
        pass

    @abstractmethod
    async def get_pending_syncs(self) -> List[Tuple[UUID, MemoryTier]]:
        """
        Get list of pending synchronizations.

        Returns:
            List of (memory_id, target_tier) tuples
        """
        pass

    @abstractmethod
    async def sync_region(
        self,
        source_region: str,
        target_region: str,
        batch_size: int = 100,
    ) -> Dict[str, int]:
        """
        Sync data between regions.

        Args:
            source_region: Source region identifier
            target_region: Target region identifier
            batch_size: Batch size for sync

        Returns:
            Dict with sync statistics
        """
        pass

    @abstractmethod
    async def get_sync_status(self) -> Dict[str, Any]:
        """
        Get synchronization status.

        Returns:
            Dict containing sync metrics and status
        """
        pass


class EmbeddingProvider(ABC):
    """
    Embedding provider interface.

    Generates vector embeddings for memory content.
    """

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """
        Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        pass

    @abstractmethod
    async def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension"""
        pass
