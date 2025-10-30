"""
performance_claims.py
-----------------------
Performance Claims Metric

Summary:
- Parses a model's README to detect performance claims.
- Searches for benchmark names, evaluation metrics, and "SOTA"-style language.
- Scores models based on density of detected claims.

Rubric:
- 1.0 = >20 claims
- 0.8 = 10–20 claims
- 0.6 = 5–9 claims
- 0.4 = 2–4 claims
- 0.2 = 1 claim
- 0.0 = 0 claims
"""

import re
from typing import Dict, Any
import contextlib
import io

from huggingface_hub import ModelCard
from src.cli.url import ModelURL
from src.metrics.metric import Metric


# Key terms that signal performance-related claims
KEY_TERMS: Dict[str, list[str]] = {
    "benchmarks": [
        "GLUE", "SuperGLUE", "SQuAD", "ImageNet", "COCO", "LibriSpeech",
        "MNIST", "CIFAR", "WMT", "WikiText", "MS MARCO",
    ],
    "metrics": [
        "accuracy", "f1", "precision", "recall", "bleu", "rouge",
        "wer", "perplexity", "auc", "exact match", "loss",
    ],
    "comparisons": [
        "state-of-the-art", "sota", "outperform", "better than",
        "surpasses", "beats baseline", "competitive with",
    ],
    "numbers": ["%", "percent", "score", "results"],
}


def count_matches(text: str, terms: list[str]) -> int:
    """Count case-insensitive matches of each term in text."""
    total = 0
    for term in terms:
        total += len(re.findall(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE))
    return total


class PerformanceClaimsMetric(Metric):
    def __init__(self, model_url: ModelURL):
        super().__init__("performance_claims")
        self.model_url = model_url

    def get_data(self) -> Dict[str, Any]:
        """
        Fetch README and count performance-related terms.
        Returns a dict with:
          - "matches": dict of category → count
          - "total": int total matches
        """
        repo_id = f"{self.model_url.author}/{self.model_url.name}"
        readme = ""
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                card = ModelCard.load(repo_id)
                readme = card.text or ""
            except Exception:
                readme = ""

        matches: Dict[str, int] = {
            cat: count_matches(readme, terms) for cat, terms in KEY_TERMS.items()
        }
        total_matches = sum(matches.values())
        return {"matches": matches, "total": total_matches}

    def calculate_score(self) -> float:
        """
        Map total matches to rubric score.
        """
        if not self.data:
            return 0.0

        total = self.data.get("total", 0)
        if not isinstance(total, int):
            return 0.0

        if total > 20:
            return 1.0
        elif total >= 10:
            return 0.8
        elif total >= 5:
            return 0.6
        elif total >= 2:
            return 0.4
        elif total >= 1:
            return 0.2
        else:
            return 0.0
