from dotenv import load_dotenv
from transformers import AutoProcessor, Qwen2VLForConditionalGeneration
from qwen_vl_utils import process_vision_info
from config import CRITERIA

# Load environment variables (if needed for other functionality)
load_dotenv()

min_pixels = 256 * 28 * 28  # Minimum token capacity (256)
max_pixels = 1280 * 28 * 28  # Maximum token capacity (1280)


class ImageAnalyzer:
    def __init__(self):
        # Initialize Qwen2-VL model and processor
        try:
            self.processor = AutoProcessor.from_pretrained(
                "Qwen/Qwen2-VL-2B",
                min_pixels=min_pixels,
                max_pixels=max_pixels,
            )
            self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                "Qwen/Qwen2-VL-2B",
                device_map="auto",
                torch_dtype="auto",
                load_in_4bit=True,  # Using 4-bit quantization for VRAM efficiency
            )

            print("Qwen2-VL model loaded successfully")
        except Exception as e:
            raise ValueError(f"Failed to load Qwen2-VL model: {e}")

    def analyze(self, context: list[str]) -> dict[str, bool]:
        """Analyze image with Qwen2-VL model using question answering"""

        str_context = " ".join(context)
        str_criteria = ""
        for criterion, value in CRITERIA.items():
            if value.use_image_analysis:
                str_criteria += f"{criterion}: {value.question}\n"

        messages = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "Analyze the content and find out if it meets the criteria. list all criteria keys, and only the keys that are met comma separated. Dont include any other text. Dont mention the criteria that are not met",
                    },
                    {
                        "type": "text",
                        "text": f"#START CRITERIA {str_criteria} #END CRITERIA",
                    },
                    {
                        "type": "text",
                        "text": f"#START CONTEXT {str_context} #END CONTEXT",
                    },
                ],
            },
        ]

        # Preparation for inference
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        inputs = self.processor(text=[text], padding=True, return_tensors="pt")
        inputs = inputs.to("cuda")

        # Inference: Generation of the output
        generated_ids = self.model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.7,  # Add randomness
            top_p=0.9,  # Nucleus sampling
            repetition_penalty=1.2,
            do_sample=True,
            num_beams=3,
        )
        generated_ids_trimmed = [
            out_ids[len(in_ids) :]
            for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text: list[str] = self.processor.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )

        result = output_text[0].lower()

        print(f"Context: {str_context}, \n Result: {result}")

        met_criteria = {}

        for key in CRITERIA.keys():
            if key in result:
                met_criteria[key] = True

        for key in CRITERIA.keys():
            if key not in met_criteria:
                met_criteria[key] = False

        return met_criteria

    def analyze_images(self, image_urls: list[str]) -> dict[str, bool]:
        met_criteria = {}

        for img_url in image_urls:
            result = self.analyze_single_images(img_url)
            print(f"Image URL: {img_url}, Result: \n {result}")

            for key in CRITERIA.keys():
                if key in result:
                    met_criteria[key] = True

            if len(met_criteria.values()) == len(CRITERIA):
                return met_criteria

        for key in CRITERIA.keys():
            if key not in met_criteria:
                met_criteria[key] = False

        return met_criteria

    def analyze_single_images(self, image_url: str) -> str:
        """Analyze image with Qwen2-VL model using question answering"""

        analysis_prompt = """Describe what you see on the image."""

        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image_url},
                        {
                            "type": "text",
                            "text": analysis_prompt,
                        },
                    ],
                }
            ]

            # Preparation for inference
            text = self.processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

            image_inputs, video_inputs = process_vision_info(messages)
            inputs = self.processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            )
            inputs = inputs.to("cuda")

            # Inference: Generation of the output
            generated_ids = self.model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.7,
            )
            generated_ids_trimmed = [
                out_ids[len(in_ids) :]
                for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = self.processor.batch_decode(
                generated_ids_trimmed,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )

            return output_text[0]

        except Exception as e:
            print(f"Error analyzing image: {e}")
            return None
