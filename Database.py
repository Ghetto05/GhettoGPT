from typing import Optional
from aiomysql import create_pool, connect
from aiomysql.utils import _PoolContextManager
import os

MARIADB_HOST = os.getenv("MARIADB_HOST")
MARIADB_USER = os.getenv("MARIADB_USER")
MARIADB_PASSWORD = os.getenv("MARIADB_PASSWORD")
MARIADB_DB = os.getenv("MARIADB_DB")

pool : Optional[_PoolContextManager] = None

async def init_pool():
    global pool
    if pool is None:
        # Connect first without DB to create it if missing
        conn = await connect(
            host=MARIADB_HOST,
            user=MARIADB_USER,
            password=MARIADB_PASSWORD,
        )
        async with conn.cursor() as cur:
            await cur.execute(f"CREATE DATABASE IF NOT EXISTS `{MARIADB_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        await conn.ensure_closed()

        # Now create pool connected to the DB
        pool = await create_pool(
            host=MARIADB_HOST,
            user=MARIADB_USER,
            password=MARIADB_PASSWORD,
            db=MARIADB_DB,
            autocommit=True,
            maxsize=10
        )

        # Create table if it doesn't exist
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                CREATE TABLE IF NOT EXISTS thread_workitem_mapping (
                    thread_id BIGINT PRIMARY KEY,
                    work_item_id INT NOT NULL
                );
                """)

async def save_mapping(thread_id: int, work_item_id: int):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """REPLACE INTO thread_workitem_mapping (thread_id, work_item_id) VALUES (%s, %s)""",
                (thread_id, work_item_id)
            )

async def get_work_item_id(thread_id: int):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT work_item_id FROM thread_workitem_mapping WHERE thread_id=%s",
                (thread_id,)
            )
            result = await cur.fetchone()
            return result[0] if result else None

async def get_thread_id(work_item_id: int):
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT thread_id FROM thread_workitem_mapping WHERE work_item_id=%s",
                (work_item_id,)
            )
            result = await cur.fetchone()
            return result[0] if result else None