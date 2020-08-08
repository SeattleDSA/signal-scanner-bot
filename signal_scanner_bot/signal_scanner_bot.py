"""Main module."""
import logging
import subprocess

import ujson

from . import env
from . import messages
from . import twitter

log = logging.getLogger(__name__)


def listen_and_print():
    api = twitter.get_api()
    proc = subprocess.Popen(
        ["signal-cli", "-u", env.BOT_NUMBER, "receive", "--json", "-t", "-1"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        for line in iter(proc.stdout.readline, b""):
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
        if proc.stderr.peek(10):
            for line in iter(proc.stderr.readline, b""):
                line = line.decode("utf-8").rstrip()
                log.warning(f"STDERR: {line}")
    finally:
        log.info("Killing signal-cli")
        proc.kill()
