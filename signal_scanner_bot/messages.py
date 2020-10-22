import logging
import re
from textwrap import dedent
from typing import Dict, List, Callable, TypeVar

from tweepy import Status, API

from . import env
from . import signal
from . import twitter
from .filters import SIGNAL_FILTERS, TWITTER_FILTERS

log = logging.getLogger(__name__)


################################################################################
# Constants
################################################################################
NON_ALPHA_NUMERIC = re.compile(r"[\W]+")
D = TypeVar("D")


################################################################################
# Private Functions
################################################################################
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


def _strip_tweet_hashtags(status_text: str) -> str:
    """
    Strip out words from tweet that are hashtags (ie. begin with a #)
    """
    text_split = [word for word in status_text.split() if not word.startswith("#")]
    text = " ".join(text_split)
    return text


def _build_tweet_url(status: Status) -> str:
    """
    Returns a link to the tweet provided. Surprisingly the Twitter API
    doesn't have a self link as a property of a tweet, so we have to
    build it ourselves.
    """
    return f"https://twitter.com/i/status/{status.id}"


def _get_tweet_text(status: Status) -> str:
    """
    Extract full text whether tweet is extended or not
    """
    if hasattr(status, "extended_tweet"):
        return _strip_tweet_hashtags(status.extended_tweet["full_text"])
    else:
        return _strip_tweet_hashtags(status.text)


def _format_tweet_text(status: Status) -> str:
    """
    Extract text from a tweet and build a signal message
    """
    return f"{_get_tweet_text(status)}\n{_build_tweet_url(status)}"


def _format_retweet_text(status: Status) -> str:
    """
    Extract text from retweet and build signal message
    """
    # Pull text out of the main tweet and sub tweet
    top_level_tweet_text = _get_tweet_text(status)
    quoted_tweet_text = _get_tweet_text(status.quoted_status)

    # Build Signal message
    if top_level_tweet_text:
        return dedent(
            f"""\
        [QUOTE TWEET]:
        {top_level_tweet_text}
        {_build_tweet_url(status)}

        [ORIGINAL TWEET]:
        {quoted_tweet_text}
        {_build_tweet_url(status.quoted_status)}
        """
        )
    else:
        return _format_tweet_text(status.quoted_status)


################################################################################
# Public Functions
################################################################################
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
        timestamp = signal.message_timestamp(data)
        log.info(f"{timestamp.isoformat()}: '{message}'")
        twitter.send_tweet(message, api)
        return

    # Check if twitter-to-signal should be on/off
    condensed = _condense_command(message)
    notice = env.STATE.update_listening_status(condensed)
    if notice:
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

    if hasattr(status, "quoted_status"):
        message = _format_retweet_text(status)
    else:
        message = _format_tweet_text(status)

    # On the off chance a message is an empty string just skip sending
    if message:
        signal.send_message(message, env.LISTEN_CONTACT)
