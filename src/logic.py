from __future__ import annotations
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from src import database


def fetch_task_tree(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Fetch the full task tree preserving hierarchical order using a recursive CTE.

    Returns a list of dicts, each containing: id, parent_id, title, status, created_at, finished_at, depth, path
    where 'path' is a string like '1/4/6' representing the ancestry and is useful for ordering.
    """
    sql = """
    WITH RECURSIVE
    tree(id, parent_id, title, status, created_at, finished_at, depth, path) AS (
        SELECT id, parent_id, title, status, created_at, finished_at, 0 AS depth, printf('%s', id) AS path
        FROM tasks
        WHERE parent_id IS NULL
        UNION ALL
        SELECT t.id, t.parent_id, t.title, t.status, t.created_at, t.finished_at, tree.depth + 1, printf('%s/%s', tree.path, t.id)
        FROM tasks t
        JOIN tree ON t.parent_id = tree.id
    )
    SELECT id, parent_id, title, status, created_at, finished_at, depth, path
    FROM tree
    ORDER BY path;
    """
    cur = conn.execute(sql)
    rows = [dict(row) for row in cur.fetchall()]
    return rows


def create_task(conn: sqlite3.Connection, title: str, parent_id: Optional[int] = None, status: str = 'Planned') -> int:
    """Create a task and return its new id."""
    cur = conn.execute(
        "INSERT INTO tasks (parent_id, status, title) VALUES (?, ?, ?)", (parent_id, status, title)
    )
    conn.commit()
    return cur.lastrowid


def update_status(conn: sqlite3.Connection, task_id: int, new_status: str) -> None:
    """Update status; if moving to 'Done', set finished_at to current timestamp.
    If moving away from 'Done', clear finished_at.
    """
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    if new_status == 'Done':
        conn.execute(
            "UPDATE tasks SET status = ?, finished_at = ? WHERE id = ?",
            (new_status, now, task_id),
        )
    else:
        conn.execute(
            "UPDATE tasks SET status = ?, finished_at = NULL WHERE id = ?",
            (new_status, task_id),
        )
    conn.commit()


def delete_task(conn: sqlite3.Connection, task_id: int) -> None:
    """Delete a task by id. FK rule will handle children behavior (set NULL or cascade depending on schema)."""
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()


def merge_tasks(conn: sqlite3.Connection, ids: List[int], new_title: str) -> int:
    """Create a new parent task with `new_title` and re-parent the tasks with ids in `ids` under it.

    Returns the id of the newly created parent.
    """
    if not ids:
        raise ValueError("ids must be a non-empty list")

    # Create parent
    cur = conn.execute(
        "INSERT INTO tasks (parent_id, status, title) VALUES (?, ?, ?)",
        (None, 'Planned', new_title),
    )
    parent_id = cur.lastrowid

    # Re-parent each task
    conn.executemany("UPDATE tasks SET parent_id = ? WHERE id = ?", [(parent_id, i) for i in ids])
    conn.commit()
    return parent_id


def promote_task(conn: sqlite3.Connection, task_id: int) -> None:
    """Promote a task to top-level by setting its parent_id to NULL."""
    conn.execute("UPDATE tasks SET parent_id = NULL WHERE id = ?", (task_id,))
    conn.commit()


def get_weekly_summary(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Return tasks that were finished in the last 7 days, grouped or sorted by finished_at.

    Returns list of dicts with id, title, finished_at, status, parent_id.
    """
    seven_days_ago = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    sql = "SELECT id, parent_id, title, status, finished_at FROM tasks WHERE finished_at IS NOT NULL AND finished_at >= ? ORDER BY finished_at DESC"
    cur = conn.execute(sql, (seven_days_ago,))
    return [dict(r) for r in cur.fetchall()]


# Small convenience wrappers that open/close connections for callers that prefer not to manage connections

def fetch_task_tree_db(db_path: Optional[str] = None):
    with database.get_connection(db_path or database.DEFAULT_DB_PATH) as conn:
        return fetch_task_tree(conn)


def create_task_db(title: str, parent_id: Optional[int] = None, status: str = 'Planned') -> int:
    with database.get_connection() as conn:
        return create_task(conn, title, parent_id, status)


def update_status_db(task_id: int, new_status: str) -> None:
    with database.get_connection() as conn:
        return update_status(conn, task_id, new_status)


def delete_task_db(task_id: int) -> None:
    with database.get_connection() as conn:
        return delete_task(conn, task_id)


def merge_tasks_db(ids: List[int], new_title: str) -> int:
    with database.get_connection() as conn:
        return merge_tasks(conn, ids, new_title)


def promote_task_db(task_id: int) -> None:
    with database.get_connection() as conn:
        return promote_task(conn, task_id)


def get_weekly_summary_db() -> List[Dict[str, Any]]:
    with database.get_connection() as conn:
        return get_weekly_summary(conn)

