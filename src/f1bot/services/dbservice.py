from psycopg_pool import AsyncConnectionPool
from typing import Optional
import logging

import asyncio

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages PostgreSQL connection pool using psycopg3.
    Singleton pattern ensures only one pool exists.
    """
    _instance: Optional['DatabaseManager'] = None
    _pool: Optional[AsyncConnectionPool] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self, database_url: str, min_size: int = 2, max_size: int = 10):
        """Initialize the connection pool"""
        if self._pool is None:
            self._pool = AsyncConnectionPool(
                conninfo=database_url,
                min_size=min_size,
                max_size=max_size,
                timeout=30
            )
            await self._pool.open()
            await self._pool.wait()
            logger.info(f"Database pool initialized (min={min_size}, max={max_size})")

    async def close(self):
        """Close the connection pool"""
        if self._pool:
            await self._pool.close()
            logger.info("Database pool closed")

    async def execute_query(self, query: str, params: tuple = ()):
        """Execute a single query (no return)"""
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                await conn.commit()

    async def fetch_one(self, query: str, params: tuple = ()):
        """Fetch a single row"""
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                return await cur.fetchone()

    async def fetch_all(self, query: str, params: tuple = ()):
        """Fetch all rows"""
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                return await cur.fetchall()

if __name__ == "__main__":
    async def main():
        db = DatabaseManager()

        await db.initialize("postgresql://nirbhaykwatra:31415@192.168.1.240/f1fantasy")
        # Get leagues from 2026 with season information
        query = """
                SELECT l.id, \
                       l.name, \
                       l.discord_guild_id, \
                       l.season_id, \
                       l.embed_color, \
                       l.created_at, \
                       s.year AS season_year
                FROM leagues l
                         JOIN seasons s ON l.season_id = s.id
                WHERE s.year = %s \
                """
        leagues_2026 = await db.fetch_all(query, (2026,))
        print(leagues_2026)

        await db.close()

    asyncio.run(main())