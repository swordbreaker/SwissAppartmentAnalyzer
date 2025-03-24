from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from pydantic import TypeAdapter


class ApartmentListing(BaseModel):
    """Basic model for an apartment listing from the search results page"""

    title: str
    price: str
    location: str
    url: str


class ApartmentDetails(ApartmentListing):
    """Detailed model for an apartment"""

    price_details: Optional[str] = None
    description: str
    street: Optional[str] = None
    city: Optional[str] = None
    area: Optional[float] = None
    area_text: Optional[str] = None
    available_from: Optional[str] = None
    floor: Optional[int] = None
    rooms: Optional[float] = None
    features: List[str] = Field(default_factory=list)
    description_features: List[str] = Field(default_factory=list)
    property_details: Optional[Dict[str, str]] = Field(default_factory=dict)
    image_urls: List[str] = Field(default_factory=list)


class FilterResult(BaseModel):
    """Model for the result of filtering an apartment based on criteria"""

    meets_all_criteria: bool
    criteria_results: Dict[str, bool]


class ApartmentAnalyzed(ApartmentDetails):
    apartment_summary: str
    filter_result: FilterResult


apartment_detail_list_adapter = TypeAdapter(list[ApartmentDetails])
