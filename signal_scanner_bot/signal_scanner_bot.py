"""Main module."""
import logging
import subprocess
import traceback

import ujson

from . import env
from . import messages
from . import twitter

log = logging.getLogger(__name__)


def panic(err: Exception) -> None:
    # We don't really care if this succeeds, particularly if there's an issue
    # with the signal config
    log.info(f"Panicing, attempting to call home at {env.ADMIN_NUMBER}")
    message = f"BOT FAILURE: {err}\n{traceback.format_exc(limit=4)}"
    proc = subprocess.run(
        ["signal-cli", "-u", env.ADMIN_NUMBER, "send", "-m", message, env.ADMIN_NUMBER],
        capture_output=True,
    )
    if proc.stdout:
        log.info(f"STDOUT: {proc.stdout.decode('utf-8')}")
    if proc.stderr:
        log.warning(f"STDERR: {proc.stderr.decode('utf-8')}")


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
            proc.stderr.seek(0)
            if proc.returncode != 0:
                raise OSError(proc.stderr.read().decode("utf-8"))
    except Exception as err:
        panic(err)
    finally:
        log.info("Killing signal-cli")
        proc.kill()
