"""
ramp_up_time.py
---------------
Ramp Up Time Metric.

Summary
- Estimates ease of adoption for developers using the model.
- Considers availability of documentation, tutorials, and example code.
- Maps estimated learning curve (minutes to days) into a [0,1] score.
- Calculates latency of the scoring process to support performance reporting.
"""

import os
from typing import Dict, Any

import requests  # type: ignore[import-untyped]

from src.cli.url import ModelURL
from src.metrics.metric import Metric


class RampUpTimeMetric(Metric):
    def __init__(self, model_url: ModelURL):
        super().__init__("ramp_up_time")
        self.model_url = model_url

    def calculate_score(self) -> float:
        # Ensure data exists and has "score"
        if not self.data or "score" not in self.data:
            return 0.0
        return float(self.data["score"])

    def get_data(self) -> Dict[str, Any]:
        api_key = os.environ.get("GEN_AI_STUDIO_API_KEY")
        if not api_key:
            # Fall back gracefully instead of raising an error
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
                    "content": f"""You are tasked with evaluating a Hugging Face model’s README file for ramp-up time. 
                                    Model URL: {self.model_url.raw}
                                    Ramp-up time is defined as the amount of effort and time it would take a new user, 
                                    with basic machine learning knowledge but no prior familiarity with this specific model, 
                                    to successfully install, load, and begin using the model in a real workflow.  

                                    When scoring, consider the following factors:  

                                    1. Installation & Setup Clarity  
                                    2. Quickstart Examples  
                                    3. Documentation Quality  
                                    4. Resource Requirements  
                                    5. Supporting Materials  
                                    6. Completeness & Accessibility  

                                    Your task: Provide a rating (float([0-1]), where 0 = very high ramp-up difficulty and 1 = very easy ramp-up).
                                    IMPORTANT: output only this float rating. Do not provide any context or thought process.
                                """
                }
            ],
        }

        try:
            response = requests.post(url, headers=headers, json=body, timeout=60)
            response.raise_for_status()
            response_data = response.json()

            output = response_data["choices"][0]["message"]["content"]
            score = float(output)
            return {"score": score}

        except Exception:
            # On any failure, fallback score is 0.0
            return {"score": 0.0}
