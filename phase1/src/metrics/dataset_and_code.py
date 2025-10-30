"""
dataset_and_code.py
-------------------
Dataset and Code Availability Metric.

Summary
- Estimates quality and availability of dataset and code for a model.
- Considers dataset documentation, benchmarks, and example usage.
- Evaluates clarity and completeness of provided training/evaluation resources.
- Maps overall availability/quality into a [0,1] score.
"""

import os
from typing import Dict, Any

import requests  # type: ignore[import-untyped]

from src.cli.url import ModelURL
from src.metrics.metric import Metric


class DatasetAndCodeMetric(Metric):
    def __init__(self, model_url: ModelURL):
        super().__init__("dataset_and_code_score")
        self.model_url = model_url

    def calculate_score(self) -> float:
        # Safely handle None or missing key
        if not self.data or "score" not in self.data:
            return 0.0
        return float(self.data["score"])

    def get_data(self) -> Dict[str, Any]:
        api_key = os.environ.get("GEN_AI_STUDIO_API_KEY")
        if not api_key:
            return {"score": 0.0}

        if not self.model_url:
            return {"score": 0.0}

        url = "https://genai.rcac.purdue.edu/api/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        body = {
            "model": "llama3.1:latest",
            "messages": [
                {
                    "role": "user",
                    "content": f"""You are tasked with evaluating a Hugging Face model’s README file 
                                    for dataset and code quality. 
                                    Model URL: {self.model_url.raw}

                                    Consider these factors:

                                    1. Dataset Documentation
                                    2. Dataset Availability
                                    3. Code Quality
                                    4. Completeness & Transparency

                                    Your task: Provide a rating (float in [0-1]).
                                    IMPORTANT: Output only this float rating. No explanation.
                                """
                }
            ],
        }

        try:
            response = requests.post(url, headers=headers, json=body, timeout=60)
            response.raise_for_status()
            response_data = response.json()

            output = response_data["choices"][0]["message"]["content"]
            score = float(output.strip())
            return {"score": score}

        except Exception:
            return {"score": 0.0}
