"""
Deep serialization utilities for complex object persistence.
Handles circular references, non-serializable objects, and compression.
"""
import json
import pickle
import gzip
import logging
from typing import Any, Dict, Set, Optional
from dataclasses import is_dataclass, asdict
import inspect

logger = logging.getLogger(__name__)


class CircularReferenceDetector:
    """
    Detects and resolves circular references in object graphs.
    
    Uses object ID tracking to identify cycles and replace them
    with reference markers.
    """
    
    def __init__(self):
        """Initialize the detector with empty tracking sets."""
        self._seen_ids: Set[int] = set()
        self._path: list = []
    
    def detect_circular(self, obj: Any, path: str = "root") -> bool:
        """
        Check if object contains circular references.
        
        Args:
            obj: Object to check
            path: Current path in object graph (for debugging)
            
        Returns:
            True if circular reference detected
        """
        obj_id = id(obj)
        
        if obj_id in self._seen_ids:
            logger.warning(f"Circular reference detected at path: {path}")
            return True
        
        # Track primitive types and immutables
        if isinstance(obj, (str, int, float, bool, type(None))):
            return False
        
        self._seen_ids.add(obj_id)
        self._path.append(path)
        
        try:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if self.detect_circular(value, f"{path}.{key}"):
                        return True
            elif isinstance(obj, (list, tuple)):
                for i, item in enumerate(obj):
                    if self.detect_circular(item, f"{path}[{i}]"):
                        return True
            elif hasattr(obj, '__dict__'):
                for key, value in obj.__dict__.items():
                    if self.detect_circular(value, f"{path}.{key}"):
                        return True
        finally:
            self._path.pop()
            if obj_id in self._seen_ids:
                self._seen_ids.remove(obj_id)
        
        return False


class DeepSerializer:
    """
    Deep serializer for complex objects with circular reference handling.
    
    Supports:
    - Dataclasses
    - Custom objects with __dict__
    - Circular reference detection and resolution
    - Compression for large objects
    - Fallback to pickle for non-JSON-serializable objects
    
    Example:
        >>> serializer = DeepSerializer()
        >>> data = serializer.serialize(complex_object)
        >>> restored = serializer.deserialize(data)
    """
    
    def __init__(self, compress: bool = True, compression_threshold: int = 1024):
        """
        Initialize deep serializer.
        
        Args:
            compress: Whether to compress large objects
            compression_threshold: Size threshold for compression (bytes)
        """
        self.compress = compress
        self.compression_threshold = compression_threshold
        self._object_registry: Dict[int, Any] = {}
    
    def serialize(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize object to JSON-compatible dictionary.
        
        Args:
            obj: Object to serialize
            
        Returns:
            Dictionary with serialized data and metadata
        """
        # Detect circular references
        detector = CircularReferenceDetector()
        has_circular = detector.detect_circular(obj)
        
        if has_circular:
            logger.warning("Object contains circular references. Using pickle fallback.")
            return self._pickle_serialize(obj)
        
        try:
            # Try JSON serialization first
            serialized = self._json_serialize(obj)
            
            # Compress if needed
            if self.compress:
                json_str = json.dumps(serialized)
                if len(json_str) > self.compression_threshold:
                    compressed = gzip.compress(json_str.encode('utf-8'))
                    return {
                        "_type": "compressed_json",
                        "_data": compressed.hex(),
                        "_original_size": len(json_str),
                        "_compressed_size": len(compressed)
                    }
            
            return {
                "_type": "json",
                "_data": serialized
            }
            
        except (TypeError, ValueError) as e:
            logger.warning(f"JSON serialization failed: {e}. Using pickle fallback.")
            return self._pickle_serialize(obj)
    
    def deserialize(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize object from dictionary.
        
        Args:
            data: Serialized data dictionary
            
        Returns:
            Restored object
        """
        data_type = data.get("_type")
        
        if data_type == "compressed_json":
            compressed_hex = data["_data"]
            compressed = bytes.fromhex(compressed_hex)
            json_str = gzip.decompress(compressed).decode('utf-8')
            serialized = json.loads(json_str)
            return self._json_deserialize(serialized)
        
        elif data_type == "json":
            return self._json_deserialize(data["_data"])
        
        elif data_type == "pickle":
            pickle_hex = data["_data"]
            pickle_bytes = bytes.fromhex(pickle_hex)
            return pickle.loads(pickle_bytes)
        
        else:
            raise ValueError(f"Unknown serialization type: {data_type}")
    
    def _json_serialize(self, obj: Any) -> Any:
        """
        Serialize object to JSON-compatible format.
        
        Args:
            obj: Object to serialize
            
        Returns:
            JSON-compatible representation
        """
        # Handle primitives
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        
        # Handle collections
        if isinstance(obj, dict):
            return {k: self._json_serialize(v) for k, v in obj.items()}
        
        if isinstance(obj, (list, tuple)):
            return [self._json_serialize(item) for item in obj]
        
        # Handle dataclasses
        if is_dataclass(obj):
            return {
                "_dataclass": obj.__class__.__name__,
                "_module": obj.__class__.__module__,
                **{k: self._json_serialize(v) for k, v in asdict(obj).items()}
            }
        
        # Handle objects with __dict__
        if hasattr(obj, '__dict__'):
            return {
                "_class": obj.__class__.__name__,
                "_module": obj.__class__.__module__,
                **{k: self._json_serialize(v) for k, v in obj.__dict__.items()}
            }
        
        # Fallback: convert to string
        return str(obj)
    
    def _json_deserialize(self, data: Any) -> Any:
        """
        Deserialize from JSON-compatible format.
        
        Args:
            data: JSON-compatible data
            
        Returns:
            Restored object
        """
        # Handle primitives
        if isinstance(data, (str, int, float, bool, type(None))):
            return data
        
        # Handle lists
        if isinstance(data, list):
            return [self._json_deserialize(item) for item in data]
        
        # Handle dictionaries
        if isinstance(data, dict):
            # Check for special markers
            if "_dataclass" in data or "_class" in data:
                # For now, return as dict (full class reconstruction requires imports)
                return {k: self._json_deserialize(v) for k, v in data.items() if not k.startswith("_")}
            
            return {k: self._json_deserialize(v) for k, v in data.items()}
        
        return data
    
    def _pickle_serialize(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize using pickle (fallback for complex objects).
        
        Args:
            obj: Object to serialize
            
        Returns:
            Dictionary with pickled data
        """
        try:
            pickle_bytes = pickle.dumps(obj)
            
            # Compress if needed
            if self.compress and len(pickle_bytes) > self.compression_threshold:
                compressed = gzip.compress(pickle_bytes)
                return {
                    "_type": "pickle",
                    "_compressed": True,
                    "_data": compressed.hex(),
                    "_original_size": len(pickle_bytes),
                    "_compressed_size": len(compressed)
                }
            
            return {
                "_type": "pickle",
                "_compressed": False,
                "_data": pickle_bytes.hex()
            }
        except Exception as e:
            logger.error(f"Pickle serialization failed: {e}")
            raise


# Global serializer instance
deep_serializer = DeepSerializer(compress=True, compression_threshold=1024)
