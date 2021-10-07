"""Main module."""
import asyncio
import logging
import subprocess
from datetime import date, datetime, timedelta

import ujson
from peony import events

from . import env, messages, signal, swat_alert


log = logging.getLogger(__name__)


################################################################################
# Twitter-to-Queue
################################################################################
def _filter_hashtags(data, filter_hashtag_list):
    for input_hashtag in data["entities"]["hashtags"]:
        if input_hashtag["text"].lower() in filter_hashtag_list:
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
                if (
                    _filter_hashtags(data, env.RECEIVE_HASHTAGS)
                    and data["user"]["id_str"] in env.TRUSTED_TWEETERS
                ):
                    await messages.process_twitter_message(data)


################################################################################
# Queue-to-Signal
################################################################################
async def queue_to_signal():
    """Run the queue-to-signal loop. Flushes the entire queue on each call."""
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
    """Run the signal-to-twitter loop."""
    try:
        while not env.STATE.STOP_REQUESTED:
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


################################################################################
# Comradely Reminder
################################################################################
async def comradely_reminder() -> None:
    """Run the comradely reminder loop."""
    # Wait for system to initialize...
    await asyncio.sleep(15)
    try:
        window_start = env.COMRADELY_TIME
        # Can't do arithmetic with python time objects...
        # So we have to convert it into a datetime, add the timedelta, then swap
        # it back to a time object
        window_end = (
            datetime.combine(date(1, 1, 1), window_start) + timedelta(hours=1)
        ).time()
        while True:
            now = datetime.now().time()
            log.debug(f"Now: {now.isoformat()} | Start: {window_start.isoformat()}")
            # Check if we're currently within a 1-hour time window
            if window_start <= now < window_end:
                log.debug("Within time window")
                await messages.send_comradely_reminder()
            # Wait at least 60 minutes for the next check
            log.debug("Waiting an hour...")
            await asyncio.sleep(60 * 60)
    except Exception as err:
        log.exception(err)
        signal.panic(err)
        raise


################################################################################
# SWAT Alert
################################################################################
async def swat_alert() -> None:
    """Run the swat alert loop."""
    # Wait for system to initialize
    await asyncio.sleep(15)
    try:
        while True:
            log.debug("Checking for SWAT activity.")
            swat_alert_message = swat_alert.check_swat_calls()
            if swat_alert_message:
                log.info("SWAT activity found sending alert to group.")
                messages.send_swat_alert(swat_alert_message)
            # Wait a minute to poll again
            log.debug("Sleeping for 1 minute before checking again.")
            await asyncio.sleep(60)
    except Exception as err:
        log.exception(err)
        signal.panic(err)
        raise
