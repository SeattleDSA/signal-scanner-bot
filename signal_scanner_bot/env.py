import logging
import os
from pathlib import Path
from threading import Lock
from typing import Any, Callable, List, Set, Optional


log = logging.getLogger(__name__)


_VARS = []
START_LISTENING = "AUTOSCANON"
STOP_LISTENING = "AUTOSCANOFF"
START_LISTENING_NOTIFICATION = "==Auto Scanning Activated=="
STOP_LISTENING_NOTIFICATION = "==Auto Scanning Deactivated=="


class _State:
    """Class for holding global state across threads/tasks"""

    # Initialize state, set LISTENING to true if state file exists,
    # sets false if not.
    def __init__(self, file: Path):
        self.file = file
        self.LISTENING = self.file.exists()
        self.STOP_REQUESTED = False

    # Method to update the listening status of the State class
    # object. Checks for on/off and creates/deletes state file.
    def update_listening_status(self, status: str) -> Optional[str]:
        if status == START_LISTENING:
            self.LISTENING = True
            self.file.touch()
            return START_LISTENING_NOTIFICATION
        elif status == STOP_LISTENING:
            self.LISTENING = False
            self.file.unlink(missing_ok=True)
            return STOP_LISTENING_NOTIFICATION
        else:
            return None

    # Method to return the current state notification message
    def get_listening_status_notice(self) -> str:
        return (
            START_LISTENING_NOTIFICATION
            if self.LISTENING
            else STOP_LISTENING_NOTIFICATION
        )


def _env(
    key: str,
    convert: Callable[[str], Any],
    fail: bool = True,
    default: Any = None,
) -> Any:
    value = os.environ.get(key)
    if value is None:
        if fail and default is None:
            raise KeyError(f"Key '{key}' is not present in environment!")
        value = default
    value = convert(str(value))
    _VARS.append((key, value))
    return value


################################################################################
# Casting functions
################################################################################
# Functions to ensure the correct types are always returned by the _env function
def _cast_to_bool(to_cast: str) -> bool:
    return to_cast.lower() == "true"


def _cast_to_list(to_cast: str) -> List[str]:
    return to_cast.split(",")


def _cast_to_set(to_cast: str) -> Set[str]:
    return set(_cast_to_list(to_cast))


def _cast_to_string(to_cast: str) -> str:
    if isinstance(to_cast, str):
        return to_cast
    else:
        return ""


def _cast_to_int(to_cast: str) -> int:
    return int(to_cast)


def _cast_to_path(to_cast: str) -> Path:
    return Path(to_cast)


def log_vars() -> None:
    for key, value in _VARS:
        log.debug(f"{key}={value}")


################################################################################
# Environment Variable declarations
################################################################################
# Declares all environment variables for application execution
TESTING = _env("TESTING", convert=_cast_to_bool, default=False)
DEBUG = TESTING or _env("DEBUG", convert=_cast_to_bool, default=False)
BOT_NUMBER = _env("BOT_NUMBER", convert=_cast_to_string)
ADMIN_CONTACT = _env("ADMIN_CONTACT", convert=_cast_to_string)
LISTEN_CONTACT = _env("LISTEN_CONTACT", convert=_cast_to_string, fail=False)
SIGNAL_TIMEOUT = _env("SIGNAL_TIMEOUT", convert=_cast_to_int, default=10)
TWITTER_API_KEY = _env("TWITTER_API_KEY", convert=_cast_to_string)
TWITTER_API_SECRET = _env("TWITTER_API_SECRET", convert=_cast_to_string)
TWITTER_ACCESS_TOKEN = _env("TWITTER_ACCESS_TOKEN", convert=_cast_to_string)
TWITTER_TOKEN_SECRET = _env("TWITTER_TOKEN_SECRET", convert=_cast_to_string)
TRUSTED_TWEETERS = _env("TRUSTED_TWEETERS", convert=_cast_to_set, default={})
SEND_HASHTAGS = _env("SEND_HASHTAGS", convert=_cast_to_list, default=[])
RECEIVE_HASHTAGS = _env("RECEIVE_HASHTAGS", convert=_cast_to_list, default=[])
SIGNAL_MESSAGE_HEADERS = _env(
    "SIGNAL_MESSAGE_HEADERS", convert=_cast_to_set, default={}
)
AUTOSCAN_STATE_FILE_PATH = _env(
    "AUTOSCAN_STATE_FILE_PATH",
    convert=_cast_to_path,
    default="signal_scanner_bot/.autoscanner-state-file",
)

SIGNAL_LOCK = Lock()

STATE = _State(AUTOSCAN_STATE_FILE_PATH)
