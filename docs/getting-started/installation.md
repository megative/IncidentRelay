---
title: Installation
description: Install IncidentRelay from source
---

# Installation

Clone the repository:

```bash
git clone https://github.com/roxy-wi/IncidentRelay.git
cd IncidentRelay
```

Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Initialize the database

Run migrations:

```bash
python app/migrate.py migrate
```

Show migration status:

```bash
python app/migrate.py list
```

Check schema after migrations:

```bash
python app/check_schema.py
```

Expected output:

```text
Schema check OK: all model tables and columns exist.
```

## Create the first administrator

```bash
python manage.py create-admin \
  --username admin \
  --password 'change-me-123' \
  --email admin@example.com
```

The administrator is needed for the first login and initial setup.

## Start the service

For local development:

```bash
python run.py
```

Open:

```text
http://127.0.0.1:8080/login
```

For production web serving:

```bash
gunicorn -w 4 -b 0.0.0.0:8080 'app:create_app()'
```

Run the scheduler separately if you have a dedicated scheduler entrypoint:

```bash
python scheduler.py
```

For local testing, `python run.py` is enough.
