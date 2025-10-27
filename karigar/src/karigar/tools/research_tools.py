"""
Research Tools
Web scraping, market analysis, competitor research, trend detection
"""

import requests
from datetime import datetime
from typing import Dict, List, Optional
from .base_tool import BaseTool, ToolResult

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False


class WebScraperTool(BaseTool):
    """Scrape websites for market and competitor research"""

    def __init__(self):
        super().__init__(
            name="web_scraper",
            description="Scrape websites for market information and competitor analysis",
            required_params=["url", "scrape_type"]
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    async def execute(self, **kwargs) -> ToolResult:
        """Scrape website with real BeautifulSoup"""
        start_time = datetime.utcnow()

        try:
            url = kwargs.get("url")
            scrape_type = kwargs.get("scrape_type")  # prices, reviews, listings, contact

            if not BEAUTIFULSOUP_AVAILABLE:
                return self._fallback_scrape(url, scrape_type, start_time)

            # REAL web scraping with BeautifulSoup
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract data based on type
            if scrape_type == "prices":
                items = self._scrape_prices(soup)
            elif scrape_type == "reviews":
                items = self._scrape_reviews(soup)
            elif scrape_type == "listings":
                items = self._scrape_listings(soup)
            elif scrape_type == "contact":
                items = self._scrape_contact(soup)
            else:
                items = self._scrape_general(soup)

            scraped_data = {
                "url": url,
                "scrape_type": scrape_type,
                "timestamp": datetime.utcnow().isoformat(),
                "items_found": len(items),
                "data": items
            }

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=scraped_data,
                message=f"Successfully scraped {url} - found {len(items)} items",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"url": url, "scrape_type": scrape_type, "items": len(items)}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return ToolResult(
                success=False,
                data=None,
                message=f"Web scraping failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )

    def _scrape_prices(self, soup) -> List[Dict]:
        """Scrape product prices"""
        items = []

        # Look for common price patterns
        for elem in soup.find_all(['span', 'div', 'p'], class_=lambda x: x and 'price' in x.lower()):
            text = elem.get_text(strip=True)
            if '₹' in text or '$' in text:
                items.append({
                    "price": text,
                    "type": "price",
                    "html": str(elem)[:100]
                })

        # Generic extraction if specific patterns don't match
        if not items:
            items = [{
                "price": elem.get_text(strip=True),
                "type": "generic"
            } for elem in soup.find_all(['span', 'div'])[:10] if any(c.isdigit() for c in elem.get_text())]

        return items[:20]  # Return top 20

    def _scrape_reviews(self, soup) -> List[Dict]:
        """Scrape reviews and ratings"""
        items = []

        # Look for review patterns
        for elem in soup.find_all(['div', 'article'], class_=lambda x: x and 'review' in x.lower()):
            text = elem.get_text(strip=True)
            rating = self._extract_rating(text)
            items.append({
                "review": text[:200],
                "rating": rating,
                "source": "website"
            })

        return items[:20]

    def _scrape_listings(self, soup) -> List[Dict]:
        """Scrape product listings"""
        items = []

        for elem in soup.find_all(['li', 'div'], class_=lambda x: x and 'product' in str(x).lower()):
            items.append({
                "listing": elem.get_text(strip=True)[:100],
                "html": str(elem)[:50]
            })

        return items[:20]

    def _scrape_contact(self, soup) -> List[Dict]:
        """Scrape contact information"""
        items = []

        # Look for phone and email
        text = soup.get_text()

        import re
        phones = re.findall(r'\+?\d{1,3}[-.\s]?\d{3,4}[-.\s]?\d{3,4}', text)
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)

        for phone in phones:
            items.append({"type": "phone", "value": phone})
        for email in emails:
            items.append({"type": "email", "value": email})

        return items

    def _scrape_general(self, soup) -> List[Dict]:
        """Scrape general content"""
        items = []

        for para in soup.find_all('p')[:10]:
            text = para.get_text(strip=True)
            if len(text) > 50:
                items.append({"content": text[:200]})

        return items

    def _extract_rating(self, text: str) -> Optional[float]:
        """Extract rating from text"""
        import re
        match = re.search(r'(\d+\.?\d*)\s*(?:out of|\/)', text)
        if match:
            return float(match.group(1))
        return None

    def _fallback_scrape(self, url: str, scrape_type: str, start_time: datetime) -> ToolResult:
        """Fallback when BeautifulSoup not available"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data={
                    "url": url,
                    "scrape_type": scrape_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "basic_scrape",
                    "content_length": len(response.content),
                    "status_code": response.status_code
                },
                message=f"Basic scrape completed (install beautifulsoup4 for full scraping)",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return ToolResult(
                success=False,
                data=None,
                message=f"Web scraping failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )


class MarketResearchTool(BaseTool):
    """Conduct market research for craft categories"""

    def __init__(self):
        super().__init__(
            name="market_research",
            description="Research market trends, demand, and opportunities",
            required_params=["craft_type", "location"]
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Research market"""
        start_time = datetime.utcnow()

        try:
            craft_type = kwargs.get("craft_type")
            location = kwargs.get("location")

            # Mock market research
            market_data = {
                "craft_type": craft_type,
                "location": location,
                "market_size": "₹500 Crores",
                "growth_rate": "15% YoY",
                "key_channels": [
                    {"channel": "Online Marketplaces", "share": "35%"},
                    {"channel": "Direct Sales", "share": "25%"},
                    {"channel": "Exhibitions/Fairs", "share": "20%"},
                    {"channel": "Wholesale", "share": "20%"},
                ],
                "customer_segments": [
                    "Tourists (40%)",
                    "Corporate Gifting (25%)",
                    "Home Decor (20%)",
                    "Fashion (15%)",
                ],
                "price_ranges": {
                    "budget": "₹500-₹2000",
                    "mid": "₹2000-₹5000",
                    "premium": "₹5000-₹20000",
                },
                "trends": [
                    "Sustainable/Eco-friendly products",
                    "Personalization and customization",
                    "Niche online communities",
                    "Experience-based sales",
                ],
                "opportunities": [
                    "Export to international markets",
                    "Corporate bulk orders",
                    "Subscription boxes",
                    "Artisan collaborations",
                ]
            }

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=market_data,
                message=f"Market research completed for {craft_type} in {location}",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"craft_type": craft_type, "location": location}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return ToolResult(
                success=False,
                data=None,
                message=f"Market research failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )


class CompetitorAnalysisTool(BaseTool):
    """Analyze competitors and pricing strategies"""

    def __init__(self):
        super().__init__(
            name="competitor_analysis",
            description="Analyze competitors and their pricing strategies",
            required_params=["craft_type", "location"]
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Analyze competitors"""
        start_time = datetime.utcnow()

        try:
            craft_type = kwargs.get("craft_type")
            location = kwargs.get("location")

            # Mock competitor analysis
            competitors = [
                {
                    "name": "Competitor A",
                    "location": location,
                    "avg_price": 5000,
                    "reviews": 250,
                    "rating": 4.3,
                    "specialization": craft_type,
                    "strengths": ["Quality", "Brand recognition"],
                    "weaknesses": ["High prices", "Limited customization"],
                },
                {
                    "name": "Competitor B",
                    "location": location,
                    "avg_price": 3500,
                    "reviews": 180,
                    "rating": 4.1,
                    "specialization": craft_type,
                    "strengths": ["Affordable", "Fast delivery"],
                    "weaknesses": ["Quality concerns", "Small variety"],
                },
            ]

            analysis = {
                "craft_type": craft_type,
                "location": location,
                "competitors_found": len(competitors),
                "average_price": sum([c["avg_price"] for c in competitors]) / len(competitors),
                "average_rating": sum([c["rating"] for c in competitors]) / len(competitors),
                "competitors": competitors,
                "pricing_strategy_recommendation": "Premium with quality focus",
            }

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=analysis,
                message=f"Competitor analysis completed: Found {len(competitors)} competitors",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"competitors_count": len(competitors)}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return ToolResult(
                success=False,
                data=None,
                message=f"Competitor analysis failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )


class TrendDetectionTool(BaseTool):
    """Detect market trends and seasonal patterns"""

    def __init__(self):
        super().__init__(
            name="trend_detection",
            description="Detect market trends, seasonal patterns, and demand forecasts",
            required_params=["craft_type"]
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Detect trends"""
        start_time = datetime.utcnow()

        try:
            craft_type = kwargs.get("craft_type")

            # Mock trend detection
            trends = {
                "craft_type": craft_type,
                "current_trends": [
                    "Sustainable materials (↑ 40% interest)",
                    "Minimalist designs (↑ 30% interest)",
                    "Personalized products (↑ 50% interest)",
                    "Fusion traditional-modern (↑ 25% interest)",
                ],
                "seasonal_patterns": {
                    "Q1": "Wedding season - high demand",
                    "Q2": "Corporate gifting season",
                    "Q3": "Back to school/office - moderate",
                    "Q4": "Festival/holiday season - peak demand",
                },
                "emerging_opportunities": [
                    "Niche online communities",
                    "Subscription models",
                    "B2B corporate partnerships",
                    "International export",
                ],
                "declining_interest": [
                    "Mass-produced imitations",
                    "Poor quality budget items",
                ],
                "forecast_next_6_months": "Positive growth expected (20-30%)",
            }

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return ToolResult(
                success=True,
                data=trends,
                message=f"Trend analysis completed for {craft_type}",
                execution_time=execution_time,
                timestamp=datetime.utcnow(),
                metadata={"craft_type": craft_type}
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return ToolResult(
                success=False,
                data=None,
                message=f"Trend detection failed: {str(e)}",
                execution_time=execution_time,
                timestamp=datetime.utcnow()
            )


# Tool instances
web_scraper = WebScraperTool()
market_research = MarketResearchTool()
competitor_analysis = CompetitorAnalysisTool()
trend_detection = TrendDetectionTool()
