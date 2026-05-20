class SafeFormatDict(dict):
    """Keep unknown template placeholders unchanged."""

    def __missing__(self, key):
        return "{" + key + "}"
