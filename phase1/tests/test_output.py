import json
from types import SimpleNamespace

import pytest

from src.cli.output import build_output
from src.cli.url import ModelURL


class DummyMetric:
    """Minimal stub metric with name, score, latency, and as_dict()."""

    def __init__(self, name, score, latency=10):
        self.name = name
        self.score = score
        self.latency = latency

    def as_dict(self):
        return {self.name: self.score, f"{self.name}_latency": self.latency}


def test_build_output_single_metric():
    model = ModelURL(raw="https://huggingface.co/test/model")
    model.name = "test-model"

    metric = DummyMetric("ramp_up_time", 0.8, latency=15)
    weights = {"ramp_up_time": 1.0}

    output_str = build_output(model, [metric], weights, net_latency=50)
    data = json.loads(output_str)

    assert data["name"] == "test-model"
    assert data["category"] == "MODEL"
    assert data["net_score"] == 0.8  # weight 1.0 * score 0.8
    assert data["net_score_latency"] == 50
    assert "ramp_up_time" in data
    assert "ramp_up_time_latency" in data


def test_build_output_with_size_score():
    model = ModelURL(raw="https://huggingface.co/test/model")
    model.name = "test-model"

    size_score = {
        "raspberry_pi": 0.5,
        "jetson_nano": 0.5,
        "desktop_pc": 1.0,
        "aws_server": 1.0,
    }
    metric = DummyMetric("size_score", size_score, latency=20)
    weights = {"size_score": 1.0}

    output_str = build_output(model, [metric], weights, net_latency=100)
    data = json.loads(output_str)

    expected_avg = (0.5 + 0.5 + 1.0 + 1.0) / 4
    assert pytest.approx(data["net_score"], rel=1e-3) == expected_avg
    assert data["size_score"] == size_score
    assert data["size_score_latency"] == 20


def test_build_output_multiple_metrics_weighted():
    model = ModelURL(raw="https://huggingface.co/test/model")
    model.name = "test-model"

    metrics = [
        DummyMetric("ramp_up_time", 0.5, latency=10),
        DummyMetric("bus_factor", 0.8, latency=20),
    ]
    weights = {"ramp_up_time": 0.4, "bus_factor": 0.6}

    output_str = build_output(model, metrics, weights, net_latency=75)
    data = json.loads(output_str)

    expected_score = 0.4 * 0.5 + 0.6 * 0.8
    assert pytest.approx(data["net_score"], rel=1e-3) == expected_score
    assert data["net_score_latency"] == 75
    assert "bus_factor" in data
    assert "bus_factor_latency" in data


def test_build_output_json_format():
    model = ModelURL(raw="https://huggingface.co/test/model")
    model.name = "test-model"

    metric = DummyMetric("code_quality", 1.0, latency=5)
    weights = {"code_quality": 1.0}

    output_str = build_output(model, [metric], weights, net_latency=10)

    # Ensure it is valid JSON and compact (no extra whitespace)
    data = json.loads(output_str)
    assert isinstance(data, dict)
    assert ":" in output_str
    assert "\n" not in output_str
