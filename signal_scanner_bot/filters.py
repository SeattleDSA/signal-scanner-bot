from datetime import datetime, timedelta
from typing import Dict, List, Callable, Optional

from tweepy import Status

from . import env


################################################################################
# Utilities
################################################################################
def message_timestamp(data: Dict, convert: bool = False) -> datetime:
    try:
        timestamp_milliseconds = data["timestamp"]
    except KeyError as err:
        raise KeyError(f"Timestamp field is not present in data: {data}") from err
    dt = datetime.fromtimestamp(timestamp_milliseconds / 1000.0)
    if env.TZ_UTC and convert:
        # TODO: Make this detect automatically
        # Convert to PDT
        dt -= timedelta(hours=7)
    return dt


################################################################################
# Signal Filters
################################################################################
def _f_no_data(data: Dict) -> bool:
    # No actual message contents
    return not data.get("message")


def _f_no_group(data: Dict) -> bool:
    # If listen group is defined and there's not group info
    return not (env.LISTEN_GROUP and data.get("groupInfo"))


def _f_wrong_group(data: Dict) -> bool:
    # Listen group is defined but ID doesn't match
    group = data.get("groupInfo") or {}
    return bool(group and env.LISTEN_GROUP and group.get("groupId") != env.LISTEN_GROUP)


def _f_not_recent(data: Dict, now: Optional[datetime] = None) -> bool:
    # Message is not within the last 5 minutes
    timestamp = message_timestamp(data)
    now = now or datetime.now()
    delta = now - timestamp
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
def _f_retweeted(status: Status) -> bool:
    # Status is retweeted
    return status.retweeted


def _f_retweet_text(status: Status) -> bool:
    # Status text starts with "RT @"
    # Twitter uses that to identify a retweet
    return status.text.startswith("RT @")


def _f_not_trusted_tweeter(status: Status) -> bool:
    # Status wasn't sent by a trusted tweeter
    return status.author.screen_name not in env.TRUSTED_TWEETERS


TWITTER_FILTERS: List[Callable[[Status], bool]] = [
    _f_retweeted,
    _f_retweet_text,
    _f_not_trusted_tweeter,
]
