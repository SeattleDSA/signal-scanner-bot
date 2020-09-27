import logging
from datetime import datetime
from typing import Sequence

from tweepy import API, OAuthHandler

from . import env

log = logging.getLogger(__name__)


################################################################################
# Constants
################################################################################
SEND_HASHTAGS = ("#SeattleProtestComms", "#SeaScanner", "#SeattleProtests")
RECEIVE_HASHTAGS = ["#SeattleProtestComms"]
TWEET_MAX_SIZE = 280


################################################################################
# Basic API
################################################################################
def get_api():
    # Authenticate to Twitter
    auth = OAuthHandler(env.TWITTER_API_KEY, env.TWITTER_API_SECRET)
    auth.set_access_token(env.TWITTER_ACCESS_TOKEN, env.TWITTER_TOKEN_SECRET)

    api = API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
    api.verify_credentials()
    return api


################################################################################
# Sending data
################################################################################
def send_tweet(
    tweet: str, timestamp: datetime, api: API, hashtags: Sequence[str] = SEND_HASHTAGS
) -> None:
    formatted_hashtags = " ".join(hashtags)
    if len(tweet + formatted_hashtags) >= 260:
        # TODO: better
        log.warning(f"Cannot tweet message, exceeds length: {tweet}")
        return

    formatted = f"""
{tweet} @ {timestamp.strftime('%l:%M:%S%p').strip()}

{formatted_hashtags}"""

    api.update_status(formatted)
