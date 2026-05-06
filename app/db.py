from pathlib import Path

from peewee import DatabaseProxy, MySQLDatabase, PostgresqlDatabase, SqliteDatabase

from app.settings import Config


database_proxy = DatabaseProxy()


def ensure_sqlite_directory(database_name):
    """
    Create parent directory for SQLite database files.
    """
    if database_name in ("", ":memory:"):
        return

    database_path = Path(database_name)

    if database_path.parent == Path("."):
        return

    database_path.parent.mkdir(parents=True, exist_ok=True)


def create_database():
    """
    Create a database instance for the configured backend.
    """

    if Config.DB_TYPE == "sqlite":
        ensure_sqlite_directory(Config.DB_NAME)

        return SqliteDatabase(
            Config.DB_NAME,
            pragmas={
                "journal_mode": "wal",
                "cache_size": -1024 * 64,
                "foreign_keys": 1,
            },
        )

    if Config.DB_TYPE == "mysql":
        return MySQLDatabase(
            Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            host=Config.DB_HOST,
            port=Config.DB_PORT or 3306,
            charset="utf8mb4",
        )

    if Config.DB_TYPE == "postgresql":
        return PostgresqlDatabase(
            Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            host=Config.DB_HOST,
            port=Config.DB_PORT or 5432,
        )

    raise RuntimeError(f"Unsupported DB_TYPE: {Config.DB_TYPE}")


def init_database():
    """
    Initialize the database proxy.
    """
    if database_proxy.obj is not None:
        return database_proxy.obj

    db = create_database()
    database_proxy.initialize(db)
    return db
