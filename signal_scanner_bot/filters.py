from datetime import datetime, timedelta
from typing import Dict, List, Callable

from . import env
from .signal import message_timestamp


################################################################################
# Signal Filters
################################################################################
def _f_no_data(data: Dict) -> bool:
    # No actual message contents
    return not data.get("message")


def _f_no_group(data: Dict) -> bool:
    # If listen group is defined and there's not group info
    return bool(env.LISTEN_CONTACT and not data.get("groupInfo"))


def _f_wrong_group(data: Dict) -> bool:
    # Listen group is defined but ID doesn't match
    group = data.get("groupInfo") or {}
    return bool(
        group and env.LISTEN_CONTACT and group.get("groupId") != env.LISTEN_CONTACT
    )


def _f_not_recent(data: Dict) -> bool:
    # Message is not within the last 5 minutes
    timestamp = message_timestamp(data)
    delta = datetime.now() - timestamp
    return delta > timedelta(minutes=5)


SIGNAL_FILTERS: List[Callable[[Dict], bool]] = [
    _f_no_data,
    _f_no_group,
    _f_wrong_group,
    _f_not_recent,
]


################################################################################
# Twitter Filters
################################################################################
def _f_retweet_text(status: Dict) -> bool:
    # Status text starts with "RT @"
    # Twitter uses that to identify a retweet
    return status["text"].startswith("RT @")


TWITTER_FILTERS: List[Callable[[Dict], bool]] = [
    _f_retweet_text,
]
