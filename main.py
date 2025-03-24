import os
import pandas as pd
from dotenv import load_dotenv
from scrapers.flatfox_scraper import FlatfoxScraper
from scrapers.immoscout24_scraper import ImmoScout24Scraper
from tasks.detail_scraping import scrape_details
from tasks.analyze_listings import analyze_listings
from tasks.overview_scraping import scrape_overview


def load_existing_apartments():
    """Load existing apartments from CSV file if it exists"""
    try:
        if os.path.exists("output/apartments_basic.csv"):
            df = pd.read_csv("output/apartments_basic.csv")
            existing_urls = set(df["url"])
            print(
                f"Loaded {len(existing_urls)} existing apartment URLs from apartments_basic.csv"
            )
            return df, existing_urls
        return None, set()
    except Exception as e:
        print(f"Error loading existing apartments: {e}")
        return None, set()


def main():
    # Load environment variables
    load_dotenv()

    # Create output directory
    os.makedirs("output", exist_ok=True)

    existing_df, existing_urls = load_existing_apartments()

    flatfox_scraper = FlatfoxScraper(existing_urls=existing_urls)
    immoscout_scraper = ImmoScout24Scraper(existing_urls=existing_urls)

    try:
        apartments = scrape_overview([flatfox_scraper, immoscout_scraper], existing_df)
        apartment_details = scrape_details(
            [flatfox_scraper, immoscout_scraper], apartments
        )
        analyze_listings(apartment_details)

    finally:
        # Clean up
        flatfox_scraper.close()


if __name__ == "__main__":
    main()
