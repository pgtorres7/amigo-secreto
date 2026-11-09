from __future__ import annotations

import os
from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

_pool: ConnectionPool | None = None


def _conninfo() -> str:
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    db = os.getenv("DB_DATABASE", "postgres")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PSW")
    return (
        f"host={host} port={port} dbname={db} user={user} password={password} "
        "sslmode=require"
    )


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=_conninfo(),
            min_size=1,
            max_size=5,
            # Supabase pooler (PgBouncer) não suporta prepared statements bem
            kwargs={"row_factory": dict_row, "prepare_threshold": None},
            open=True,
        )
    return _pool


@contextmanager
def get_conn():
    pool = get_pool()
    with pool.connection() as conn:
        yield conn


def query_all(sql: str, params: tuple | dict | None = None) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())


def query_one(sql: str, params: tuple | dict | None = None) -> dict | None:
    rows = query_all(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple | dict | None = None) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()


def execute_returning(sql: str, params: tuple | dict | None = None) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        conn.commit()
        return row


def ensure_schema() -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS public.participants (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          name TEXT NOT NULL,
          name_key TEXT NOT NULL UNIQUE,
          phone TEXT NOT NULL,
          access_token_hash TEXT UNIQUE,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS public.draws (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          giver_id UUID NOT NULL UNIQUE REFERENCES public.participants(id) ON DELETE CASCADE,
          receiver_ciphertext TEXT NOT NULL,
          receiver_hash TEXT NOT NULL UNIQUE,
          sms_sent BOOLEAN NOT NULL DEFAULT FALSE,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        "ALTER TABLE public.participants ADD COLUMN IF NOT EXISTS access_token_hash TEXT",
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_participants_access_token_hash
          ON public.participants(access_token_hash)
        """,
        "CREATE INDEX IF NOT EXISTS idx_draws_giver_id ON public.draws(giver_id)",
        "CREATE INDEX IF NOT EXISTS idx_draws_receiver_hash ON public.draws(receiver_hash)",
    ]
    for statement in statements:
        execute(statement)


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
