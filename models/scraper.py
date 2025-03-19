from abc import ABC, abstractmethod
from typing import List, Dict, Any, Set


class Scraper(ABC):
    """Abstract base class for apartment listing scrapers."""

    def __init__(self, existing_urls: Set[str] = None):
        self.existing_urls = existing_urls or set()

    @abstractmethod
    def setup_browser(self) -> None:
        """Initialize the browser for scraping"""
        pass

    @abstractmethod
    def scrape_listings(self) -> List[Dict[str, Any]]:
        """Scrape apartment listings and return a list of basic apartment data"""
        pass

    @abstractmethod
    def get_apartment_details(self, apartment_url: str) -> Dict[str, Any]:
        """Fetch detailed information about an apartment from its URL"""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the browser and clean up resources"""
        pass
