from __future__ import annotations

import logging
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)


class DatabaseHelper:
    """Database helper for direct DB verification and data management.

    This is a lightweight wrapper that supports common database operations.
    It uses psycopg2 for PostgreSQL connections. Install psycopg2-binary
    if you need database connectivity.
    """

    def __init__(self, connection_string: str | None = None) -> None:
        self.connection_string = connection_string or settings.db_connection
        self._connection: Any = None

    def connect(self) -> None:
        """Establish a database connection."""
        try:
            import psycopg2

            self._connection = psycopg2.connect(self.connection_string)
            self._connection.autocommit = False
            logger.info("Database connection established")
        except ImportError:
            logger.warning(
                "psycopg2 is not installed. Install psycopg2-binary for DB support."
            )
            raise
        except Exception as e:
            logger.error("Failed to connect to database: %s", e)
            raise

    def disconnect(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")

    def execute(self, query: str, params: tuple[Any, ...] | None = None) -> None:
        """Execute a query without returning results."""
        if not self._connection:
            raise RuntimeError("Not connected to database. Call connect() first.")
        with self._connection.cursor() as cursor:
            cursor.execute(query, params)
        self._connection.commit()

    def fetch_one(self, query: str, params: tuple[Any, ...] | None = None) -> dict[str, Any] | None:
        """Execute a query and return a single row as a dict."""
        if not self._connection:
            raise RuntimeError("Not connected to database. Call connect() first.")
        with self._connection.cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()
            if row is None:
                return None
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))

    def fetch_all(self, query: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        """Execute a query and return all rows as a list of dicts."""
        if not self._connection:
            raise RuntimeError("Not connected to database. Call connect() first.")
        with self._connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    def cleanup_table(self, table_name: str, condition: str = "", params: tuple[Any, ...] | None = None) -> int:
        """Delete rows from a table, optionally with a WHERE condition. Returns deleted count."""
        if not self._connection:
            raise RuntimeError("Not connected to database. Call connect() first.")
        query = f"DELETE FROM {table_name}"  # noqa: S608
        if condition:
            query += f" WHERE {condition}"
        with self._connection.cursor() as cursor:
            cursor.execute(query, params)
            count = cursor.rowcount
        self._connection.commit()
        logger.info("Deleted %d rows from %s", count, table_name)
        return count

    def seed_data(self, table_name: str, rows: list[dict[str, Any]]) -> None:
        """Insert seed data into a table."""
        if not rows:
            return
        if not self._connection:
            raise RuntimeError("Not connected to database. Call connect() first.")
        columns = list(rows[0].keys())
        col_str = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(columns))
        query = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders})"  # noqa: S608
        with self._connection.cursor() as cursor:
            for row in rows:
                values = tuple(row[col] for col in columns)
                cursor.execute(query, values)
        self._connection.commit()
        logger.info("Seeded %d rows into %s", len(rows), table_name)

    def __enter__(self) -> DatabaseHelper:
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._connection and exc_type:
            self._connection.rollback()
        self.disconnect()
