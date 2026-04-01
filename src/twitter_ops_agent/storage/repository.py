from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sqlite3

from twitter_ops_agent.domain.models import (
    Account,
    CaptureResult,
    Event,
    EventBundle,
    EventContext,
    EventLink,
    EventPost,
    Post,
    PostRelation,
    StyleExample,
    utc_now,
)
from twitter_ops_agent.storage.schema import create_schema


class SqliteRepository:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = create_schema(db_path)

    def upsert_account(self, account: Account) -> None:
        with self._connect() as connection:
            upsert_account(connection, account)

    def upsert_post(self, post: Post) -> None:
        with self._connect() as connection:
            upsert_post(connection, post)

    def upsert_relation(self, relation: PostRelation) -> None:
        with self._connect() as connection:
            upsert_relation(connection, relation)

    def upsert_event(self, event: Event) -> None:
        with self._connect() as connection:
            upsert_event(connection, event)

    def attach_post_to_event(self, event_post: EventPost) -> None:
        with self._connect() as connection:
            attach_post_to_event(connection, event_post)

    def save_capture_result(self, capture: CaptureResult) -> None:
        with self._connect() as connection:
            save_capture_result(connection, capture)

    def save_style_example(
        self,
        handle: str,
        track: str | None,
        target_post_id: str,
        source_post_id: str | None,
    ) -> None:
        with self._connect() as connection:
            save_style_example(connection, handle, track, target_post_id, source_post_id)

    def mark_batch_run(self, run_key: str, value: str) -> None:
        with self._connect() as connection:
            mark_batch_run(connection, run_key, value)

    def read_run_state(self, run_key: str) -> str | None:
        with self._connect() as connection:
            return read_run_state(connection, run_key)

    def load_event_context(
        self,
        post_ids: list[str],
        conversation_ids: list[str | None],
    ) -> EventContext:
        with self._connect() as connection:
            return load_event_context(connection, post_ids, conversation_ids)

    def load_event_bundle(self, event_id: str) -> EventBundle:
        with self._connect() as connection:
            return load_event_bundle(connection, event_id)

    def persist_event_link(self, capture: CaptureResult, link: EventLink) -> None:
        with self._connect() as connection:
            persist_event_link(connection, capture, link)

    def load_style_examples(
        self,
        track: str | None,
        limit: int = 20,
        fallback_to_any_track: bool = True,
    ) -> list[StyleExample]:
        with self._connect() as connection:
            return load_style_examples(connection, track, limit, fallback_to_any_track)

    def list_relations_for_post(self, from_post_id: str) -> list[PostRelation]:
        with self._connect() as connection:
            return list_relations_for_post(connection, from_post_id)

    def list_event_posts(self, event_id: str) -> list[EventPost]:
        with self._connect() as connection:
            return list_event_posts(connection, event_id)

    def count_candidate_outputs_for_day(self, day_key: str) -> int:
        with self._connect() as connection:
            return count_candidate_outputs_for_day(connection, day_key)

    def record_candidate_output(
        self,
        day_key: str,
        event_id: str,
        draft_id: str,
        note_path: str,
    ) -> None:
        with self._connect() as connection:
            record_candidate_output(connection, day_key, event_id, draft_id, note_path)

    def record_v2_seed_snapshots(self, snapshots: list[dict[str, object]]) -> None:
        with self._connect() as connection:
            record_v2_seed_snapshots(connection, snapshots)

    def load_latest_v2_seed_snapshots(self, tweet_ids: list[str]) -> dict[str, dict[str, object]]:
        with self._connect() as connection:
            return load_latest_v2_seed_snapshots(connection, tweet_ids)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def upsert_account(connection: sqlite3.Connection, account: Account) -> None:
    connection.execute(
        """
        INSERT INTO accounts (account_id, platform, handle, display_name)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(account_id) DO UPDATE SET
            platform = excluded.platform,
            handle = excluded.handle,
            display_name = excluded.display_name
        """,
        (account.account_id, account.platform, account.handle, account.display_name),
    )


def upsert_post(connection: sqlite3.Connection, post: Post) -> None:
    connection.execute(
        """
        INSERT INTO posts (
            post_id,
            account_id,
            url,
            created_at,
            captured_at,
            text_exact,
            text_normalized,
            post_type,
            track,
            conversation_id,
            lang,
            likes,
            retweets,
            replies,
            views
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(post_id) DO UPDATE SET
            account_id = excluded.account_id,
            url = excluded.url,
            created_at = excluded.created_at,
            captured_at = excluded.captured_at,
            text_exact = excluded.text_exact,
            text_normalized = excluded.text_normalized,
            post_type = excluded.post_type,
            track = excluded.track,
            conversation_id = excluded.conversation_id,
            lang = excluded.lang,
            likes = excluded.likes,
            retweets = excluded.retweets,
            replies = excluded.replies,
            views = excluded.views
        """,
        (
            post.post_id,
            post.account_id,
            post.url,
            _serialize_datetime(post.created_at),
            _serialize_datetime(post.captured_at),
            post.text_exact,
            post.text_normalized,
            post.post_type,
            post.track,
            post.conversation_id,
            post.lang,
            post.likes,
            post.retweets,
            post.replies,
            post.views,
        ),
    )


def upsert_relation(connection: sqlite3.Connection, relation: PostRelation) -> None:
    connection.execute(
        """
        INSERT INTO post_relations (
            relation_id,
            from_post_id,
            to_post_id,
            relation_type,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(relation_id) DO UPDATE SET
            from_post_id = excluded.from_post_id,
            to_post_id = excluded.to_post_id,
            relation_type = excluded.relation_type,
            created_at = excluded.created_at
        """,
        (
            relation.relation_id,
            relation.from_post_id,
            relation.to_post_id,
            relation.relation_type,
            _serialize_datetime(relation.created_at),
        ),
    )


def upsert_event(connection: sqlite3.Connection, event: Event) -> None:
    connection.execute(
        """
        INSERT INTO events (event_id, title, track, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(event_id) DO UPDATE SET
            title = excluded.title,
            track = excluded.track,
            updated_at = excluded.updated_at
        """,
        (
            event.event_id,
            event.title,
            event.track,
            _serialize_datetime(event.created_at),
            _serialize_datetime(event.updated_at),
        ),
    )


def attach_post_to_event(connection: sqlite3.Connection, event_post: EventPost) -> None:
    connection.execute(
        """
        INSERT INTO event_posts (event_id, post_id, role_in_event, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(event_id, post_id, role_in_event) DO UPDATE SET
            created_at = excluded.created_at
        """,
        (
            event_post.event_id,
            event_post.post_id,
            event_post.role_in_event,
            _serialize_datetime(event_post.created_at),
        ),
    )


def save_capture_result(connection: sqlite3.Connection, capture: CaptureResult) -> None:
    upsert_account(connection, capture.target_account)
    upsert_post(connection, capture.target_post)

    if capture.source_account is not None:
        upsert_account(connection, capture.source_account)
    if capture.source_post is not None:
        upsert_post(connection, capture.source_post)

    for relation in capture.relations:
        upsert_relation(connection, relation)


def save_style_example(
    connection: sqlite3.Connection,
    handle: str,
    track: str | None,
    target_post_id: str,
    source_post_id: str | None,
) -> None:
    resolved_track = track or _read_post_track(connection, target_post_id)
    source_kind = _read_source_kind(connection, target_post_id, source_post_id)
    example_id = f"{handle}:{target_post_id}:{source_post_id or 'none'}"

    connection.execute(
        """
        INSERT INTO style_examples (
            example_id,
            handle,
            track,
            target_post_id,
            source_post_id,
            source_kind,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(example_id) DO UPDATE SET
            handle = excluded.handle,
            track = excluded.track,
            target_post_id = excluded.target_post_id,
            source_post_id = excluded.source_post_id,
            source_kind = excluded.source_kind,
            created_at = excluded.created_at
        """,
        (
            example_id,
            handle,
            resolved_track,
            target_post_id,
            source_post_id,
            source_kind,
            _serialize_datetime(utc_now()),
        ),
    )


def mark_batch_run(connection: sqlite3.Connection, run_key: str, value: str) -> None:
    connection.execute(
        """
        INSERT INTO run_state (run_key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(run_key) DO UPDATE SET
            value = excluded.value,
            updated_at = excluded.updated_at
        """,
        (run_key, value, _serialize_datetime(utc_now())),
    )


def read_run_state(connection: sqlite3.Connection, run_key: str) -> str | None:
    row = connection.execute(
        "SELECT value FROM run_state WHERE run_key = ?",
        (run_key,),
    ).fetchone()
    return None if row is None else str(row["value"])


def load_event_context(
    connection: sqlite3.Connection,
    post_ids: list[str],
    conversation_ids: list[str | None],
) -> EventContext:
    event_ids = _find_context_event_ids(connection, post_ids, conversation_ids)
    if not event_ids:
        return EventContext()

    events = tuple(_read_events(connection, event_ids))
    event_posts = tuple(_read_event_posts(connection, event_ids))
    posts = tuple(_read_posts_for_events(connection, event_ids))
    post_to_event = {event_post.post_id: event_post.event_id for event_post in event_posts}
    conversation_to_event = {
        post.conversation_id: post_to_event[post.post_id]
        for post in posts
        if post.conversation_id and post.post_id in post_to_event
    }

    return EventContext(
        posts=posts,
        events=events,
        event_posts=event_posts,
        by_post_id=post_to_event,
        by_conversation_id=conversation_to_event,
    )


def load_event_bundle(connection: sqlite3.Connection, event_id: str) -> EventBundle:
    events = _read_events(connection, [event_id])
    event = events[0] if events else None
    event_posts = tuple(_read_event_posts(connection, [event_id]))
    posts = tuple(_read_posts_for_events(connection, [event_id]))
    seed_post_ids = {item.post_id for item in event_posts if item.role_in_event == "seed_news"}
    seed_post = next((post for post in posts if post.post_id in seed_post_ids), posts[0] if posts else None)
    return EventBundle(
        event=event,
        posts=posts,
        event_posts=event_posts,
        seed_post=seed_post,
        related_posts=posts,
        search_query="" if seed_post is None else seed_post.text_exact,
    )


def persist_event_link(
    connection: sqlite3.Connection,
    capture: CaptureResult,
    link: EventLink,
) -> None:
    now = utc_now()
    upsert_event(
        connection,
        Event(
            event_id=link.event_id,
            title=link.title,
            track=link.track or capture.target_post.track,
            created_at=now,
            updated_at=now,
        ),
    )

    if capture.source_post is not None:
        attach_post_to_event(
            connection,
            EventPost(
                event_id=link.event_id,
                post_id=capture.source_post.post_id,
                role_in_event=link.source_role,
                created_at=now,
            ),
        )

    attach_post_to_event(
        connection,
        EventPost(
            event_id=link.event_id,
            post_id=capture.target_post.post_id,
            role_in_event=link.target_role,
            created_at=now,
        ),
    )


def load_style_examples(
    connection: sqlite3.Connection,
    track: str | None,
    limit: int = 20,
    fallback_to_any_track: bool = True,
) -> list[StyleExample]:
    rows = _query_style_examples(connection, track, limit)
    if not rows and track is not None and fallback_to_any_track:
        rows = _query_style_examples(connection, None, limit)

    return [_style_example_from_row(row) for row in rows]


def list_relations_for_post(
    connection: sqlite3.Connection,
    from_post_id: str,
) -> list[PostRelation]:
    rows = connection.execute(
        """
        SELECT relation_id, from_post_id, to_post_id, relation_type, created_at
        FROM post_relations
        WHERE from_post_id = ?
        ORDER BY created_at ASC, relation_id ASC
        """,
        (from_post_id,),
    ).fetchall()

    return [
        PostRelation(
            relation_id=str(row["relation_id"]),
            from_post_id=str(row["from_post_id"]),
            to_post_id=str(row["to_post_id"]),
            relation_type=str(row["relation_type"]),
            created_at=_parse_datetime(str(row["created_at"])),
        )
        for row in rows
    ]


def list_event_posts(connection: sqlite3.Connection, event_id: str) -> list[EventPost]:
    return _read_event_posts(connection, [event_id])


def count_candidate_outputs_for_day(connection: sqlite3.Connection, day_key: str) -> int:
    row = connection.execute(
        "SELECT COUNT(*) AS count FROM candidate_outputs WHERE day_key = ?",
        (day_key,),
    ).fetchone()
    return 0 if row is None else int(row["count"])


def record_candidate_output(
    connection: sqlite3.Connection,
    day_key: str,
    event_id: str,
    draft_id: str,
    note_path: str,
) -> None:
    connection.execute(
        """
        INSERT INTO candidate_outputs (day_key, event_id, draft_id, note_path, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(day_key, draft_id) DO UPDATE SET
            event_id = excluded.event_id,
            note_path = excluded.note_path,
            created_at = excluded.created_at
        """,
        (day_key, event_id, draft_id, note_path, _serialize_datetime(utc_now())),
    )


def record_v2_seed_snapshots(connection: sqlite3.Connection, snapshots: list[dict[str, object]]) -> None:
    rows = [
        (
            str(item["tweet_id"]),
            _serialize_datetime(item["captured_at"]),
            str(item["source_kind"]),
            str(item["query"]),
            item.get("track"),
            int(item.get("views", 0) or 0),
            int(item.get("likes", 0) or 0),
            int(item.get("replies", 0) or 0),
        )
        for item in snapshots
    ]
    connection.executemany(
        """
        INSERT INTO v2_seed_snapshots (
            tweet_id,
            captured_at,
            source_kind,
            query,
            track,
            views,
            likes,
            replies
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def load_latest_v2_seed_snapshots(connection: sqlite3.Connection, tweet_ids: list[str]) -> dict[str, dict[str, object]]:
    if not tweet_ids:
        return {}
    placeholders = ",".join("?" for _ in tweet_ids)
    rows = connection.execute(
        f"""
        SELECT s1.tweet_id, s1.captured_at, s1.source_kind, s1.query, s1.track, s1.views, s1.likes, s1.replies
        FROM v2_seed_snapshots AS s1
        JOIN (
            SELECT tweet_id, MAX(captured_at) AS max_captured_at
            FROM v2_seed_snapshots
            WHERE tweet_id IN ({placeholders})
            GROUP BY tweet_id
        ) AS latest
        ON latest.tweet_id = s1.tweet_id AND latest.max_captured_at = s1.captured_at
        """,
        tuple(tweet_ids),
    ).fetchall()
    result: dict[str, dict[str, object]] = {}
    for row in rows:
        result[str(row["tweet_id"])] = {
            "tweet_id": str(row["tweet_id"]),
            "captured_at": str(row["captured_at"]),
            "source_kind": str(row["source_kind"]),
            "query": str(row["query"]),
            "track": row["track"],
            "views": int(row["views"]),
            "likes": int(row["likes"]),
            "replies": int(row["replies"]),
        }
    return result


def _query_style_examples(
    connection: sqlite3.Connection,
    track: str | None,
    limit: int,
) -> list[sqlite3.Row]:
    if track is None:
        rows = connection.execute(
            """
            SELECT
                se.example_id,
                se.handle,
                se.track,
                se.target_post_id,
                target.text_exact AS target_text,
                target.post_type AS target_post_type,
                target.url AS target_url,
                se.source_post_id,
                source.text_exact AS source_text,
                source.url AS source_url,
                se.source_kind
            FROM style_examples AS se
            JOIN posts AS target ON target.post_id = se.target_post_id
            LEFT JOIN posts AS source ON source.post_id = se.source_post_id
            ORDER BY se.created_at DESC, se.example_id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT
                se.example_id,
                se.handle,
                se.track,
                se.target_post_id,
                target.text_exact AS target_text,
                target.post_type AS target_post_type,
                target.url AS target_url,
                se.source_post_id,
                source.text_exact AS source_text,
                source.url AS source_url,
                se.source_kind
            FROM style_examples AS se
            JOIN posts AS target ON target.post_id = se.target_post_id
            LEFT JOIN posts AS source ON source.post_id = se.source_post_id
            WHERE se.track = ?
            ORDER BY se.created_at DESC, se.example_id ASC
            LIMIT ?
            """,
            (track, limit),
        ).fetchall()

    return list(rows)


def _style_example_from_row(row: sqlite3.Row) -> StyleExample:
    return StyleExample(
        example_id=str(row["example_id"]),
        handle=str(row["handle"]),
        track=None if row["track"] is None else str(row["track"]),
        target_post_id=str(row["target_post_id"]),
        target_text=str(row["target_text"]),
        target_post_type=str(row["target_post_type"]),
        target_url=str(row["target_url"]),
        source_post_id=None if row["source_post_id"] is None else str(row["source_post_id"]),
        source_text=None if row["source_text"] is None else str(row["source_text"]),
        source_url=None if row["source_url"] is None else str(row["source_url"]),
        source_kind=str(row["source_kind"]),
    )


def _find_context_event_ids(
    connection: sqlite3.Connection,
    post_ids: list[str],
    conversation_ids: list[str | None],
) -> list[str]:
    cleaned_post_ids = [post_id for post_id in post_ids if post_id]
    cleaned_conversation_ids = [conversation_id for conversation_id in conversation_ids if conversation_id]
    if not cleaned_post_ids and not cleaned_conversation_ids:
        return []

    clauses: list[str] = []
    params: list[str] = []

    if cleaned_post_ids:
        placeholders = ", ".join("?" for _ in cleaned_post_ids)
        clauses.append(f"ep.post_id IN ({placeholders})")
        params.extend(cleaned_post_ids)
    if cleaned_conversation_ids:
        placeholders = ", ".join("?" for _ in cleaned_conversation_ids)
        clauses.append(f"p.conversation_id IN ({placeholders})")
        params.extend(cleaned_conversation_ids)

    rows = connection.execute(
        f"""
        SELECT DISTINCT ep.event_id
        FROM event_posts AS ep
        JOIN posts AS p ON p.post_id = ep.post_id
        WHERE {" OR ".join(clauses)}
        ORDER BY ep.event_id ASC
        """,
        params,
    ).fetchall()

    return [str(row["event_id"]) for row in rows]


def _read_events(connection: sqlite3.Connection, event_ids: list[str]) -> list[Event]:
    if not event_ids:
        return []

    placeholders = ", ".join("?" for _ in event_ids)
    rows = connection.execute(
        f"""
        SELECT event_id, title, track, created_at, updated_at
        FROM events
        WHERE event_id IN ({placeholders})
        ORDER BY event_id ASC
        """,
        event_ids,
    ).fetchall()

    return [
        Event(
            event_id=str(row["event_id"]),
            title=None if row["title"] is None else str(row["title"]),
            track=None if row["track"] is None else str(row["track"]),
            created_at=_parse_datetime(str(row["created_at"])),
            updated_at=_parse_datetime(str(row["updated_at"])),
        )
        for row in rows
    ]


def _read_event_posts(
    connection: sqlite3.Connection,
    event_ids: list[str],
) -> list[EventPost]:
    if not event_ids:
        return []

    placeholders = ", ".join("?" for _ in event_ids)
    rows = connection.execute(
        f"""
        SELECT event_id, post_id, role_in_event, created_at
        FROM event_posts
        WHERE event_id IN ({placeholders})
        ORDER BY created_at ASC, post_id ASC, role_in_event ASC
        """,
        event_ids,
    ).fetchall()

    return [
        EventPost(
            event_id=str(row["event_id"]),
            post_id=str(row["post_id"]),
            role_in_event=str(row["role_in_event"]),
            created_at=_parse_datetime(str(row["created_at"])),
        )
        for row in rows
    ]


def _read_posts_for_events(
    connection: sqlite3.Connection,
    event_ids: list[str],
) -> list[Post]:
    if not event_ids:
        return []

    placeholders = ", ".join("?" for _ in event_ids)
    rows = connection.execute(
        f"""
        SELECT DISTINCT
            p.post_id,
            p.account_id,
            p.url,
            p.created_at,
            p.captured_at,
            p.text_exact,
            p.text_normalized,
            p.post_type,
            p.track,
            p.conversation_id,
            p.lang,
            p.likes,
            p.retweets,
            p.replies,
            p.views
        FROM posts AS p
        JOIN event_posts AS ep ON ep.post_id = p.post_id
        WHERE ep.event_id IN ({placeholders})
        ORDER BY p.created_at ASC, p.post_id ASC
        """,
        event_ids,
    ).fetchall()

    return [_post_from_row(row) for row in rows]


def _post_from_row(row: sqlite3.Row) -> Post:
    return Post(
        post_id=str(row["post_id"]),
        account_id=str(row["account_id"]),
        url=str(row["url"]),
        created_at=_parse_datetime(str(row["created_at"])),
        captured_at=_parse_datetime(str(row["captured_at"])),
        text_exact=str(row["text_exact"]),
        text_normalized=str(row["text_normalized"]),
        post_type=str(row["post_type"]),
        track=None if row["track"] is None else str(row["track"]),
        conversation_id=None if row["conversation_id"] is None else str(row["conversation_id"]),
        lang=None if row["lang"] is None else str(row["lang"]),
        likes=int(row["likes"]),
        retweets=int(row["retweets"]),
        replies=int(row["replies"]),
        views=int(row["views"]),
    )


def _read_post_track(connection: sqlite3.Connection, post_id: str) -> str | None:
    row = connection.execute(
        "SELECT track FROM posts WHERE post_id = ?",
        (post_id,),
    ).fetchone()
    if row is None or row["track"] is None:
        return None
    return str(row["track"])


def _read_source_kind(
    connection: sqlite3.Connection,
    target_post_id: str,
    source_post_id: str | None,
) -> str:
    if source_post_id is None:
        return "standalone"

    row = connection.execute(
        """
        SELECT relation_type
        FROM post_relations
        WHERE from_post_id = ? AND to_post_id = ?
        ORDER BY created_at ASC
        LIMIT 1
        """,
        (target_post_id, source_post_id),
    ).fetchone()
    if row is None:
        return "source"
    return str(row["relation_type"])


def _serialize_datetime(value: datetime) -> str:
    return value.isoformat()


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)
