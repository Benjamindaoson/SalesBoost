# SalesBoost Database Migrations

This directory contains Alembic database migrations.

## Setup

1. Install Alembic:
```bash
pip install alembic
```

2. Initialize Alembic (already done):
```bash
alembic init alembic
```

3. Configure `alembic.ini` with your database URL

## Usage

### Create a new migration

```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific revision
alembic upgrade <revision_id>

# Downgrade one revision
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade <revision_id>
```

### View migration history

```bash
alembic history
alembic current
```

## Quick Start

For initial setup, use the init_database.py script instead:

```bash
python scripts/init_database.py
```

This will create all tables and seed initial data.
