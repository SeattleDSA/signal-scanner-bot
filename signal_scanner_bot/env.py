import os
from typing import Optional


def _env(key: str, fail: bool = True) -> Optional[str]:
    value = os.environ.get(key)
    if value is None and fail:
        raise KeyError(f"Key '{key}' is not present in environment!")
    return value


BOT_NUMBER = _env("BOT_NUMBER")
ADMIN_NUMBER = _env("ADMIN_NUMBER")
