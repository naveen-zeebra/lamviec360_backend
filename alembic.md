# Alembic Database Migrations Guide

This document covers how database migrations are configured and managed in the **LamViec360 Backend** using [Alembic](https://alembic.sqlalchemy.org/).

All commands listed here run identically on **Linux servers (Ubuntu, Debian, CentOS, Alpine)**, **Docker containers**, and **Windows**.

---

## 1. Overview & Project Integration

Alembic tracks database revisions incrementally and synchronizes your database schema with SQLAlchemy models defined under `shared/models/`.

### Key Files:
* `alembic.ini` – Alembic global configuration.
* `alembic/env.py` – Connects Alembic to `shared.environment.env.DATABASE_URL` and `shared.models.Base.metadata`.
* `alembic/versions/` – Directory where all revision scripts are stored.
* `alembic.md` – This command reference and cheatsheet.

---

## 2. Environment Activation & Execution

### 🐧 On Linux Server (Ubuntu / Debian / CentOS):
```bash
# 1. Activate virtualenv
source .venv/bin/activate

# 2. Run alembic directly
alembic upgrade head

# Or run via Python module:
python3 -m alembic upgrade head

# Or run directly without activating venv (great for cron, systemd, or scripts):
./.venv/bin/alembic upgrade head
```

### 🪟 On Windows PowerShell:
```powershell
# 1. Activate virtualenv
.\.venv\Scripts\Activate.ps1

# 2. Run alembic
python -m alembic upgrade head
```

### 🐳 Inside Docker (Linux Container):
```bash
docker compose exec backend alembic upgrade head
# or
docker exec -it <container_name> alembic upgrade head
```

---

## 3. Quick Command Cheatsheet

> In all commands below, you can run either `alembic <command>` or `python3 -m alembic <command>`.

| Purpose | Linux Server / Windows Command |
| :--- | :--- |
| **Apply all pending migrations** | `alembic upgrade head` |
| **Apply only 1 step forward** | `alembic upgrade +1` |
| **Rollback last migration** | `alembic downgrade -1` |
| **Rollback all migrations** | `alembic downgrade base` |
| **Show current database revision** | `alembic current` |
| **Show latest available revision** | `alembic heads` |
| **Show migration history** | `alembic history --verbose` |
| **Check if models & DB are in sync** | `alembic check` |
| **Auto-generate revision from models** | `alembic revision --autogenerate -m "your_message"` |
| **Create empty manual revision** | `alembic revision -m "your_message"` |
| **Generate raw SQL without executing** | `alembic upgrade head --sql` |
| **Stamp existing database to latest** | `alembic stamp head` |

---

## 4. Step-by-Step Workflows

### A. Making a Schema Change (Standard Developer Workflow)

1. **Modify your SQLAlchemy Model:**
   * Edit or add columns in `shared/models/` (e.g. `user.py`, `job.py`, etc.).
   
2. **Auto-generate a new revision:**
   ```bash
   alembic revision --autogenerate -m "add_headline_to_user"
   ```
   Alembic detects differences between your models and database tables, generating a new file in `alembic/versions/<hash>_add_headline_to_user.py`.

3. **Inspect the generated revision file:**
   Always open and review the generated file in `alembic/versions/` to verify that `upgrade()` and `downgrade()` match your expectations.

4. **Apply the migration to your database:**
   ```bash
   alembic upgrade head
   ```

5. **Commit the revision file to Git:**
   Always commit new files in `alembic/versions/` to version control along with your model changes.

---

### B. Rolling Back Migrations

If you need to undo a change:

* **Undo the most recent migration:**
  ```bash
  alembic downgrade -1
  ```
* **Roll back to a specific revision:**
  ```bash
  alembic downgrade <revision_id>
  ```
* **Roll back all migrations (resets schema completely):**
  ```bash
  alembic downgrade base
  ```

---

### C. First-Time Setup on an Existing Database (`stamp`)

If your database tables were already created previously using `Base.metadata.create_all()`:

1. Generate your initial baseline revision:
   ```bash
   alembic revision --autogenerate -m "initial_schema"
   ```
2. Because the tables already exist in the database, do **not** run `upgrade head` (it would fail trying to recreate existing tables). Instead, **stamp** the database:
   ```bash
   alembic stamp head
   ```
   This marks the current database as up-to-date in the `alembic_version` table without re-executing the DDL.

---

### D. Team Collaboration & Merge Conflicts

When two developers create migrations simultaneously on different git branches, you may see multiple heads:

```bash
alembic heads
```
Output:
```text
1a2b3c4d5e (head)
5f6g7h8i9j (head)
```

To merge multiple heads into a single unified branch:
```bash
alembic merge heads -m "merge_conflicting_heads"
```
Then run:
```bash
alembic upgrade head
```

---

### E. Generating Raw SQL for Production / DBA Review ("Offline Mode")

If your production deployment requires giving raw SQL scripts to a DBA instead of running migrations directly:

```bash
# Output all pending SQL statements to console
alembic upgrade head --sql

# Or save the SQL to a file on Linux
alembic upgrade head --sql > /tmp/migration_output.sql

# Generate SQL between two specific revisions
alembic upgrade <old_revision>:<new_revision> --sql > diff.sql
```

---

## 5. Writing Custom Migrations (Manual Operations)

Alembic revision files use the `op` object to modify the database. Common examples:

### Adding a Column:
```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('users', sa.Column('bio', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('users', 'bio')
```

### Creating an Index:
```python
def upgrade():
    op.create_index('ix_jobs_salary_min', 'job_postings', ['salary_min'], unique=False)

def downgrade():
    op.drop_index('ix_jobs_salary_min', table_name='job_postings')
```

### Renaming a Column:
```python
def upgrade():
    op.alter_column('users', 'mobile_no', new_column_name='phone_number')

def downgrade():
    op.alter_column('users', 'phone_number', new_column_name='mobile_no')
```

### Safe Data Updates in a Migration:
```python
def upgrade():
    op.execute("UPDATE users SET is_active = TRUE WHERE is_active IS NULL")

def downgrade():
    pass
```

---

## 6. Linux Server & Production Deployment Patterns

### Pattern 1: Automated Deploy Script (`deploy.sh` on Linux)
```bash
#!/bin/bash
set -e

echo "=== Pulling latest changes ==="
git pull origin main

echo "=== Activating virtual environment ==="
source .venv/bin/activate
pip install -r requirements.txt

echo "=== Running Database Migrations ==="
alembic upgrade head

echo "=== Reloading Application (PM2 / Systemd) ==="
pm2 reload ecosystem.config.js --update-env
# or: sudo systemctl restart jobportal-backend

echo "=== Deployment Complete ==="
```

### Pattern 2: Docker Entrypoint (`entrypoint.sh`)
If running in Docker on Linux, automatically apply migrations before starting gateway servers:
```bash
#!/bin/sh
set -e

echo "Applying database migrations..."
alembic upgrade head

echo "Starting services..."
exec python run.py
```

### Pattern 3: Linux Systemd One-Off Service
You can create a pre-start migration service `/etc/systemd/system/jobportal-migration.service`:
```ini
[Unit]
Description=JobPortal Alembic Database Migration
After=network.target postgresql.service

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=/var/www/jobportal_backend
ExecStart=/var/www/jobportal_backend/.venv/bin/alembic upgrade head

[Install]
WantedBy=multi-user.target
```
