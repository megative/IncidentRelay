def upgrade():
    """
    Legacy no-op.

    Service version is no longer stored in the database.
    Version is provided by app.version instead.
    """
    pass


def downgrade():
    """
    Legacy no-op.
    """
    pass
