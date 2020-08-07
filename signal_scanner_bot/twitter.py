import tweepy

from . import env


def get_api() -> tweepy.API:
    # Authenticate to Twitter
    auth = tweepy.OAuthHandler(env.TWITTER_API_KEY, env.TWITTER_API_SECRET)
    auth.set_access_token(env.TWITTER_ACCESS_TOKEN, env.TWITTER_TOKEN_SECRET)

    api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
    api.verify_credentials()
    return api
