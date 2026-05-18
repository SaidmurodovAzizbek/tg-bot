"""
Instagram Scraper module (Powered by Apify).

This module collects comments from Instagram posts without requiring
login credentials, avoiding IP blacklists using Apify's infrastructure.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any

from apify_client import ApifyClient
from config import Config

logger = logging.getLogger(__name__)

# ── Data Models ────────────────────────────────────────────────────────

@dataclass
class ScrapedComment:
    """Represents a single scraped comment."""
    id: str
    username: str
    text: str
    likes_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "text": self.text,
            "likes_count": self.likes_count,
        }

@dataclass
class ScrapeResult:
    """Container for the scraping results."""
    post_url: str
    media_id: str = "unknown"
    comments: List[ScrapedComment] = field(default_factory=list)
    total_comments: int = 0


# ── Validation ────────────────────────────────────────────────────────

_INSTAGRAM_URL_PATTERN = re.compile(
    r"^https?://(www\.)?instagram\.com/(p|reel|tv)/[\w-]+/?(.*?)$"
)

# ── Main Scraper Class ────────────────────────────────────────────────

class ApifyInstagramScraper:
    """Class to scrape Instagram comments using Apify."""

    def __init__(self, config: Config):
        self._config = config
        
        if not self._config.apify_api_token or self._config.apify_api_token.startswith("your_"):
            raise ValueError(
                "APIFY_API_TOKEN is missing! "
                "Please register on apify.com, get a token, and add it to the .env file."
            )
            
        self.client = ApifyClient(self._config.apify_api_token)

    def scrape_comments(self, post_url: str) -> ScrapeResult:
        """
        Scrapes comments from the given URL using Apify.
        """
        self._validate_url(post_url)
        
        logger.info(f"Analyzing URL via Apify: {post_url}")
        
        # Official Instagram comment scraper actor on Apify
        actor_id = "apify/instagram-comment-scraper"
        
        # Actor input payload
        run_input = {
            "directUrls": [post_url],
            "resultsLimit": self._config.max_comments,
        }

        try:
            logger.info("Starting Apify scraper. This may take a few seconds...")
            # Run the actor synchronously
            run = self.client.actor(actor_id).call(run_input=run_input)
            
            # Fetch results (Dataset)
            dataset_id = run["defaultDatasetId"]
            items = list(self.client.dataset(dataset_id).iterate_items())
            
            logger.info(f"Apify found {len(items)} comments.")
            
            scraped_comments = []
            for item in items:
                # Map Apify JSON to our data model
                scraped_comments.append(
                    ScrapedComment(
                        id=item.get("id", "unknown"),
                        username=item.get("ownerUsername", "unknown"),
                        text=item.get("text", ""),
                        likes_count=item.get("likesCount", 0),
                    )
                )

            return ScrapeResult(
                post_url=post_url,
                media_id=self._extract_shortcode(post_url),
                comments=scraped_comments,
                total_comments=len(scraped_comments)
            )
            
        except Exception as e:
            logger.error(f"Communication error with Apify: {e}")
            raise ConnectionError(f"Error collecting data (Apify): {e}")

    @staticmethod
    def _validate_url(url: str) -> None:
        """Validates the Instagram URL format."""
        if not _INSTAGRAM_URL_PATTERN.match(url):
            raise ValueError(
                f"Invalid Instagram URL: {url}\n"
                f"Correct format: https://www.instagram.com/p/XXXXXX/"
            )

    @staticmethod
    def _extract_shortcode(url: str) -> str:
        """Extracts the post shortcode from the URL."""
        # Example: https://www.instagram.com/p/ABC123/?igsh=...
        try:
            clean_url = url.split("?")[0].rstrip("/")
            parts = clean_url.split("/")
            return parts[-1] if parts else "unknown"
        except Exception:
            return "unknown"


# ── Convenience wrapper ───────────────────────────────────────────────

def scrape_comments(config: Config, post_url: str) -> ScrapeResult:
    """
    Convenience wrapper for external use.
    """
    scraper = ApifyInstagramScraper(config)
    return scraper.scrape_comments(post_url)
