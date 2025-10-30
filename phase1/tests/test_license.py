"""
test_license.py
---------------
Basic unit tests for LicenseMetric.

Tests cover:
- All license tiers (1-5)
- Unknown license string
- Missing license field
"""

import pytest

from src.cli.url import ModelURL
from src.metrics.license import LicenseMetric

# Dummy empty url to pass into test cases in which we just set the data manually
dummy_url = ModelURL(
    raw="https://huggingface.co/Alibaba-NLP/Tongyi-DeepResearch-30B-A3B")


def test_get_data1():
    url = ModelURL(
        raw="https://huggingface.co/Alibaba-NLP/Tongyi-DeepResearch-30B-A3B")

    metric = LicenseMetric(url)
    metric.run()
    assert metric.data == {"license": "apache-2.0"}
    assert metric.score == 1.0


def test_get_data2():
    url = ModelURL(raw="https://huggingface.co/inclusionAI/Ling-flash-2.0")

    metric = LicenseMetric(url)
    metric.run()
    assert metric.data == {"license": "mit"}
    assert metric.score == 1.0


def test_get_data3():
    url = ModelURL(
        raw="https://huggingface.co/deepseek-ai/DeepSeek-V3.1-Terminus")

    metric = LicenseMetric(url)
    metric.run()
    assert metric.data == {"license": "mit"}
    assert metric.score == 1.0


def test_get_data4():
    # model does not have license in metadata, should score 0
    url = ModelURL(
        raw="https://huggingface.co/ShaunMendes001/llama-3.2-1b-instruct-customer-support-gguf")

    metric = LicenseMetric(url)
    metric.run()
    assert metric.data == {"license": None}
    assert metric.score == 0.0


def test_get_data5():
    url = ModelURL(
        raw="https://huggingface.co/XLabs-AI/flux-controlnet-hed-v3")

    metric = LicenseMetric(url)
    metric.run()
    assert metric.data == {"license": "flux-1-dev-non-commercial-license"}
    assert metric.score == 0.0


def test_level_5_license():
    metric = LicenseMetric(dummy_url)
    metric.set_data({"license": "apache-2.0"})
    metric.run()
    assert metric.score == 1


def test_level_4_license():
    metric = LicenseMetric(dummy_url)
    metric.set_data({"license": "lgpl-3.0"})
    metric.run()
    assert metric.score == 0.8


def test_level_3_license():
    metric = LicenseMetric(dummy_url)
    metric.set_data({"license": "cc-by-nc-4.0"})
    metric.run()
    assert metric.score == 0.6


def test_level_2_license():
    metric = LicenseMetric(dummy_url)
    metric.set_data({"license": "openrail"})
    metric.run()
    assert metric.score == 0.4


def test_level_1_license():
    metric = LicenseMetric(dummy_url)
    metric.set_data({"license": "llama3"})
    metric.run()
    assert metric.score == 0.2


def test_case_insensitivity():
    metric = LicenseMetric(dummy_url)
    metric.set_data({"license": "APACHE-2.0"})
    metric.run()
    assert metric.score == 1.0


def test_license_with_whitespace():
    metric = LicenseMetric(dummy_url)
    metric.set_data({"license": "  mit  "})
    metric.run()
    assert metric.score == 1.0


def test_unknown_license():
    metric = LicenseMetric(dummy_url)
    metric.set_data({"license": "something-unknown"})
    metric.run()
    assert metric.score == 0.0


def test_none_license():
    metric = LicenseMetric(dummy_url)
    metric.set_data({"license": None})
    metric.run()
    assert metric.score == 0.0


def test_empty_license_string():
    metric = LicenseMetric(dummy_url)
    metric.set_data({"license": ""})
    metric.run()
    assert metric.score == 0.0
