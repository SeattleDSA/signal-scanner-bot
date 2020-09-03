import pytest


@pytest.fixture
def env_module(monkeypatch):
    for var in [
        "BOT_NUMBER",
        "ADMIN_NUMBER",
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_TOKEN_SECRET",
    ]:
        monkeypatch.setenv(var, "fakevalue")
    from signal_scanner_bot import env

    yield env