"""Main module."""
import asyncio
import logging
import subprocess

from peony import events
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


async def twitter_to_queue():
    log.info("Starting Twitter Event Stream")
    stream_obj = env.CLIENT.stream.statuses.filter.post(
        follow=",".join(env.TRUSTED_TWEETERS)
    )
    async with stream_obj as stream:
        async for data in stream:
            if events.on_connect(data):
                log.info("Connected to the stream")
            elif events.on_tweet(data) and env.STATE.LISTENING:
                if _filter_hashtags(data, env.RECEIVE_HASHTAGS):
                    await messages.process_twitter_message(data)


################################################################################
# Queue-to-Signal
################################################################################
async def queue_to_signal():
    """
    Top level function for running the queue-to-signal loop. Flushes the entire
    queue which might take a while we'll have to see.
    """
    while True:
        log.debug("Trying to empty Twitter to Signal queue.")
        while not env.TWITTER_TO_SIGNAL_QUEUE.empty():
            try:
                log.debug("Emptying Twitter to Signal queue.")
                message = await env.TWITTER_TO_SIGNAL_QUEUE.get()
                signal.send_message(message, env.LISTEN_CONTACT)
                env.TWITTER_TO_SIGNAL_QUEUE.task_done()
            except asyncio.QueueEmpty:
                log.debug("Queue is empty breaking out of async loop.")
            except Exception as err:
                log.error("Exception occurred, halting queue to signal process")
                log.exception(err)
                signal.panic(err)
                env.STATE.STOP_REQUESTED = True
                raise
        await asyncio.sleep(1)


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
                    await messages.process_signal_message(blob, env.CLIENT)
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
