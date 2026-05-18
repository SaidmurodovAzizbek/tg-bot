"""
Telegram Bot — Web App Main File (FastAPI).

This module creates and configures the FastAPI application.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

from config import Config
from web.routes import setup_routes

# ── Create FastAPI App ────────────────────────────────────────────
app = FastAPI(
    title="Instagram Comment Analyzer",
    description="Analyze Instagram comments using AI",
    version="1.0.0",
)

# ── Directory Paths ────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# ── Mount Static Files ────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ── Setup Jinja2 Templates ─────────────────────────────────────────
templates = Jinja2Templates(directory=TEMPLATES_DIR)

def init_app(config: Config) -> FastAPI:
    """
    Initializes the FastAPI application with the given configuration.
    """
    app.state.config = config
    setup_routes(app, templates)
    return app
