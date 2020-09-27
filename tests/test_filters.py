from datetime import datetime as dt
from unittest import mock

import pytest


@pytest.fixture
def filters_module(env_module):
    from signal_scanner_bot import filters

    yield filters


################################################################################
# Message timestamp
################################################################################
@pytest.mark.parametrize(
    "ts, convert, expected",
    [
        # TZ without convert
        (dt(2020, 1, 1, 1, 1, 1), False, dt(2020, 1, 1, 1, 1, 1)),
        # TZ with convert
        (dt(2020, 1, 1, 8, 1, 1), True, dt(2020, 1, 1, 1, 1, 1)),
    ],
)
def test_message_timestamp(ts, convert, expected, filters_module, env_module):
    env_module.TZ_UTC = convert
    data = {"timestamp": ts.timestamp() * 1000}
    actual = filters_module.message_timestamp(data, convert)
    assert actual == expected


def test_message_timestamp_failure(filters_module):
    data = {}
    with pytest.raises(KeyError):
        filters_module.message_timestamp(data)


################################################################################
# Signal filters
################################################################################
@pytest.mark.parametrize(
    "data, expected",
    [
        # Don't care
        ({}, True),
        ({"message": ""}, True),
        ({"message": False}, True),
        ({"message": 0}, True),
        # Do care
        ({"message": "actual message"}, False),
        ({"message": 1}, False),
    ],
)
def test_f_no_data(data, expected, filters_module):
    actual = filters_module._f_no_data(data)
    assert actual == expected


@pytest.mark.parametrize(
    "data, listen_group, expected",
    [
        # Don't care
        ({}, "foo", True),
        # Has group, but no group specified in env
        ({"groupInfo": "asdf"}, "", True),
        # Has group
        ({"groupInfo": "asdf"}, "foo", False),
    ],
)
def test_f_no_group(data, listen_group, expected, filters_module, env_module):
    env_module.LISTEN_GROUP = listen_group
    actual = filters_module._f_no_group(data)
    assert actual == expected


@pytest.mark.parametrize(
    "data, listen_group, expected",
    [
        # # Don't care, but will still pass
        # ({}, "foo", False),
        # # Has group, but no group specified in env, but will still pass
        # ({"groupInfo": {"groupId": "asdf"}}, "", False),
        # Differing groups
        ({"groupInfo": {"groupId": "asdf"}}, "foo", True),
        # Matching group
        ({"groupInfo": {"groupId": "foo"}}, "foo", False),
    ],
)
def test_f_wrong_group(data, listen_group, expected, filters_module, env_module):
    env_module.LISTEN_GROUP = listen_group
    actual = filters_module._f_wrong_group(data)
    assert actual == expected


@pytest.mark.parametrize(
    "ts, now, expected",
    [
        # Not recent
        (dt(2020, 1, 1, 1, 1, 1), dt(2020, 1, 2, 2, 2, 2), True),
        (dt(2020, 1, 1, 1, 1, 1), dt(2020, 1, 1, 1, 7, 1), True),
        # Recent
        (dt(2020, 1, 1, 1, 0, 1), dt(2020, 1, 1, 1, 1, 1), False),
    ],
)
def test_f_not_recent(ts, now, expected, filters_module):
    data = {"timestamp": ts.timestamp() * 1000}
    actual = filters_module._f_not_recent(data, now=now)
    assert actual == expected


################################################################################
# Twitter filters
################################################################################
@pytest.mark.parametrize("retweeted", [True, False])
def test_f_retweeted(retweeted, filters_module):
    status = mock.Mock()
    status.retweeted = retweeted
    expected = retweeted
    actual = filters_module._f_retweeted(status)
    assert actual == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("RT @", True),
        ("Starts with useful content", False),
    ],
)
def test_f_retweet_text(text, expected, filters_module):
    status = mock.Mock()
    status.text = text
    actual = filters_module._f_retweet_text(status)
    assert actual == expected


@pytest.mark.parametrize(
    "name, trusted, expected", [("foo", {}, True), ("foo", {"foo"}, False)]
)
def test_f_not_trusted_tweeter(name, trusted, expected, filters_module, env_module):
    status = mock.Mock()
    status.author.screen_name = name
    env_module.TRUSTED_TWEETERS = trusted
    actual = filters_module._f_not_trusted_tweeter(status)
    assert actual == expected
