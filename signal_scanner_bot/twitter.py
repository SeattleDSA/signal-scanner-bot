import logging
from datetime import datetime
from textwrap import dedent

import tweepy

from . import env
from . import signal


log = logging.getLogger(__name__)


################################################################################
# Constants
################################################################################
SEND_HASHTAGS = ["#SeattleProtestComms", "#SeaScanner", "#SeattleProtests"]
RECEIVE_HASHTAGS = ["#SeattleProtestComms"]
TRUSTED_SCANNERS = {}
TWEET_MAX_SIZE = 280


################################################################################
# Basic API
################################################################################
def get_api():
    # Authenticate to Twitter
    auth = tweepy.OAuthHandler(env.TWITTER_API_KEY, env.TWITTER_API_SECRET)
    auth.set_access_token(env.TWITTER_ACCESS_TOKEN, env.TWITTER_TOKEN_SECRET)

    api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
    api.verify_credentials()
    return api


################################################################################
# Sending data
################################################################################
def send_tweet(tweet: str, timestamp: datetime, api: tweepy.API) -> None:
    hashtags = " ".join(SEND_HASHTAGS)
    if len(tweet + hashtags) >= 260:
        # TODO: better
        log.warning(f"Cannot tweet message, exceeds length: {tweet}")
        return

    formatted = dedent(
        f"""
    {tweet} @ {timestamp.strftime('%l:%M:%S%p').strip()}

    {hashtags}
    """
    )
    api.update_status(formatted)


################################################################################
# Stream listener
################################################################################
class Listener(tweepy.StreamListener):

    IS_LISTENING = True

    def on_status(self, status: tweepy.Status):
        # We don't are about retweets
        if not status.is_quote_status and self.IS_LISTENING:
            log.info(f"STATUS RECEIVED: {status.text}")
            signal.send_message(status.text, env.LISTEN_GROUP, group=True)


# Have to make this a global object so that we can modify
# the listening attribute in another thread
LISTENER = Listener()
