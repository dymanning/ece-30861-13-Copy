import pytest
from github import BadCredentialsException

import src.git

def test_validate_github_token_missing_env(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with pytest.raises(SystemExit):
        src.git.validate_github_token()   # call from src.git

    captured = capsys.readouterr()
    assert "Missing GITHUB_TOKEN" in captured.err


class DummyGithub:
    def __init__(self, token):
        self.token = token

    def get_user(self):
        class DummyUser:
            id = 123
        return DummyUser()


def test_validate_github_token_valid(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setattr(src.git, "Github", lambda token: DummyGithub(token))

    # should not raise if valid
    src.git.validate_github_token()



def test_validate_github_token_invalid(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_TOKEN", "bad-token")

    class BadGithub:
        def __init__(self, token):
            pass

        def get_user(self):
            raise BadCredentialsException(
                status=401, data="bad token", headers={})

    monkeypatch.setattr(src.git, "Github", lambda token: BadGithub(token))

    with pytest.raises(SystemExit):
        src.git.validate_github_token()

    captured = capsys.readouterr()
    assert "Invalid GITHUB_TOKEN" in captured.err
