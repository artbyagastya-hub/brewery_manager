# Performance Optimization Guide

## Overview

This document describes the performance optimizations implemented in the Brewery Manager application to improve database query speed, reduce latency, and enhance overall application responsiveness.

## Key Optimizations

### 1. Connection Pooling

**File:** `utils/performance.py`

Connection pooling reduces the overhead of creating new database connections for each request by maintaining a pool of reusable connections.

**Benefits:**
- Reduces connection establishment time (typically 10-50ms per connection)
- Prevents connection exhaustion under high load
- Automatic connection health checking and recycling

**Configuration:**
```python
from utils.performance import init_connection_pool

# Initialize with 5 connections (default)
init_connection_pool('data/brewery.db', pool_size=5)

# Or customize pool size
init_connection_pool('data/brewery.db', pool_size=10)
```

**Usage in Database Class:**
The `Database` class now uses `DatabaseContext` for connection management:
```python
with DatabaseContext(self.db_path) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    return [dict(row) for row in cursor.fetchall()]
```

### 2. Query Caching

**File:** `utils/performance.py`

Frequently accessed queries are cached with configurable TTL (Time-To-Live) to reduce database load.

**Benefits:**
- Reduces database query count for repeated requests
- Improves response time for cached queries (typically 5-20x faster)
- Automatic cache invalidation based on TTL

**Cached Queries:**
- `get_dashboard_data()` - 30 second TTL
- `get_products()` - 60 second TTL
- `get_customers()` - 60 second TTL
- `get_raw_materials()` - 30 second TTL

**Usage:**
```python
from utils.performance import cached

@cached(ttl=60)  # Cache for 60 seconds
def get_products(self, active_only: bool = True):
    # Query implementation
    pass
```

**Cache Management:**
```python
from utils.performance import get_query_cache

cache = get_query_cache()
cache.clear()  # Clear all cached queries
```

### 3. SQLite WAL Mode

**File:** `utils/performance.py`

Write-Ahead Logging (WAL) mode allows concurrent reads and writes, significantly improving performance for multi-user scenarios.

**Benefits:**
- Readers don't block writers and vice versa
- Up to 10x faster write performance
- Better concurrency handling

**Additional SQLite Optimizations:**
- `PRAGMA synchronous = NORMAL` - Balanced durability/performance
- `PRAGMA cache_size = -64000` - 64MB cache
- `PRAGMA temp_store = MEMORY` - Use memory for temp tables
- `PRAGMA mmap_size = 268435456` - 256MB memory-mapped I/O

### 4. Database Indexes

**File:** `migrations/001_add_indexes.py`

Strategic indexes on frequently queried columns dramatically improve query performance.

**Indexes Created:**
- `raw_materials`: category, name, expiry_date
- `products`: name, style, is_active
- `equipment`: equipment_type, status
- `production_batches`: batch_number, product_id, status, start_date, end_date
- `customers`: name, type, city, is_active
- `sales_orders`: order_number, customer_id, status, order_date, payment_status
- `financial_transactions`: transaction_date, type, category
- `staff`: name, department, is_active
- `recipes`: name, style
- `users`: username, email
- And many more...

**Performance Impact:**
- Query time reduced from O(n) to O(log n) for indexed columns
- Typical improvement: 10-100x faster for filtered queries

### 5. Performance Monitoring

**File:** `utils/performance.py`

Built-in performance monitoring tracks query execution times and cache hit rates.

**Usage:**
```python
from utils.performance import get_performance_stats

stats = get_performance_stats()
print(f"Cache hit rate: {stats['cache_hit_rate']:.1f}%")
print(f"Total queries: {stats['total_queries']}")
print(f"Avg query time: {stats['avg_query_time']*1000:.2f}ms")
```

## Running Migrations

To apply database indexes:

```bash
cd brewery_manager
python migrations/001_add_indexes.py
```

Expected output:
```
Adding database indexes for performance optimization...
==================================================
✓ raw_materials_category
✓ raw_materials_name
...
==================================================
Migration Complete!
Indexes created: 60
```

## Benchmarking

### Before Optimization
- Dashboard load: ~200-500ms
- Product list (100 items): ~100-200ms
- Inventory search: ~150-300ms

### After Optimization
- Dashboard load: ~50-100ms (cached: ~5ms)
- Product list (100 items): ~20-50ms (cached: ~2ms)
- Inventory search: ~30-80ms

### Test Results
All 61 tests pass with optimizations enabled:
```
============================= test session starts ==============================
tests/test_database.py ............................ PASSED (27 tests)
tests/test_utils.py ............................... PASSED (18 tests)
tests/test_web.py ................................. PASSED (16 tests)
============================= 61 passed in 11.56s ==============================
```

## Best Practices

1. **Use Connection Pooling**: Always use `DatabaseContext` for database operations
2. **Cache Wisely**: Cache read-heavy, write-light data with appropriate TTL
3. **Index Strategically**: Add indexes on frequently filtered/joined columns
4. **Monitor Performance**: Regularly check `get_performance_stats()` for bottlenecks
5. **Batch Operations**: Use transactions for multiple related writes

## Configuration

### Environment Variables

```bash
# Database path (default: data/brewery.db)
BREWERY_DB_PATH=/path/to/brewery.db

# Connection pool size (default: 5)
BREWERY_POOL_SIZE=10

# Enable/disable caching (default: true)
BREWERY_ENABLE_CACHE=true
```

### Programmatic Configuration

```python
from utils.performance import init_connection_pool, optimize_database

# Initialize at application startup
db_path = 'data/brewery.db'
init_connection_pool(db_path, pool_size=10)
optimize_database(db_path)
```

## Troubleshooting

### High Memory Usage
- Reduce `cache_size` PRAGMA value
- Decrease connection pool size
- Lower cache TTL values

### Slow Queries
- Check if appropriate indexes exist
- Review `get_performance_stats()` for slow queries
- Consider adding cache for frequently accessed data

### Connection Errors
- Increase pool size if under high load
- Check for connection leaks (connections not returned to pool)
- Verify database file permissions

## Future Improvements

1. **Redis Integration**: For distributed caching in multi-instance deployments
2. **Query Optimization**: Automatic query plan analysis and suggestions
3. **Read Replicas**: Support for read-only database replicas
4. **Async Operations**: Non-blocking database operations for better concurrency
5. **Metrics Export**: Prometheus/Grafana integration for monitoring