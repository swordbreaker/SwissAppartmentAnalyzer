import pandas as pd
from models.scraper import Scraper


def scrape_overview(scraper: Scraper, existing_df: pd.DataFrame):
    print("Scraping apartment listings...")
    # new_apartments = scraper.scrape_listings()
    new_apartments = []

    new_df = None
    # Merge with existing apartments if any
    if existing_df is not None and not existing_df.empty:
        print(f"Found {len(new_apartments)} new apartments to add")
        new_df = pd.DataFrame(new_apartments)
        apartments_df = pd.concat([existing_df, new_df], ignore_index=True)
        # Remove duplicates just in case
        apartments_df = apartments_df.drop_duplicates(subset=["url"], keep="first")
        apartments = apartments_df.to_dict("records")
    else:
        print(f"Found {len(new_apartments)} apartments")
        apartments = new_apartments
        new_df = pd.DataFrame(apartments)

    # Save all listings
    apartments_df.to_csv("output/apartments_basic.csv", index=False)
    print(f"Saved {len(apartments)} total listings to output/apartments_basic.csv")

    return apartments_df, new_df
