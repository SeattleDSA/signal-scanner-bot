import logging
import os
from threading import Lock
from typing import Optional, Any, Callable, List, Set


log = logging.getLogger(__name__)


_VARS = []


class _State:
    """Class for holding global state across threads/tasks"""

    LISTENING = False
    STOP_REQUESTED = False


def _env(key: str, convert: Callable[[str],Any] = None, fail: bool = True,default: Any = None) -> Optional[str]:
    value = os.environ.get(key)
    if value is None:
        if fail and default is None:
            raise KeyError(f"Key '{key}' is not present in environment!")
        return default
    if convert is not None:
        value = convert(value)
    _VARS.append((key, value))
    return value


def _cast_to_bool(to_cast: str) -> bool:
    return to_cast.lower() == "true"


def _cast_to_list(to_cast: str) -> List[str]:
    return to_cast.split(",")


def _cast_to_set(to_cast: str) -> Set[str]:
    return set(to_cast.split(","))


def log_vars() -> None:
    for key, value in _VARS:
        log.debug(f"{key}={value}")


TESTING = _env("TESTING", convert=_cast_to_bool, default=False)
DEBUG = TESTING or _env("DEBUG", default=False)
BOT_NUMBER = _env("BOT_NUMBER")
ADMIN_NUMBER = _env("ADMIN_NUMBER")
LISTEN_GROUP = _env("LISTEN_GROUP", fail=False)
SIGNAL_TIMEOUT = _env("SIGNAL_TIMEOUT", default=10)
TWITTER_API_KEY = _env("TWITTER_API_KEY")
TWITTER_API_SECRET = _env("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = _env("TWITTER_ACCESS_TOKEN")
TWITTER_TOKEN_SECRET = _env("TWITTER_TOKEN_SECRET")
TRUSTED_TWEETERS = _env("TRUSTED_TWEETERS", convert=_cast_to_set, default="")
SEND_HASHTAGS = _env("SEND_HASHTAGS", convert=_cast_to_list, default="")
RECEIVE_HASHTAGS = _env("RECEIVE_HASHTAGS", convert=_cast_to_list, default="")
SIGNAL_MESSAGE_HEADERS = _env("SIGNAL_MESSAGE_HEADERS", convert=_cast_to_set, default="")

SIGNAL_LOCK = Lock()

STATE = _State()
