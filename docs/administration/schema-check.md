---
title: Schema Check
description: Validate database schema after migrations
---

# Schema Check

After running migrations, you can check that all Peewee model tables and columns exist in the configured database:

```bash
python app/check_schema.py
```

Expected output:

```text
Schema check OK: all model tables and columns exist.
```

Fresh initialization creates all application tables from the initial schema migration.
