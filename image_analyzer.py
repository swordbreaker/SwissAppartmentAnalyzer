from dotenv import load_dotenv
from pydantic import BaseModel
import requests
import os
import base64
from config import CRITERIA
import ollama

from models.apartment_models import ApartmentDetails


# Load environment variables (for Ollama configuration)
load_dotenv()


class CriteriaResponse(BaseModel):
    key: str
    question: str
    reason: str
    meets_criteria: bool


class CriteriaListResponse(BaseModel):
    criteria: list[CriteriaResponse]


class ImageAnalyzer:
    def __init__(self):
        # Initialize Ollama configuration
        try:
            self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
            self.model_name = os.getenv("OLLAMA_MODEL", "gemma3:4b")

            # Test connection to Ollama
            models = ollama.list()
            if not models:
                raise ConnectionError(
                    f"Failed to connect to Ollama at {self.ollama_host}"
                )

            print(f"Connected to Ollama successfully, using model: {self.model_name}")
        except Exception as e:
            raise ValueError(f"Failed to initialize Ollama client: {e}")

    def _encode_image(self, image_url):
        """Convert image to base64 encoding for Ollama API"""
        try:
            # If image_url is a local file path
            if os.path.exists(image_url):
                with open(image_url, "rb") as img_file:
                    encoded = base64.b64encode(img_file.read()).decode("utf-8")
                    return encoded
            # If image_url is a URL
            else:
                response = requests.get(image_url)
                if response.status_code == 200:
                    encoded = base64.b64encode(response.content).decode("utf-8")
                    return encoded
                else:
                    raise ValueError(f"Failed to download image from {image_url}")
        except Exception as e:
            print(f"Error encoding image: {e}")
            return None

    def _summarize_images(self, img_descriptions: str) -> str:
        prompt = f"""Summarize the following apartment details and images.
        {img_descriptions}
        """

        response = ollama.generate(
            model=self.model_name,
            prompt=prompt,
            options={
                "temperature": 0.7,
                "top_p": 0.9,
            },
        )

        return response.get("response", "")

    def _summarize_apartment(
        self, text_description: str, image_description: str
    ) -> str:
        prompt = f"""Summarize the following apartment details and images. And give your opinion about the apartment.
        {text_description}
        {image_description}
        """

        response = ollama.generate(
            model=self.model_name,
            prompt=prompt,
            options={
                "temperature": 0.7,
                "top_p": 0.9,
            },
        )

        return response.get("response", "")

    def analyze(
        self, apartment_details: ApartmentDetails
    ) -> tuple[dict[str, bool], str]:
        """Analyze context with Ollama using question answering"""

        img_descriptions = self.analyze_images(apartment_details.image_urls)
        img_descriptions = self._summarize_images(img_descriptions)

        text_descriptions = f"""
        ## Title
        {apartment_details.title}
        ## Description
        {apartment_details.description}
        ## Features
        {apartment_details.features}
        """

        str_criteria = ""
        for criterion, value in CRITERIA.items():
            if value.use_image_analysis:
                str_criteria += f"{criterion}: {value.question}\n"

        prompt = (
            """
Analyze the entire provided context thoroughly, including the description and all image descriptions. Pay special attention to information mentioned multiple times across different sections. Prioritize textual information over image descriptions when they conflict. Cross-reference details across all sections before answering.

For each criterion, provide:
1. A confidence level (High/Medium/Low)
2. A detailed reason for your answer, citing specific parts of the text or images
3. A boolean value indicating if the criterion is met
"""
            f"Format the response as a JSON object with the following structure: {CriteriaListResponse.model_json_schema()}"
            f"#START CRITERIA\n{str_criteria}\n#END CRITERIA\n\n"
            f"#START CONTEXT\n{text_descriptions + img_descriptions}\n#END CONTEXT"
        )

        # Make API call to Ollama
        try:
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                format=CriteriaListResponse.model_json_schema(),
                options={
                    "temperature": 0.7,
                    "top_p": 0.9,
                },
            )

            if not response:
                print("Error: Empty response from Ollama")
                raise ValueError("Failed to analyze context")

            result = CriteriaListResponse.model_validate_json(
                response.get("response", "")
            )
            print(f"## PROMPT ## \n {prompt}, \n ## Result ## \n {result}")

            # Process results
            met_criteria: dict[str, bool] = {}
            result_dict = {}
            for crit in result.criteria:
                result_dict[crit.key] = crit.meets_criteria

            for key in CRITERIA.keys():
                met_criteria[key] = result_dict.get(key, False)

            apartment_summary = self._summarize_apartment(
                text_description=text_descriptions, image_description=img_descriptions
            )

            return met_criteria, apartment_summary

        except Exception as e:
            print(f"Error calling Ollama API: {e}")
            return {key: False for key in CRITERIA.keys()}, ""

    def analyze_images(self, image_urls: list[str]) -> str:
        results: str = ""

        for i, img_url in enumerate(image_urls):
            result = self.analyze_single_image(img_url)
            results += f"""
            ## Image {i + 1}
            {result}
            """

        return results

    def analyze_single_image(self, image_url: str) -> str:
        """Analyze image with Ollama using multimodal API"""

        criteria = "\n".join(map(lambda x: x.question, CRITERIA.values()))

        analysis_prompt = f"""Describe what you see on the image, so the following questions can be answered. Be precise and concise.
        
        #START CRITERIA\n{criteria}\n#END CRITERIA\n\n"""

        encoded_image = self._encode_image(image_url)

        if not encoded_image:
            return "Error: Could not process image"

        try:
            response = ollama.generate(
                model=self.model_name,
                prompt=analysis_prompt,
                images=[encoded_image],
                options={
                    "temperature": 0.7,
                },
            )

            if not response:
                print("Error: Empty response from Ollama")
                return "Error: Failed to analyze image"

            return response.get("response", "")

        except Exception as e:
            print(f"Error analyzing image: {e}")
            return f"Error: {str(e)}"
