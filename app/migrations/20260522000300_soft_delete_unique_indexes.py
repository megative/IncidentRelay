from app.db import init_database

db = init_database()


def upgrade():
    # Rotation: remove old unique constraint/index.
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


def downgrade():
    db.execute_sql("""
        ALTER TABLE rotation
        ADD CONSTRAINT rotation_team_id_name UNIQUE(team_id, name);
    """)

    db.execute_sql("""
        ALTER TABLE rotation_layer
        ADD CONSTRAINT rotation_layer_rotation_id_name UNIQUE(rotation_id, name);
    """)
