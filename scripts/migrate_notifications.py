import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.database.session import engine
from sqlalchemy import text, inspect

sql_statements = [
    "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS channel VARCHAR(20) NOT NULL DEFAULT 'in_app'",
    "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS delivery_status VARCHAR(20) NOT NULL DEFAULT 'delivered'",
    "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS scheduled_send_time TIMESTAMP WITHOUT TIME ZONE NULL",
    "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS action_url VARCHAR(500) NULL",
    "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS template_id VARCHAR(50) NULL",
    "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS language VARCHAR(10) NOT NULL DEFAULT 'vi'",
]

with engine.begin() as conn:
    for stmt in sql_statements:
        conn.execute(text(stmt))

insp = inspect(engine)
cols = {c['name'] for c in insp.get_columns('notifications')}
required = {'channel', 'delivery_status', 'scheduled_send_time', 'action_url', 'template_id', 'language'}
assert required.issubset(cols), f"Missing columns: {required - cols}"
print(f"Migration completed! All notification columns present: {required.intersection(cols)}")

