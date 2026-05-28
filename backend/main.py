"""FastAPI main application."""
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from backend.api import stock, watchlist, trend_prediction, auth, captcha, institutional_trading_analysis, index_metrics, hourly_news

# Load .env file from backend directory
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)

app = FastAPI(
    title="Stock Analysis API",
    description="API for stock data, K-line charts, and technical indicators",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(stock.router)
app.include_router(watchlist.router)
app.include_router(trend_prediction.router)
app.include_router(auth.router)
app.include_router(captcha.router)
app.include_router(institutional_trading_analysis.router)
app.include_router(index_metrics.router)
app.include_router(hourly_news.router)


def start_scheduler():
    """Start the background scheduler for hourly news analysis."""
    from backend.services.trend_prediction_service import init_hourly_news_db, cleanup_old_hourly_news
    from backend.services.news_analysis_task_queue import run_hourly_news_analysis

    # Initialize hourly_news database table
    init_hourly_news_db()

    # Cleanup old news on startup
    cleanup_old_hourly_news(max_age_days=7)

    scheduler = BackgroundScheduler()

    # Run news analysis at the end of every hour (minute=0, second=0 runs at start of hour)
    # We want it at the end of the hour, so use cron with minute=59 and second=59
    scheduler.add_job(
        run_hourly_news_analysis,
        'cron',
        minute=0,
        second=5,  # Run at 5 seconds past each hour
        id='hourly_news_analysis',
        name='Hourly News Analysis',
        replace_existing=True,
    )

    scheduler.start()
    print("[Scheduler] Hourly news analysis scheduler started")
    return scheduler


# Global scheduler instance
_scheduler = None


@app.on_event("startup")
async def startup_event():
    """Start background scheduler on app startup."""
    global _scheduler
    _scheduler = start_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown scheduler on app shutdown."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        print("[Scheduler] Scheduler shut down")


@app.get("/")
async def root():
    return {"message": "Stock Analysis API", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
