from typing import List, Dict, Any, Set
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.remote.webelement import WebElement
import config  # Import the entire module
from tqdm import tqdm
from models.scraper import Scraper


class FlatfoxScraper(Scraper):
    def __init__(self, existing_urls: Set[str] = None):
        super().__init__(existing_urls)
        self.setup_browser()

    def setup_browser(self) -> None:
        """Initialize the browser for scraping"""
        options = Options()
        if config.HEADLESS_BROWSER:  # Access as config.VARIABLE
            options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--enable-unsafe-swiftshader")

        self.driver = webdriver.Edge(
            service=Service(EdgeChromiumDriverManager().install()), options=options
        )

    def scrape_listings(self) -> List[Dict[str, str]]:
        """Scrape apartment listings from flatfox.ch"""
        print("Starting to scrape Flatfox listings...")
        self.driver.get(config.SEARCH_URL)  # Access as config.VARIABLE

        new_listings_count = 0
        existing_count = len(self.existing_urls)
        if existing_count > 0:
            print(f"Will skip {existing_count} already scraped listings")

        # Wait for the page to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "listing-thumb"))
        )

        try:
            self.driver.find_element(By.ID, "onetrust-accept-btn-handler").click()
        except:
            # Cookie button might not appear if cookies are already accepted
            pass

        apartments: List[Dict[str, str]] = []
        pages_loaded: int = 1

        # Continue loading more pages until reaching the maximum or no more results
        while pages_loaded <= config.MAX_PAGES_TO_SCRAPE:
            # Extract property cards on the current page
            property_cards: List[WebElement] = self.driver.find_elements(
                By.CLASS_NAME, "listing-thumb"
            )

            # Process current cards
            # ...existing code...

            print(
                f"Loaded page {pages_loaded} - found {len(property_cards)} listings so far"
            )

            # Try to click "Show more" button to load more results
            try:
                # Find the "Mehr anzeigen" (Show more) button
                show_more_button: WebElement = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[@aria-label='Mehr anzeigen']")
                    )
                )

                # Scroll to the button to make it visible
                self.driver.execute_script(
                    "arguments[0].scrollIntoView(true);", show_more_button
                )
                time.sleep(1)  # Brief pause to ensure element is clickable

                # Click the button
                show_more_button.click()
                pages_loaded += 1

                # Wait for new content to load
                time.sleep(3)

                # Wait until the page finishes loading the new content
                old_count: int = len(property_cards)
                WebDriverWait(self.driver, 10).until(
                    lambda driver: len(
                        driver.find_elements(By.CLASS_NAME, "listing-thumb")
                    )
                    > old_count
                )

            except Exception:
                print(f"No more results to load or reached the end")
                break

        # After loading all pages, collect all listings
        all_property_cards = self.driver.find_elements(By.CLASS_NAME, "listing-thumb")
        print(f"Total listings found: {len(all_property_cards)}")

        # Process all cards to extract data
        for card in tqdm(all_property_cards):
            try:
                # Get link element and URL
                link_element = card.find_element(
                    By.CSS_SELECTOR, "a.listing-thumb__image"
                )
                url = link_element.get_attribute("href")

                # Skip if already in our database
                if url in self.existing_urls:
                    continue

                new_listings_count += 1

                # Extract basic info from the card
                # Title is in h2 inside listing-thumb-title
                title_element = card.find_element(By.CSS_SELECTOR, "h2")
                title = (
                    title_element.text.split("\n")[0]
                    if "\n" in title_element.text
                    else title_element.text
                )

                # Location is in a span with class listing-thumb-title__location
                location = card.find_element(
                    By.CSS_SELECTOR, "span.listing-thumb-title__location"
                ).text

                # Get currency and additional price info
                price_container = card.find_element(
                    By.CSS_SELECTOR, ".attributes div div"
                )
                price_info = (
                    price_container.text
                )  # Contains "1'387 CHF" or "1'900 CHF / m²"

                apartment = {
                    "title": title,
                    "price": price_info,
                    "location": location,
                    "url": url,
                }

                apartments.append(apartment)
            except Exception as e:
                print(f"Error scraping apartment card: {e}")

        print(
            f"Found {new_listings_count} new apartments (skipped {len(all_property_cards) - new_listings_count} existing)"
        )
        return apartments

    def get_apartment_details(self, apartment_url: str) -> Dict[str, Any]:
        """Fetch detailed information about an apartment"""
        print(f"Fetching details for: {apartment_url}")
        self.driver.get(apartment_url)

        # Wait for the page to load
        WebDriverWait(self.driver, 1).until(
            EC.presence_of_element_located((By.CLASS_NAME, "flat-details-gallery"))
        )

        try:
            self.driver.find_element(By.ID, "onetrust-accept-btn-handler").click()
        except:
            # Cookie button might not appear if cookies are already accepted
            pass

        # Extract detailed information
        details = {}

        # Try the new title structure first, then fall back to the old one
        try:
            widget_title = self.driver.find_element(
                By.CSS_SELECTOR, ".widget-listing-title"
            )
            if widget_title:
                # Extract main title from h1
                main_title = widget_title.find_element(
                    By.CSS_SELECTOR, "h1"
                ).text.strip()
                details["title"] = main_title

                # Extract location and price from h2
                subtitle = widget_title.find_element(By.CSS_SELECTOR, "h2").text.strip()

                # Parse subtitle (format: "Street, Postal Code City - Price")
                if "-" in subtitle:
                    location_part, price_part = subtitle.split(" - ", 1)

                    # Extract location
                    if "," in location_part:
                        street, city_info = location_part.split(",", 1)
                        details["street"] = street.strip()
                        details["city_info"] = city_info.strip()
                    else:
                        details["location"] = location_part.strip()

                    # Extract price
                    details["price_details"] = price_part.strip()
        except Exception as e:
            print(f"Error extracting from new title structure: {e}")

        # Fall back to the old structure if needed
        if "title" not in details:
            try:
                details["title"] = self.driver.find_element(
                    By.CSS_SELECTOR, "h1.PropertyDetailPage-title"
                ).text
            except Exception as e:
                print(f"Error extracting title from old structure: {e}")
                details["title"] = ""

        # Description - Try the new structure first
        try:
            description_section = self.driver.find_element(
                By.XPATH, "//div/h2[contains(text(), 'Beschreibung')]/.."
            )
            if description_section:
                # Try to get the heading (in strong tag)
                description_heading = ""
                try:
                    heading_element = description_section.find_element(
                        By.CSS_SELECTOR, "strong.user-generated-content"
                    )
                    description_heading = heading_element.text.strip()
                except Exception:
                    pass  # No heading found

                # Get the main description content
                description_content = ""
                try:
                    content_element = description_section.find_element(
                        By.CSS_SELECTOR, "div.markdown"
                    )
                    description_content = content_element.text.strip()
                except Exception as e:
                    print(f"Error extracting markdown content: {e}")

                # Combine heading and content
                full_description = ""
                if description_heading:
                    full_description = f"{description_heading}\n\n"
                if description_content:
                    full_description += description_content

                if full_description:
                    details["description"] = full_description

                    # Extract features from description bullet points
                    # Look for lines starting with "-" or "•"
                    description_features = []
                    for line in description_content.split("\n"):
                        line = line.strip()
                        if line.startswith("-") or line.startswith("•"):
                            # Remove the bullet and trim
                            feature = line[1:].strip()
                            if feature:
                                description_features.append(feature)

                    # Add these features to the features list
                    if description_features:
                        if "features" not in details:
                            details["features"] = []

                        # Add features from description if not already in the list
                        for feature in description_features:
                            if feature not in details["features"]:
                                details["features"].append(feature)

                        # Also store them separately if needed
                        details["description_features"] = description_features
        except Exception as e:
            print(f"Error extracting from new description structure: {e}")
            details["description"] = ""

        # Extract property details from table
        property_details = {}
        try:
            # Look for the details table
            tables = self.driver.find_elements(By.CSS_SELECTOR, "table.table--rows")
            for table in tables:
                # Check if this is the details table
                try:
                    # Get all rows in the table
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    for row in rows:
                        # Each row has two cells: key and value
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) == 2:
                            key = cells[0].text.strip().rstrip(":")
                            value = cells[1].text.strip()
                            if key and value:
                                # Clean up the key to make it usable as a dictionary key
                                key_cleaned = (
                                    key.lower().replace(" ", "_").replace(":", "")
                                )
                                property_details[key_cleaned] = value
                except Exception as e:
                    print(f"Error processing table row: {e}")

            # Store the extracted details
            if property_details:
                details["property_details"] = property_details

                # Extract some common fields to the top level for easier access
                if "nutzfläche" in property_details:
                    area_text = property_details["nutzfläche"]
                    # Try to extract numeric area value (e.g., "99 m²" -> 99)
                    try:
                        area_value = area_text.split()[0].replace(",", ".")
                        details["area"] = float(area_value)
                    except (IndexError, ValueError):
                        details["area_text"] = area_text

                if "bezugstermin" in property_details:
                    details["available_from"] = property_details["bezugstermin"]

                if "ausstattung" in property_details:
                    # Split features by comma if they're combined
                    features_text = property_details["ausstattung"]
                    additional_features = [f.strip() for f in features_text.split(",")]

                    # Add to existing features or create new list
                    if "features" not in details:
                        details["features"] = []
                    details["features"].extend(additional_features)

                if "etage" in property_details:
                    details["floor"] = property_details["etage"]

        except Exception as e:
            print(f"Error extracting property details table: {e}")

        # Images
        image_urls = []
        try:
            # Try the new gallery structure first
            try:
                figure_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, ".flat-detail-gallery figure"
                )
                if figure_elements:
                    for fig in figure_elements:
                        try:
                            link_element = fig.find_element(By.TAG_NAME, "a")
                            img_url = link_element.get_attribute("href")
                            if img_url and not img_url.endswith("placeholder.jpg"):
                                image_urls.append(img_url)
                        except Exception as e:
                            print(f"Error extracting image from figure: {e}")
                else:
                    # Fall back to the old structure
                    image_elements = self.driver.find_elements(
                        By.CSS_SELECTOR, ".PropertyGallery img"
                    )
                    for img in image_elements:
                        img_url = img.get_attribute("src")
                        if img_url and not img_url.endswith("placeholder.jpg"):
                            image_urls.append(img_url)
            except Exception as e:
                # If new structure fails, try the old one
                print(f"Error with new image structure, trying old structure: {e}")
                image_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, ".PropertyGallery img"
                )
                for img in image_elements:
                    img_url = img.get_attribute("src")
                    if img_url and not img_url.endswith("placeholder.jpg"):
                        image_urls.append(img_url)
        except Exception as e:
            print(f"Error extracting images: {e}")

        details["image_urls"] = image_urls

        return details

    def close(self) -> None:
        """Close the browser"""
        if hasattr(self, "driver"):
            self.driver.quit()


if __name__ == "__main__":
    scraper = FlatfoxScraper()
    try:
        apartments = scraper.scrape_listings()

        # Save basic apartment data
        df = pd.DataFrame(apartments)
        df.to_csv("apartments_basic.csv", index=False)
        print(
            f"Saved {len(apartments)} basic apartment listings to apartments_basic.csv"
        )

        # Get detailed information for the first 5 apartments as a test
        for i, apt in enumerate(apartments[:5]):
            details = scraper.get_apartment_details(apt["url"])
            print(f"Details for apartment {i + 1}:")
            print(f"Title: {details['title']}")
            print(f"Features: {details['features']}")
            print(f"Images: {len(details['image_urls'])}")
            print("---")

    finally:
        scraper.close()
