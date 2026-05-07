"""
Telegram Bot — Web Ilova Marshrutlari (Routes).

Bu modul FastAPI ilovasining barcha endpointlarini o'z ichiga oladi.
"""

from fastapi import APIRouter, Request, Form, Depends, HTTPException, FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import uuid
import logging

from core.scraper import ApifyInstagramScraper
from core.analyzer import analyze_comments
from core.reporter import format_for_web

logger = logging.getLogger(__name__)

# Vaqtincha xotira (DB o'rniga)
_analysis_results = {}

def setup_routes(app: FastAPI, templates: Jinja2Templates) -> None:
    """Ilovaga barcha route-larni qo'shadi."""
    
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Bosh sahifa — URL kiritish formasi."""
        return templates.TemplateResponse("index.html", {"request": request})

    @app.post("/api/analyze", response_class=JSONResponse)
    async def api_analyze(request: Request, post_url: str = Form(...)):
        """API endpoint: URL qabul qiladi, tahlil qiladi va ID qaytaradi."""
        config = request.app.state.config
        
        try:
            # 1. URL Validatsiya
            ApifyInstagramScraper._validate_url(post_url)
            
            # 2. Scrape
            scraper = ApifyInstagramScraper(config)
            scrape_result = scraper.scrape_comments(post_url)
            
            # 3. Analyze
            analysis_result = analyze_comments(config, scrape_result)
            
            # 4. Format & Save
            web_data = format_for_web(analysis_result)
            result_id = str(uuid.uuid4())
            _analysis_results[result_id] = web_data
            
            return {"status": "success", "result_id": result_id}
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except LookupError as e:
            raise HTTPException(status_code=404, detail="Post topilmadi. Ochiq post ekanligiga ishonch hosil qiling.")
        except ConnectionError as e:
            raise HTTPException(status_code=500, detail=f"Ulanish xatosi: {e}")
        except Exception as e:
            logger.exception("Tahlil paytida kutilmagan xato")
            raise HTTPException(status_code=500, detail="Ichki server xatosi yuz berdi.")

    @app.get("/result/{result_id}", response_class=HTMLResponse)
    async def get_result(request: Request, result_id: str):
        """Natija sahifasini ko'rsatadi."""
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
