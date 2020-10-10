import logging
import os
import os.path
from threading import Lock
from typing import Optional, Any


log = logging.getLogger(__name__)


_VARS = []


class _State:
    """Class for holding global state across threads/tasks"""

    # Initialize state, set LISTENING to true if state file exists,
    # sets false if not.
    def __init__(self, file: str):
        self.file = file
        self.LISTENING = True if os.path.isfile(file) else False
        self.STOP_REQUESTED = False

    # Method to update the listening status of the State class
    # object. Checks for on/off and creates/deletes state file.
    def update_listening_status(self, status: str) -> Optional[str]:
        if status == "AUTOSCANON":
            self.LISTENING = True
            open(self.file, "a").close()
            return "==Auto Scanning Activated=="
        elif status == "AUTOSCANOFF":
            self.LISTENING = False
            try:
                os.remove(self.file)
            except OSError:
                pass
            finally:
                return "==Auto Scanning Deactivated=="
        else:
            # Should be impossible to get her but it's here to
            # satisfy mypy
            return None

    # Method to return the current state notification message
    def get_listening_status_notice(self) -> Optional[str]:
        if self.LISTENING:
            return "==Auto Scanning Activated=="
        elif not self.LISTENING:
            return "==Auto Scanning Deactivated=="
        else:
            # Should be impossible to get her but it's here to
            # satisfy mypy
            return None


def _env(key: str, fail: bool = True, default: Any = None) -> Optional[str]:
    value = os.environ.get(key)
    if value is None:
        if fail and default is None:
            raise KeyError(f"Key '{key}' is not present in environment!")
        return default
    _VARS.append((key, value))
    return value


def log_vars() -> None:
    for key, value in _VARS:
        log.debug(f"{key}={value}")


DEBUG = _env("DEBUG", default=False)
BOT_NUMBER = _env("BOT_NUMBER")
ADMIN_NUMBER = _env("ADMIN_NUMBER")
LISTEN_GROUP = _env("LISTEN_GROUP", fail=False)
SIGNAL_TIMEOUT = _env("SIGNAL_TIMEOUT", default=10)
TWITTER_API_KEY = _env("TWITTER_API_KEY")
TWITTER_API_SECRET = _env("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = _env("TWITTER_ACCESS_TOKEN")
TWITTER_TOKEN_SECRET = _env("TWITTER_TOKEN_SECRET")
TRUSTED_TWEETERS = set(str(_env("TRUSTED_TWEETERS", default="")).split(","))

SIGNAL_LOCK = Lock()

STATE = _State("signal_scanner_bot/.autoscanner-state-file")
