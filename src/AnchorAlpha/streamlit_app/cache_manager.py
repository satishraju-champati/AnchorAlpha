"""
Advanced caching manager for Streamlit data operations.
"""

import json
import logging
import pickle
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Callable
import streamlit as st
import hashlib


logger = logging.getLogger(__name__)


class CacheManager:
    """Advanced caching manager with TTL and persistence."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory for persistent cache files
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path(tempfile.gettempdir()) / "anchoralpha_cache"
        self.cache_dir.mkdir(exist_ok=True)
        self._memory_cache = {}
        self._cache_metadata = {}
        
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        # Check memory cache first
        if key in self._memory_cache:
            if self._is_cache_valid(key):
                logger.debug(f"Cache hit (memory): {key}")
                return self._memory_cache[key]
            else:
                # Remove expired cache
                self._remove_from_memory_cache(key)
        
        # Check persistent cache
        cache_file = self._get_cache_file_path(key)
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                
                # Check if persistent cache is still valid
                if self._is_persistent_cache_valid(cached_data):
                    # Load back to memory cache
                    self._memory_cache[key] = cached_data['value']
                    self._cache_metadata[key] = {
                        'timestamp': cached_data['timestamp'],
                        'ttl': cached_data['ttl']
                    }
                    logger.debug(f"Cache hit (persistent): {key}")
                    return cached_data['value']
                else:
                    # Remove expired persistent cache
                    cache_file.unlink()
                    
            except Exception as e:
                logger.warning(f"Error reading persistent cache for {key}: {e}")
                if cache_file.exists():
                    cache_file.unlink()
        
        logger.debug(f"Cache miss: {key}")
        return default
    
    def set(self, key: str, value: Any, ttl: int = 300, persist: bool = True) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            persist: Whether to persist to disk
        """
        timestamp = datetime.now()
        
        # Store in memory cache
        self._memory_cache[key] = value
        self._cache_metadata[key] = {
            'timestamp': timestamp,
            'ttl': ttl
        }
        
        # Store in persistent cache if requested
        if persist:
            try:
                cache_data = {
                    'value': value,
                    'timestamp': timestamp,
                    'ttl': ttl
                }
                
                cache_file = self._get_cache_file_path(key)
                with open(cache_file, 'wb') as f:
                    pickle.dump(cache_data, f)
                    
                logger.debug(f"Cached (persistent): {key}")
                
            except Exception as e:
                logger.warning(f"Error writing persistent cache for {key}: {e}")
        
        logger.debug(f"Cached (memory): {key}")
    
    def invalidate(self, key: str) -> None:
        """
        Invalidate cache entry.
        
        Args:
            key: Cache key to invalidate
        """
        # Remove from memory cache
        self._remove_from_memory_cache(key)
        
        # Remove from persistent cache
        cache_file = self._get_cache_file_path(key)
        if cache_file.exists():
            try:
                cache_file.unlink()
                logger.debug(f"Invalidated cache: {key}")
            except Exception as e:
                logger.warning(f"Error removing persistent cache for {key}: {e}")
    
    def clear_all(self) -> None:
        """Clear all cache entries."""
        # Clear memory cache
        self._memory_cache.clear()
        self._cache_metadata.clear()
        
        # Clear persistent cache
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink()
            logger.info("Cleared all cache entries")
        except Exception as e:
            logger.warning(f"Error clearing persistent cache: {e}")
    
    def cleanup_expired(self) -> int:
        """
        Clean up expired cache entries.
        
        Returns:
            Number of entries cleaned up
        """
        cleaned_count = 0
        
        # Clean memory cache
        expired_keys = []
        for key in self._memory_cache:
            if not self._is_cache_valid(key):
                expired_keys.append(key)
        
        for key in expired_keys:
            self._remove_from_memory_cache(key)
            cleaned_count += 1
        
        # Clean persistent cache
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    with open(cache_file, 'rb') as f:
                        cached_data = pickle.load(f)
                    
                    if not self._is_persistent_cache_valid(cached_data):
                        cache_file.unlink()
                        cleaned_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error checking cache file {cache_file}: {e}")
                    # Remove corrupted cache file
                    cache_file.unlink()
                    cleaned_count += 1
                    
        except Exception as e:
            logger.warning(f"Error during cache cleanup: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired cache entries")
        
        return cleaned_count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        memory_count = len(self._memory_cache)
        persistent_count = len(list(self.cache_dir.glob("*.cache")))
        
        # Calculate total cache size
        total_size = 0
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                total_size += cache_file.stat().st_size
        except Exception as e:
            logger.warning(f"Error calculating cache size: {e}")
        
        return {
            'memory_entries': memory_count,
            'persistent_entries': persistent_count,
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'cache_dir': str(self.cache_dir)
        }
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if memory cache entry is still valid."""
        if key not in self._cache_metadata:
            return False
        
        metadata = self._cache_metadata[key]
        age = datetime.now() - metadata['timestamp']
        return age.total_seconds() < metadata['ttl']
    
    def _is_persistent_cache_valid(self, cached_data: Dict[str, Any]) -> bool:
        """Check if persistent cache entry is still valid."""
        if 'timestamp' not in cached_data or 'ttl' not in cached_data:
            return False
        
        age = datetime.now() - cached_data['timestamp']
        return age.total_seconds() < cached_data['ttl']
    
    def _remove_from_memory_cache(self, key: str) -> None:
        """Remove entry from memory cache."""
        self._memory_cache.pop(key, None)
        self._cache_metadata.pop(key, None)
    
    def _get_cache_file_path(self, key: str) -> Path:
        """Get file path for persistent cache entry."""
        # Create a safe filename from the key
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.cache"


class CachedDataLoader:
    """Wrapper for data loading functions with caching."""
    
    def __init__(self, cache_manager: CacheManager):
        """
        Initialize cached data loader.
        
        Args:
            cache_manager: Cache manager instance
        """
        self.cache_manager = cache_manager
    
    def cached_load(self, 
                   key: str, 
                   loader_func: Callable[[], Any], 
                   ttl: int = 300,
                   persist: bool = True) -> Any:
        """
        Load data with caching.
        
        Args:
            key: Cache key
            loader_func: Function to load data if not cached
            ttl: Time to live in seconds
            persist: Whether to persist to disk
            
        Returns:
            Loaded data (from cache or fresh)
        """
        # Try to get from cache first
        cached_value = self.cache_manager.get(key)
        if cached_value is not None:
            return cached_value
        
        # Load fresh data
        try:
            fresh_data = loader_func()
            if fresh_data is not None:
                self.cache_manager.set(key, fresh_data, ttl=ttl, persist=persist)
            return fresh_data
            
        except Exception as e:
            logger.error(f"Error loading data for key {key}: {e}")
            raise
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match (simple string matching)
            
        Returns:
            Number of entries invalidated
        """
        invalidated_count = 0
        
        # Find matching keys in memory cache
        matching_keys = [key for key in self.cache_manager._memory_cache.keys() if pattern in key]
        
        for key in matching_keys:
            self.cache_manager.invalidate(key)
            invalidated_count += 1
        
        # Find matching keys in persistent cache
        try:
            for cache_file in self.cache_manager.cache_dir.glob("*.cache"):
                # This is a simplified approach - in practice, you might want to store
                # the original key in the cache file for pattern matching
                pass
        except Exception as e:
            logger.warning(f"Error during pattern invalidation: {e}")
        
        if invalidated_count > 0:
            logger.info(f"Invalidated {invalidated_count} cache entries matching pattern: {pattern}")
        
        return invalidated_count


# Global cache manager instance
@st.cache_resource
def get_cache_manager() -> CacheManager:
    """Get cached cache manager instance."""
    return CacheManager()


@st.cache_resource
def get_cached_data_loader() -> CachedDataLoader:
    """Get cached data loader instance."""
    return CachedDataLoader(get_cache_manager())