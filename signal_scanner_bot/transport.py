"""Main module."""
import asyncio
import logging
import re
import subprocess
from asyncio import IncompleteReadError
from datetime import datetime, timedelta, date
from typing import Dict

from peony import events

from . import env
from . import messages
from . import signal

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
# Pull out the important bits, all other messages are ignored
HOTFIX_REGEX = re.compile(
    """.*
Timestamp: (?P<timestamp>.*?) .*
.*?
Body: (?P<message>.*?)
Group info:
  Id: (?P<groupId>.*?)
.*
""",
    flags=re.MULTILINE | re.DOTALL,
)


def _hotfix_convert_to_dict(text: str) -> Dict:
    """
    Hotfix to maintain JSON message format
    """
    if match := HOTFIX_REGEX.match(text):
        log.debug(f"MATCH GROUPS: {match.groups()}")
        d = match.groupdict()
        return {
            "envelope": {
                "dataMessage": {
                    "message": d["message"],
                    "timestamp": int(d["timestamp"]),
                    "groupInfo": {"groupId": d["groupId"]},
                }
            }
        }
    return {}


async def signal_to_twitter():
    """
    Top level function for running the signal-to-twitter loop.
    """
    try:
        while not env.STATE.STOP_REQUESTED:
            log.debug("Listening on signal")
            # TODO: re-enable JSON
            proc = await asyncio.create_subprocess_shell(
                f"signal-cli -u {env.BOT_NUMBER} receive -t {env.SIGNAL_TIMEOUT}",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            try:
                # V2 non-json messages are separated by two newlines
                while line := await proc.stdout.readuntil(separator=b"\n\n"):
                    line = line.decode("utf-8").rstrip()
                    log.debug(f"MESSAGE LINE: {line}")
                    blob = _hotfix_convert_to_dict(line)
                    if not blob:
                        continue
                    try:
                        await messages.process_signal_message(blob, env.CLIENT)
                    except Exception:
                        log.error(f"Malformed message: {blob}")
                        raise
            except IncompleteReadError:
                # If nothing is read this error will be thrown, it can be safely ignored
                pass
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
    """
    Top level function for running the comradely reminder loop
    """
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
