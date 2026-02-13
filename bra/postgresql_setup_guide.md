# PostgreSQL Integration - Complete Deployment Guide

## Overview

This guide walks you through setting up PostgreSQL on your Ubuntu 24.04 EC2 instance and integrating it with your Drug Analysis API.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Flask API Server                         │
│                         (server.py)                              │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Queue Manager                              │
│              (Processes jobs in background)                      │
└────────┬───────────────────────────────────┬────────────────────┘
         │                                   │
         │ (Main Thread)                     │ (Async DB Thread)
         ▼                                   ▼
┌─────────────────────┐           ┌──────────────────────────────┐
│  Analysis Pipeline  │           │    Database Handler          │
│  (main.py)          │           │    (Non-blocking ops)        │
└─────────────────────┘           └──────────┬───────────────────┘
                                              │
                                              ▼
                                  ┌────────────────────────────┐
                                  │   PostgreSQL Database      │
                                  │   (Persistent Storage)     │
                                  └────────────────────────────┘
```

**Key Features:**
- ✅ Non-blocking database operations (separate thread)
- ✅ Main analysis pipeline stays fast
- ✅ Results persist in database
- ✅ Can query old results anytime
- ✅ Auto-cleanup of old data

---

## Part 1: PostgreSQL Setup on EC2

### Step 1: Upload Setup Script

```bash
# On your EC2 instance
cd /home/ubuntu
```

Upload the `setup_postgresql.sh` script to this directory.

### Step 2: Make Script Executable

```bash
chmod +x setup_postgresql.sh
```

### Step 3: Run Setup Script

```bash
./setup_postgresql.sh
```

**What this script does:**
1. ✅ Updates system packages
2. ✅ Installs PostgreSQL 16
3. ✅ Creates database `drug_analysis`
4. ✅ Creates user `drug_api_user` with secure password
5. ✅ Creates tables: `analysis_results`, `medication_analyses`
6. ✅ Sets up indexes for fast queries
7. ✅ Saves credentials to `~/db_credentials.txt`

**Expected Output:**
```
==========================================
PostgreSQL Setup Complete!
==========================================
✓ Database: drug_analysis
✓ User: drug_api_user
✓ Password saved to: /home/ubuntu/db_credentials.txt
```

### Step 4: View Credentials

```bash
cat ~/db_credentials.txt
```

**Save these credentials** - you'll need them for the `.env` file.

---

## Part 2: Install Python Dependencies

### Install PostgreSQL Python Driver

```bash
pip install psycopg2-binary python-dotenv --break-system-packages
```

**What these packages do:**
- `psycopg2-binary`: PostgreSQL database adapter for Python
- `python-dotenv`: Load environment variables from `.env` file

---

## Part 3: Deploy Updated Code

### Step 1: Create Project Structure

```bash
cd /path/to/your/project

# Create database utilities directory
mkdir -p utils/database
```

### Step 2: Copy Files

Copy these files to your project:

1. **Database Handler**
   ```bash
   cp db_handler.py utils/database/
   ```

2. **Updated Queue Manager**
   ```bash
   cp queue_manager_with_database.py utils/queue_manager/queue_manager.py
   ```

3. **Updated Server**
   ```bash
   cp server_with_database.py server.py
   ```

### Step 3: Create .env File

```bash
# Copy template
cp .env.template .env

# Edit with your database credentials
nano .env
```

Replace `YOUR_PASSWORD_HERE` with the password from `~/db_credentials.txt`.

**Example .env:**
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=drug_analysis
DB_USER=drug_api_user
DB_PASSWORD=aB3xK9mP2qL7nV5tR8wE1yU4iO6zA0sD

NUM_WORKERS=2
```

### Step 4: Secure the .env File

```bash
chmod 600 .env
```

**Add to .gitignore:**
```bash
echo ".env" >> .gitignore
echo "db_credentials.txt" >> .gitignore
```

---

## Part 4: Test Database Connection

### Test Script

Create `test_db.py`:

```python
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    
    print("✓ Database connection successful!")
    print(f"PostgreSQL version: {version[0]}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"✗ Database connection failed: {e}")
```

Run test:
```bash
python test_db.py
```

**Expected output:**
```
✓ Database connection successful!
PostgreSQL version: PostgreSQL 16.x on x86_64-pc-linux-gnu
```

---

## Part 5: Start the Server

### Load Environment Variables

```bash
# Load .env file
export $(cat .env | xargs)
```

**Or** use python-dotenv (recommended):

Update your `server.py` to include at the top:
```python
from dotenv import load_dotenv
load_dotenv()  # Load .env file
```

### Start Server

```bash
python server.py
```

**Expected output:**
```
================================================================================
Drug Analysis API Server v2.0
With PostgreSQL Database Integration
================================================================================
✓ Database handler initialized (Host: localhost, DB: drug_analysis)
✓ Connection pool initialized (5 connections)
✓ Database worker thread started
✓ Database integration enabled
✓ Started 2 worker threads
Server: http://0.0.0.0:8000
Workers: 2
Database: Enabled
================================================================================
```

---

## Part 6: Test the Integration

### Submit a Test Job

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d @test_input.json
```

**Response:**
```json
{
  "status": "accepted",
  "job_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "message": "Job queued for processing",
  "poll_url": "/status/f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

### Check Status (Immediate)

```bash
curl http://localhost:8000/status/f47ac10b-58cc-4372-a567-0e02b2c3d479
```

**Response (while processing):**
```json
{
  "job_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "processing",
  "created_at": "2026-02-14T10:30:00",
  "started_at": "2026-02-14T10:30:01"
}
```

### Check Status (After completion)

```bash
curl http://localhost:8000/status/f47ac10b-58cc-4372-a567-0e02b2c3d479
```

**Response (completed):**
```json
{
  "job_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "completed",
  "created_at": "2026-02-14T10:30:00",
  "started_at": "2026-02-14T10:30:01",
  "completed_at": "2026-02-14T10:30:20",
  "execution_time": 19.04,
  "result": { ... complete analysis result ... }
}
```

### Query Same Job Later (From Database)

Even after server restart:

```bash
curl http://localhost:8000/status/f47ac10b-58cc-4372-a567-0e02b2c3d479
```

**Response:**
```json
{
  "job_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "completed",
  "result": { ... },
  "source": "database",
  "note": "Retrieved from database (analysis completed earlier)"
}
```

---

## Part 7: Database Management

### View Database Statistics

```bash
curl http://localhost:8000/database/stats
```

**Response:**
```json
{
  "total_analyses": 150,
  "completed": 142,
  "failed": 8,
  "processing": 0,
  "queued": 0,
  "avg_execution_time": 18.5,
  "max_execution_time": 45.2,
  "min_execution_time": 12.1
}
```

### View Recent Analyses

```bash
# Get 10 most recent
curl http://localhost:8000/database/recent?limit=10

# Get only completed
curl "http://localhost:8000/database/recent?status=completed&limit=5"
```

### Clean Up Old Data

Remove jobs older than 30 days:

```bash
curl -X POST http://localhost:8000/database/cleanup \
  -H "Content-Type: application/json" \
  -d '{"days": 30}'
```

**Response:**
```json
{
  "status": "success",
  "removed_jobs": 45,
  "days": 30
}
```

---

## Part 8: Database Access (Direct)

### Using psql Command Line

```bash
psql -U drug_api_user -d drug_analysis -h localhost
```

**Useful queries:**

```sql
-- View recent analyses
SELECT job_id, status, patient_name, created_at, execution_time
FROM analysis_results
ORDER BY created_at DESC
LIMIT 10;

-- Count by status
SELECT status, COUNT(*) 
FROM analysis_results 
GROUP BY status;

-- View medication analyses
SELECT medication_name, diagnosis, safety_outcome, COUNT(*)
FROM medication_analyses
GROUP BY medication_name, diagnosis, safety_outcome
ORDER BY COUNT(*) DESC;

-- Find jobs with critical alerts
SELECT job_id, patient_name, created_at
FROM analysis_results
WHERE has_critical_alerts = true
ORDER BY created_at DESC;
```

---

## API Endpoints Reference

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze` | POST | Submit analysis job |
| `/status/<job_id>` | GET | Get job status (checks memory & DB) |
| `/health` | GET | Health check with DB status |

### Database Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/database/stats` | GET | Database statistics |
| `/database/recent` | GET | Recent analyses |
| `/database/cleanup` | POST | Clean old jobs |

### Queue Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/queue/stats` | GET | Queue statistics |
| `/queue/cleanup` | POST | Clean memory jobs |

---

## Monitoring and Maintenance

### Daily Health Check

```bash
curl http://localhost:8000/health
```

### Weekly Cleanup

Set up a cron job:

```bash
crontab -e
```

Add:
```cron
# Clean up old jobs every Sunday at 2 AM
0 2 * * 0 curl -X POST http://localhost:8000/database/cleanup -H "Content-Type: application/json" -d '{"days": 30}'
```

### Database Backup

```bash
# Create backup
pg_dump -U drug_api_user -d drug_analysis > backup_$(date +%Y%m%d).sql

# Restore from backup
psql -U drug_api_user -d drug_analysis < backup_20260214.sql
```

---

## Troubleshooting

### Database Connection Failed

**Error:** `psycopg2.OperationalError: could not connect to server`

**Solution:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Restart if needed
sudo systemctl restart postgresql

# Check credentials in .env
cat .env
```

### Database Worker Not Starting

**Error:** `⚠ Database integration disabled`

**Solution:**
```bash
# Check psycopg2-binary is installed
pip list | grep psycopg2

# Reinstall if needed
pip install psycopg2-binary --break-system-packages

# Check .env file exists and is loaded
ls -la .env
```

### Slow Database Queries

**Solution:**
```sql
-- Check index usage
SELECT schemaname, tablename, indexname
FROM pg_indexes
WHERE tablename IN ('analysis_results', 'medication_analyses');

-- Rebuild indexes if needed
REINDEX TABLE analysis_results;
```

---

## Performance Optimization

### Connection Pool Tuning

Edit `db_handler.py`:

```python
self.pool_size = 10  # Increase for high load
```

### Database Vacuum

Run monthly:
```bash
psql -U drug_api_user -d drug_analysis -c "VACUUM ANALYZE;"
```

### Monitor Database Size

```sql
SELECT 
    pg_size_pretty(pg_database_size('drug_analysis')) as db_size;
```

---

## Security Best Practices

### 1. Secure .env File
```bash
chmod 600 .env
chown ubuntu:ubuntu .env
```

### 2. Firewall Rules (PostgreSQL)
```bash
# Allow only localhost connections
sudo ufw allow from 127.0.0.1 to any port 5432
```

### 3. Regular Password Rotation
```sql
ALTER USER drug_api_user WITH PASSWORD 'new_secure_password';
```

### 4. Monitor Failed Login Attempts
```bash
sudo tail -f /var/log/postgresql/postgresql-16-main.log
```

---

## Summary

✅ **What you've achieved:**
- PostgreSQL database setup on EC2
- Non-blocking database operations
- Persistent storage of analysis results
- Fast status queries (memory → database fallback)
- Database statistics and monitoring
- Automated cleanup

✅ **Key benefits:**
- Results survive server restarts
- Can query historical data
- Main analysis pipeline unaffected
- Easy database management via API

✅ **Files created:**
- `setup_postgresql.sh` - Database setup
- `db_handler.py` - Async database operations
- `queue_manager.py` - Updated with DB integration
- `server.py` - Updated with DB endpoints
- `.env` - Configuration file

---

## Next Steps

1. ✅ Set up automated backups
2. ✅ Configure monitoring/alerting
3. ✅ Set up log rotation
4. ✅ Plan for scaling (if needed)
5. ✅ Document API for users

**You're all set! 🎉**