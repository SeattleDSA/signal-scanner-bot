from datetime import datetime, timedelta
from typing import Dict

from signal_scanner_bot import env


################################################################################
# Utilities
################################################################################
def message_timestamp(data: Dict) -> datetime:
    try:
        timestamp_milliseconds = data["timestamp"]
    except KeyError as err:
        raise KeyError(f"Timestamp field is not present in data: {data}") from err
    return datetime.fromtimestamp(timestamp_milliseconds / 1000.0)


################################################################################
# Filters
################################################################################
def _f_no_data(data: Dict) -> bool:
    # No actual message contents
    return not data.get("message")


def _f_no_group(data: Dict) -> bool:
    # If listen group is defined and there's not group info
    return env.LISTEN_GROUP and not data.get("groupInfo")


def _f_wrong_group(data: Dict) -> bool:
    # Listen group is defined but ID doesn't match
    group = data.get("groupInfo") or {}
    return group and env.LISTEN_GROUP and group.get("groupId") != env.LISTEN_GROUP


def _f_not_recent(data: Dict) -> bool:
    # Message is not within the last 5 minutes
    timestamp = message_timestamp(data)
    delta = datetime.now() - timestamp
    return delta > timedelta(minutes=5)


def _f_not_scanner_message(data: Dict) -> bool:
    message: str = data["message"]
    headers = {
        "SCANNER",
        "DISPATCH W",
        "DISPATCH E",
        "DISPATCH N",
        "DISPATCH S",
        "DISP W",
        "DISP E",
        "DISP N",
        "DISP S",
    }
    return not any([message.upper().startswith(header) for header in headers])


FILTERS = [
    _f_no_data,
    _f_no_group,
    _f_wrong_group,
    _f_not_recent,
    _f_not_scanner_message,
]
