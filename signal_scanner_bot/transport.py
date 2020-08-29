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
from . import signal

log = logging.getLogger(__name__)


################################################################################
# Stream listener
################################################################################
class Listener(tweepy.StreamListener):
    def on_status(self, status: tweepy.Status):
        if not env.STATE.LISTENING:
            return

        messages.process_twitter_message(status)


################################################################################
# Twitter-to-signal
################################################################################
def _twitter_to_signal():
    api = twitter.get_api()
    stream = tweepy.Stream(auth=api.auth, listener=Listener())
    log.info("Stream initialized, starting to follow")
    stream.filter(track=twitter.RECEIVE_HASHTAGS)


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
                    messages.process_signal_message(blob, api)
                except Exception:
                    log.error(f"Malformed message: {blob}")
                    raise
            # Check to see if there's any content in stderr
            error = (await proc.stderr.read()).decode()
            for line in error.split("\n"):
                if line.strip():
                    log.warning(f"STDERR: {line}")
            if proc.returncode != 0:
                raise OSError(error)
    except Exception as err:
        signal.panic(err)
        raise
    finally:
        log.info("Killing signal-cli")
        try:
            proc.kill()
        except ProcessLookupError:
            pass
