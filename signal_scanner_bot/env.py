import os
from typing import Optional


def _env(key: str, fail: bool = True) -> Optional[str]:
    value = os.environ.get(key)
    if value is None and fail:
        raise KeyError(f"Key '{key}' is not present in environment!")
    return value


BOT_NUMBER = _env("BOT_NUMBER")
ADMIN_NUMBER = _env("ADMIN_NUMBER")
LISTEN_GROUP = _env("LISTEN_GROUP", fail=False)
TWITTER_API_KEY = _env("TWITTER_API_KEY")
TWITTER_API_SECRET = _env("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = _env("TWITTER_ACCESS_TOKEN")
TWITTER_TOKEN_SECRET = _env("TWITTER_TOKEN_SECRET")
TZ_UTC = _env("TZ_UTC", fail=False)
