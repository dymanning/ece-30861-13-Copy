"""
test_dataset_quality.py
---------------
Basic unit tests for DatasetQualityeMetric.

Tests cover:
- Metric gets the correct score from an example url
- Metric gets the correct score given the number of significant phrases
- Metric gives the correct score when there are no significant phrases
"""

import pytest

from src.cli.url import CodeURL, DatasetURL
from src.metrics.dataset_quality import DatasetQualityMetric


def test_null_dataset_url_returns_zero_score():
    """If dataset_url is None, get_data should return score=0.0."""
    metric = DatasetQualityMetric(dataset_url=None)
    data = metric.get_data()
    assert "score" in data
    assert data["score"] == 0.0


def test_calculate_score_reads_from_data():
    """calculate_score should return the value stored in self.data['score']."""
    dummy = DatasetURL(raw="https://huggingface.co/datasets/test/dummy")
    metric = DatasetQualityMetric(dataset_url=dummy)
    metric.data = {"score": 0.55}
    assert metric.calculate_score() == 0.55


def test_get_data_with_missing_api_key(monkeypatch):
    dummy = DatasetURL(raw="https://huggingface.co/datasets/test/dummy")
    metric = DatasetQualityMetric(dataset_url=dummy)

    monkeypatch.delenv("GEN_AI_STUDIO_API_KEY", raising=False)

    data = metric.get_data()
    assert isinstance(data, dict)
    assert "score" in data
    assert data["score"] == 0.0

def test_dataset_quality_prompt():
    """Integration test: run end-to-end and check score is float in [0,1]."""
    url = DatasetURL(raw="https://huggingface.co/datasets/glue")
    metric = DatasetQualityMetric(dataset_url=url)
    metric.run()
    assert isinstance(metric.data["score"], float)
    assert 0.0 <= metric.data["score"] <= 1.0
