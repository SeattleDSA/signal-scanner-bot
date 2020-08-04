"""Main module."""
import subprocess

from . import env


def listen_and_print():
    proc = subprocess.Popen(
        ["signal-cli", "-u", env.BOT_PHONE_NUMBER, "receive", "--json", "-t", "-1"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    for line in iter(proc.stdout.readline, b""):
        line = line.decode("utf-8").rstrip()
        print(line)
    # Check to see if there's any content in stderr
    if proc.stderr.peek(10):
        for line in iter(proc.stderr.readline, b""):
            line = line.decode("utf-8").rstrip()
            print(f"STDERR: {line}")


if __name__ == '__main__':
    listen_and_print()

