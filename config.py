from pydantic import BaseModel, Field
# Configuration settings for the flatfox scraper

# Search parameters
SEARCH_URL = "https://flatfox.ch/de/search/?east=7.737651&is_furnished=false&is_temporary=false&max_price=2250&min_space=68&north=47.625658&ordering=date&south=47.412497&take=48&west=7.496511"


# Filtering criteria - can be modified as needed
class Criteria(BaseModel):
    question: str
    use_image_analysis: bool = Field(default=True)


CRITERIA = {
    "pets_allowed": Criteria(question="are pets allowed?", use_image_analysis=False),
    "bath_has_window": Criteria(question="does the bathroom have a window?"),
    "kitchen_floor_not_wood": Criteria(
        question="is the kitchen floor not made of wood?"
    ),
    "has_dishwasher": Criteria(question="is there a dishwasher?"),
    "has_washingmachine": Criteria(
        question="is there a washing machine in the apartment?"
    ),
    "has_balcony": Criteria(question="does it have a balcony?"),
}

# OpenAI API configuration for image analysis
OPENAI_API_KEY = ""  # Set this in .env file or directly here

# Scraping settings
RESULTS_PER_PAGE = 48
MAX_PAGES_TO_SCRAPE = 10  # Limit number of pages to scrape
HEADLESS_BROWSER = False  # Run browser in headless mode
