"""
Telegram Bot — Web Ilova Asosiy fayli (FastAPI).

Bu modul FastAPI ilovasini yaratadi va sozlaydi.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os

from config import Config
from web.routes import setup_routes

# ── FastAPI Ilova yaratish ────────────────────────────────────────────
app = FastAPI(
    title="Instagram Comment Analyzer",
    description="Instagram kommentariyalarini AI yordamida tahlil qilish",
    version="1.0.0",
)

# ── Papka yo'llari ────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# ── Statik fayllarni ulash ────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ── Jinja2 Shablonlarni ulash ─────────────────────────────────────────
templates = Jinja2Templates(directory=TEMPLATES_DIR)

def init_app(config: Config) -> FastAPI:
    """
    FastAPI ilovasini konfiguratsiya bilan ishga tayyorlaydi.
    """
    app.state.config = config
    setup_routes(app, templates)
    return app
