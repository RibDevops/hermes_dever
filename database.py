#!/usr/bin/env python3
"""Módulo de persistência: eventos concluídos (SQLite)."""

import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hermes.db")


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    """Cria a tabela se não existir."""
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS completed_events (
                event_id TEXT PRIMARY KEY,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def is_completed(event_id: str) -> bool:
    """Retorna True se o evento já foi marcado como concluído."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM completed_events WHERE event_id = ?",
            (event_id,)
        ).fetchone()
        return row is not None


def mark_completed(event_id: str) -> bool:
    """Marca evento como concluído. Retorna True se inseriu novo."""
    with _conn() as conn:
        try:
            conn.execute(
                "INSERT INTO completed_events (event_id) VALUES (?)",
                (event_id,)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # já existia


def list_completed(limit: int = 50) -> list[dict]:
    """Lista últimos eventos concluídos (para debug)."""
    with _conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT event_id, completed_at FROM completed_events ORDER BY completed_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def uncomplete(event_id: str) -> bool:
    """Desfaz conclusão (caso precise reverter)."""
    with _conn() as conn:
        cur = conn.execute(
            "DELETE FROM completed_events WHERE event_id = ?",
            (event_id,)
        )
        conn.commit()
        return cur.rowcount > 0


# Inicializa ao importar
init_db()
