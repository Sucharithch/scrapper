import os
import logging
import time
import csv
import io
import asyncio
from fastapi import FastAPI, Request, HTTPException, Header, status, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
from collections import defaultdict, deque
from dotenv import load_dotenv
from enhanced_amazon_agent import EnhancedAmazonProductAgent
from config import Config

# --- ENVIRONMENT ---
load_dotenv()
API_KEY = os.getenv("BACKEND_API_KEY", "changeme")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
RATE_LIMIT = int(os.getenv("RATE_LIMIT", 10))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", 60))

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("backend_api")

# --- FASTAPI APP ---
app = FastAPI(title="Amazon Product Data Agent API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if CORS_ORIGINS == ["*"] else CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# --- RATE LIMITING ---
rate_limiters: Dict[str, deque] = defaultdict(lambda: deque())
def rate_limiter(x_api_key: str = Header(...)):
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    dq = rate_limiters[x_api_key]
    while dq and dq[0] < window_start:
        dq.popleft()
    if len(dq) >= RATE_LIMIT:
        logger.warning(f"Rate limit exceeded for API key: {x_api_key}")
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded: {RATE_LIMIT} requests per {RATE_LIMIT_WINDOW} seconds")
    dq.append(now)

# --- AUTH ---
def api_key_auth(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        logger.warning(f"Unauthorized access attempt with API key: {x_api_key}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")

# --- MODELS ---
class ScrapeRequest(BaseModel):
    url: str

class ScrapeResponse(BaseModel):
    data: dict

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None

# --- HEALTH CHECK ---
@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}

# --- SINGLE SCRAPE ENDPOINT ---
@app.post("/scrape", response_model=ScrapeResponse, responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}}, tags=["Scraping"])
async def scrape(
    request: ScrapeRequest,
    x_api_key: str = Depends(api_key_auth),
    _rate_limit: None = Depends(rate_limiter)
):
    logger.info(f"Received scrape request: {request.url}")
    agent = EnhancedAmazonProductAgent()
    try:
        if hasattr(agent, "get_product_info") and asyncio.iscoroutinefunction(agent.get_product_info):
            result = await agent.get_product_info(request.url)
        else:
            result = agent.get_product_info_sync(request.url)
        if "error" in result:
            logger.error(f"Scraping error: {result['error']} | Input: {request.url}")
            raise HTTPException(status_code=400, detail=result["error"])
        logger.info(f"Scraping successful for: {request.url}")
        return {"data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Internal error during scraping: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# --- BULK CSV EXPORT ENDPOINT ---
@app.post("/bulk-csv", tags=["Bulk"])
async def bulk_csv(
    request: ScrapeRequest,
    x_api_key: str = Depends(api_key_auth),
    _rate_limit: None = Depends(rate_limiter)
):
    """
    Accepts a list of URLs/ASINs (newline-separated in request.url), returns a CSV file.
    """
    lines = [line.strip() for line in request.url.splitlines() if line.strip()]
    agent = EnhancedAmazonProductAgent()
    results = []
    for line in lines:
        if hasattr(agent, "get_product_info") and asyncio.iscoroutinefunction(agent.get_product_info):
            result = await agent.get_product_info(line)
        else:
            result = agent.get_product_info_sync(line)
        result["input_received"] = line
        results.append(result)

    # Prepare CSV
    output = io.StringIO()
    writer = csv.writer(output)
    header = ["URL", "ASIN", "Product Name", "Price", "Currency", "Domain", "Status", "Description", "Error"]
    writer.writerow(header)
    for r in results:
        url = r.get("input_received", "")
        asin = r.get("asin", "")
        name = r.get("product_name", "")
        price = r.get("price", {}).get("discounted") or r.get("price", {}).get("original") or ""
        currency = ""
        if "price" in r:
            for val in [r["price"].get("discounted"), r["price"].get("original")]:
                if val and any(c in val for c in "$₹€£"):
                    currency = next((c for c in "$₹€£" if c in val), "")
                    break
        domain = ""
        try:
            domain = url and __import__("urllib.parse").urlparse(url).hostname or ""
        except Exception:
            pass
        status = "Error" if "error" in r else "OK"
        desc = r.get("description", "")[:200]
        error = r.get("error", "")
        writer.writerow([url, asin, name, price, currency, domain, status, desc, error])
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=amazon_bulk_report.csv"
    })

# --- ERROR HANDLERS ---
@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTPException: {exc.detail} (status {exc.status_code})")
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(status_code=500, content={"error": "Internal server error"}) 