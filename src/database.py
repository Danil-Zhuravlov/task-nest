import sqlite3
from pathlib import Path
from typing import List

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "tasks.db"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY,
    parent_id INTEGER DEFAULT NULL,
    status TEXT NOT NULL CHECK (status IN ('Planned', 'In progress', 'Done')),
    title TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT DEFAULT NULL,
    FOREIGN KEY (parent_id) REFERENCES tasks(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CHECK (parent_id IS NULL OR parent_id <> id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_parent_id ON tasks(parent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
"""


def get_connection(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON;")
    # Use row factory for convenience in callers
    connection.row_factory = sqlite3.Row
    return connection


def _table_info(connection: sqlite3.Connection, table: str) -> List[sqlite3.Row]:
    cur = connection.execute(f"PRAGMA table_info({table});")
    return cur.fetchall()


def _rebuild_tasks_table(connection: sqlite3.Connection) -> None:
    """Rebuild the tasks table to match the desired schema (used for migrations).

    This handles older DBs that may have different column names (finished_at) or FK behavior.
    The procedure creates a new table, copies data, drops the old table, and renames the new one.
    """
    # Create new table with desired schema
    connection.executescript("""
    PRAGMA foreign_keys = OFF;
    BEGIN TRANSACTION;

    CREATE TABLE IF NOT EXISTS tasks_new (
        id INTEGER PRIMARY KEY,
        parent_id INTEGER DEFAULT NULL,
        status TEXT NOT NULL CHECK (status IN ('Planned', 'In progress', 'Done')),
        title TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT DEFAULT NULL,
        FOREIGN KEY (parent_id) REFERENCES tasks_new(id) ON DELETE CASCADE ON UPDATE CASCADE,
        CHECK (parent_id IS NULL OR parent_id <> id)
    );

    -- Copy data from old table to new table where possible (map finished_at -> completed_at)
    INSERT INTO tasks_new (id, parent_id, status, title, created_at, completed_at)
    SELECT id, parent_id, status,
           COALESCE(title, ''),
           COALESCE(created_at, CURRENT_TIMESTAMP),
           COALESCE(
               (SELECT finished_at FROM tasks WHERE tasks.id = tasks.id),
               (SELECT completed_at FROM tasks WHERE tasks.id = tasks.id)
           )
    FROM tasks;

    DROP TABLE tasks;
    ALTER TABLE tasks_new RENAME TO tasks;

    COMMIT;
    PRAGMA foreign_keys = ON;
    """)
    # Recreate indexes
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tasks_parent_id ON tasks(parent_id);")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);")
    connection.commit()


def _ensure_schema(connection: sqlite3.Connection) -> None:
    # Create table if missing
    connection.executescript(SCHEMA_SQL)
    connection.commit()

    # Inspect current columns to decide if migration is needed
    cols = [r[1] for r in _table_info(connection, 'tasks')]
    # If legacy finished_at exists or FK doesn't have CASCADE we rebuild
    needs_rebuild = False
    if 'completed_at' not in cols:
        needs_rebuild = True

    if needs_rebuild:
        _rebuild_tasks_table(connection)


def initialize_database(db_path: Path | str = DEFAULT_DB_PATH) -> Path:
    with get_connection(db_path) as connection:
        _ensure_schema(connection)
    return Path(db_path)


if __name__ == "__main__":
    initialize_database()
    print(f"Initialized database at {DEFAULT_DB_PATH}")
