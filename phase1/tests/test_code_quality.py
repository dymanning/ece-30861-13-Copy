import pytest
from src.metrics.code_quality import CodeQualityMetric
from src.cli.url import CodeURL, ModelURL


class DummyMetric(CodeQualityMetric):
    """Subclass that allows injecting fake data instead of hitting API."""
    def __init__(self):
        code_url = CodeURL(raw="https://github.com/dummy/repo")
        model_url = ModelURL(raw="https://huggingface.co/dummy/model")
        super().__init__(code_url, model_url)


@pytest.mark.parametrize(
    "issues, loc, expected_score",
    [
        (0, 1000, 1.0),       # 0 per 1000 LOC → perfect
        (5, 1000, 1.0),       # 5 per 1000 LOC → still perfect
        (10, 1000, 0.8),      # 10 per 1000 LOC → in 6–15 range
        (25, 1000, 0.6),      # 25 per 1000 LOC → in 16–30 range
        (45, 1000, 0.4),      # 45 per 1000 LOC → in 31–60 range
        (100, 1000, 0.2),     # >60 per 1000 LOC → lowest nonzero
    ]
)
def test_calculate_score_various_ratios(issues, loc, expected_score):
    metric = DummyMetric()
    metric.data = {"Issues": issues, "Lines of Code": loc}
    assert metric.calculate_score() == expected_score


def test_calculate_score_invalid_data():
    metric = DummyMetric()
    metric.data = {"Issues": None, "Lines of Code": None}
    assert metric.calculate_score() == 0.0


def test_get_data_handles_no_python_files(monkeypatch):
    """Simulate a repo with no python files → Issues=-1, LOC=-1."""
    metric = DummyMetric()

    class DummyInfo:
        siblings = []
        cardData = {}

    class DummyApi:
        def model_info(self, full_name):
            return DummyInfo()

    monkeypatch.setattr("src.metrics.code_quality.HfApi", lambda: DummyApi())
    metric.code_url = CodeURL(raw="https://github.com/dummy/repo")
    metric.model_url = ModelURL(raw="https://huggingface.co/dummy/model")

    result = metric.get_data()
    assert result["Issues"] is None
    assert result["Lines of Code"] is None
