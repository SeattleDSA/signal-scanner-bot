"""Main module."""
import subprocess
from datetime import datetime
from typing import Dict

import ujson

from . import env


def process_message(blob: Dict) -> None:
    print(f"Got message: {blob}")
    envelope = blob.get("envelope", {})
    if not envelope or "dataMessage" not in envelope:
        print(f"Malformed message: {blob}")

    data = envelope["dataMessage"]
    if data is None or not data.get("message"):
        # No actual message contents
        return

    message = data["message"]
    timestamp = datetime.fromtimestamp(data["timestamp"] / 1000.0)
    print(f"{timestamp.isoformat()}: '{message}'")


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
            process_message(blob)
        # Check to see if there's any content in stderr
        if proc.stderr.peek(10):
            for line in iter(proc.stderr.readline, b""):
                line = line.decode("utf-8").rstrip()
                print(f"STDERR: {line}")
    except Exception:
        print("Killing signal-cli")
        proc.kill()
        raise
