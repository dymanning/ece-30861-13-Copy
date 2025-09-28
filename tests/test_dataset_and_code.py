import pytest
from src.metrics.dataset_and_code import DatasetAndCodeMetric
from src.cli.url import ModelURL


def test_null_model_url_returns_zero_score(monkeypatch):
    """If no model_url is provided, get_data should return score=0.0."""
    metric = DatasetAndCodeMetric(model_url=None)
    data = metric.get_data()
    assert "score" in data
    assert data["score"] == 0.0


def test_calculate_score_reads_from_data():
    """calculate_score should return the value stored in self.data['score']."""
    dummy_url = ModelURL(raw="https://huggingface.co/test/model")
    metric = DatasetAndCodeMetric(dummy_url)
    # Manually set mock data
    metric.data = {"score": 0.65}
    score = metric.calculate_score()
    assert score == 0.65


def test_get_data_with_missing_api_key(monkeypatch):
    """get_data should raise an Exception if API_KEY is not set."""
    dummy_url = ModelURL(raw="https://huggingface.co/test/model")
    metric = DatasetAndCodeMetric(dummy_url)
    # ensure API_KEY is missing
    monkeypatch.delenv("GEN_AI_STUDIO_API_KEY", raising=False)
    with pytest.raises(Exception, match="API key not set"):
        metric.get_data()


def test_dataset_and_code_prompt():
    """Integration test: run the metric end-to-end and check output type and range."""
    url = ModelURL(raw="https://huggingface.co/bert-base-uncased")
    metric = DatasetAndCodeMetric(url)
    metric.run()
    assert isinstance(metric.data["score"], float)
    assert 0.0 <= metric.data["score"] <= 1.0
