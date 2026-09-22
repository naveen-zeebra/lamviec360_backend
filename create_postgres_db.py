import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared.environment import env

def create_database_if_not_exists():
    """
    Connects to Postgres server's default 'postgres' database
    and creates the target database if it does not already exist.
    """
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    db_name = env.POSTGRES_DB
    user = env.POSTGRES_USER
    password = env.POSTGRES_PASSWORD
    host = env.POSTGRES_HOST
    port = env.POSTGRES_PORT

    print(f"Connecting to PostgreSQL server at {host}:{port} as user '{user}'...")
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=user,
            password=password,
            host=host,
            port=port,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}';")
        exists = cursor.fetchone()

        if not exists:
            print(f"Creating database '{db_name}'...")
            cursor.execute(f'CREATE DATABASE "{db_name}";')
            print(f"[OK] Database '{db_name}' created successfully!")
        else:
            print(f"[OK] Database '{db_name}' already exists.")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"[ERROR] Could not create database: {e}")
        print("Please check your PostgreSQL credentials and server status.")

if __name__ == "__main__":
    create_database_if_not_exists()
