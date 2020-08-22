"""Main module."""
import asyncio
import logging
import subprocess
import traceback

import tweepy
import ujson

from . import env
from . import messages
from . import twitter

log = logging.getLogger(__name__)


################################################################################
# Stream listener
################################################################################
class Listener(tweepy.StreamListener):

    IS_LISTENING = False

    def on_status(self, status: tweepy.Status):
        # We don't are about retweets
        if not status.is_quote_status and self.IS_LISTENING:
            log.info(f"STATUS RECEIVED: {status.text}")


# Have to make this a global object so that
LISTENER = Listener()


################################################################################
# Panic
################################################################################
def panic(err: Exception) -> None:
    # We don't really care if this succeeds, particularly if there's an issue
    # with the signal config
    log.info(f"Panicing, attempting to call home at {env.ADMIN_NUMBER}")
    message = f"BOT FAILURE: {err}\n{traceback.format_exc(limit=4)}"
    proc = subprocess.run(
        [
            "signal-cli",
            "-u",
            str(env.BOT_NUMBER),
            "send",
            "-m",
            message,
            str(env.ADMIN_NUMBER),
        ],
        capture_output=True,
    )
    if proc.stdout:
        log.info(f"STDOUT: {proc.stdout.decode('utf-8')}")
    if proc.stderr:
        log.warning(f"STDERR: {proc.stderr.decode('utf-8')}")


################################################################################
# Signal-to-twitter
################################################################################
async def signal_to_twitter():
    api = twitter.get_api()
    proc = await asyncio.create_subprocess_shell(
        f"signal-cli -u {env.BOT_NUMBER} receive --json -t -1",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            line = line.decode("utf-8").rstrip()
            blob = ujson.loads(line)
            try:
                response = messages.process_message(blob)
                if response:
                    message, timestamp = response
                    twitter.send_tweet(message, timestamp, api)
            except Exception:
                log.error(f"Malformed message: {blob}")
                raise
        # Check to see if there's any content in stderr
        error = (await proc.stderr.read()).decode()
        for line in error.split("\n"):
            log.warning(f"STDERR: {line}")
        if proc.returncode != 0:
            raise OSError(error)
    except Exception as err:
        panic(err)
    finally:
        log.info("Killing signal-cli")
        try:
            proc.kill()
        except ProcessLookupError:
            pass


################################################################################
# Twitter-to-signal
################################################################################
async def twitter_to_signal():
    api = twitter.get_async_api()
    stream = tweepy.Stream(auth=api.auth, listener=LISTENER)
    stream.filter(track=twitter.RECEIVE_HASHTAGS, is_async=True)
