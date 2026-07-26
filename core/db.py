"""Thin DB abstraction for the fusion core.

SQLite for local/dev and fixtures/CI; production substrate is PENDING decision
D4 (PostgreSQL + pgvector proposed) -- same schema, minor DDL deltas for the
proposed target noted in core/schema/schema.sql. Nothing
here is analysis logic; this is the persistence concern only (ARCHITECTURE.md 3).
"""
from __future__ import annotations
import sqlite3


def connect(path: str = ":memory:") -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys=ON")
    con.row_factory = sqlite3.Row
    return con


def apply_schema(con: sqlite3.Connection, schema_path: str) -> None:
    with open(schema_path) as f:
        con.executescript(f.read())
    con.commit()
