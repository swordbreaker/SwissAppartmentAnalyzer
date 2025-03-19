import json
import os
from tqdm import tqdm
from models.scraper import Scraper
import pandas as pd


def scrape_details(scraper: Scraper, apartments_df: pd.DataFrame):
    print("load apartment details")

    # File path for apartment details
    output_file = "output/apartments_details.json"

    # Load existing apartment details if file exists
    existing_details = []
    existing_urls = set()
    if os.path.exists(output_file):
        try:
            with open(output_file, "r") as f:
                existing_details = json.load(f)
                # Create a set of URLs that we already have details for
                existing_urls = {apt.get("url", "") for apt in existing_details}
            print(f"Loaded {len(existing_details)} existing apartment details")
        except Exception as e:
            print(f"Error loading existing details: {e}")

    # Filter apartments to only scrape new ones
    new_apartments = [
        apt
        for apt in apartments_df.to_dict("records")
        if apt["url"] not in existing_urls
    ]
    print(
        f"Scraping {len(new_apartments)} new apartments out of {len(apartments_df)} total"
    )

    # Scrape new apartment details
    new_details = []
    for i, apt in tqdm(enumerate(new_apartments), total=len(new_apartments)):
        try:
            # Get detailed info
            details = scraper.get_apartment_details(apt["url"])
            new_details.append({**details, "url": apt["url"]})
        except Exception as e:
            print(f"Error getting details for apartment {apt['url']}: {e}")

    # Merge existing and new details
    all_details = existing_details + new_details

    # Store combined results
    with open(output_file, "w") as f:
        json.dump(all_details, f, indent=2)

    print(
        f"Saved {len(all_details)} apartment details ({len(new_details)} newly scraped)"
    )

    return all_details
