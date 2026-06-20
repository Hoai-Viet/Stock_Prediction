# Automated Stock Crawling Setup

## Problem with Airflow on Windows

Airflow has known issues on Windows, particularly with logging configuration. The error "Unable to configure handler 'task'" is a common problem that's difficult to resolve.

**Official Airflow documentation states:**
> "Note that Airflow is not officially supported on Windows. Some features may not work correctly."

## Recommended Solution: Windows Task Scheduler

Instead of Airflow, we'll use **Windows Task Scheduler** which is:
- ✅ Native to Windows
- ✅ More reliable
- ✅ Easier to configure
- ✅ No additional dependencies

---

## Setup Instructions

### Option 1: Using PowerShell Scripts (Recommended)

I've created two PowerShell scripts that you can run to set up automated tasks:

#### 1. Setup Intraday Crawl Task

Run this script to create a scheduled task for `crawl_intraday.py`:

```powershell
cd d:\antigravity\stock_project\airflow
.\setup_intraday_task.ps1
```

This will create a task that runs **daily at 6:00 PM**.

#### 2. Setup Financial Statements Crawl Task

Run this script to create a scheduled task for `crawl_bctc.py`:

```powershell
cd d:\antigravity\stock_project\airflow
.\setup_bctc_task.ps1
```

This will create a task that runs **daily at 2:00 AM**.

---

### Option 2: Manual Setup via Task Scheduler GUI

1. Open **Task Scheduler** (search in Start menu)
2. Click **Create Basic Task**
3. Follow the wizard:
   - **Name**: Stock Crawl Intraday
   - **Trigger**: Daily at 6:00 PM
   - **Action**: Start a program
   - **Program**: `D:\antigravity\stock_project\scripts\crawling\cr_venv\Scripts\python.exe`
   - **Arguments**: `crawl_intraday.py`
   - **Start in**: `D:\antigravity\stock_project\scripts\crawling`

Repeat for `crawl_bctc.py` with daily trigger at 2:00 AM.

---

## Verify Tasks

### View Scheduled Tasks

```powershell
Get-ScheduledTask -TaskName "Stock*"
```

### Run Task Manually

```powershell
Start-ScheduledTask -TaskName "Stock Crawl Intraday"
Start-ScheduledTask -TaskName "Stock Crawl Financial Statements"
```

### View Task History

1. Open Task Scheduler
2. Find your task in the list
3. Click on the **History** tab
4. Check for successful runs

---

## Task Schedule Summary

| DAG | Schedule | Tasks |
|-----|----------|-------|
| `prediction_dag` | Mon-Fri 21:30 | feature hiện tại → FP-Growth combo matching → `fact_decision` → Telegram |
| `stock_crawl_news` | Daily 01:30 | `crawl_news` → `build_news_features` |
| `stock_crawl_financial_statements` | Daily 02:00 | `crawl_bctc` |
| `ml_evaluate_predictions` | Mon-Fri 08:00 | `evaluate_predictions` |
| `ml_weekly_maintenance` | Sunday 03:00 | `train_model` → `mine_feature_pairs` |

---

## Troubleshooting

### Task not running
1. Check Task Scheduler history for errors
2. Verify the Python path is correct
3. Ensure the script runs manually first

### Script fails when run by Task Scheduler
1. Make sure "Start in" directory is set correctly
2. Check that `.env` file exists in the script directory
3. Verify database connection from the script directory

---

## Alternative: Keep Airflow (Advanced)

If you still want to use Airflow despite the Windows limitations, you can:

1. **Use WSL2 (Windows Subsystem for Linux)**
   - Install Ubuntu on WSL2
   - Install Airflow in WSL2
   - Much more stable than native Windows

2. **Use Docker**
   - Run Airflow in Docker containers
   - Official Airflow Docker images available

Both options require additional setup but provide full Airflow functionality.
