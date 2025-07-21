#!/usr/bin/env python3
"""
Enhanced Amazon Product Data Agent
Advanced version with better error handling, retry logic, and multiple fallback methods.
"""

import re
import json
import asyncio
import aiohttp
import requests
import random
import time
from typing import Dict, List, Optional, Union, Tuple
from urllib.parse import urlparse, parse_qs, quote
from bs4 import BeautifulSoup
import logging
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedAmazonProductAgent:
    """Enhanced Amazon Product Data Agent with multiple fallback methods"""
    
    def __init__(self):
        """Initialize the Enhanced Amazon Product Agent"""
        self.config = Config()
        
        # Enhanced user agents to better mimic real browsers
        self.config.USER_AGENTS = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        # Enhanced headers to better mimic real browser requests
        self.config.HEADERS = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
    
    def extract_asin(self, input_data: str) -> Optional[str]:
        """Extract ASIN from Amazon URL or return ASIN if already provided"""
        # Clean input
        input_data = input_data.strip()
        
        # If it's already an ASIN (10 characters, alphanumeric)
        if re.match(r'^[A-Z0-9]{10}$', input_data.upper()):
            return input_data.upper()
        
        # Extract ASIN from URL patterns (including Indian Amazon)
        asin_patterns = [
            r'/dp/([A-Z0-9]{10})',
            r'/gp/product/([A-Z0-9]{10})',
            r'/ASIN/([A-Z0-9]{10})',
            r'/product/([A-Z0-9]{10})',
            r'/d/([A-Z0-9]{10})',
            r'asin=([A-Z0-9]{10})',
            r'/([A-Z0-9]{10})(?:[/?]|$)'
        ]
        
        for pattern in asin_patterns:
            match = re.search(pattern, input_data, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        return None
    
    def get_amazon_domain(self, input_data: str) -> str:
        """Extract Amazon domain from URL"""
        if 'amazon.in' in input_data:
            return 'amazon.in'
        elif 'amazon.co.uk' in input_data:
            return 'amazon.co.uk'
        elif 'amazon.ca' in input_data:
            return 'amazon.ca'
        elif 'amazon.de' in input_data:
            return 'amazon.de'
        elif 'amazon.fr' in input_data:
            return 'amazon.fr'
        elif 'amazon.it' in input_data:
            return 'amazon.it'
        elif 'amazon.es' in input_data:
            return 'amazon.es'
        elif 'amazon.com.au' in input_data:
            return 'amazon.com.au'
        elif 'amazon.com.br' in input_data:
            return 'amazon.com.br'
        elif 'amazon.co.jp' in input_data:
            return 'amazon.co.jp'
        else:
            return 'amazon.com'  # Default to US Amazon
    
    def _clean_description(self, description: str) -> str:
        """Clean and format product description"""
        if not description:
            return ""
        
        # Remove common prefixes
        prefixes_to_remove = [
            "About this item",
            "About this Item",
            "ABOUT THIS ITEM",
            "Product Description",
            "Description",
            "Features:",
            "Features :",
            "FEATURES:",
            "FEATURES :"
        ]
        
        for prefix in prefixes_to_remove:
            if description.startswith(prefix):
                description = description[len(prefix):].strip()
        
        # Remove extra whitespace and normalize
        description = re.sub(r'\s+', ' ', description)
        description = description.strip()
        
        # Remove HTML entities
        description = description.replace('&amp;', '&')
        description = description.replace('&quot;', '"')
        description = description.replace('&#39;', "'")
        description = description.replace('&lt;', '<')
        description = description.replace('&gt;', '>')
        description = description.replace('&nbsp;', ' ')
        
        # Remove any remaining HTML tags
        description = re.sub(r'<[^>]+>', '', description)
        
        # Clean up multiple spaces again
        description = re.sub(r'\s+', ' ', description)
        description = description.strip()
        
        return description
    
    async def _make_request_with_retry(self, session: aiohttp.ClientSession, 
                                     url: str, params: Optional[Dict] = None, 
                                     headers: Optional[Dict] = None) -> Optional[Tuple[int, str]]:
        """Make HTTP request with retry logic"""
        # SSL context to handle certificate issues
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        for attempt in range(self.config.MAX_RETRIES):
            try:
                async with aiohttp.ClientSession(connector=connector) as temp_session:
                    async with temp_session.get(
                        url,
                        params=params,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=self.config.REQUEST_TIMEOUT)
                    ) as response:
                        content = await response.text()
                        return response.status, content
            except Exception as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt < self.config.MAX_RETRIES - 1:
                    await asyncio.sleep(self.config.RETRY_DELAY * (attempt + 1))
                else:
                    logger.error(f"All request attempts failed for {url}")
                    return None
    
    async def fetch_with_rainforest_api(self, asin: str) -> Optional[Dict]:
        """Fetch product data using Rainforest API"""
        try:
            params = self.apis['rainforest']['params'].copy()
            params['asin'] = asin
            
            async with aiohttp.ClientSession() as session:
                result = await self._make_request_with_retry(session, self.apis['rainforest']['url'], params)
                if result:
                    status, content = result
                    if status == 200:
                        data = json.loads(content)
                        return self._parse_rainforest_response(data)
                    else:
                        logger.warning(f"Rainforest API failed with status {status}")
                return None
        except Exception as e:
            logger.error(f"Rainforest API error: {e}")
            return None
    
    async def fetch_with_scraperapi(self, asin: str) -> Optional[Dict]:
        """Fetch product data using ScraperAPI"""
        try:
            params = self.apis['scraperapi']['params'].copy()
            params['url'] = f'https://www.amazon.com/dp/{asin}'
            
            async with aiohttp.ClientSession() as session:
                result = await self._make_request_with_retry(session, self.apis['scraperapi']['url'], params)
                if result:
                    status, content = result
                    if status == 200:
                        return self._parse_amazon_html(content, asin)
                    else:
                        logger.warning(f"ScraperAPI failed with status {status}")
                return None
        except Exception as e:
            logger.error(f"ScraperAPI error: {e}")
            return None
    
    async def fetch_with_rapidapi(self, asin: str) -> Optional[Dict]:
        """Fetch product data using RapidAPI"""
        try:
            headers = self.apis['rapidapi']['headers'].copy()
            params = {'keyword': asin, 'country': 'US', 'category': 'aps'}
            
            async with aiohttp.ClientSession() as session:
                result = await self._make_request_with_retry(
                    session, self.apis['rapidapi']['url'], params, headers
                )
                if result:
                    status, content = result
                    if status == 200:
                        data = json.loads(content)
                        return self._parse_rapidapi_response(data)
                    else:
                        logger.warning(f"RapidAPI failed with status {status}")
                return None
        except Exception as e:
            logger.error(f"RapidAPI error: {e}")
            return None
    
    async def fetch_with_direct_amazon(self, asin: str, original_url: Optional[str] = None) -> Optional[Dict]:
        """Direct Amazon page fetch (fallback method)"""
        try:
            # Use the original domain if available, otherwise default to amazon.com
            if original_url:
                domain = self.get_amazon_domain(original_url)
                url = f'https://www.{domain}/dp/{asin}'
            else:
                url = f'https://www.amazon.com/dp/{asin}'
            
            # Enhanced headers to better mimic real browser
            headers = {
                'User-Agent': random.choice(self.config.USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'Referer': 'https://www.google.com/',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"'
            }
            
            # Add a small delay to avoid rate limiting
            await asyncio.sleep(random.uniform(1, 3))
            
            async with aiohttp.ClientSession() as session:
                result = await self._make_request_with_retry(session, url, headers=headers)
                if result:
                    status, content = result
                    if status == 200:
                        return self._parse_amazon_html_enhanced(content, asin, original_url)
                    else:
                        logger.warning(f"Direct Amazon fetch failed with status {status}")
                return None
        except Exception as e:
            logger.error(f"Direct Amazon fetch error: {e}")
            return None
    
    def _parse_rainforest_response(self, data: Dict) -> Optional[Dict]:
        """Parse Rainforest API response"""
        try:
            if 'product' not in data:
                return None
            
            product = data['product']
            
            return {
                "product_name": product.get('title', ''),
                "price": {
                    "original": product.get('list_price', {}).get('value', ''),
                    "discounted": product.get('price', {}).get('value', '')
                },
                "description": ' '.join(product.get('feature_bullets', [])),
                "variants": [variant.get('title', '') for variant in product.get('variants', [])],
                "image_urls": [img.get('link', '') for img in product.get('images', [])]
            }
        except Exception as e:
            logger.error(f"Error parsing Rainforest response: {e}")
            return None
    
    def _parse_rapidapi_response(self, data: Dict) -> Optional[Dict]:
        """Parse RapidAPI response"""
        try:
            if 'products' not in data or not data['products']:
                return None
            
            product = data['products'][0]
            
            return {
                "product_name": product.get('title', ''),
                "price": {
                    "original": product.get('original_price', ''),
                    "discounted": product.get('current_price', '')
                },
                "description": product.get('description', ''),
                "variants": product.get('variants', []),
                "image_urls": [product.get('image', '')] if product.get('image') else []
            }
        except Exception as e:
            logger.error(f"Error parsing RapidAPI response: {e}")
            return None
    
    def _parse_amazon_html(self, html: str, asin: str) -> Optional[Dict]:
        """Parse Amazon HTML page (basic method)"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract product name
            title_selectors = [
                'span#productTitle',
                'h1#title',
                'h1.a-size-large',
                '[data-automation-id="product-title"]'
            ]
            
            product_name = ''
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    product_name = title_elem.get_text().strip()
                    break
            
            # Extract price
            price_selectors = [
                'span.a-price-whole',
                'span.a-price.a-text-price span.a-offscreen',
                'span.a-price.a-text-price',
                '.a-price .a-offscreen'
            ]
            
            price = ''
            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    price = price_elem.get_text().strip()
                    break
            
            # Extract description
            desc_selectors = [
                '#feature-bullets',
                '#productDescription',
                '.a-expander-content',
                '.a-section.a-spacing-base',
                '[data-automation-id="feature-bullets"]'
            ]
            
            description = ''
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    description = desc_elem.get_text().strip()
                    # Clean up the description
                    description = self._clean_description(description)
                    if description and len(description) > 20:  # Ensure we have meaningful content
                        break
            
            # Extract images
            img_selectors = [
                'img[data-old-hires]',
                'img[data-a-dynamic-image]',
                '.a-dynamic-image'
            ]
            
            image_urls = []
            for selector in img_selectors:
                img_elements = soup.select(selector)
                for img in img_elements:
                    img_url = img.get('data-old-hires') or img.get('src')
                    if img_url and img_url not in image_urls:
                        image_urls.append(img_url)
            
            return {
                "product_name": product_name,
                "price": {
                    "original": price,
                    "discounted": price
                },
                "description": description,
                "variants": [],
                "image_urls": image_urls[:5]  # Limit to 5 images
            }
        except Exception as e:
            logger.error(f"Error parsing Amazon HTML: {e}")
            return None
    
    def _extract_price_with_currency(self, html: str, original_url: str = "") -> Dict[str, str]:
        """Extract price with currency detection based on domain and HTML content"""
        price_data = {"original": "", "discounted": "", "currency": ""}
        
        # First, determine the expected currency based on the original URL domain
        expected_currency = ""
        if "amazon.in" in original_url:
            expected_currency = "INR"
        elif "amazon.com" in original_url:
            expected_currency = "USD"
        elif "amazon.co.uk" in original_url:
            expected_currency = "GBP"
        elif "amazon.de" in original_url:
            expected_currency = "EUR"
        elif "amazon.ca" in original_url:
            expected_currency = "CAD"
        elif "amazon.com.au" in original_url:
            expected_currency = "AUD"
        
        # Check if we have real product data (not an error page)
        if not self._has_real_product_data(html):
            # If we don't have real product data, try to extract any price-like patterns
            # This is a fallback for when Amazon blocks us but we still get some content
            fallback_price = self._extract_fallback_price(html, expected_currency)
            if fallback_price:
                return fallback_price
            return price_data
        
        # Enhanced price extraction with currency detection - ORDER MATTERS!
        # For India domains, prioritize INR patterns first
        if expected_currency == "INR":
            price_patterns = [
                # Indian Rupees - put first for India domains
                (r'₹(\d+(?:,\d+)*)', '₹', 'INR'),
                (r'Rs\.?\s*(\d+(?:,\d+)*)', '₹', 'INR'),
                (r'INR\s*(\d+(?:,\d+)*)', '₹', 'INR'),
                
                # British Pounds
                (r'£(\d+(?:\.\d{2})?)', '£', 'GBP'),
                (r'GBP\s*(\d+(?:\.\d{2})?)', '£', 'GBP'),
                
                # US Dollars
                (r'\$(\d+(?:\.\d{2})?)', '$', 'USD'),
                (r'USD\s*(\d+(?:\.\d{2})?)', '$', 'USD'),
                
                # Euro
                (r'€(\d+(?:\.\d{2})?)', '€', 'EUR'),
                (r'EUR\s*(\d+(?:\.\d{2})?)', '€', 'EUR'),
                
                # Canadian Dollars
                (r'C\$\s*(\d+(?:\.\d{2})?)', 'C$', 'CAD'),
                (r'CAD\s*(\d+(?:\.\d{2})?)', 'C$', 'CAD'),
                
                # Australian Dollars
                (r'A\$\s*(\d+(?:\.\d{2})?)', 'A$', 'AUD'),
                (r'AUD\s*(\d+(?:\.\d{2})?)', 'A$', 'AUD'),
                
                # Generic price patterns - LAST, and only if no specific currency found
                # Make these more specific to avoid false matches
                (r'<span[^>]*class="[^"]*a-price-whole[^"]*"[^>]*>(\d+(?:,\d+)*)</span>', '', ''),
                (r'<span[^>]*class="[^"]*a-offscreen[^"]*"[^>]*>([^<]+)</span>', '', ''),
            ]
        else:
            # For non-India domains, use standard order
            price_patterns = [
                # British Pounds - put first to avoid INR conflicts
                (r'£(\d+(?:\.\d{2})?)', '£', 'GBP'),
                (r'GBP\s*(\d+(?:\.\d{2})?)', '£', 'GBP'),
                
                # US Dollars
                (r'\$(\d+(?:\.\d{2})?)', '$', 'USD'),
                (r'USD\s*(\d+(?:\.\d{2})?)', '$', 'USD'),
                
                # Euro
                (r'€(\d+(?:\.\d{2})?)', '€', 'EUR'),
                (r'EUR\s*(\d+(?:\.\d{2})?)', '€', 'EUR'),
                
                # Canadian Dollars
                (r'C\$\s*(\d+(?:\.\d{2})?)', 'C$', 'CAD'),
                (r'CAD\s*(\d+(?:\.\d{2})?)', 'C$', 'CAD'),
                
                # Australian Dollars
                (r'A\$\s*(\d+(?:\.\d{2})?)', 'A$', 'AUD'),
                (r'AUD\s*(\d+(?:\.\d{2})?)', 'A$', 'AUD'),
                
                # Indian Rupees - put last for non-India domains
                (r'₹(\d+(?:,\d+)*)', '₹', 'INR'),
                (r'Rs\.?\s*(\d+(?:,\d+)*)', '₹', 'INR'),
                (r'INR\s*(\d+(?:,\d+)*)', '₹', 'INR'),
                
                # Generic price patterns - LAST, and only if no specific currency found
                # Make these more specific to avoid false matches
                (r'<span[^>]*class="[^"]*a-price-whole[^"]*"[^>]*>(\d+(?:,\d+)*)</span>', '', ''),
                (r'<span[^>]*class="[^"]*a-offscreen[^"]*"[^>]*>([^<]+)</span>', '', ''),
            ]
        
        # First pass: look for specific currency patterns
        for pattern, symbol, currency_code in price_patterns[:-2]:  # Skip generic patterns
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                price_value = match.group(1)
                # Validate that this looks like a real price (not just a number)
                if self._is_valid_price(price_value):
                    price_data["discounted"] = f"{symbol}{price_value}"
                    price_data["original"] = f"{symbol}{price_value}"
                    price_data["currency"] = currency_code
                    return price_data  # Return immediately if specific currency found
        
        # Second pass: if no specific currency found, use generic patterns with domain-based currency
        for pattern, symbol, currency_code in price_patterns[-2:]:  # Only generic patterns
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                price_value = match.group(1)
                # Additional validation for generic patterns
                if self._is_valid_price(price_value):
                    # Use the expected currency from domain - this is the key fix
                    if expected_currency:
                        if expected_currency == "INR":
                            price_data["discounted"] = f"₹{price_value}"
                            price_data["original"] = f"₹{price_value}"
                            price_data["currency"] = "INR"
                        elif expected_currency == "USD":
                            price_data["discounted"] = f"${price_value}"
                            price_data["original"] = f"${price_value}"
                            price_data["currency"] = "USD"
                        elif expected_currency == "GBP":
                            price_data["discounted"] = f"£{price_value}"
                            price_data["original"] = f"£{price_value}"
                            price_data["currency"] = "GBP"
                        elif expected_currency == "EUR":
                            price_data["discounted"] = f"€{price_value}"
                            price_data["original"] = f"€{price_value}"
                            price_data["currency"] = "EUR"
                        elif expected_currency == "CAD":
                            price_data["discounted"] = f"C${price_value}"
                            price_data["original"] = f"C${price_value}"
                            price_data["currency"] = "CAD"
                        elif expected_currency == "AUD":
                            price_data["discounted"] = f"A${price_value}"
                            price_data["original"] = f"A${price_value}"
                            price_data["currency"] = "AUD"
                    else:
                        # Fallback: try to detect from HTML context
                        context_start = max(0, match.start() - 100)
                        context_end = min(len(html), match.end() + 100)
                        context = html[context_start:context_end]
                        
                        if '₹' in context or 'INR' in context:
                            price_data["currency"] = "INR"
                            price_data["discounted"] = f"₹{price_value}"
                            price_data["original"] = f"₹{price_value}"
                        elif '$' in context or 'USD' in context:
                            price_data["currency"] = "USD"
                            price_data["discounted"] = f"${price_value}"
                            price_data["original"] = f"${price_value}"
                        elif '£' in context or 'GBP' in context:
                            price_data["currency"] = "GBP"
                            price_data["discounted"] = f"£{price_value}"
                            price_data["original"] = f"£{price_value}"
                        elif '€' in context or 'EUR' in context:
                            price_data["currency"] = "EUR"
                            price_data["discounted"] = f"€{price_value}"
                            price_data["original"] = f"€{price_value}"
                        else:
                            # Default to USD if no currency detected
                            price_data["currency"] = "USD"
                            price_data["discounted"] = f"${price_value}"
                            price_data["original"] = f"${price_value}"
                    
                    break
        
        return price_data
    
    def _extract_fallback_price(self, html: str, expected_currency: str) -> Dict[str, str]:
        """Extract price from limited HTML content when Amazon blocks us"""
        price_data = {"original": "", "discounted": "", "currency": ""}
        
        # Look for any price-like patterns in the HTML, even if it's limited
        price_patterns = [
            # Currency symbols with numbers - ORDER MATTERS!
            # British Pounds - put first to avoid INR conflicts
            (r'£(\d+(?:\.\d{2})?)', '£', 'GBP'),
            (r'GBP\s*(\d+(?:\.\d{2})?)', '£', 'GBP'),
            
            # US Dollars
            (r'\$(\d+(?:\.\d{2})?)', '$', 'USD'),
            (r'USD\s*(\d+(?:\.\d{2})?)', '$', 'USD'),
            
            # Euro
            (r'€(\d+(?:\.\d{2})?)', '€', 'EUR'),
            (r'EUR\s*(\d+(?:\.\d{2})?)', '€', 'EUR'),
            
            # Canadian Dollars
            (r'C\$\s*(\d+(?:\.\d{2})?)', 'C$', 'CAD'),
            (r'CAD\s*(\d+(?:\.\d{2})?)', 'C$', 'CAD'),
            
            # Australian Dollars
            (r'A\$\s*(\d+(?:\.\d{2})?)', 'A$', 'AUD'),
            (r'AUD\s*(\d+(?:\.\d{2})?)', 'A$', 'AUD'),
            
            # Indian Rupees - put last to avoid conflicts
            (r'₹(\d+(?:,\d+)*)', '₹', 'INR'),
            (r'Rs\.?\s*(\d+(?:,\d+)*)', '₹', 'INR'),
            (r'INR\s*(\d+(?:,\d+)*)', '₹', 'INR'),
            
            # Just numbers that might be prices (be more lenient)
            (r'(\d{2,4}(?:,\d{3})*(?:\.\d{2})?)', '', ''),
        ]
        
        for pattern, symbol, currency_code in price_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                price_value = match
                # More lenient validation for fallback
                if self._is_valid_fallback_price(price_value):
                    if currency_code:  # If we found a specific currency
                        price_data["discounted"] = f"{symbol}{price_value}"
                        price_data["original"] = f"{symbol}{price_value}"
                        price_data["currency"] = currency_code
                        return price_data
                    elif expected_currency:  # Use expected currency from domain
                        if expected_currency == "INR":
                            price_data["discounted"] = f"₹{price_value}"
                            price_data["original"] = f"₹{price_value}"
                            price_data["currency"] = "INR"
                        elif expected_currency == "USD":
                            price_data["discounted"] = f"${price_value}"
                            price_data["original"] = f"${price_value}"
                            price_data["currency"] = "USD"
                        elif expected_currency == "GBP":
                            price_data["discounted"] = f"£{price_value}"
                            price_data["original"] = f"£{price_value}"
                            price_data["currency"] = "GBP"
                        elif expected_currency == "EUR":
                            price_data["discounted"] = f"€{price_value}"
                            price_data["original"] = f"€{price_value}"
                            price_data["currency"] = "EUR"
                        elif expected_currency == "CAD":
                            price_data["discounted"] = f"C${price_value}"
                            price_data["original"] = f"C${price_value}"
                            price_data["currency"] = "CAD"
                        elif expected_currency == "AUD":
                            price_data["discounted"] = f"A${price_value}"
                            price_data["original"] = f"A${price_value}"
                            price_data["currency"] = "AUD"
                        return price_data
        
        return price_data
    
    def _is_valid_fallback_price(self, price_value: str) -> bool:
        """More lenient validation for fallback price extraction"""
        if not price_value:
            return False
        
        # Remove any non-digit characters except decimal and comma
        clean_price = re.sub(r'[^\d.,]', '', price_value)
        
        # Check if it's a reasonable price (not just a single digit)
        if len(clean_price) < 2:
            return False
        
        # Check if it's a reasonable range (not too small, not too large)
        try:
            # Remove commas and convert to float
            numeric_price = float(clean_price.replace(',', ''))
            if numeric_price < 0.01 or numeric_price > 10000000:  # More lenient range
                return False
        except ValueError:
            return False
        
        return True
    
    def _has_real_product_data(self, html: str) -> bool:
        """Check if the HTML contains real product data (not an error page)"""
        # Look for indicators of real product pages
        product_indicators = [
            'productTitle',
            'feature-bullets',
            'productDescription',
            'a-price',
            'a-offscreen',
            'data-old-hires',
            'data-a-dynamic-image'
        ]
        
        # Look for indicators of error pages
        error_indicators = [
            'Sorry, we just need to make sure you\'re not a robot',
            'Enter the characters you see below',
            'Type the characters you see in this image',
            'To discuss automated access to Amazon data please contact',
            'Robot Check',
            'captcha',
            'blocked'
        ]
        
        # Check for error indicators first
        for error_indicator in error_indicators:
            if error_indicator.lower() in html.lower():
                return False
        
        # Check for product indicators
        product_count = 0
        for indicator in product_indicators:
            if indicator in html:
                product_count += 1
        
        # Need at least 2 product indicators to consider it real
        return product_count >= 2
    
    def _is_valid_price(self, price_value: str) -> bool:
        """Check if a price value looks like a real price"""
        if not price_value:
            return False
        
        # Remove any non-digit characters except decimal and comma
        clean_price = re.sub(r'[^\d.,]', '', price_value)
        
        # Check if it's a reasonable price (not just a single digit or very small number)
        if len(clean_price) < 2:
            return False
        
        # Check if it starts with 0 (likely not a real price)
        if clean_price.startswith('0') and len(clean_price) == 1:
            return False
        
        # Check if it's a reasonable range (not too small, not too large)
        try:
            # Remove commas and convert to float
            numeric_price = float(clean_price.replace(',', ''))
            if numeric_price < 1 or numeric_price > 1000000:  # Reasonable price range
                return False
        except ValueError:
            return False
        
        return True

    def _parse_amazon_html_enhanced(self, html: str, asin: str, original_url: str = "") -> Optional[Dict]:
        """Enhanced Amazon HTML parsing with more selectors and currency detection"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Enhanced product name extraction
            title_patterns = [
                r'<span[^>]*id="productTitle"[^>]*>(.*?)</span>',
                r'<h1[^>]*id="title"[^>]*>(.*?)</h1>',
                r'<title[^>]*>(.*?)</title>'
            ]
            
            product_name = ''
            for pattern in title_patterns:
                match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
                if match:
                    product_name = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                    # Clean HTML entities
                    product_name = product_name.replace('&#39;', "'").replace('&amp;', '&')
                    break
            
            # Extract price with currency detection
            price_data = self._extract_price_with_currency(html, original_url)
            
            # Enhanced description extraction with multiple patterns
            desc_patterns = [
                r'<div[^>]*id="feature-bullets"[^>]*>(.*?)</div>',
                r'<div[^>]*id="productDescription"[^>]*>(.*?)</div>',
                r'<div[^>]*class="[^"]*a-expander-content[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*class="[^"]*a-section[^"]*"[^>]*>.*?About this item.*?(.*?)</div>',
                r'<span[^>]*class="[^"]*a-list-item[^"]*"[^>]*>(.*?)</span>',
                r'<div[^>]*class="[^"]*a-spacing-base[^"]*"[^>]*>(.*?)</div>'
            ]
            
            description = ''
            for pattern in desc_patterns:
                match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
                if match:
                    description = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                    # Clean up the description
                    description = self._clean_description(description)
                    if description and len(description) > 20:  # Ensure we have meaningful content
                        break
            
            # Enhanced image extraction with better parsing
            img_patterns = [
                r'data-old-hires="([^"]+)"',
                r'data-a-dynamic-image="([^"]+)"',
                r'src="([^"]*amazon[^"]*\.(?:jpg|jpeg|png|webp)[^"]*)"'
            ]
            
            image_urls = []
            for pattern in img_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches:
                    if match and match not in image_urls:
                        # Clean HTML entities in URLs
                        clean_url = match.replace('&quot;', '"').replace('&#39;', "'")
                        image_urls.append(clean_url)
            
            # Clean up image URLs - extract actual URLs from JSON-like strings
            cleaned_image_urls = []
            for url in image_urls[:10]:  # Take more initially for cleaning
                if url.startswith('{') and url.endswith('}'):
                    # Extract URLs from JSON-like structure
                    url_matches = re.findall(r'"([^"]*amazon[^"]*\.(?:jpg|jpeg|png|webp)[^"]*)"', url)
                    cleaned_image_urls.extend(url_matches)
                else:
                    cleaned_image_urls.append(url)
            
            # Remove duplicates, but do not limit
            unique_urls = list(dict.fromkeys(cleaned_image_urls))
            
            return {
                "product_name": product_name,
                "price": price_data,
                "description": description,
                "variants": [],
                "image_urls": unique_urls
            }
        except Exception as e:
            logger.error(f"Error parsing enhanced Amazon HTML: {e}")
            return None
    
    async def get_product_info(self, input_data: str) -> Dict:
        """
        Main method to get product information with multiple fallback methods
        
        Args:
            input_data: Amazon URL or ASIN
            
        Returns:
            Dictionary with product information or error message
        """
        # Extract ASIN
        asin = self.extract_asin(input_data)
        if not asin:
            return {
                "error": "Invalid input. Please provide a valid Amazon URL or ASIN.",
                "input_received": input_data,
                "supported_formats": [
                    "https://www.amazon.com/dp/ASIN",
                    "https://www.amazon.com/gp/product/ASIN",
                    "ASIN (10-character product code)"
                ]
            }
        
        logger.info(f"Fetching product information for ASIN: {asin}")
        
        # Try multiple APIs and methods in sequence
        methods = [
            ('rainforest_api', self.fetch_with_rainforest_api),
            ('scraperapi', self.fetch_with_scraperapi),
            ('rapidapi', self.fetch_with_rapidapi),
            ('direct_amazon', lambda asin: self.fetch_with_direct_amazon(asin, input_data))
        ]
        
        for method_name, method_func in methods:
            try:
                logger.info(f"Trying {method_name}...")
                result = await method_func(asin)
                if result and result.get('product_name'):
                    logger.info(f"Successfully retrieved data using {method_name}")
                    result['source_method'] = method_name
                    result['asin'] = asin
                    return result
                else:
                    logger.warning(f"{method_name} returned no data")
            except Exception as e:
                logger.error(f"Error with {method_name}: {e}")
                continue
        
        # If all methods fail, return error
        return {
            "error": "Unable to fetch product information. All methods failed.",
            "asin": asin,
            "suggestion": "Please check if the ASIN is valid or try again later.",
            "tried_methods": [method[0] for method in methods]
        }
    
    def get_product_info_sync(self, input_data: str) -> Dict:
        """Synchronous wrapper for get_product_info"""
        return asyncio.run(self.get_product_info(input_data))


def main():
    """Example usage of the Enhanced Amazon Product Agent"""
    agent = EnhancedAmazonProductAgent()
    
    # Example inputs
    test_inputs = [
        "https://www.amazon.com/dp/B08N5WRWNW",  # Echo Dot
        "B08N5WRWNW",  # ASIN directly
        "https://www.amazon.com/gp/product/B08N5WRWNW"  # Different URL format
    ]
    
    for test_input in test_inputs:
        print(f"\n{'='*60}")
        print(f"Testing with input: {test_input}")
        print(f"{'='*60}")
        
        result = agent.get_product_info_sync(test_input)
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main() 