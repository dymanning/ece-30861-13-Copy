"""
bus_factor.py
---------------
Bus Factor Metric.

Summary
- Calculates contributor redundancy relative to project size.
- Uses number of contributors per parameter scale as described in the rubric.
- Gets number of parameters from model_info.safetensors
- Gets contributors from GitHub API using validated token
"""
from typing import Dict, Optional
from huggingface_hub import HfApi
from github import Github

from src.cli.url import CodeURL, ModelURL
from src.metrics.metric import Metric
from src.git import validate_github_token


def get_contributors(owner: str, repo: str) -> list[str]:
    """
    Fetch contributors for a repo using the authenticated GitHub client.
    """
    gh: Github = validate_github_token()
    repo_obj = gh.get_repo(f"{owner}/{repo}")
    contributors = repo_obj.get_contributors()
    return [c.login for c in contributors]


class BusFactorMetric(Metric):
    def __init__(self, code_url: CodeURL, model_url: ModelURL):
        super().__init__("bus_factor")
        self.model_url = model_url
        self.code_url = code_url

    def get_data(self) -> Dict[str, Optional[int]]:
        """
        Gets number of parameters from Hugging Face model_info.
        Gets contributors from GitHub API.
        """
        api = HfApi()
        info = api.model_info(f"{self.model_url.author}/{self.model_url.name}")

        params: Optional[int] = None
        if info.safetensors and "total" in info.safetensors:
            params = info.safetensors.get("total")

        num_contributors = 0
        if self.code_url and self.code_url.author and self.code_url.name:
            contributors = get_contributors(self.code_url.author, self.code_url.name)
            num_contributors = len(contributors)

        return {
            "params": params,
            "num_contributors": num_contributors,
        }

    def calculate_score(self) -> float:
        """
        Calculate bus factor score based on contributors per billion parameters.
        Normalized to [0,1].
        """
        if not self.data:
            return 0.0

        params = self.data.get("params")
        num_contributors = self.data.get("num_contributors")

        if not params or num_contributors is None:
            return 0.0

        # Convert to billions to match rubric scale
        params_in_billions = params / 1e9 if params > 0 else 1
        ratio = num_contributors / params_in_billions

        if num_contributors == 0:
            raw_score = 0.2
        elif ratio < 1:
            raw_score = 0.4
        elif 1 <= ratio <= 2:
            raw_score = 0.6
        elif 3 <= ratio <= 9:
            raw_score = 0.8
        else:
            raw_score = 1.0

        return raw_score
