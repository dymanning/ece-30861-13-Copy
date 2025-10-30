"""
size.py
-------
Model Size Metric.

Summary
- Scores model size based on parameter count and deployability.
- Uses Hugging Face API metadata to fetch number of parameters

Score:
{
    "raspberry_pi": float([0-1]),
    "jetson_nano": float([0-1]),
    "desktop_pc": float([0-1]),
    "aws_server": float([0-1])
}

NOTES: potentially upgrade in future to infer number of parameters from model name or use parse README with AI
"""

from typing import Dict, Optional, Any

from huggingface_hub import HfApi

from src.cli.url import ModelURL
from src.metrics.metric import Metric


class SizeMetric(Metric):
    def __init__(self, model_url: ModelURL):
        super().__init__("size_score")
        self.model_url = model_url

    def get_data(self) -> Dict[str, Optional[int]]:
        """
        Gets number of parameters from model_info.safetensors or cardData "params".
        """
        api = HfApi()
        info = api.model_info(f"{self.model_url.author}/{self.model_url.name}")

        if info.safetensors and "total" in info.safetensors:
            return {"size": info.safetensors.get("total")}

        return {"size": None}

    def calculate_score(self) -> Dict[str, float]:
        """
        Calculate the size score based on parameter count.
        Returns a dictionary mapping hardware targets to normalized scores.
        """
        # Ensure self.data exists and contains "size"
        params: Optional[int] = None
        if self.data is not None:
            raw_size: Any = self.data.get("size")
            if isinstance(raw_size, int):
                params = raw_size

        if not params:
            return {
                "raspberry_pi": 0.0,
                "jetson_nano": 0.0,
                "desktop_pc": 0.0,
                "aws_server": 0.0,
            }

        return {
            "raspberry_pi": score_raspberry_pi(params),
            "jetson_nano": score_jetson_nano(params),
            "desktop_pc": score_desktop_pc(params),
            "aws_server": score_aws_server(params),
        }


def score_raspberry_pi(params: int) -> float:
    if params <= 50e6:
        return 1.0
    elif params <= 100e6:
        return 0.8
    elif params <= 200e6:
        return 0.5
    elif params <= 500e6:
        return 0.2
    else:
        return 0.0


def score_jetson_nano(params: int) -> float:
    if params <= 100e6:
        return 1.0
    elif params <= 300e6:
        return 0.8
    elif params <= 500e6:
        return 0.5
    elif params <= 1e9:
        return 0.2
    else:
        return 0.0


def score_desktop_pc(params: int) -> float:
    if params <= 3e9:
        return 1.0
    elif params <= 7e9:
        return 0.8
    elif params <= 13e9:
        return 0.5
    elif params <= 30e9:
        return 0.2
    else:
        return 0.0


def score_aws_server(params: int) -> float:
    if params <= 10e9:
        return 1.0
    elif params <= 30e9:
        return 0.8
    elif params <= 70e9:
        return 0.5
    elif params <= 200e9:
        return 0.2
    else:
        return 0.0
