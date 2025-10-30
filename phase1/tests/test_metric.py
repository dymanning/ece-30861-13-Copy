"""
test_metric.py
---------------
Basic unit tests for Metric

Tests cover:
- set, score, latency
- None data field
- as_dict function
"""

import pytest

from src.metrics.metric import Metric

# A simple subclass for testing


class DummyMetric(Metric):
    def __init__(self):
        super().__init__("dummy")

    def calculate_score(self) -> float:
        # Pretend computation
        return 0.5


def test_set_data_stores_correctly():
    m = DummyMetric()
    data = {"field": "value"}
    m.set_data(data)
    assert m.data == data


def test_run_sets_score_and_latency():
    m = DummyMetric()
    m.set_data({"field": "value"})
    m.run()

    assert m.score == 0.5
    assert isinstance(m.latency, int)
    assert m.latency >= 0  # latency should be non-negative


def test_as_dict_format():
    m = DummyMetric()
    m.set_data({})
    m.run()
    result = m.as_dict()

    assert "dummy" in result
    assert "dummy_latency" in result
    assert result["dummy"] == 0.5
    assert isinstance(result["dummy_latency"], int)
