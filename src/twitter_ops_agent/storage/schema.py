from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    handle TEXT NOT NULL,
    display_name TEXT
);

CREATE TABLE IF NOT EXISTS posts (
    post_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    url TEXT NOT NULL,
    created_at TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    text_exact TEXT NOT NULL,
    text_normalized TEXT NOT NULL,
    post_type TEXT NOT NULL,
    track TEXT,
    conversation_id TEXT,
    lang TEXT,
    likes INTEGER NOT NULL DEFAULT 0,
    retweets INTEGER NOT NULL DEFAULT 0,
    replies INTEGER NOT NULL DEFAULT 0,
    views INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS post_relations (
    relation_id TEXT PRIMARY KEY,
    from_post_id TEXT NOT NULL,
    to_post_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (from_post_id) REFERENCES posts(post_id),
    FOREIGN KEY (to_post_id) REFERENCES posts(post_id)
);

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    title TEXT,
    track TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS event_posts (
    event_id TEXT NOT NULL,
    post_id TEXT NOT NULL,
    role_in_event TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (event_id, post_id, role_in_event),
    FOREIGN KEY (event_id) REFERENCES events(event_id),
    FOREIGN KEY (post_id) REFERENCES posts(post_id)
);

CREATE TABLE IF NOT EXISTS style_examples (
    example_id TEXT PRIMARY KEY,
    handle TEXT NOT NULL,
    track TEXT,
    target_post_id TEXT NOT NULL,
    source_post_id TEXT,
    source_kind TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (target_post_id) REFERENCES posts(post_id),
    FOREIGN KEY (source_post_id) REFERENCES posts(post_id)
);

CREATE TABLE IF NOT EXISTS candidate_outputs (
    day_key TEXT NOT NULL,
    event_id TEXT NOT NULL,
    draft_id TEXT NOT NULL,
    note_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (day_key, draft_id)
);

CREATE TABLE IF NOT EXISTS run_state (
    run_key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS v2_seed_snapshots (
    tweet_id TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    query TEXT NOT NULL,
    track TEXT,
    views INTEGER NOT NULL DEFAULT 0,
    likes INTEGER NOT NULL DEFAULT 0,
    replies INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (tweet_id, captured_at)
);
"""


def create_schema(db_path: str | Path) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA_SQL)

    return path
