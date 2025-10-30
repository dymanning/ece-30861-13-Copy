import os
import tempfile

import pytest

from src.cli.cli import CLIArgs, parse_args, parse_url_file
from src.cli.url import URL, classify_url

# -----------------------------
# parse_args coverage
# -----------------------------


def test_parse_args_install():
    args = parse_args(['install'])
    assert isinstance(args, CLIArgs)
    assert args.command == 'install'
    assert args.url_file is None


def test_parse_args_test():
    args = parse_args(['test'])
    assert isinstance(args, CLIArgs)
    assert args.command == 'test'
    assert args.url_file is None


def test_parse_args_missing_raises():
    with pytest.raises(SystemExit):
        # triggers "Missing positional argument" parser.error (line ~91)
        parse_args([])


def test_parse_args_file_processing(tmp_path):
    # create dummy URL file
    url_file = tmp_path / "urls.txt"
    url_file.write_text(",,https://huggingface.co/owner/model1\n")

    args = parse_args([str(url_file)])
    assert args.command == 'process'
    assert args.url_file == str(url_file)


def test_parse_args_invalid_target_raises(tmp_path):
    # invalid target (not file)
    with pytest.raises(SystemExit):
        # triggers "Target must be a path..." (line ~121)
        parse_args(['not_a_file.txt'])


def test_parse_url_file_empty_lines_and_comments(tmp_path):
    url_file = tmp_path / "urls.txt"
    url_file.write_text(
        "\n# comment line\n,,https://huggingface.co/owner/model1")

    rows = parse_url_file(str(url_file))
    assert len(rows) == 1
    code, dataset, model = rows[0]
    assert code is None and dataset is None
    assert isinstance(model, URL)


def test_parse_url_file_invalid_url(tmp_path):
    url_file = tmp_path / "urls.txt"
    url_file.write_text(",,invalid_url_here")

    rows = parse_url_file(str(url_file))
    assert len(rows) == 1
    code, dataset, model = rows[0]
    # invalid URL becomes None
    assert code is None and dataset is None and model is None


def test_parse_url_file_nonexistent_file():
    with pytest.raises(FileNotFoundError):
        # triggers file not found check (~line 68)
        parse_url_file("/tmp/this_file_does_not_exist.txt")


def test_parse_url_file_valid_and_none_urls(tmp_path):
    """Trigger normal append to url_lines (lines 142-145)."""
    url_file = tmp_path / "urls.txt"
    url_file.write_text(
        "https://github.com/org/repo1, , https://huggingface.co/owner/model1\n"
        ", , https://huggingface.co/owner/model2"
    )

    rows = parse_url_file(str(url_file))

    # Should have 2 rows
    assert len(rows) == 2

    # First row: code + model, dataset None
    code, dataset, model = rows[0]
    assert code is not None
    assert dataset is None
    assert model is not None

    # Second row: only model
    code, dataset, model = rows[1]
    assert code is None
    assert dataset is None
    assert model is not None
