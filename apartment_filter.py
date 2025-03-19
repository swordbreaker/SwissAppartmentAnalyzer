from config import CRITERIA
from image_analyzer import ImageAnalyzer


class ApartmentFilter:
    def __init__(self, image_analyzer: ImageAnalyzer):
        self.image_analyzer = image_analyzer

    def update_criteria(self, new_criteria):
        """Update filtering criteria"""
        self.criteria.update(new_criteria)

    def filter_apartment(self, apartment_details):
        """Check if apartment meets all the criteria"""
        results = {}

        img_results = self.image_analyzer.analyze_images(
            apartment_details.get("image_urls", [])
        )

        text_results = self.image_analyzer.analyze(
            [
                apartment_details.get("description", ""),
                "".join(apartment_details.get("features", [])),
                apartment_details.get("title", ""),
                # apartment_details.get("property_details", ""),
            ]
        )

        for key, _ in CRITERIA.items():
            results[key] = img_results[key] or text_results[key]

        # Check if all criteria are met
        all_criteria_met = all(results.values())

        return {"meets_all_criteria": all_criteria_met, "criteria_results": results}
