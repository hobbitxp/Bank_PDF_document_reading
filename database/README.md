# Database Setup Guide

## Prerequisites
- PostgreSQL 15+ installed
- psql CLI tool
- Database user with CREATE DATABASE privileges

## Quick Start

### 1. Create Database
```bash
psql -U postgres
CREATE DATABASE bank_analyzer;
\c bank_analyzer
```

### 2. Apply Schema
```bash
psql -U postgres -d bank_analyzer -f database/schema.sql
```

### 3. Verify Tables
```bash
psql -U postgres -d bank_analyzer
\dt
```

Expected output:
```
              List of relations
 Schema |       Name       | Type  |  Owner   
--------+------------------+-------+----------
 public | analyses         | table | postgres
 public | audit_logs       | table | postgres
 public | masked_mappings  | table | postgres
 public | statements       | table | postgres
 public | transactions     | table | postgres
```

## Docker Setup

### Using docker-compose
```bash
docker-compose up -d db
docker-compose exec db psql -U bankuser -d bankdb -f /schema.sql
```

### Manual Docker Container
```bash
# Run PostgreSQL container
docker run --name bank-db \
  -e POSTGRES_DB=bank_analyzer \
  -e POSTGRES_USER=bankuser \
  -e POSTGRES_PASSWORD=changeme \
  -p 5432:5432 \
  -v $(pwd)/database:/database \
  -d postgres:15-alpine

# Apply schema
docker exec -i bank-db psql -U bankuser -d bank_analyzer < database/schema.sql
```

## Connection String

### Development
```
postgresql://bankuser:changeme@localhost:5432/bank_analyzer
```

### Production (Environment Variable)
```bash
export DATABASE_URL="postgresql://user:pass@host:5432/dbname?sslmode=require"
```

## Test Queries

Run sample queries to verify setup:
```bash
psql -U postgres -d bank_analyzer -f database/queries.sql
```

## Backup & Restore

### Backup
```bash
pg_dump -U postgres bank_analyzer > backup_$(date +%Y%m%d).sql
```

### Restore
```bash
psql -U postgres -d bank_analyzer < backup_20251025.sql
```

## Security Notes

1. **Change default passwords** in production
2. **masked_mappings table** contains sensitive encrypted data
3. Use **SSL/TLS** for database connections in production
4. Configure **pg_hba.conf** to restrict access
5. Enable **audit logging** in PostgreSQL

## Monitoring

### Check database size
```sql
SELECT pg_size_pretty(pg_database_size('bank_analyzer'));
```

### Check table sizes
```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Active connections
```sql
SELECT count(*) FROM pg_stat_activity WHERE datname = 'bank_analyzer';
```

## Troubleshooting

### Connection refused
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check port
sudo netstat -plnt | grep 5432
```

### Permission denied
```bash
# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE bank_analyzer TO bankuser;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bankuser;
```

### Schema already exists
```bash
# Drop and recreate
DROP DATABASE bank_analyzer;
CREATE DATABASE bank_analyzer;
```
