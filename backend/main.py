"""FastAPI main application."""
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import stock, watchlist, trend_prediction

# Load .env file from backend directory
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

app = FastAPI(
    title="Stock Analysis API",
    description="API for stock data, K-line charts, and technical indicators",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(stock.router)
app.include_router(watchlist.router)
app.include_router(trend_prediction.router)


@app.get("/")
async def root():
    return {"message": "Stock Analysis API", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
