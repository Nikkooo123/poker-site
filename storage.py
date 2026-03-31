import os
from typing import List, Dict, Any

from psycopg_pool import ConnectionPool


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")


pool = ConnectionPool(
    conninfo=DATABASE_URL,
    min_size=1,
    max_size=5,
    open=False
)


def init_db():
    if pool.closed:
        pool.open()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS poker_tables (
                    id SERIAL PRIMARY KEY,
                    club TEXT NOT NULL DEFAULT '',
                    game TEXT NOT NULL DEFAULT '',
                    blinds TEXT NOT NULL DEFAULT '',
                    buyin TEXT NOT NULL DEFAULT '',
                    players TEXT NOT NULL DEFAULT '',
                    tags TEXT NOT NULL DEFAULT ''
                )
            """)
        conn.commit()


def load_tables() -> List[Dict[str, Any]]:
    if pool.closed:
        pool.open()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, club, game, blinds, buyin, players, tags
                FROM poker_tables
                ORDER BY id ASC
            """)
            rows = cur.fetchall()

    tables = []
    for row in rows:
        tables.append({
            "id": row[0],
            "club": row[1],
            "game": row[2],
            "blinds": row[3],
            "buyin": row[4],
            "players": row[5],
            "tags": row[6],
        })

    return tables


def add_table(club: str, game: str, blinds: str, buyin: str, players: str, tags: str):
    if pool.closed:
        pool.open()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO poker_tables (club, game, blinds, buyin, players, tags)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (club, game, blinds, buyin, players, tags))
        conn.commit()


def update_players(table_id: int, players: str):
    if pool.closed:
        pool.open()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE poker_tables
                SET players = %s
                WHERE id = %s
            """, (players, table_id))
        conn.commit()


def delete_table(table_id: int):
    if pool.closed:
        pool.open()

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM poker_tables
                WHERE id = %s
            """, (table_id,))
        conn.commit()
