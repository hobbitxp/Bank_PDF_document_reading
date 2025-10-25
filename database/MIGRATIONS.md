# Database Migrations with Alembic

This document describes how to manage database schema changes using Alembic.

## Overview

We use Alembic for database version control and migrations. This allows:
- Track schema changes over time
- Apply/rollback migrations safely
- Maintain consistency across environments

## Setup

Alembic is already configured in:
- `alembic.ini` - Configuration file
- `alembic/env.py` - Environment setup
- `alembic/versions/` - Migration scripts

Dependencies are in `requirements.txt`:
```
alembic>=1.13.0
psycopg2-binary>=2.9.9
```

## Configuration

Alembic reads the database URL from the `DATABASE_URL` environment variable:

```bash
export DATABASE_URL="postgresql://user:password@host:port/database"
```

Default (if not set):
```
postgresql://postgres:postgres@localhost:5432/bank_statements
```

## Common Commands

### Check Current Version
```bash
alembic current
```

### View Migration History
```bash
alembic history --verbose
```

### Upgrade to Latest
```bash
alembic upgrade head
```

### Upgrade to Specific Version
```bash
alembic upgrade 001_initial
```

### Downgrade One Step
```bash
alembic downgrade -1
```

### Downgrade to Base (Remove All)
```bash
alembic downgrade base
```

### Create New Migration
```bash
alembic revision -m "description of changes"
```

### Auto-Generate Migration (with SQLAlchemy models)
```bash
alembic revision --autogenerate -m "description"
```

## Docker Usage

### Option 1: Run Alembic Inside Container

First, rebuild Docker image with Alembic:
```bash
# Update Dockerfile to include Alembic
docker compose build api
docker compose up -d

# Run migrations inside container
docker compose exec api alembic upgrade head
```

### Option 2: Run From Host (Current Setup)

Connect to Docker database from host:
```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/bank_statements"
alembic upgrade head
```

### Option 3: Use Migration Script

```bash
python scripts/run_migrations.py upgrade head
python scripts/run_migrations.py downgrade base
python scripts/run_migrations.py current
```

## Initial Migration (001_initial)

The first migration creates:

**Tables:**
- `analyses` - Salary analysis results
- `audit_logs` - API operation audit trail

**Indexes:**
- `analyses`: user_id, confidence, detected_salary, created_at
- `audit_logs`: user_id, analysis_id, action, status, created_at

**Constraints:**
- `analyses.confidence`: CHECK IN ('high', 'medium', 'low')
- `audit_logs.status`: CHECK IN ('success', 'failed', 'pending')
- Foreign key: `audit_logs.analysis_id` → `analyses.id`

## Creating New Migrations

1. **Write Tests First (TDD)**:
   ```python
   # tests/test_migrations.py
   @pytest.mark.integration
   async def test_new_migration():
       # Test migration logic
       pass
   ```

2. **Create Migration**:
   ```bash
   alembic revision -m "add_user_preferences_table"
   ```

3. **Edit Migration File**:
   ```python
   # alembic/versions/YYYYMMDD_HHMM_002_add_user_preferences_table.py
   def upgrade() -> None:
       op.create_table(
           'user_preferences',
           sa.Column('id', sa.Integer, primary_key=True),
           # ... more columns
       )
   
   def downgrade() -> None:
       op.drop_table('user_preferences')
   ```

4. **Test Migration**:
   ```bash
   # Test upgrade
   alembic upgrade head
   
   # Test downgrade
   alembic downgrade -1
   
   # Re-upgrade
   alembic upgrade head
   ```

5. **Run Integration Tests**:
   ```bash
   pytest tests/test_migrations.py -v -m integration
   ```

## Best Practices

1. **Always Test Migrations**
   - Test both upgrade and downgrade
   - Test on empty database
   - Test with existing data

2. **One Migration Per Feature**
   - Keep migrations focused and small
   - Easier to review and rollback

3. **Never Edit Applied Migrations**
   - Create new migration to fix issues
   - Editing breaks version history

4. **Include Rollback Logic**
   - Always implement `downgrade()`
   - Test downgrade path

5. **Backup Before Production**
   ```bash
   # Backup database
   pg_dump -U postgres bank_statements > backup.sql
   
   # Run migration
   alembic upgrade head
   
   # If issues, restore
   psql -U postgres bank_statements < backup.sql
   ```

## Troubleshooting

### "relation already exists"
Migration already applied or manual schema exists.
```bash
# Stamp current version without running
alembic stamp head
```

### "can't connect to database"
Check `DATABASE_URL` environment variable:
```bash
echo $DATABASE_URL
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/bank_statements"
```

### "password authentication failed"
Check credentials in DATABASE_URL match docker-compose.yml:
```yaml
# docker-compose.yml
environment:
  - POSTGRES_PASSWORD=postgres  # Should match DATABASE_URL
```

### Reset Everything
```bash
# Drop all tables
alembic downgrade base

# Or drop alembic_version manually
psql -U postgres -d bank_statements -c "DROP TABLE IF EXISTS alembic_version CASCADE"

# Re-run migrations
alembic upgrade head
```

## Production Deployment

1. **Backup Database**:
   ```bash
   pg_dump -h prod-host -U user -d bank_statements > backup_$(date +%Y%m%d).sql
   ```

2. **Test on Staging**:
   ```bash
   export DATABASE_URL="postgresql://user:pass@staging-host:5432/bank_statements"
   alembic upgrade head
   ```

3. **Apply to Production**:
   ```bash
   export DATABASE_URL="postgresql://user:pass@prod-host:5432/bank_statements"
   alembic upgrade head
   ```

4. **Verify**:
   ```bash
   alembic current
   psql -h prod-host -U user -d bank_statements -c "\dt"
   ```

## Files

```
alembic/
├── env.py                          # Environment configuration
├── script.py.mako                  # Migration template
└── versions/
    └── 001_initial.py              # Initial schema migration

alembic.ini                         # Alembic configuration
scripts/run_migrations.py           # Helper script
tests/test_migrations.py            # Migration integration tests
```

## References

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- Project: `.github/DESIGN.md` (Section 2.2 - Database Schema)
