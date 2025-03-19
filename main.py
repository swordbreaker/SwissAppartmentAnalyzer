import os
import pandas as pd
from dotenv import load_dotenv
from scrapers.flatfox_scraper import FlatfoxScraper
from tasks.detail_scraping import scrape_details
from tasks.filter_listings import filter_listings
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

    print("Initializing Flatfox Apartment Scraper...")
    scraper = FlatfoxScraper(existing_urls=existing_urls)

    try:
        apartments_df, _ = scrape_overview(scraper, existing_df)
        apartment_details = scrape_details(scraper, apartments_df)
        filter_listings(apartment_details)

    finally:
        # Clean up
        scraper.close()


if __name__ == "__main__":
    main()
