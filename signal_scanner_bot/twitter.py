import logging
from textwrap import dedent
from typing import List

import peony

from . import env, signal


log = logging.getLogger(__name__)


################################################################################
# Constants
################################################################################
# TWEET_MAX_SIZE is the current tweet character limit
# TWEET_THREAD_MAX sets the maximum tweet thrad length
# TWEET_PADDING calculates the padding necessary based on TWEET_THREAD_MAX. This
# is done by converting the int to str, getting the number of digits,
# multiplying the digits by two, and adding
################################################################################
TWEET_MAX_SIZE = 280
TWEET_PADDING = 2 * len(str(env.TWEET_THREAD_MAX)) + 2


################################################################################
# Private functions
################################################################################
def _create_tweet_thread(message: str, hashtags: str) -> List[str]:
    """
    Take in a string of variable length and build a list of unformatted tweet
    messages of the proper length.
    """
    # Split tweet into word list, create empty list to store serialized tweets
    # index to track last position
    tweet_word_list = message.split(" ")
    tweet_list: List[str] = []
    base_index = 0

    # For loop through word list and enumerate the index because we'll need
    # it but don't actually care about the list value so send to null
    for index in range(len(tweet_word_list)):

        # Check if it is the first tweet, which will contain hashtags and
        # timestamp. If not first it will only contain the text plus ellipses
        # and for the final one drop the ellipses
        if len(tweet_list) == 0:
            sub_tweet = " ".join(tweet_word_list[base_index:index]) + " ..." + hashtags
        elif index < len(tweet_word_list):
            sub_tweet = " ".join(tweet_word_list[base_index:index]) + " ..."
        elif index == len(tweet_word_list):
            sub_tweet = " ".join(tweet_word_list[base_index:index])

        # When length of tweet reaches >280 chars save to list and set
        # base index for next tweet
        # noinspection PyUnboundLocalVariable
        if len(sub_tweet) > TWEET_MAX_SIZE - TWEET_PADDING:
            last_index = index - 1
            tweet_list.append(" ".join(tweet_word_list[base_index:last_index]) + " ...")
            base_index = index - 1

    # Save the last tweet
    tweet_list.append(" ".join(tweet_word_list[base_index:]))

    # Append the tweet number / tweet thread length to end of tweet. Again
    # don't actually care about the list value so sending to null.
    for index in range(len(tweet_list)):
        tweet_list[index] += f" {index + 1}/{len(tweet_list)}"

    return tweet_list


def _build_hashtags(hashtags: List[str]) -> str:
    """
    Build single string object from list of hashtags, replacing the leading # with
    a _ in case of testing so as not to pollute any production comms.
    """
    if env.TESTING:
        hashtags = [x.replace("#", "_") for x in hashtags]
    return " ".join(hashtags)


def _format_tweet_message(tweet_list: List[str], hashtags: str) -> List[str]:
    """
    Format tweets as desired. This function should be fairly flexible
    and really only require that you be mindful of the tweet padding constants
    when attempting to make changes to the formatting of any tweets you wish to
    send.
    """
    return_list: List[str] = []
    for index, sub_tweet in enumerate(tweet_list):
        # If this is the first tweet add hashtags
        if index == 0:
            return_list.append(
                dedent(
                    f"""
                {sub_tweet}

                {hashtags}
                """
                )
            )
        else:
            return_list.append(sub_tweet)
    return return_list


async def _send_tweet_thread(tweet_list: List[str], client: peony.PeonyClient) -> None:
    """
    Take a list of tweet messages and send them as a twitter thread,
    or, if there is only one object in the list, a single tweet.
    """
    tweet_id = None
    for tweet in tweet_list:
        # If first tweet send without reply to tweet ID parameter, if part
        # of a thread send reply using ID of last tweet sent.
        if tweet_id is None:
            status_obj = await client.api.statuses.update.post(status=tweet)
            tweet_id = status_obj.id
        else:
            status_obj = await client.api.statuses.update.post(
                status=tweet,
                in_reply_to_status_id=tweet_id,
                auto_populate_reply_metadata=True,
            )
            tweet_id = status_obj.id


################################################################################
# Public functions
################################################################################
async def send_tweet(tweet: str, client: peony.PeonyClient) -> None:
    """Build and send tweets from incoming message streams."""
    # Builds the hashtags that will be sent along with the tweet, if any
    hashtags = _build_hashtags(env.SEND_HASHTAGS)

    # Check if tweet is longer than 280 minus the defined amount of padding for
    # a tweet. Creates list of tweets to send in a thread or single tweet.
    if len(tweet + hashtags) >= TWEET_MAX_SIZE - TWEET_PADDING:
        tweet_list = _create_tweet_thread(tweet, hashtags)
    else:
        tweet_list = [tweet]

    if len(tweet_list) > env.TWEET_THREAD_MAX:
        log.error(
            f"""
            Attempted to send too long of a tweet thread:
            thread length = {len(tweet_list)}
            thread maximum = {env.TWEET_THREAD_MAX}
            """
        )
    else:
        # Tries to send the tweet thread and sends a panic message to the admin
        # Signal group if there is an error.
        try:
            formatted_tweet_list = _format_tweet_message(tweet_list, hashtags)
            await _send_tweet_thread(formatted_tweet_list, client)
        except Exception as err:
            log.warning(
                f"There was an unexpected error returned from the Twitter API:\n{err}"
            )
            signal.panic(err)
