from datetime import datetime as dt
from unittest import mock

import pytest
from tweepy import API


@pytest.fixture
def twitter_module(env_module):
    from signal_scanner_bot import twitter

    yield twitter


@pytest.fixture
def api() -> API:
    api = mock.Mock(spec=API)
    return api


def test_get_api(twitter_module):
    with mock.patch("signal_scanner_bot.twitter.OAuthHandler"), mock.patch(
        "signal_scanner_bot.twitter.API"
    ) as _API:
        api = _API.return_value
        actual = twitter_module.get_api()
        assert actual == api
        api.verify_credentials.assert_called_once()


@pytest.mark.parametrize(
    "tweet, timestamp, expected",
    [
        ("test tweet", dt(2020, 1, 1, 1, 1, 1), "\ntest tweet @ 1:01:01AM\n\n#HASH"),
        ("test tweet", dt(2020, 1, 1, 14, 2, 2), "\ntest tweet @ 2:02:02PM\n\n#HASH"),
        (
            "Longer tweet\nwith multiple newlines",
            dt(2020, 1, 1, 1, 1, 1),
            "\nLonger tweet\nwith multiple newlines @ 1:01:01AM\n\n#HASH",
        ),
    ],
)
def test_send_tweet(tweet, timestamp, expected, api, twitter_module):
    twitter_module.send_tweet(tweet, timestamp, api, hashtags=["#HASH"])
    actual = api.update_status.call_args.args[0]
    assert actual == expected


@pytest.mark.parametrize(
    "tweet, hashtags",
    [
        ("*" * 260, ["#HASH"]),
        ("*" * 400, ["#HASH"]),
        # Total + hash is greater than 260
        ("*" * 255, ["#HASH"]),
    ],
    ids=["260", "400", "255+hash"],
)
def test_send_tweet_too_long(tweet, hashtags, api, twitter_module):
    timestamp = dt(2020, 1, 1, 1, 1, 1)
    twitter_module.send_tweet(tweet, timestamp, api, hashtags=hashtags)
    api.update_status.assert_not_called()
