import json
from apartment_filter import ApartmentFilter
from config import CRITERIA
from image_analyzer import ImageAnalyzer
import pandas as pd


def filter_listings(apartment_details: list[dict[str, any]]):
    # Step 2: Initialize image analyzer
    print("Initializing image analyzer...")
    image_analyzer = ImageAnalyzer()

    # Step 3: Initialize apartment filter
    print("Setting up apartment filter with criteria:")
    for criterion, value in CRITERIA.items():
        print(f"  - {criterion}: {value}")
    apartment_filter = ApartmentFilter(image_analyzer)

    # Step 4: Process each apartment
    print("\nProcessing apartments (this may take some time)...")
    results = []

    # For demo purposes, limit to first 10 apartments
    processing_limit = min(10, len(apartment_details))
    print(f"Will process first {processing_limit} apartments as a demo...")

    for i, apt in enumerate(apartment_details[:processing_limit]):
        print(f"\nProcessing apartment {i + 1}/{processing_limit}: {apt['title']}")

        # Filter apartment
        filter_result = apartment_filter.filter_apartment(apt)

        # Store results
        apartment_result = {
            **apt,
            "filter_result": filter_result,
        }

        results.append(apartment_result)

        # Print result summary
        criteria_results = filter_result["criteria_results"]
        print(f"Results for: {apt['title']} {apt['url']}")
        print(f"  - Meets all criteria: {filter_result['meets_all_criteria']}")
        for criterion, met in criteria_results.items():
            print(f"  - {criterion}: {'✓' if met else '✗'}")

    # Step 5: Save final results
    filtered_apartments = [
        apt for apt in results if apt["filter_result"]["meets_all_criteria"]
    ]

    # Save as JSON
    with open("output/filtered_apartments.json", "w") as f:
        json.dump(filtered_apartments, f, indent=2)

    # Save as CSV
    flat_results = []
    for apt in results:
        flat_apt = {
            "title": apt["title"],
            "price_details": apt["price_details"],
            "street": apt["street"],
            "city_info": apt["city_info"],
            "url": apt["url"],
            "meets_all_criteria": apt["filter_result"]["meets_all_criteria"],
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
