"""
test_bus_factor.py
---------------
Basic unit tests for BusFactorMetric.

Tests cover:
- 
"""

import pytest

from src.cli.url import CodeURL, ModelURL
from src.metrics.bus_factor import BusFactorMetric


def test_get_data_contributors1():
    model_url = ModelURL(
        raw="https://huggingface.co/google-bert/bert-base-uncased")
    code_url = CodeURL(raw="https://github.com/google-research/bert")

    metric = BusFactorMetric(code_url, model_url)
    metric.run()
    assert metric.data["num_contributors"] and metric.data["params"]


def test_get_data_contributors2():
    model_url = ModelURL(
        raw="https://huggingface.co/google-bert/bert-base-uncased")
    code_url = CodeURL(raw="https://github.com/rtipper1/ece-30861")
    # Thats us!

    metric = BusFactorMetric(code_url, model_url)
    metric.run()
    assert metric.data["num_contributors"] and metric.data["params"]

# --------------------------
# calculate_score logic tests
# --------------------------


def test_calculate_score_no_data1():
    """If no params or contributors are present, score should be 0.0"""
    metric = BusFactorMetric(
        CodeURL("https://github.com/fake/fake"),
        ModelURL("https://huggingface.co/fake/fake-model")
    )
    metric.data = {}  # simulate missing data
    assert metric.calculate_score() == 0.0


def test_calculate_score_no_data2():
    """If no params or contributors are present, score should be 0.0"""
    metric = BusFactorMetric(
        CodeURL("https://github.com/fake/fake"),
        ModelURL("https://huggingface.co/fake/fake-model")
    )
    metric.data = {
        "num_contributors": None,
        "params": None,
    }
    assert metric.calculate_score() == 0.0


def test_calculate_score_zero_contributors():
    """0 contributors should always map to score 1 -> normalized 0.2"""
    metric = BusFactorMetric(
        CodeURL("https://github.com/fake/fake"),
        ModelURL("https://huggingface.co/fake/fake-model")
    )
    metric.data = {"params": int(1e9), "num_contributors": 0}
    assert pytest.approx(metric.calculate_score(), 0.01) == 0.2


def test_calculate_score_low_ratio():
    """< 1 contributor per billion params -> score 2 -> normalized 0.4"""
    metric = BusFactorMetric(
        CodeURL("https://github.com/fake/fake"),
        ModelURL("https://huggingface.co/fake/fake-model")
    )
    metric.data = {"params": int(2e9), "num_contributors": 1}  # 0.5 contrib/B
    assert pytest.approx(metric.calculate_score(), 0.01) == 0.4


def test_calculate_score_mid_ratio():
    """1–2 contributors per billion -> score 3 -> normalized 0.6"""
    metric = BusFactorMetric(
        CodeURL("https://github.com/fake/fake"),
        ModelURL("https://huggingface.co/fake/fake-model")
    )
    metric.data = {"params": int(1e9), "num_contributors": 2}  # 2 contrib/B
    assert pytest.approx(metric.calculate_score(), 0.01) == 0.6


def test_calculate_score_high_ratio():
    """3–9 contributors per billion -> score 4 -> normalized 0.8"""
    metric = BusFactorMetric(
        CodeURL("https://github.com/fake/fake"),
        ModelURL("https://huggingface.co/fake/fake-model")
    )
    metric.data = {"params": int(1e9), "num_contributors": 5}  # 5 contrib/B
    assert pytest.approx(metric.calculate_score(), 0.01) == 0.8


def test_calculate_score_very_high_ratio():
    """>= 10 contributors per billion -> score 5 -> normalized 1.0"""
    metric = BusFactorMetric(
        CodeURL("https://github.com/fake/fake"),
        ModelURL("https://huggingface.co/fake/fake-model")
    )
    metric.data = {"params": int(1e9), "num_contributors": 20}  # 20 contrib/B
    assert pytest.approx(metric.calculate_score(), 0.01) == 1.0
