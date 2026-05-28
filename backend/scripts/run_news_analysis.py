#!/usr/bin/env python3
"""Manually trigger hourly news analysis."""
import sys
import os

# Add project root to path so 'backend' module can be found
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Now we can import using backend. prefix
from backend.services.trend_prediction_service import init_hourly_news_db
from backend.services.news_analysis_task_queue import run_hourly_news_analysis

def main():
    print("[Manual Trigger] Starting hourly news analysis...")

    # Initialize the hourly_news table if it doesn't exist
    init_hourly_news_db()

    # Run the news analysis task
    task_id = run_hourly_news_analysis()

    print(f"[Manual Trigger] Task submitted with ID: {task_id}")
    print("[Manual Trigger] Check logs for progress...")

if __name__ == "__main__":
    main()
