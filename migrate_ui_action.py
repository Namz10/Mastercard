import os
from sqlalchemy import text
from apps.api.db import engine

def add_ui_action_column():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE killchain_atlas ADD COLUMN IF NOT EXISTS ui_action VARCHAR(12) DEFAULT 'pending';"))

if __name__ == "__main__":
    add_ui_action_column()
    print("ui_action column ensured")
