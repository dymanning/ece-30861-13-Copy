import pytest

from src.cli.url import ModelURL
from src.metrics.ramp_up_time import RampUpTimeMetric


def test_null_model_url_returns_zero_score(monkeypatch):
    """If no model_url is provided, get_data should return score=0.0."""
    metric = RampUpTimeMetric(model_url=None)
    data = metric.get_data()
    assert "score" in data
    assert data["score"] == 0.0


def test_calculate_score_reads_from_data():
    """calculate_score should return the value stored in self.data['score']."""
    dummy_url = ModelURL(raw="https://huggingface.co/test/model")
    metric = RampUpTimeMetric(dummy_url)
    # Manually set mock data
    metric.data = {"score": 0.75}
    score = metric.calculate_score()
    assert score == 0.75


def test_get_data_with_missing_api_key(monkeypatch):
    dummy_url = ModelURL(raw="https://huggingface.co/test/model")
    metric = RampUpTimeMetric(dummy_url)

    monkeypatch.delenv("GEN_AI_STUDIO_API_KEY", raising=False)

    data = metric.get_data()
    assert isinstance(data, dict)
    assert "score" in data
    assert data["score"] == 0.0


def test_ramp_up_time_prompt():
    url = ModelURL(
        raw="https://huggingface.co/Alibaba-NLP/Tongyi-DeepResearch-30B-A3B")
    metric = RampUpTimeMetric(url)
    metric.run()
    assert (type(metric.data["score"]) == float)
    assert (metric.data["score"] >= 0 and metric.data["score"] <= 1)
