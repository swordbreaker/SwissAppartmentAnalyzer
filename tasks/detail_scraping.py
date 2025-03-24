import os
import logging
from tqdm import tqdm
from models.scraper import Scraper
from models.apartment_models import (
    ApartmentDetails,
    ApartmentListing,
    apartment_detail_list_adapter,
)


def scrape_details(
    scrapers: list[Scraper], apartments: list[ApartmentListing]
) -> list[ApartmentDetails]:
    print("load apartment details")

    # File path for apartment details
    output_file = "output/apartments_details.json"

    # Load existing apartment details if file exists
    existing_details: list[ApartmentDetails] = []
    existing_urls = set()
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                existing_details = apartment_detail_list_adapter.validate_json(f.read())

                # Create a set of URLs that we already have details for
                existing_urls = {apt.url for apt in existing_details}
            print(f"Loaded {len(existing_details)} existing apartment details")
        except Exception as e:
            logging.error(f"Error loading existing details: {e}")

    # Filter apartments to only scrape new ones
    new_apartments = [apt for apt in apartments if apt.url not in existing_urls]
    print(
        f"Scraping {len(new_apartments)} new apartments out of {len(apartments)} total"
    )

    # Scrape new apartment details
    new_details: list[ApartmentDetails] = []
    for i, apt in tqdm(enumerate(new_apartments), total=len(new_apartments)):
        try:
            details: ApartmentDetails | None = None
            for scraper in scrapers:
                if scraper.is_scraped_by_me(apt):
                    # Use the scraper to get details for this apartment
                    details = scraper.get_apartment_details(apt)
                    break

            if details is not None:
                new_details.append(details)
        except Exception as e:
            logging.error(f"Error getting details for apartment {apt.url}: {e}")

    # Merge existing and new details
    all_details = existing_details + new_details

    # Store combined results
    with open(output_file, "w", encoding="utf-8") as f:
        json_string = apartment_detail_list_adapter.dump_json(all_details, indent=2)
        f.write(json_string.decode("utf-8"))

    print(
        f"Saved {len(all_details)} apartment details ({len(new_details)} newly scraped)"
    )

    return all_details
