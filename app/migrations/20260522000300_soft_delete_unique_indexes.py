from app.db import init_database

db = init_database()


def _is_sqlite():
    return db.__class__.__name__.lower().startswith("sqlite")


def _is_postgres():
    name = db.__class__.__name__.lower()
    return "postgres" in name or "postgre" in name


def upgrade():
    if _is_sqlite():
        _upgrade_sqlite()
        return

    if _is_postgres():
        _upgrade_postgres()
        return

    # Fallback: do the safest possible generic operations.
    _upgrade_sqlite()


def downgrade():
    if _is_sqlite():
        _downgrade_sqlite()
        return

    if _is_postgres():
        _downgrade_postgres()
        return

    _downgrade_sqlite()


def _upgrade_postgres():
    # rotation: remove old ordinary unique constraint/index.
    db.execute_sql("""
        ALTER TABLE rotation
        DROP CONSTRAINT IF EXISTS rotation_team_id_name;
    """)

    db.execute_sql("""
        DROP INDEX IF EXISTS rotation_team_id_name;
    """)

    db.execute_sql("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_rotation_team_name_not_deleted
        ON rotation(team_id, name)
        WHERE deleted = false;
    """)

    # rotation_layer: remove old ordinary unique constraint/index.
    db.execute_sql("""
        ALTER TABLE rotation_layer
        DROP CONSTRAINT IF EXISTS rotation_layer_rotation_id_name;
    """)

    db.execute_sql("""
        DROP INDEX IF EXISTS rotation_layer_rotation_id_name;
    """)

    db.execute_sql("""
        DROP INDEX IF EXISTS rotationlayer_rotation_id_name;
    """)

    db.execute_sql("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_rotation_layer_rotation_name_not_deleted
        ON rotation_layer(rotation_id, name)
        WHERE deleted = false;
    """)


def _upgrade_sqlite():
    # SQLite does not support ALTER TABLE ... DROP CONSTRAINT.
    # If the old uniqueness was created as an index, this removes it.
    # If it was embedded as a table constraint in an old SQLite DB, SQLite
    # would require a table rebuild. Fresh CI DBs with the updated models
    # should not have that embedded constraint.

    db.execute_sql("""
        DROP INDEX IF EXISTS rotation_team_id_name;
    """)

    db.execute_sql("""
        DROP INDEX IF EXISTS rotation_layer_rotation_id_name;
    """)

    db.execute_sql("""
        DROP INDEX IF EXISTS rotationlayer_rotation_id_name;
    """)

    db.execute_sql("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_rotation_team_name_not_deleted
        ON rotation(team_id, name)
        WHERE deleted = 0;
    """)

    db.execute_sql("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_rotation_layer_rotation_name_not_deleted
        ON rotation_layer(rotation_id, name)
        WHERE deleted = 0;
    """)


def _downgrade_postgres():
    db.execute_sql("""
        DROP INDEX IF EXISTS ux_rotation_layer_rotation_name_not_deleted;
    """)

    db.execute_sql("""
        DROP INDEX IF EXISTS ux_rotation_team_name_not_deleted;
    """)

    db.execute_sql("""
        ALTER TABLE rotation
        ADD CONSTRAINT rotation_team_id_name UNIQUE(team_id, name);
    """)

    db.execute_sql("""
        ALTER TABLE rotation_layer
        ADD CONSTRAINT rotation_layer_rotation_id_name UNIQUE(rotation_id, name);
    """)


def _downgrade_sqlite():
    db.execute_sql("""
        DROP INDEX IF EXISTS ux_rotation_layer_rotation_name_not_deleted;
    """)

    db.execute_sql("""
        DROP INDEX IF EXISTS ux_rotation_team_name_not_deleted;
    """)

    db.execute_sql("""
        CREATE UNIQUE INDEX IF NOT EXISTS rotation_team_id_name
        ON rotation(team_id, name);
    """)

    db.execute_sql("""
        CREATE UNIQUE INDEX IF NOT EXISTS rotation_layer_rotation_id_name
        ON rotation_layer(rotation_id, name);
    """)
