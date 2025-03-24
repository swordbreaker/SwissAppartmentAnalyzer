from abc import ABC, abstractmethod
from typing import List, Set

from models.apartment_models import ApartmentDetails, ApartmentListing


class Scraper(ABC):
    """Abstract base class for apartment listing scrapers."""

    def __init__(self, existing_urls: Set[str]):
        self.existing_urls = existing_urls or set()

    @abstractmethod
    def setup_browser(self) -> None:
        """Initialize the browser for scraping"""
        pass

    @abstractmethod
    def scrape_listings(self) -> List[ApartmentListing]:
        """Scrape apartment listings and return a list of basic apartment data"""
        pass

    @abstractmethod
    def get_apartment_details(
        self, apartment_url: ApartmentListing
    ) -> ApartmentDetails:
        """Fetch detailed information about an apartment from its URL"""
        pass

    @abstractmethod
    def is_scraped_by_me(self, apartment: ApartmentListing) -> bool:
        """Check if the apartment was scraped by this scraper"""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the browser and clean up resources"""
        pass
