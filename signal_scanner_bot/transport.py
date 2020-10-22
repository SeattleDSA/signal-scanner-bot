"""Main module."""
import asyncio
import logging
import subprocess
import queue
import concurrent.futures

import tweepy
import ujson

from . import env
from . import messages
from . import twitter
from . import signal

log = logging.getLogger(__name__)


################################################################################
# Stream Listener
################################################################################
class Listener(tweepy.StreamListener):
    """
    Listener implementation for when a status matching the track is received.
    """

    def on_status(self, status: tweepy.Status):
        if not env.STATE.LISTENING:
            return

        messages.process_twitter_message(status)


################################################################################
# Twitter-to-Queue
################################################################################
def _twitter_to_queue():
    """
    Top level function for running the twitter-to-signal loop.
    """
    api = twitter.get_api()
    stream = tweepy.Stream(auth=api.auth, listener=Listener())
    log.info("Twitter stream initialized, starting to follow")
    stream.filter(track=env.RECEIVE_HASHTAGS, stall_warnings=True)


async def twitter_to_queue():
    """
    Asynchronous interface for the twitter-to-signal loop.
    """
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        try:
            await loop.run_in_executor(pool, _twitter_to_queue)
            await asyncio.sleep(5)
        except Exception as err:
            log.error("Exception occurred in the Twitter to Queue pipeline, halting process")
            log.exception(err)
            signal.panic(err)
            env.STATE.STOP_REQUESTED = True
            raise


################################################################################
# Queue-to-Signal
################################################################################
def _queue_to_signal():
    """
    Top level function for running the queue-to-signal loop. Flushes the entire
    queue which might take a while we'll have to see.
    """
    log.debug("Trying to empty Twitter to Signal queue.")
    while not env.TWITTER_TO_SIGNAL_QUEUE.empty():
        try:
            log.debug("Emptying Twitter to Signal queue.")
            message = env.TWITTER_TO_SIGNAL_QUEUE.get_nowait()
            signal.send_message(message, env.LISTEN_CONTACT)
            env.TWITTER_TO_SIGNAL_QUEUE.task_done()
        except queue.Empty():
            log.debug("Queue is empty breaking out of aync loop.")


async def queue_to_signal():
    """
    Asynchronous interface for queue-to-signal loop.
    """
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        try:
            while True:
                await loop.run_in_executor(pool, _queue_to_signal)
                await asyncio.sleep(5)
        except Exception as err:
            log.error("Exception occurred, halting queue to signal process")
            log.exception(err)
            signal.panic(err)
            env.STATE.STOP_REQUESTED = True
            raise


################################################################################
# Signal-to-Twitter
################################################################################
async def signal_to_twitter():
    """
    Top level function for running the signal-to-twitter loop.
    """
    api = twitter.get_api()
    try:
        while not env.STATE.STOP_REQUESTED:
            log.debug("Acquiring lock to listen for Signal messages")
            with env.SIGNAL_LOCK:
                log.debug("Listen lock for Signal messages acquired")
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
            if proc.returncode != 0 and proc.returncode is not None:
                log.warning(f"Something went wrong (error code {proc.returncode})")
    except Exception as err:
        signal.panic(err)
        raise
    finally:
        log.info("Killing signal-cli")
        try:
            proc.kill()
            log.info("signal-cli process killed")
        except ProcessLookupError:
            log.warning("Failed to kill process, moving on.")
            pass
