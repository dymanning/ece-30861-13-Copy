import os
import tempfile

import pytest

import src.logging  # adjust import path


def test_missing_log_file_env(monkeypatch, capsys):
    monkeypatch.delenv("LOG_FILE", raising=False)
    with pytest.raises(SystemExit):
        src.logging.validate_log_file()

    captured = capsys.readouterr()
    assert "LOG_FILE environment variable is missing" in captured.err


def test_nonexistent_log_file(monkeypatch):
    fake_path = "/tmp/this_file_should_not_exist_123456.log"
    # Make extra sure it doesn’t exist
    if os.path.exists(fake_path):
        os.unlink(fake_path)

    monkeypatch.setenv("LOG_FILE", fake_path)
    with pytest.raises(SystemExit):
        src.logging.validate_log_file()


def test_unwritable_log_file(monkeypatch, capsys):
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        path = tmp.name
    os.chmod(path, 0o400)  # read-only

    monkeypatch.setenv("LOG_FILE", path)
    with pytest.raises(SystemExit):
        src.logging.validate_log_file()

    captured = capsys.readouterr()
    assert "Log file is not writable" in captured.err

    os.unlink(path)


def test_valid_log_file(monkeypatch):
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        path = tmp.name
    os.chmod(path, 0o600)  # writable

    monkeypatch.setenv("LOG_FILE", path)
    result = src.logging.validate_log_file()
    assert result == path

    os.unlink(path)
