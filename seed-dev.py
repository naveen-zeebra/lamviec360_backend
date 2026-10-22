#!/usr/bin/env python
# ─────────────────────────────────────────────────────────────────────────────
# File    : seed-dev.py
# Purpose : Backend Root CLI Runner for Developer Seeder (Yopmail Test Accounts)
# Usage   : python seed-dev.py [optional_default_password]
# ─────────────────────────────────────────────────────────────────────────────

import sys
from pathlib import Path

# Ensure UTF-8 output on Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure backend root is in sys.path
BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from shared.database.seed_dev import seed_dev_database

if __name__ == "__main__":
    password = sys.argv[1] if len(sys.argv) > 1 else "Password123!"
    seed_dev_database(password=password)
