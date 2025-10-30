"""
tests/test_urls.py
------------------
Unit tests for URL class hierarchy:
- ModelURL
- DatasetURL
- CodeURL

These tests validate that each subclass:
1. Correctly parses `author` and `name` fields.
2. Correctly identifies its `url_type`.
3. Correctly validates valid and invalid URLs.
4. Retains `raw` for any given input.
"""

import pytest

from src.cli.url import CodeURL, DatasetURL, ModelURL, classify_url

# ------------------------------
# ModelURL Tests
# ------------------------------

def test_modelurl_valid_huggingface():
    url = "https://huggingface.co/google/bert-base-uncased"
    m = ModelURL(url)

    assert m.raw == url
    assert m.url_type == "model"
    assert m.validate() is True
    assert m.author == "google"
    assert m.name == "bert-base-uncased"
    assert m.display_name() == "google/bert-base-uncased"


def test_modelurl_invalid_url():
    url = "https://github.com/google/bert"
    m = ModelURL(url)

    assert m.raw == url
    assert m.url_type == "model"
    # Should fail validation
    assert m.validate() is False
    # Author and name remain None
    assert m.author is None
    assert m.name is None
    assert m.display_name() == url


# ------------------------------
# DatasetURL Tests
# ------------------------------

def test_dataseturl_valid_huggingface():
    url = "https://huggingface.co/datasets/bookcorpus/bookcorpus"
    d = DatasetURL(url)

    assert d.raw == url
    assert d.url_type == "dataset"
    assert d.validate() is True
    assert d.author == "bookcorpus"
    assert d.name == "bookcorpus"
    assert d.display_name() == "bookcorpus/bookcorpus"


def test_dataseturl_valid_imagenet():
    url = "https://www.image-net.org/data/imagenet_data.tar.gz"
    d = DatasetURL(url)

    assert d.raw == url
    assert d.url_type == "dataset"
    assert d.validate() is True
    assert d.author == "imagenet"
    assert d.name == "imagenet"
    assert d.display_name() == "imagenet/imagenet"


def test_dataseturl_invalid_url():
    url = "https://github.com/someorg/somerepo"
    d = DatasetURL(url)

    assert d.raw == url
    assert d.url_type == "dataset"
    assert d.validate() is False
    assert d.author is None
    assert d.name is None
    assert d.display_name() == url


# ------------------------------
# CodeURL Tests
# ------------------------------

def test_codeurl_valid_github():
    url = "https://github.com/google-research/bert"
    c = CodeURL(url)

    assert c.raw == url
    assert c.url_type == "code"
    assert c.validate() is True
    assert c.author == "google-research"
    assert c.name == "bert"
    assert c.display_name() == "google-research/bert"


def test_codeurl_valid_gitlab():
    url = "https://gitlab.com/myorg/myrepo"
    c = CodeURL(url)

    assert c.raw == url
    assert c.url_type == "code"
    assert c.validate() is True
    assert c.author == "myorg"
    assert c.name == "myrepo"
    assert c.display_name() == "myorg/myrepo"


def test_codeurl_valid_hf_spaces():
    url = "https://huggingface.co/spaces/user/demo-app"
    c = CodeURL(url)

    assert c.raw == url
    assert c.url_type == "code"
    assert c.validate() is True
    assert c.author == "user"
    assert c.name == "demo-app"
    assert c.display_name() == "user/demo-app"


def test_codeurl_invalid_url():
    url = "https://huggingface.co/google/bert-base-uncased"
    c = CodeURL(url)

    assert c.raw == url
    assert c.url_type == "code"
    assert c.validate() is False
    assert c.author is None
    assert c.name is None
    assert c.display_name() == url


# ------------------------------
# classify_url Tests
# ------------------------------

@pytest.mark.parametrize("url,expected_type", [
    ("https://huggingface.co/google/bert-base-uncased", "model"),
    ("https://huggingface.co/datasets/bookcorpus/bookcorpus", "dataset"),
    ("https://www.image-net.org/data/imagenet_data.tar.gz", "dataset"),
    ("https://github.com/google-research/bert", "code"),
    ("https://gitlab.com/org/repo", "code"),
    ("https://huggingface.co/spaces/user/demo-app", "code"),
])
def test_classify_url_valid(url, expected_type):
    parsed = classify_url(url)
    assert parsed is not None
    assert parsed.url_type == expected_type
    assert parsed.validate() is True


def test_classify_url_invalid():
    url = "https://example.com/not-a-valid-url"
    parsed = classify_url(url)
    assert parsed is None
