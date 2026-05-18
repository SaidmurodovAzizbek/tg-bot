"""
Instagram Comment Analyzer — Web App Routes.

This module contains all FastAPI endpoints for the web application.
"""

from fastapi import APIRouter, Request, Form, Depends, HTTPException, FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import uuid
import logging
import asyncio

from core.scraper import ApifyInstagramScraper
from core.analyzer import analyze_comments
from core.reporter import format_for_web

logger = logging.getLogger(__name__)

# Temporary in-memory storage (Replace with DB or Redis for production)
_analysis_results = {}

def _save_to_cache(cache: dict, key: str, value: dict, max_size: int = 100) -> None:
    """Saves to cache and evicts oldest item if max_size is exceeded."""
    if key not in cache and len(cache) >= max_size:
        oldest = next(iter(cache))
        del cache[oldest]
    cache[key] = value

def setup_routes(app: FastAPI, templates: Jinja2Templates) -> None:
    """Registers all routes to the application."""
    
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Home page — URL input form."""
        return templates.TemplateResponse("index.html", {"request": request})

    @app.post("/api/analyze", response_class=JSONResponse)
    async def api_analyze(request: Request, post_url: str = Form(...)):
        """API endpoint: Receives URL, performs analysis, and returns an ID."""
        config = request.app.state.config
        
        try:
            # 1. URL Validation
            ApifyInstagramScraper._validate_url(post_url)
            
            # 2. Scrape (async to avoid blocking)
            scraper = ApifyInstagramScraper(config)
            scrape_result = await asyncio.to_thread(scraper.scrape_comments, post_url)
            
            # 3. Analyze (async to avoid blocking)
            analysis_result = await asyncio.to_thread(analyze_comments, config, scrape_result)
            
            # 4. Format & Save
            web_data = format_for_web(analysis_result)
            result_id = str(uuid.uuid4())
            _save_to_cache(_analysis_results, result_id, web_data)
            
            return {"status": "success", "result_id": result_id}
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except LookupError as e:
            raise HTTPException(status_code=404, detail="Post topilmadi. Ochiq post ekanligiga ishonch hosil qiling.")
        except ConnectionError as e:
            raise HTTPException(status_code=500, detail=f"Ulanish xatosi: {e}")
        except Exception as e:
            logger.exception("Unexpected error during analysis")
            raise HTTPException(status_code=500, detail="Internal server error.")

    @app.get("/result/{result_id}", response_class=HTMLResponse)
    async def get_result(request: Request, result_id: str):
        """Displays the result page."""
        result_data = _analysis_results.get(result_id)
        
        if not result_data:
            return templates.TemplateResponse(
                "index.html", 
                {"request": request, "error": "Natija topilmadi yoki muddati o'tgan. Iltimos qayta tahlil qiling."}
            )
            
        return templates.TemplateResponse(
            "result.html", 
            {"request": request, "result": result_data}
        )
