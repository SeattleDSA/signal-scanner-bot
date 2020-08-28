"""Main module."""
import asyncio
import logging
import subprocess
import concurrent.futures

import tweepy
import ujson

from . import env
from . import messages
from . import twitter
from .signal import panic
from .twitter import LISTENER

log = logging.getLogger(__name__)


################################################################################
# Twitter-to-signal
################################################################################
def _twitter_to_signal():
    api = twitter.get_api()
    stream = tweepy.Stream(auth=api.auth, listener=LISTENER)
    log.info("Stream initialized, starting to follow")
    stream.filter(track=twitter.RECEIVE_HASHTAGS, is_async=True)


async def twitter_to_signal():
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        await loop.run_in_executor(pool, _twitter_to_signal)


################################################################################
# Signal-to-twitter
################################################################################
async def signal_to_twitter():
    api = twitter.get_api()
    try:
        while True:
            log.debug("Acquiring signal lock to listen")
            with env.SIGNAL_LOCK:
                log.debug("Listen lock acquired")
                proc = await asyncio.create_subprocess_shell(
                    f"signal-cli -u {env.BOT_NUMBER} receive --json -t {env.SIGNAL_TIMEOUT}",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            while line := await proc.stdout.readline():
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
