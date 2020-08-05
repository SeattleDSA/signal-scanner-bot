"""Main module."""
import logging
import subprocess

import ujson

from . import env
from . import messages

log = logging.getLogger(__name__)


def listen_and_print():
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
                messages.process_message(blob)
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
