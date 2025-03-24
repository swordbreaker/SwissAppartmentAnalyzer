import json
from config import CRITERIA
from image_analyzer import ImageAnalyzer
import pandas as pd
from tqdm import tqdm

from models.apartment_models import ApartmentDetails, ApartmentAnalyzed, FilterResult


def analyze_listings(apartment_details: list[ApartmentDetails]):
    # Step 2: Initialize image analyzer
    print("Initializing image analyzer...")
    image_analyzer = ImageAnalyzer()

    # Step 3: Initialize apartment filter
    print("Setting up apartment filter with criteria:")
    for criterion, value in CRITERIA.items():
        print(f"  - {criterion}: {value}")

    # Step 4: Process each apartment
    print("\nProcessing apartments (this may take some time)...")
    criteria_results = []

    # For demo purposes, limit to first 10 apartments
    processing_limit = min(10, len(apartment_details))

    for i, apt in tqdm(enumerate(apartment_details)):
        # print(f"\nProcessing apartment {i + 1}/{processing_limit}: {apt['title']}")

        # Filter apartment
        met_criteria, apartment_summary = image_analyzer.analyze(apt)
        # Check if all criteria are met
        all_criteria_met = all(met_criteria.values())

        # Store results
        apartment_result = ApartmentAnalyzed(
            **apt.model_dump(),
            apartment_summary=apartment_summary,
            filter_result=FilterResult(
                meets_all_criteria=all_criteria_met,
                criteria_results=met_criteria,
            ),
        )

        criteria_results.append(apartment_result)

        # Print result summary
        print(f"Results for: {apt.title} {apt.url}")
        print(f"  - Meets all criteria: {all_criteria_met}")
        for criterion, met in met_criteria.items():
            print(f"  - {criterion}: {'✓' if met else '✗'}")

    # Step 5: Save final results
    filtered_apartments = [
        apt for apt in criteria_results if apt["filter_result"]["meets_all_criteria"]
    ]

    # Save as JSON
    with open("output/filtered_apartments.json", "w") as f:
        json.dump(filtered_apartments, f, indent=2)

    # Save as CSV
    flat_results = []
    for apt in criteria_results:
        flat_apt = {
            "title": apt["title"],
            "price_details": apt.get("price_details", ""),
            "street": apt.get("street", ""),
            "city_info": apt.get("city_info", ""),
            "url": apt["url"],
            "meets_all_criteria": apt["filter_result"]["meets_all_criteria"],
            "apartment_summary": apt["apartment_summary"],
        }

        # Add criteria results
        for criterion, met in apt["filter_result"]["criteria_results"].items():
            flat_apt[criterion] = met

        flat_results.append(flat_apt)

    df = pd.DataFrame(flat_results)
    df.to_csv("output/filtered_apartments.csv", index=False)

    print(f"\nProcessing complete!")
    print(
        f"Found {len(filtered_apartments)} apartments matching all criteria out of {processing_limit} processed"
    )
    print(f"Results saved to:")
    print(f"  - output/filtered_apartments.csv")
    print(f"  - output/filtered_apartments.json")
