"""
dataset_quality.py
--------------------
Dataset Quality Metric.

Summary
- Evaluates datasets linked to the model by prompting an AI.
- Considers documentation, peer review, community adoption, and transparency.
- Normalizes dataset quality into [0,1].
"""

import os
from typing import Dict, Any

import requests  # type: ignore[import-untyped]

from src.cli.url import DatasetURL
from src.metrics.metric import Metric


class DatasetQualityMetric(Metric):
    def __init__(self, dataset_url: DatasetURL):
        super().__init__("dataset_quality")
        self.dataset_url = dataset_url

    def calculate_score(self) -> float:
        # Safely handle if self.data is None or missing "score"
        if not self.data or "score" not in self.data:
            return 0.0
        return float(self.data["score"])

    def get_data(self) -> Dict[str, Any]:
        api_key = os.environ.get("GEN_AI_STUDIO_API_KEY")
        if not api_key:
            # Fallback instead of raising → ensures mypy sees consistent return
            return {"score": 0.0}

        if not self.dataset_url:
            return {"score": 0.0}

        url = "https://genai.rcac.purdue.edu/api/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": "llama3.1:latest",
            "messages": [
                {
                    "role": "user",
                    "content": f"""You are tasked with evaluating the quality of a Hugging Face dataset.
                                    Dataset URL: {self.dataset_url.raw}

                                    Consider the following factors:

                                    1. Documentation
                                    2. Availability & Transparency
                                    3. Community & Peer Review
                                    4. Supporting Code

                                    Your task: Provide a rating as a float in [0,1], 
                                    where 0 = very poor dataset quality and 1 = excellent dataset quality.
                                    IMPORTANT: Output only the float rating. Do not provide any context or explanation.
                                """,
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
            # Always return a dict for mypy consistency
            return {"score": 0.0}
