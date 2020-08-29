import logging
from datetime import datetime
from typing import Dict, Optional, Tuple, List, Callable, TypeVar

from tweepy import Status, API

from . import env
from . import signal
from . import twitter
from .filters import SIGNAL_FILTERS, message_timestamp, TWITTER_FILTERS

log = logging.getLogger(__name__)


D = TypeVar("D")


def _pass_filters(data: D, filters: List[Callable[[D], bool]]) -> bool:
    for filter_ in filters:
        filt_value = filter_(data)
        log.debug(f"{filter_}={filt_value}")
        if filt_value:
            return False
    return True


def process_signal_message(blob: Dict, api: API) -> Optional[Tuple[str, datetime]]:
    log.debug(f"Got message: {blob}")
    envelope = blob.get("envelope", {})
    if not envelope or "dataMessage" not in envelope:
        log.error(f"Malformed message: {blob}")

    data = envelope.get("dataMessage") or {}
    # TODO: change listening status
    if not _pass_filters(data, SIGNAL_FILTERS):
        return None

    message = data["message"]
    timestamp = message_timestamp(data, convert=True)
    log.info(f"{timestamp.isoformat()}: '{message}'")
    twitter.send_tweet(message, timestamp, api)


def process_twitter_message(status: Status) -> Optional[str]:
    log.debug(f"STATUS RECEIVED ({status.id}) {status.text}")
    if not _pass_filters(status, TWITTER_FILTERS):
        return None
    # Tweet is too larged to be parsed in the OG text
    if hasattr(status, "extended_tweet"):
        text = status.extended_tweet["full_text"]
    else:
        text = status.text

    # Remove hashtags
    text_split = [word for word in text.split() if not word.startswith("#")]
    text = " ".join(text_split)
    signal.send_message(text, env.LISTEN_GROUP, group=True)
