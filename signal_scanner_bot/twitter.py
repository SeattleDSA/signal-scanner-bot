import logging
from datetime import datetime
from textwrap import dedent
from typing import List

import tweepy

from . import env

log = logging.getLogger(__name__)


################################################################################
# Constants
################################################################################
SEND_HASHTAGS = ["#SeattleProtestComms", "#SeaScanner", "#SeattleProtests"]
RECEIVE_HASHTAGS = ["#SeattleProtestComms"]
TWEET_MAX_SIZE = 280
TWEET_PADDING = 20


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

    # Check if tweet is longer than 280 minus a 20 char padding, add to list if
    # not, continue with dividing up text if so
    if len(tweet + hashtags) >= TWEET_MAX_SIZE - TWEET_PADDING:
        tweets_list = create_tweet_thread(tweet, hashtags)
    else:
        tweets_list = [tweet]

    # tweet_id used to track previous tweet in thread, set to None for first
    # This iterates through all (even if just one) tweets in list to send
    tweet_id = None
    for index, sub_tweet in enumerate(tweets_list):

        # If this is the first tweet add timestamp and hashtags
        if index == 0:
            formatted = dedent(
                f"""
            {timestamp.strftime('%H:%M:%S%p').strip()}

            {sub_tweet}

            {hashtags}
            """
            )
        else:
            formatted = sub_tweet

        # If first tweet send without reply to tweet ID parameter, if part
        # of a thread send reply using ID of last tweet sent.
        if tweet_id is None:
            status_obj = api.update_status(status=formatted)
            tweet_id = status_obj.id
        else:
            status_obj = api.update_status(
                status=formatted,
                in_reply_to_status_id=tweet_id,
                auto_populate_reply_metadata=True,
            )
            tweet_id = status_obj.id


def create_tweet_thread(message: str, hashtags: str) -> List[str]:
    # Split tweet into word list, create empty list to store serialized tweets, index to track last position
    tweet_word_list = message.split(" ")
    tweets_list: List[str] = []
    base_index = 0

    # For loop through word list and enumerate the index because we'll need
    # it but don't actually care about the list value so send to null
    for index in range(len(tweet_word_list)):

        # Check if it is the first tweet, which will contain hashtags and
        # timestamp. If not first it will only contain the text plus ellipses
        # and for the final one drop the ellipses
        if len(tweets_list) == 0:
            sub_tweet = " ".join(tweet_word_list[base_index:index]) + " ..." + hashtags
        elif index < len(tweet_word_list):
            sub_tweet = " ".join(tweet_word_list[base_index:index]) + " ..."
        elif index == len(tweet_word_list):
            sub_tweet = " ".join(tweet_word_list[base_index:index])

        # When length of tweet reaches >260 chars save to list and set
        # base index for next tweet
        if len(sub_tweet) > TWEET_MAX_SIZE - TWEET_PADDING:
            tweets_list.append(
                " ".join(tweet_word_list[base_index : index - 1]) + " ..."
            )
            base_index = index - 1

    # Save the last tweet
    tweets_list.append(" ".join(tweet_word_list[base_index:]))

    # Append the tweet number / tweet thread length to end of tweet. Again
    # don't actually care about the list value so sending to null.
    for index in range(len(tweets_list)):
        tweets_list[index] += f" {index + 1}/{len(tweets_list)}"

    return tweets_list
