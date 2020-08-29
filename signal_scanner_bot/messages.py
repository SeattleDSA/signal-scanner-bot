import logging
import re
from typing import Dict, List, Callable, TypeVar

from tweepy import Status, API

from . import env
from . import signal
from . import twitter
from .filters import SIGNAL_FILTERS, message_timestamp, TWITTER_FILTERS

log = logging.getLogger(__name__)


D = TypeVar("D")


################################################################################
# Constants
################################################################################
NON_ALPHA_NUMERIC = re.compile(r"[\W_]+")
START_LISTENING = "AUTOSCANON"
STOP_LISTENING = "AUTOSCANOFF"
HEADERS = {
    "SCANNER",
    "DISPATCH W",
    "DISPATCH E",
    "DISPATCH N",
    "DISPATCH S",
    "DISP W",
    "DISP E",
    "DISP N",
    "DISP S",
    "GROUND",
}


def _pass_filters(data: D, filters: List[Callable[[D], bool]]) -> bool:
    for filter_ in filters:
        filt_value = filter_(data)
        log.debug(f"{filter_}={filt_value}")
        if filt_value:
            return False
    return True


def _is_scanner_message(message: str) -> bool:
    return not any([message.upper().startswith(header) for header in HEADERS])


def _condense_command(message: str) -> str:
    return NON_ALPHA_NUMERIC.sub("", message).upper()


def process_signal_message(blob: Dict, api: API) -> None:
    log.debug(f"Got message: {blob}")
    envelope = blob.get("envelope", {})
    if not envelope or "dataMessage" not in envelope:
        log.error(f"Malformed message: {blob}")

    data = envelope.get("dataMessage") or {}
    if not _pass_filters(data, SIGNAL_FILTERS):
        return
    message = data["message"]

    # Signal-to-twitter
    if _is_scanner_message(message):
        timestamp = message_timestamp(data, convert=True)
        log.info(f"{timestamp.isoformat()}: '{message}'")
        twitter.send_tweet(message, timestamp, api)
        return

    # Check if twitter-to-signal should be on/off
    condensed = _condense_command(message)
    if condensed == START_LISTENING:
        notice = "==Auto Scanning Activated=="
        listening = True
    elif condensed == STOP_LISTENING:
        notice = "==Auto Scanning Deactivated=="
        listening = False
    else:
        return
    log.info(notice)
    env.STATE.LISTENING = listening
    signal.send_message(notice, env.LISTEN_GROUP, group=True)


def process_twitter_message(status: Status) -> None:
    log.debug(f"STATUS RECEIVED ({status.id}) {status.text}")
    if not _pass_filters(status, TWITTER_FILTERS):
        return None
    # Tweet is too large to be parsed in the OG text
    if hasattr(status, "extended_tweet"):
        text = status.extended_tweet["full_text"]
    else:
        text = status.text

    # Remove hashtags
    text_split = [word for word in text.split() if not word.startswith("#")]
    text = " ".join(text_split)
    signal.send_message(text, env.LISTEN_GROUP, group=True)
