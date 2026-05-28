#!/bin/bash
cd "$(dirname "$0")"
export PYTHONPATH=.
backend/.venv/bin/python -c "
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path('backend/.env')
if env_path.exists():
    load_dotenv(env_path, override=True)

sys.path.insert(0, '.')
from backend.services.trend_prediction_service import init_hourly_news_db
from backend.services.news_analysis_task_queue import run_hourly_news_analysis

print('[Manual Trigger] Starting hourly news analysis...')
init_hourly_news_db()
task_id = run_hourly_news_analysis()
print(f'[Manual Trigger] Task submitted with ID: {task_id}')
print('[Manual Trigger] Check logs for progress...')
"
