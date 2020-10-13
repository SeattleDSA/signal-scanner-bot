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
NON_ALPHA_NUMERIC = re.compile(r"[\W]+")


def _pass_filters(data: D, filters: List[Callable[[D], bool]]) -> bool:
    """
    Given a certain data object, run all of the filters against that object.
    If the data passes all of the filters (they all come back False),
    this function returns True.
    """
    for filter_ in filters:
        filt_value = filter_(data)
        log.debug(f"{filter_}={filt_value}")
        if filt_value:
            return False
    return True


def _is_scanner_message(message: str) -> bool:
    """
    Check if a string starts with any of the header prefixes.
    """
    return any(
        [message.upper().startswith(header) for header in env.SIGNAL_MESSAGE_HEADERS]
    )


def _condense_command(message: str) -> str:
    """
    Remove any non alphanumeric characters from a string.
    """
    return NON_ALPHA_NUMERIC.sub("", message).upper()


def process_signal_message(blob: Dict, api: API) -> None:
    """
    Process a signal message.

    If the message passes initial filters and has an appropriate header,
    a tweet is sent out.
    If the message passes initial filters and is either the auto-scan on
    or off trigger, the global twitter listening state is updated.
    """
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
        timestamp = message_timestamp(data)
        log.info(f"{timestamp.isoformat()}: '{message}'")
        twitter.send_tweet(message, api)
        return

    # Check if twitter-to-signal should be on/off
    condensed = _condense_command(message)
    notice = env.STATE.update_listening_status(condensed)
    log.info(notice)
    signal.send_message(notice, env.LISTEN_CONTACT)


def process_twitter_message(status: Status) -> None:
    """
    Process a twitter status.

    If the status passes initial filters, strip the status text of any
    hashtags and send it as a signal message to the listening group.
    """
    log.info(f"STATUS RECEIVED ({status.id}) {status.text}")
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
    text += f"\nhttps://twitter.com/i/status/{status.id}"
    signal.send_message(text, env.LISTEN_CONTACT)
