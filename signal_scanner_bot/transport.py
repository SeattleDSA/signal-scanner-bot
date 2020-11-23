"""Main module."""
import pprint
import asyncio
import logging
import subprocess
import concurrent.futures

import peony
import ujson

from . import env
from . import messages
from . import signal

log = logging.getLogger(__name__)


################################################################################
# Twitter-to-Queue
################################################################################
def _filter_hashtags(data, filter_hashtag_list):
    for input_hashtag in data["entities"]["hashtags"]:
        if input_hashtag["text"] in filter_hashtag_list:
            return True
    return False


class Stream(peony.PeonyClient):
    """
    Base class for the Event Stream
    Nothing is changed here as we are not editing the base class
    """

    pass


@Stream.event_stream
class UserStream(peony.EventStream):
    async def stream_request(self):
        """
        Basic stream set up
        """
        await self.api.client.stream.statuses.filter.post(
            follow=",".join(env.TRUSTED_TWEETERS)
        )

    @peony.events.on_connected.handler
    def connection(self):
        """
        Action to perform on connection
        """
        print("Connected to Twitter Stream API")

    @peony.events.on_retweeted_status.handler
    async def on_retweet(self, data):
        """
        Filter tweets from followed users on specified hashtags
        Execute something (send to Signal or whatever)
        """
        pass

    @peony.events.on_tweet.handler
    async def on_tweet(self, data):
        """
        Filter tweets from followed users on specified hashtags
        Execute something (send to Signal or whatever)
        """
        print("Got a tweet\n\n\n\n\n")
        if _filter_hashtags(data, env.RECEIVE_HASHTAGS):
            pprint.pprint(data)

    @peony.events.reconnecting_in.handler
    async def reconnecting(self, data):
        """
        Action to perform on reconnect
        """
        print("reconnecting in %ss" % data.reconnecting_in)

    @peony.events.on_restart.handler
    async def restart_notice(self):
        """
        Action to perform on reconnect
        """
        print("*Stream restarted*\n" + "-" * 10)
        await self.api.client.stream.statuses.filter.post(
            follow=",".join(env.TRUSTED_TWEETERS)
        )

    @peony.events.on_dm.handler
    async def direct_message(self, data):
        pass

    @peony.events.friends.handler
    async def pass_friends(self):
        pass

    @peony.events.default.handler
    async def default(self, data):
        pass


async def twitter_to_queue():
    log.info("Starting Twitter Event Stream")
    stream = peony.PeonyClient(**env.API_KEYS)
    stream.run()


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
        except asyncio.QueueEmpty:
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
                    messages.process_signal_message(blob, env.CLIENT)
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
