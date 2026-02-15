PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY,
    parent_id INTEGER DEFAULT NULL,
    status TEXT NOT NULL CHECK (status IN ('Planned', 'In progress', 'Done')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT DEFAULT NULL,
    FOREIGN KEY (parent_id) REFERENCES tasks(id) ON DELETE SET NULL ON UPDATE CASCADE,
    CHECK (parent_id IS NULL OR parent_id <> id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_parent_id ON tasks(parent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

