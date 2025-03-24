import pandas as pd
from models.apartment_models import ApartmentListing
from models.scraper import Scraper


def scrape_overview(
    scrapers: list[Scraper], existing_df: pd.DataFrame | None
) -> list[ApartmentListing]:
    print("Scraping apartment listings...")
    new_apartments: list[ApartmentListing] = []
    for scraper in scrapers:
        new_apartments.extend(scraper.scrape_listings())

    apartment_dicts = list(map(lambda x: x.model_dump(), new_apartments))

    new_df = None
    apartments_df = None
    # Merge with existing apartments if any
    if existing_df is not None and not existing_df.empty:
        print(f"Found {len(new_apartments)} new apartments to add")
        new_df = pd.DataFrame(apartment_dicts)
        apartments_df = pd.concat([existing_df, new_df], ignore_index=True)
        # Remove duplicates just in case
        apartments_df = apartments_df.drop_duplicates(subset=["url"], keep="first")
    else:
        print(f"Found {len(new_apartments)} apartments")
        new_df = pd.DataFrame(apartment_dicts)
        apartments_df = new_df.copy()

    # Save all listings
    apartments_df.to_csv("output/apartments_basic.csv", index=False)

    apartments = apartments_df.to_dict(orient="records")

    print(f"Saved {len(apartments)} total listings to output/apartments_basic.csv")

    return [ApartmentListing(**{str(k): v for k, v in d.items()}) for d in apartments]
