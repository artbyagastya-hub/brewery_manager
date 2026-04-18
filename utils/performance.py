"""
Brewery Manager - Performance Optimization Module
Provides connection pooling, caching, and SQLite optimizations
"""

import sqlite3
import os
import time
import threading
from functools import wraps
from typing import Any, Optional, Dict, Callable
from collections import OrderedDict
from datetime import datetime, timedelta


class ConnectionPool:
    """
    Thread-safe SQLite connection pool.
    Reuses connections to avoid overhead of repeated open/close operations.
    """
    
    def __init__(self, db_path: str, pool_size: int = 5):
        self.db_path = db_path
        self.pool_size = pool_size
        self._connections: list = []
        self._lock = threading.Lock()
        self._in_use: set = set()
        
        # Pre-create connections
        for _ in range(pool_size):
            conn = self._create_connection()
            self._connections.append(conn)
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new optimized SQLite connection"""
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        
        # SQLite performance optimizations
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for concurrent reads
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety vs speed
        conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        conn.execute("PRAGMA temp_store=MEMORY")  # Store temp tables in memory
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O
        conn.execute("PRAGMA foreign_keys = ON")
        
        return conn
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a connection from the pool"""
        with self._lock:
            if self._connections:
                conn = self._connections.pop()
                self._in_use.add(id(conn))
                return conn
        
        # Pool exhausted, create temporary connection
        conn = self._create_connection()
        with self._lock:
            self._in_use.add(id(conn))
        return conn
    
    def return_connection(self, conn: sqlite3.Connection):
        """Return a connection to the pool"""
        conn_id = id(conn)
        with self._lock:
            if conn_id in self._in_use:
                self._in_use.discard(conn_id)
                if len(self._connections) < self.pool_size:
                    self._connections.append(conn)
                    return
        
        # Pool full or temporary connection, close it
        try:
            conn.close()
        except Exception:
            pass
    
    def close_all(self):
        """Close all connections in the pool"""
        with self._lock:
            for conn in self._connections:
                try:
                    conn.close()
                except Exception:
                    pass
            self._connections.clear()
            self._in_use.clear()


class QueryCache:
    """
    Thread-safe LRU cache with TTL for query results.
    Automatically expires entries after a configurable duration.
    """
    
    def __init__(self, max_size: int = 256, default_ttl: int = 60):
        """
        Args:
            max_size: Maximum number of cached entries
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def _make_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from function name and arguments"""
        key_parts = [func_name]
        key_parts.extend(str(a) for a in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return "|".join(key_parts)
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if it exists and hasn't expired"""
        with self._lock:
            if key not in self._cache:
                return None
            
            # Check TTL
            timestamp = self._timestamps.get(key, 0)
            if time.time() - timestamp > self.default_ttl:
                del self._cache[key]
                del self._timestamps[key]
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return self._cache[key]
    
    def set(self, key: str, value: Any):
        """Set cached value"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            elif len(self._cache) >= self.max_size:
                # Remove oldest entry
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]
            
            self._cache[key] = value
            self._timestamps[key] = time.time()
    
    def invalidate(self, pattern: str = None):
        """
        Invalidate cache entries.
        If pattern is provided, only keys containing the pattern are invalidated.
        """
        with self._lock:
            if pattern is None:
                self._cache.clear()
                self._timestamps.clear()
            else:
                keys_to_remove = [k for k in self._cache if pattern in k]
                for key in keys_to_remove:
                    del self._cache[key]
                    del self._timestamps[key]
    
    def clear(self):
        """Clear all cached entries"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
    
    @property
    def stats(self) -> Dict:
        """Get cache statistics"""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "default_ttl": self.default_ttl
            }


# Global instances
_connection_pool: Optional[ConnectionPool] = None
_query_cache = QueryCache(max_size=512, default_ttl=30)


def init_connection_pool(db_path: str, pool_size: int = 5):
    """Initialize the global connection pool"""
    global _connection_pool
    if _connection_pool:
        _connection_pool.close_all()
    _connection_pool = ConnectionPool(db_path, pool_size)


def get_connection_pool() -> Optional[ConnectionPool]:
    """Get the global connection pool"""
    return _connection_pool


def get_query_cache() -> QueryCache:
    """Get the global query cache"""
    return _query_cache


def cached(ttl: int = None, invalidate_on_write: bool = True):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time-to-live in seconds (uses default if not specified)
        invalidate_on_write: If True, cache is invalidated when write operations occur
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_query_cache()
            
            # Generate cache key
            cache_key = cache._make_key(func.__name__, args, kwargs)
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            
            # Only cache non-None results
            if result is not None:
                if ttl:
                    # Temporarily override TTL for this entry
                    old_ttl = cache.default_ttl
                    cache.default_ttl = ttl
                    cache.set(cache_key, result)
                    cache.default_ttl = old_ttl
                else:
                    cache.set(cache_key, result)
            
            return result
        
        # Add cache control methods to wrapper
        wrapper.cache_invalidate = lambda pattern=None: get_query_cache().invalidate(pattern)
        wrapper.cache_clear = lambda: get_query_cache().clear()
        
        return wrapper
    return decorator


def cached_property(ttl: int = 60):
    """
    Decorator for caching property-like methods.
    Useful for dashboard data that doesn't change frequently.
    """
    def decorator(func: Callable) -> Callable:
        cache_key = f"property|{func.__name__}"
        last_update = [0]
        
        @wraps(func)
        def wrapper(self):
            cache = get_query_cache()
            now = time.time()
            
            # Check if cached value is still valid
            if now - last_update[0] < ttl:
                result = cache.get(cache_key)
                if result is not None:
                    return result
            
            # Refresh cache
            result = func(self)
            cache.set(cache_key, result)
            last_update[0] = now
            return result
        
        return property(wrapper)
    return decorator


class DatabaseContext:
    """
    Context manager for database operations with automatic connection pooling.
    Ensures connections are properly returned to the pool.
    """
    
    def __init__(self, pool: ConnectionPool = None):
        self.pool = pool or get_connection_pool()
        self.conn = None
        self.cursor = None
    
    def __enter__(self):
        if self.pool:
            self.conn = self.pool.get_connection()
        else:
            # Fallback to direct connection
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'data', 'brewery.db'
            )
            self.conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON")
        
        self.cursor = self.conn.cursor()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        
        if self.pool:
            self.pool.return_connection(self.conn)
        else:
            self.conn.close()
        
        return False
    
    def execute(self, query: str, params: tuple = None):
        """Execute a query"""
        if params:
            return self.cursor.execute(query, params)
        return self.cursor.execute(query)
    
    def fetchone(self):
        """Fetch one result"""
        return self.cursor.fetchone()
    
    def fetchall(self):
        """Fetch all results"""
        return self.cursor.fetchall()
    
    @property
    def lastrowid(self):
        """Get last inserted row ID"""
        return self.cursor.lastrowid


def optimize_database(db_path: str):
    """
    Run SQLite optimization commands on the database.
    Should be called periodically for maintenance.
    """
    conn = sqlite3.connect(db_path)
    
    # Enable WAL mode
    conn.execute("PRAGMA journal_mode=WAL")
    
    # Analyze tables for query optimizer
    conn.execute("ANALYZE")
    
    # Rebuild database file
    conn.execute("VACUUM")
    
    # Update statistics
    conn.execute("PRAGMA optimize")
    
    conn.close()
    print(f"Database optimized: {db_path}")


def get_performance_stats() -> Dict:
    """Get performance statistics"""
    cache = get_query_cache()
    pool = get_connection_pool()
    
    stats = {
        "cache": cache.stats,
        "connection_pool": {
            "pool_size": pool.pool_size if pool else 0,
            "available_connections": len(pool._connections) if pool else 0,
            "in_use_connections": len(pool._in_use) if pool else 0
        } if pool else None
    }
    
    return stats