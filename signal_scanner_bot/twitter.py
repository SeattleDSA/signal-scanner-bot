import logging
from datetime import datetime
from textwrap import dedent

import tweepy

from . import env

log = logging.getLogger(__name__)

HASHTAGS = ["#SeattleProtestComms", "#SeaScanner", "#SeattleProtests"]
TWEET_MAX_SIZE = 280


def get_api() -> tweepy.API:
    # Authenticate to Twitter
    auth = tweepy.OAuthHandler(env.TWITTER_API_KEY, env.TWITTER_API_SECRET)
    auth.set_access_token(env.TWITTER_ACCESS_TOKEN, env.TWITTER_TOKEN_SECRET)

    api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
    api.verify_credentials()
    return api


def send_tweet(tweet: str, timestamp: datetime, api: tweepy.API) -> None:
    hashtags = " ".join(HASHTAGS)
    if len(tweet + hashtags) >= 260:
        # TODO: better
        log.warning(f"Cannot tweet message, exceeds length: {tweet}")

    formatted = dedent(
        f"""
    {tweet} @ {timestamp.strftime('%l:%M:%S%p').strip()}

    {hashtags}
    """
    )
    api.update_status(formatted)
