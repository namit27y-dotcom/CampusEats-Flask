import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB
from backend_flask.config import Config
import logging

logger = logging.getLogger(__name__)

# Fallback pool implementation if dbutils is not installed
class SimpleDBPool:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def connection(self):
        return pymysql.connect(
            cursorclass=DictCursor,
            autocommit=True,
            **self.kwargs
        )

try:
    from dbutils.pooled_db import PooledDB
    pool = PooledDB(
        creator=pymysql,
        maxconnections=20,
        mincached=0,
        maxcached=10,
        blocking=True,
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        port=Config.DB_PORT,
        cursorclass=DictCursor,
        autocommit=True,
        charset='utf8mb4'
    )
except ImportError:
    pool = SimpleDBPool(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        port=Config.DB_PORT,
        charset='utf8mb4'
    )

def get_db_connection():
    """Returns a connection from the pool or creates a new one."""
    return pool.connection()

class DBTransaction:
    """Context manager for explicit MySQL transactions with automatic rollback on error."""
    def __init__(self):
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.conn = pool.connection()
        self.conn.begin()
        self.cursor = self.conn.cursor(DictCursor)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is not None:
                self.conn.rollback()
            else:
                self.conn.commit()
        finally:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()

    def query(self, sql, params=None):
        """Execute a query within transaction and return (rows, lastrowid, affected_rows)"""
        # Adapt IN clauses with lists/tuples if needed
        formatted_sql, formatted_params = adapt_query(sql, params)
        self.cursor.execute(formatted_sql, formatted_params)
        rows = self.cursor.fetchall()
        return rows, self.cursor.lastrowid, self.cursor.rowcount

def query_db(sql, params=None, one=False):
    """
    Execute a query outside an explicit multi-step transaction.
    Returns list of dicts, or single dict if one=True.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(DictCursor) as cursor:
            formatted_sql, formatted_params = adapt_query(sql, params)
            cursor.execute(formatted_sql, formatted_params)
            rows = cursor.fetchall()
            if one:
                return rows[0] if rows else None
            return rows
    finally:
        conn.close()

def execute_db(sql, params=None):
    """
    Execute an INSERT/UPDATE/DELETE statement.
    Returns (lastrowid, rowcount).
    """
    conn = get_db_connection()
    try:
        with conn.cursor(DictCursor) as cursor:
            formatted_sql, formatted_params = adapt_query(sql, params)
            cursor.execute(formatted_sql, formatted_params)
            conn.commit()
            return cursor.lastrowid, cursor.rowcount
    finally:
        conn.close()

def adapt_query(sql, params):
    """
    Adapts SQL placeholders (? or %s) and expands sequences (lists/tuples) for IN clauses.
    """
    if params is None:
        return sql.replace('?', '%s'), None

    # Normalize single param to tuple if not already a collection
    if not isinstance(params, (list, tuple)):
        params = [params]

    # Convert all ? to %s first
    unified_sql = sql.replace('?', '%s')
    
    # Check if there are list/tuple elements inside params that need expanding
    has_sequence = any(isinstance(p, (list, tuple, set)) for p in params)
    
    if not has_sequence:
        return unified_sql, tuple(params)

    # Split on %s and reconstruct
    parts = unified_sql.split('%s')
    if len(parts) - 1 != len(params):
        # Mismatch fallback
        return unified_sql, tuple(params)

    new_sql = ""
    new_params = []
    for i, part in enumerate(parts[:-1]):
        param = params[i]
        if isinstance(param, (list, tuple, set)):
            seq = list(param)
            if len(seq) == 0:
                new_sql += part + "NULL"
            else:
                placeholders = ', '.join(['%s'] * len(seq))
                new_sql += part + placeholders
                new_params.extend(seq)
        else:
            new_sql += part + '%s'
            new_params.append(param)

    new_sql += parts[-1]
    return new_sql, tuple(new_params)
