import logging
import os
from asyncio import Queue
from datetime import time
from pathlib import Path
from typing import Any, Callable, List, Optional, Set

import peony


log = logging.getLogger(__name__)


################################################################################
# Constants
################################################################################
_VARS = []
START_LISTENING = "AUTOSCANON"
STOP_LISTENING = "AUTOSCANOFF"
START_LISTENING_NOTIFICATION = "==Auto Scanning Activated=="
STOP_LISTENING_NOTIFICATION = "==Auto Scanning Deactivated=="


################################################################################
# Other Functions
################################################################################
def _env(
    key: str,
    convert: Callable[[str], Any],
    fail: bool = True,
    default: Any = None,
) -> Any:
    """
    Read container/OS environment variables in and return the values,
    which can then be stored in global Python variables.
    """
    value = os.environ.get(key)
    if value is None:
        if fail and default is None:
            raise KeyError(f"Key '{key}' is not present in environment!")
        value = default
    value = convert(str(value))
    _VARS.append((key, value))
    return value


def log_vars() -> None:
    """Log all environment variables in any part of the application."""
    log.debug("Input environment variables")
    for key, value in _VARS:
        log.debug(f"{key}={value}")


################################################################################
# Classes
################################################################################
class _State:
    """Global state management across threads/tasks."""

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


################################################################################
# Casting functions
################################################################################
# These functions simply cast all incoming environment variables, which are
# only able to be returned as strings, into the desired type
################################################################################
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


def _cast_to_time(to_cast: str) -> time:
    return time.fromisoformat(to_cast)


def _format_hashtags(to_cast: str) -> List[str]:
    hashtags = _cast_to_list(to_cast)
    if any("#" in hashtag for hashtag in hashtags):
        log.warning(
            "WARNING: Receive hashtags should no longer contain a # at the start,"
            " only the contents of the hashtag itself is needed."
        )

    # Remove any hashtags
    return [hashtag.strip("#") for hashtag in hashtags]


################################################################################
# Scanner Environment Variables
################################################################################
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
RECEIVE_HASHTAGS = _env("RECEIVE_HASHTAGS", convert=_format_hashtags, default=[])
SIGNAL_MESSAGE_HEADERS = _env(
    "SIGNAL_MESSAGE_HEADERS", convert=_cast_to_set, default={}
)
AUTOSCAN_STATE_FILE_PATH = _env(
    "AUTOSCAN_STATE_FILE_PATH",
    convert=_cast_to_path,
    default="signal_scanner_bot/.autoscanner-state-file",
)

################################################################################
# Comradely Reminder Environment Variables
################################################################################
COMRADELY_CONTACT = _env("COMRADELY_CONTACT", convert=_cast_to_string, fail=False)
COMRADELY_MESSAGE = _env("COMRADELY_MESSAGE", convert=_cast_to_string, fail=False)
COMRADELY_TIME = _env(
    "COMRADELY_TIME",
    convert=_cast_to_time,
    fail=False,
    default="20:00:00",  # 2pm PST
)

################################################################################
# SWAT Alert Environment Variables
################################################################################
SWAT_OPENMHZ_URL = _env("SWAT_OPENMHZ_URL", convert=_cast_to_string, fail=False)
SWAT_LOOKUP_URL = _env("SWAT_LOOKUP_URL", convert=_cast_to_string, fail=False)
SWAT_UNITS = _env("SWAT_UNITS", convert=_cast_to_set, fail=False)
SWAT_CONTACT = _env("SWAT_CONTACT", convert=_cast_to_string, fail=False)

# Checking to ensure user ids are in the proper format, raise error if not.
for tweeter in TRUSTED_TWEETERS:
    if tweeter[0] == "@":
        raise ValueError(
            "TRUSTER_TWEETERS must be user IDs and not handles. Please visit http://gettwitterid.com/"
            " to find the user ID of a user's handle."
        )

################################################################################
# Environment State Variables
################################################################################
STATE = _State(AUTOSCAN_STATE_FILE_PATH)
TWITTER_TO_SIGNAL_QUEUE: Queue = Queue(maxsize=10000)  # shooting from the hip here...

################################################################################
# Peony Twitter Event Stream client
################################################################################
API_KEYS = {
    "consumer_key": TWITTER_API_KEY,
    "consumer_secret": TWITTER_API_SECRET,
    "access_token": TWITTER_ACCESS_TOKEN,
    "access_token_secret": TWITTER_TOKEN_SECRET,
}
CLIENT = peony.PeonyClient(**API_KEYS)
