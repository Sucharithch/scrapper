"""
Configuration file for Amazon Product Data Agent
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for API keys and settings"""
    
    # API Keys (replace with your actual keys)
    RAINFOREST_API_KEY = os.getenv('RAINFOREST_API_KEY', 'demo')
    SCRAPERAPI_KEY = os.getenv('SCRAPERAPI_KEY', 'demo')
    RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY', 'demo')
    
    # API Endpoints
    RAINFOREST_URL = 'https://api.rainforestapi.com/request'
    SCRAPERAPI_URL = 'https://api.scraperapi.com/'
    RAPIDAPI_URL = 'https://amazon-product-reviews-keywords.p.rapidapi.com/product/search'
    
    # Request settings
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
    RETRY_DELAY = 1
    
    # User agents for rotation
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0'
    ] 