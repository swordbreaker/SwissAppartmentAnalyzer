from typing import List, Set
import time
import logging
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import config
from tqdm import tqdm
from models.scraper import Scraper
from models.apartment_models import (
    ApartmentListing,
    ApartmentDetails,
)


class ImmoScout24Scraper(Scraper):
    def __init__(self, existing_urls: Set[str] = set()):
        super().__init__(existing_urls)
        self.base_url = "https://www.immoscout24.ch"
        self.setup_browser()

    def setup_browser(self) -> None:
        """Initialize the browser for scraping"""
        options = Options()
        if config.HEADLESS_BROWSER:
            options.add_argument("--headless")
        options.add_argument("--lang=de-CH")
        options.add_argument("--charset=UTF-8")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--log-level=3")
        options.add_argument("--enable-unsafe-swiftshader")
        options.add_argument("--log-level=3")
        options.add_argument("--disable-logging")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        self.driver = webdriver.Edge(
            service=Service(EdgeChromiumDriverManager().install()), options=options
        )

    def scrape_listings(self) -> List[ApartmentListing]:
        """Scrape apartment listings from immoscout24.ch"""
        print("Starting to scrape ImmoScout24 listings...")
        self.driver.get(config.IMMOSCOUT_URL)

        new_listings_count = 0
        existing_count = len(self.existing_urls)
        if existing_count > 0:
            print(f"Will skip {existing_count} already scraped listings")

        # Wait for the page to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='listitem']"))
        )

        try:
            # Accept cookies if the button appears
            cookie_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            cookie_button.click()
        except:
            # Cookie button might not appear if cookies are already accepted
            pass

        apartments: List[ApartmentListing] = []
        current_page = 1
        max_pages = config.MAX_PAGES_TO_SCRAPE

        # Continue scraping until we reach the maximum pages or no more results
        while current_page <= max_pages:
            print(f"Scraping page {current_page}...")

            # Wait for listings to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='list']"))
            )

            # Get all property cards/listings on the current page
            time.sleep(1)  # Brief pause to ensure the page is fully loaded
            listing_container = self.driver.find_element(
                By.CSS_SELECTOR, "div[role='list']"
            )
            property_cards = listing_container.find_elements(
                By.CSS_SELECTOR, "div[role='listitem']"
            )

            print(f"Found {len(property_cards)} listings on page {current_page}")

            # Process current cards
            for card in tqdm(property_cards):
                try:
                    # Get link element and URL
                    link_element = card.find_element(
                        By.CSS_SELECTOR, "a.HgCardElevated_content_uir_2"
                    )
                    relative_url: str | None = link_element.get_attribute("href")

                    if relative_url is None:
                        print("No URL found for the listing")
                        continue

                    full_url = (
                        self.base_url + relative_url
                        if relative_url.startswith("/")
                        else relative_url
                    )

                    # Skip if already in our database
                    if full_url in self.existing_urls:
                        continue

                    new_listings_count += 1

                    # Extract basic info from the card
                    # Title and rooms/area/price
                    try:
                        price_info = card.find_element(
                            By.CSS_SELECTOR,
                            ".HgListingRoomsLivingSpacePrice_roomsLivingSpacePrice_M6Ktp",
                        ).text
                    except:
                        price_info = "N/A"

                    # Location
                    try:
                        location = card.find_element(By.TAG_NAME, "address").text
                    except:
                        location = "N/A"

                    # Description
                    try:
                        # Try to get the title first
                        title = ""
                        adress_element = card.find_element(By.TAG_NAME, "address")
                        title = adress_element.text.strip()
                    except Exception as e:
                        print(f"Error extracting description: {e}")
                        title = "N/A"

                    apartment = ApartmentListing(
                        title=title,
                        price=price_info,
                        location=location,
                        url=full_url,
                    )

                    apartments.append(apartment)
                except Exception as e:
                    print(f"Error scraping apartment card: {e}")

            # Check if there are more pages to scrape
            if current_page >= max_pages:
                break

            # Try to go to the next page
            try:
                # Find the next page button (right arrow)
                next_button = self.driver.find_element(
                    By.CSS_SELECTOR, "a.HgPaginationSelector_nextPreviousArrow__Mlz2"
                )

                # Check if the next button is disabled
                next_button_class = next_button.get_attribute("class")

                if (
                    next_button_class is not None
                    and "HgPaginationSelector_disabledButton_zA1Ku" in next_button_class
                ):
                    print("Reached the last page.")
                    break

                # Scroll to the button to make it visible
                self.driver.execute_script(
                    "arguments[0].scrollIntoView(true);", next_button
                )
                time.sleep(1)  # Brief pause

                # Click the button
                next_button.click()
                current_page += 1

                # Wait for the new page to load
                time.sleep(3)

                # Wait for the listing container to reload
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div[role='list']")
                    )
                )

            except Exception as e:
                print(f"Error navigating to the next page: {e}")
                break

        print(
            f"Found {new_listings_count} new apartments (skipped {len(self.existing_urls) & new_listings_count} existing)"
        )
        return apartments

    def get_apartment_details(self, apartment: ApartmentDetails) -> ApartmentDetails:
        """Fetch detailed information about an apartment"""
        self.driver.get(apartment.url)

        # Wait for the page to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "header"))
        )

        try:
            # Accept cookies if the button appears
            cookie_button = WebDriverWait(self.driver, 0.1).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            cookie_button.click()
        except Exception:
            # Cookie button might not appear if cookies are already accepted
            pass

        # Extract detailed information
        details = apartment.model_dump()

        details["title"] = self._extract_title(apartment)
        details["street"], details["city"] = self._extract_address(apartment)
        details["rooms"] = self._extract_rooms(apartment)
        details["area"], details["area_text"] = self._extract_area(apartment)
        details["price"] = self._extract_price(apartment)
        details["property_details"], details["available_from"] = (
            self._extract_property_details(apartment)
        )
        details["description"] = self._extract_description(apartment)
        details["image_urls"] = self._extract_image_urls()
        details["features"] = self._extract_features(apartment)

        # Convert the dictionary to an ApartmentDetails object
        return ApartmentDetails(**details)

    def _extract_title(self, apartment: ApartmentDetails) -> str:
        try:
            title_element = self.driver.find_element(
                By.CSS_SELECTOR, "h1.ListingTitle_spotlightTitle_ENVSi"
            )
            return title_element.text.strip()
        except Exception as e:
            logging.error(f"Error extracting title: {e} {apartment.url}")
            return ""

    def _extract_address(self, apartment: ApartmentDetails) -> tuple[str, str]:
        """
        Extracts the street and city from the apartment's address.

        Returns:
            A tuple containing the street and city information.
        """
        try:
            address_element = self.driver.find_element(
                By.CSS_SELECTOR, "address.AddressDetails_address_i3koO"
            )
            address_text = address_element.text.strip()

            # Extract street and city components
            try:
                street_element = address_element.find_element(
                    By.CSS_SELECTOR, "span.AddressDetails_street_nXScL"
                )
                street = street_element.text.strip()
                if street.endswith(", "):
                    street = street[:-2]  # Remove trailing comma and space
            except Exception:
                street = ""

            try:
                # Get the city info - it's in the second span
                city_spans = address_element.find_elements(By.CSS_SELECTOR, "span")
                if len(city_spans) > 1:
                    city_info = city_spans[1].text.strip()
                else:
                    # If we can't get it directly, extract from full address
                    if "," in address_text:
                        _, city_info = address_text.split(",", 1)
                        city_info = city_info.strip()
                    else:
                        city_info = ""
            except Exception:
                city_info = ""

            return street, city_info
        except Exception as e:
            logging.warning(f"Error extracting address: {e} {apartment.url}")
            return "", ""

    def _extract_rooms(self, apartment: ApartmentDetails) -> float:
        try:
            rooms_element = self.driver.find_element(
                By.CSS_SELECTOR, ".SpotlightAttributesNumberOfRooms_value_TUMrd"
            )

            if not rooms_element:
                logging.warning(f"Rooms element not found for {apartment.url}")
                return 0.0

            return float(rooms_element.text.strip())
        except (IndexError, ValueError) as e:
            logging.warning(f"Error extracting number of rooms: {e} {apartment.url}")
            return 0.0

    def _extract_area(self, apartment: ApartmentDetails) -> tuple[float, str]:
        try:
            area_element = self.driver.find_element(
                By.CSS_SELECTOR, ".SpotlightAttributesUsableSpace_value_cpfrh"
            )
            area_text = area_element.text.strip()
            # Try to extract numeric area value

            area_value = area_text.split()[0].replace("'", "").replace(",", ".")
            return float(area_value), area_text

        except (IndexError, ValueError):
            logging.warning(f"Error extracting area value: {area_text} {apartment.url}")
            return 0.0, area_text

    def _extract_price(self, apartment: ApartmentDetails) -> str:
        try:
            # Price
            price_element = self.driver.find_element(
                By.CSS_SELECTOR, ".SpotlightAttributesPrice_value_TqKGz"
            )
            price_text = price_element.text.strip()
            # Also get the currency
            currency_element = price_element.find_element(
                By.CSS_SELECTOR, ".SpotlightAttributesPrice_currency_fiCzT"
            )
            currency = currency_element.text.strip()

            return f"{currency} {price_text}"
        except Exception as e:
            logging.warning(f"Error extracting price: {e} {apartment.url}")
            return ""

    def _extract_property_details(
        self, apartment: ApartmentDetails
    ) -> tuple[dict[str, str], str]:
        property_details = {}
        available_from = ""
        try:
            core_attributes = self.driver.find_element(
                By.CSS_SELECTOR, ".CoreAttributes_coreAttributes_e2NAm"
            )

            # Get all dt/dd pairs
            dt_elements = core_attributes.find_elements(By.TAG_NAME, "dt")
            dd_elements = core_attributes.find_elements(By.TAG_NAME, "dd")

            for i in range(min(len(dt_elements), len(dd_elements))):
                key = dt_elements[i].text.strip().rstrip(":")
                value = dd_elements[i].text.strip()

                if key and value:
                    # Clean up the key for dictionary
                    key_cleaned = key.lower().replace(" ", "_").replace(":", "")
                    property_details[key_cleaned] = value

                    # Extract specific properties to top level
                    if "availability" in key_cleaned:
                        available_from = value

            return property_details, available_from
        except Exception as e:
            logging.warning(f"Error extracting core attributes: {e} {apartment.url}")
            return property_details, available_from

    def _extract_description(self, apartment: ApartmentDetails) -> str:
        try:
            description_element = self.driver.find_element(
                By.CSS_SELECTOR, ".Description_descriptionBody_AYyuy"
            )
            return description_element.text.strip()
        except Exception as e:
            logging.warning(f"Error extracting description: {e} {apartment.url}")
            return ""

    def _extract_features(self, apartment: ApartmentDetails) -> List[str]:
        """Extract features from the apartment listing's 'Eigenschaften' (Properties) section"""
        features = []
        try:
            # Try to locate the features container
            features_container = self.driver.find_element(
                By.CSS_SELECTOR, ".FeaturesFurnishings_list_S54KV"
            )

            # Get all list items representing features
            feature_items = features_container.find_elements(By.TAG_NAME, "li")

            # Extract the text for each feature
            for item in feature_items:
                try:
                    # Extract the text which is inside a paragraph element
                    feature_text = item.find_element(By.TAG_NAME, "p").text.strip()
                    if feature_text:
                        features.append(feature_text)
                except Exception as e:
                    logging.warning(f"Error extracting feature text: {e}")

        except Exception:
            return []

        return features

    def _extract_image_urls(self) -> List[str]:
        """Extract all image URLs from the image carousel"""
        image_urls = []
        seen_urls = set()

        try:
            # Check if image gallery exists
            try:
                WebDriverWait(self.driver, 0.2).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, ".glide__slide img")
                    )
                )
            except:
                return []

            # Get the total number of images from the counter
            try:
                counter_element = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, ".SlidesCounter_slidesCounter_VEGHw")
                    )
                )
                counter_text = counter_element.text.strip()
                total_images = int(counter_text.split("/")[1].strip())
            except Exception as e:
                logging.warning(f"Could not extract total images from counter: {e}")
                # If we can't determine total, assume there might be at least 10

                total_images = 10

            # Extract current image, then click through all images
            for i in range(total_images):
                # Wait for image to load
                time.sleep(0.5)

                # Find all visible images
                try:
                    active_slide = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, ".glide__slide--active img")
                        )
                    )

                    # Extract the high-resolution image URL
                    img_srcset = active_slide.get_attribute("srcset")
                    if img_srcset:
                        # Parse srcset to get the highest resolution
                        srcset_parts = img_srcset.split(",")
                        # Get the largest image (last one in srcset)
                        largest_img = srcset_parts[-1].strip().split(" ")[0]
                        if largest_img and largest_img not in seen_urls:
                            image_urls.append(largest_img)
                            seen_urls.add(largest_img)
                    else:
                        # Fallback to src if srcset isn't available
                        img_src = active_slide.get_attribute("src")
                        if img_src and img_src not in seen_urls:
                            image_urls.append(img_src)
                            seen_urls.add(img_src)
                except Exception as e:
                    logging.warning(f"Error extracting image {i + 1} URL: {e}")

                # Click the next button to move to the next image
                try:
                    next_button = self.driver.find_element(
                        By.CSS_SELECTOR, "button[data-glide-dir='>']"
                    )
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView(true);", next_button
                    )
                    next_button.click()

                    # Wait for the next image to load
                    time.sleep(0.5)
                except Exception as e:
                    logging.warning(f"Error clicking next image button: {e}")
                    break

                # Check if we've seen all images by comparing URLs
                # This handles the case where we reach the end and it wraps around
                if len(image_urls) >= total_images:
                    break

                # Additional safety check - if we've gone through more iterations than
                # expected and still getting new images, break to avoid infinite loops
                if i >= total_images * 2:
                    logging.warning(
                        "Safety limit reached for image extraction, stopping."
                    )
                    break

            return image_urls

        except Exception as e:
            logging.warning(f"Error in image extraction: {e}")
            return image_urls

    def is_scraped_by_me(self, apartment: ApartmentListing) -> bool:
        return "immoscout24" in apartment.url

    def close(self) -> None:
        """Close the browser"""
        if hasattr(self, "driver"):
            self.driver.quit()
