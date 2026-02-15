"""Temporary script to seed tasks.db with sample hierarchical tasks.
Inserts: 1 parent, 2 children, 1 grandchild.
"""
from pathlib import Path
import sys

# Ensure project root is on sys.path so `from src import database` works when running from scripts/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import database as db


def main():
    # Ensure schema and DB exist
    db.initialize_database()

    # Insert tasks in a single transaction
    with db.get_connection() as conn:
        cur = conn.cursor()
        # Parent task
        cur.execute("INSERT INTO tasks (parent_id, status) VALUES (?, ?)", (None, "Planned"))
        parent_id = cur.lastrowid

        # Two children of parent
        cur.execute("INSERT INTO tasks (parent_id, status) VALUES (?, ?)", (parent_id, "Planned"))
        child1_id = cur.lastrowid

        cur.execute("INSERT INTO tasks (parent_id, status) VALUES (?, ?)", (parent_id, "Planned"))
        child2_id = cur.lastrowid

        # One grandchild (child of the first child)
        cur.execute("INSERT INTO tasks (parent_id, status) VALUES (?, ?)", (child1_id, "Planned"))
        grandchild_id = cur.lastrowid

    print("Inserted IDs:")
    print(f"  parent:     {parent_id}")
    print(f"  child 1:    {child1_id}")
    print(f"  child 2:    {child2_id}")
    print(f"  grandchild: {grandchild_id}")

    # Show all rows for verification
    print("\nCurrent rows in tasks table:")
    with db.get_connection() as conn:
        for row in conn.execute("SELECT id, parent_id, status, created_at, finished_at FROM tasks ORDER BY id"):
            print(row)


if __name__ == "__main__":
    main()
