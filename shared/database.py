import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT NOT NULL,
            date        TEXT,
            merchant    TEXT,
            items       TEXT,
            total       REAL,
            currency    TEXT DEFAULT 'IDR',
            photo_file  TEXT,
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS hajj_goals (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         TEXT NOT NULL UNIQUE,
            package_type    TEXT DEFAULT 'reguler',
            target_year     INTEGER,
            current_savings REAL DEFAULT 0,
            monthly_target  REAL,
            updated_at      TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS savings_targets (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT NOT NULL,
            category    TEXT NOT NULL,
            target_amount REAL NOT NULL,
            month       TEXT NOT NULL,
            created_at  TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(user_id, category, month)
        );

        CREATE TABLE IF NOT EXISTS zakat_assets (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT NOT NULL,
            year        INTEGER,
            tabungan    REAL DEFAULT 0,
            emas_gram   REAL DEFAULT 0,
            saham       REAL DEFAULT 0,
            deposito    REAL DEFAULT 0,
            crypto_idr  REAL DEFAULT 0,
            piutang     REAL DEFAULT 0,
            zakat_due   REAL DEFAULT 0,
            calculated_at TEXT DEFAULT (datetime('now','localtime'))
        );
    """)
    conn.commit()
    conn.close()
