#!/usr/bin/env python3
"""
Simple Amazon Product Scraper
A completely new approach that focuses on getting real prices with correct currencies
"""

import asyncio
import aiohttp
import re
import random
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse
import time
import ssl
import certifi

class SimpleAmazonScraper:
    def __init__(self):
        """Initialize the simple scraper"""
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        ]
        
        # Simple price patterns for each currency
        self.price_patterns = {
            'INR': [
                r'₹(\d+(?:,\d+)*)',
                r'Rs\.?\s*(\d+(?:,\d+)*)',
                r'INR\s*(\d+(?:,\d+)*)',
            ],
            'USD': [
                r'\$(\d+(?:\.\d{2})?)',
                r'USD\s*(\d+(?:\.\d{2})?)',
            ],
            'GBP': [
                r'£(\d+(?:\.\d{2})?)',
                r'GBP\s*(\d+(?:\.\d{2})?)',
            ],
            'EUR': [
                r'€(\d+(?:\.\d{2})?)',
                r'EUR\s*(\d+(?:\.\d{2})?)',
            ],
            'CAD': [
                r'C\$\s*(\d+(?:\.\d{2})?)',
                r'CAD\s*(\d+(?:\.\d{2})?)',
            ],
            'AUD': [
                r'A\$\s*(\d+(?:\.\d{2})?)',
                r'AUD\s*(\d+(?:\.\d{2})?)',
            ]
        }
        
        # Currency symbols
        self.currency_symbols = {
            'INR': '₹',
            'USD': '$',
            'GBP': '£',
            'EUR': '€',
            'CAD': 'C$',
            'AUD': 'A$'
        }
    
    def get_domain_currency(self, url: str) -> str:
        """Get expected currency based on Amazon domain"""
        if 'amazon.in' in url:
            return 'INR'
        elif 'amazon.com' in url:
            return 'USD'
        elif 'amazon.co.uk' in url:
            return 'GBP'
        elif 'amazon.de' in url:
            return 'EUR'
        elif 'amazon.ca' in url:
            return 'CAD'
        elif 'amazon.com.au' in url:
            return 'AUD'
        else:
            return 'USD'  # Default
    
    def extract_asin(self, url: str) -> Optional[str]:
        """Extract ASIN from Amazon URL"""
        patterns = [
            r'/dp/([A-Z0-9]{10})',
            r'/gp/product/([A-Z0-9]{10})',
            r'/product/([A-Z0-9]{10})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def extract_price_from_html(self, html: str, expected_currency: str) -> Dict[str, str]:
        """Extract price from HTML with currency detection"""
        result = {"price": "", "currency": ""}
        
        # First, try to find prices in specific product price elements
        product_price_patterns = [
            # Amazon's specific price classes - these are more reliable
            r'<span[^>]*class="[^"]*a-price-whole[^"]*"[^>]*>(\d+(?:,\d+)*)</span>',
            r'<span[^>]*class="[^"]*a-offscreen[^"]*"[^>]*>([^<]+)</span>',
            r'<span[^>]*class="[^"]*a-price[^"]*"[^>]*>([^<]+)</span>',
        ]
        
        # Try product-specific patterns first
        for pattern in product_price_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                # Clean the match
                clean_match = re.sub(r'[^\d.,]', '', match)
                if self._is_valid_price(clean_match):
                    # Determine currency from the original match
                    if '₹' in match or expected_currency == 'INR':
                        result["price"] = f"₹{clean_match}"
                        result["currency"] = "INR"
                        return result
                    elif '$' in match or expected_currency == 'USD':
                        result["price"] = f"${clean_match}"
                        result["currency"] = "USD"
                        return result
                    elif '£' in match or expected_currency == 'GBP':
                        result["price"] = f"£{clean_match}"
                        result["currency"] = "GBP"
                        return result
                    elif '€' in match or expected_currency == 'EUR':
                        result["price"] = f"€{clean_match}"
                        result["currency"] = "EUR"
                        return result
                    elif 'C$' in match or expected_currency == 'CAD':
                        result["price"] = f"C${clean_match}"
                        result["currency"] = "CAD"
                        return result
                    elif 'A$' in match or expected_currency == 'AUD':
                        result["price"] = f"A${clean_match}"
                        result["currency"] = "AUD"
                        return result
        
        # If no product-specific price found, try currency patterns
        # But exclude common filter/navigation text that contains prices
        exclude_patterns = [
            r'Under ₹\d+',
            r'Over ₹\d+',
            r'Under \$\d+',
            r'Over \$\d+',
            r'Under £\d+',
            r'Over £\d+',
            r'search-alias=',
            r'filter=',
            r'price-range=',
        ]
        
        # Create a cleaned HTML without filter/navigation elements
        cleaned_html = html
        for exclude_pattern in exclude_patterns:
            cleaned_html = re.sub(exclude_pattern, '', cleaned_html, flags=re.IGNORECASE)
        
        # Now try currency patterns on cleaned HTML
        if expected_currency in self.price_patterns:
            for pattern in self.price_patterns[expected_currency]:
                matches = re.findall(pattern, cleaned_html, re.IGNORECASE)
                for match in matches:
                    if self._is_valid_price(match):
                        result["price"] = f"{self.currency_symbols[expected_currency]}{match}"
                        result["currency"] = expected_currency
                        return result
        
        # If no price found with expected currency, try all currencies
        for currency, patterns in self.price_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, cleaned_html, re.IGNORECASE)
                for match in matches:
                    if self._is_valid_price(match):
                        result["price"] = f"{self.currency_symbols[currency]}{match}"
                        result["currency"] = currency
                        return result
        
        return result
    
    def _is_valid_price(self, price_str: str) -> bool:
        """Check if a price string is valid"""
        if not price_str:
            return False
        
        # Remove commas and convert to float
        try:
            clean_price = price_str.replace(',', '')
            price = float(clean_price)
            return 0.01 <= price <= 1000000  # Reasonable price range
        except ValueError:
            return False
    
    def extract_description_from_html(self, html: str) -> str:
        """Extract product description from HTML"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try multiple description patterns
            description_patterns = [
                # Amazon's feature bullets
                'div[data-feature-name="feature-bullets"] ul li span',
                'div[id="feature-bullets"] ul li span',
                'div[class*="feature-bullets"] ul li span',
                
                # Product description sections
                'div[id="productDescription"] p',
                'div[class*="productDescription"] p',
                'div[id="aplus"] p',
                'div[class*="aplus"] p',
                
                # Feature list
                'div[id="feature-bullets"] li',
                'div[class*="feature-bullets"] li',
                
                # Generic description areas
                'div[class*="description"] p',
                'div[class*="Description"] p',
            ]
            
            description_parts = []
            
            for pattern in description_patterns:
                elements = soup.select(pattern)
                for element in elements:
                    text = element.get_text(strip=True)
                    if text and len(text) > 10:  # Only meaningful text
                        description_parts.append(text)
                        if len(description_parts) >= 5:  # Limit to 5 bullet points
                            break
                if description_parts:
                    break
            
            # If no structured description found, skip meta tag extraction for now
            pass
            
            # Clean and combine description parts
            if description_parts:
                # Remove duplicates and clean text
                cleaned_parts = []
                for part in description_parts:
                    cleaned = re.sub(r'\s+', ' ', part).strip()
                    if cleaned and len(cleaned) > 10 and cleaned not in cleaned_parts:
                        cleaned_parts.append(cleaned)
                
                # Combine into a neat description
                if cleaned_parts:
                    # Take first 3 meaningful parts and combine
                    final_desc = ' | '.join(cleaned_parts[:3])
                    # Limit length to reasonable size
                    if len(final_desc) > 500:
                        final_desc = final_desc[:497] + "..."
                    return final_desc
            
            return "Description not available"
            
        except Exception as e:
            return f"Description extraction error: {str(e)}"

    def extract_product_name(self, html: str) -> str:
        """Extract product name from HTML"""
        patterns = [
            r'<span[^>]*id="productTitle"[^>]*>(.*?)</span>',
            r'<h1[^>]*id="title"[^>]*>(.*?)</h1>',
            r'<title[^>]*>(.*?)</title>'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if match:
                name = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                name = name.replace('&#39;', "'").replace('&amp;', '&')
                return name[:200]  # Limit length
        
        return "Product name not found"
    
    async def scrape_product(self, url: str) -> Dict:
        """Scrape a single Amazon product"""
        try:
            # Extract ASIN
            asin = self.extract_asin(url)
            if not asin:
                return {"error": "Could not extract ASIN from URL"}
            
            # Get expected currency
            expected_currency = self.get_domain_currency(url)
            
            # Construct clean URL
            domain = urlparse(url).netloc
            clean_url = f"https://{domain}/dp/{asin}"
            
            # Headers to mimic real browser
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
                'Referer': 'https://www.google.com/'
            }
            
            # Create SSL context that doesn't verify certificates
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Create connector with SSL context
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            # Make request
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(clean_url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # Extract data
                        price_data = self.extract_price_from_html(html, expected_currency)
                        product_name = self.extract_product_name(html)
                        description = self.extract_description_from_html(html)
                        
                        return {
                            "url": url,
                            "asin": asin,
                            "product_name": product_name,
                            "price": price_data["price"],
                            "currency": price_data["currency"],
                            "domain": domain,
                            "status": "success",
                            "description": description
                        }
                    else:
                        return {
                            "url": url,
                            "asin": asin,
                            "error": f"HTTP {response.status}",
                            "status": "error"
                        }
                        
        except Exception as e:
            return {
                "url": url,
                "error": str(e),
                "status": "error"
            }
    
    async def scrape_products_batch(self, urls: List[str], batch_size: int = 5) -> List[Dict]:
        """Scrape multiple products with batching and delays"""
        results = []
        
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(urls) + batch_size - 1)//batch_size}")
            
            # Process batch concurrently
            tasks = [self.scrape_product(url) for url in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    results.append({
                        "url": batch[j],
                        "error": str(result),
                        "status": "error"
                    })
                else:
                    results.append(result)
            
            # Add delay between batches
            if i + batch_size < len(urls):
                delay = random.uniform(2, 5)
                print(f"Waiting {delay:.1f} seconds before next batch...")
                await asyncio.sleep(delay)
        
        return results
    
    def save_to_excel(self, results: List[Dict], filename: str = None):
        """Save results to Excel file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"amazon_products_simple_{timestamp}.xlsx"
        
        # Prepare data for Excel
        excel_data = []
        for result in results:
            excel_data.append({
                'URL': result.get('url', ''),
                'ASIN': result.get('asin', ''),
                'Product Name': result.get('product_name', ''),
                'Price': result.get('price', ''),
                'Currency': result.get('currency', ''),
                'Domain': result.get('domain', ''),
                'Status': result.get('status', ''),
                'Error': result.get('error', ''),
                'Description': result.get('description', '')
            })
        
        # Create DataFrame and save
        df = pd.DataFrame(excel_data)
        df.to_excel(filename, index=False, engine='openpyxl')
        
        # Print summary
        successful = len([r for r in results if r.get('status') == 'success'])
        total = len(results)
        
        print(f"\n📊 Summary:")
        print(f"   Total products: {total}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {total - successful}")
        print(f"   Success rate: {(successful/total)*100:.1f}%")
        
        # Currency breakdown
        currencies = {}
        for result in results:
            if result.get('status') == 'success':
                currency = result.get('currency', 'Unknown')
                currencies[currency] = currencies.get(currency, 0) + 1
        
        print(f"\n💰 Currency Distribution:")
        for currency, count in currencies.items():
            print(f"   {currency}: {count} products")
        
        print(f"\n📁 Excel file saved: {filename}")
        return filename

async def main():
    """Main function to run the scraper"""
    # Read URLs from file
    try:
        with open('amazon_50_products.txt', 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("❌ amazon_50_products.txt not found!")
        return
    
    print(f"🚀 Starting Simple Amazon Scraper")
    print(f"📋 Found {len(urls)} URLs to process")
    print("=" * 60)
    
    # Create scraper and run
    scraper = SimpleAmazonScraper()
    results = await scraper.scrape_products_batch(urls, batch_size=3)
    
    # Save results
    filename = scraper.save_to_excel(results)
    
    # Open the file
    import subprocess
    try:
        subprocess.run(['open', filename], check=True)
        print(f"✅ Opened {filename}")
    except:
        print(f"📁 File saved as {filename}")

if __name__ == "__main__":
    asyncio.run(main()) 