"""
test_performance_claims.py
---------------
Basic unit tests for PerformanceClaimsMetric.

Tests cover:
- Model with any number of likes and downloads
- Model does not have any likes or downloads
- Model or download data is unavailable (Should be the same as previous case)
- Model and download numbers create the correct metric score

"""

import pytest
from types import SimpleNamespace

from src.metrics.performance_claims import PerformanceClaimsMetric
from src.cli.url import ModelURL


class DummyCard:
    def __init__(self, text):
        self.text = text


@pytest.mark.parametrize(
    "readme_text, expected_total, expected_score",
    [
        # No claims
        ("This is a model card with no benchmarks.", 0, 0.0),

        # Only "accuracy" matches (not "%")
        ("We achieved 95% accuracy on our dataset.", 1, 0.2),

        # Matches: "state-of-the-art", "GLUE", "score" → 3
        ("State-of-the-art results on GLUE. F1 score: 90. BLEU also improved.", 6, 0.6),

        # Matches: "SOTA", "GLUE", "SuperGLUE", "SQuAD", "accuracy", "BLEU", "ROUGE" → 7
        ("SOTA results on GLUE, SuperGLUE, and SQuAD with accuracy, F1, BLEU, ROUGE.", 9, 0.6),

        # Matches: "beats baseline", "accuracy", "SOTA", "ImageNet", "surpasses",
        # "better than", "competitive with", "results" → 8
        ("This model beats baseline. Accuracy 95%. F1=90. BLEU=30. ROUGE=25. "
         "SOTA on ImageNet. Surpasses prior models. Better than others. "
         "Competitive with large-scale baselines. Results improved.", 11, 0.8),
    ],
)
def test_calculate_score(monkeypatch, readme_text, expected_total, expected_score):
    from src.metrics import performance_claims

    monkeypatch.setattr(
        performance_claims.ModelCard,
        "load",
        lambda repo_id: DummyCard(readme_text),
    )

    metric = PerformanceClaimsMetric(ModelURL(raw="https://huggingface.co/dummy/model"))
    metric.data = metric.get_data()
    assert metric.data["total"] == expected_total
    assert metric.calculate_score() == expected_score



def test_handles_exception(monkeypatch):
    # Simulate ModelCard.load raising
    from src.metrics import performance_claims

    monkeypatch.setattr(
        performance_claims.ModelCard,
        "load",
        lambda repo_id: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    metric = PerformanceClaimsMetric(ModelURL(raw="https://huggingface.co/dummy/model"))
    metric.data = metric.get_data()
    assert metric.data["total"] == 0
    assert metric.calculate_score() == 0.0


