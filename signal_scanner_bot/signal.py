import logging
import subprocess
import traceback
from datetime import datetime
from typing import Dict, List

from . import env


log = logging.getLogger(__name__)


################################################################################
# Private Functions
################################################################################
def _check_group(recipient: str) -> bool:
    """
    Function to check whether a supplied recipient string is in the phone number
    or group format.
    """
    if recipient.endswith("=") and len(recipient) in {24, 44}:
        # Heuristic: this is usually the pattern of group IDs
        return True
    elif recipient.startswith("+"):
        # Heuristic: this is what phone numbers have to start with
        return False
    else:
        raise ValueError(f"Supplied recipient is invalid: {recipient}")


################################################################################
# Public Functions
################################################################################
def message_timestamp(data: Dict) -> datetime:
    """
    Function to extract the timestamp from a Signal message and convert it to
    a proper datetime object.
    """
    try:
        timestamp_milliseconds = data["timestamp"]
    except KeyError as err:
        raise KeyError(f"Timestamp field is not present in data: {data}") from err

    dt = datetime.fromtimestamp(timestamp_milliseconds / 1000.0)
    return dt


def list_identities() -> List[str]:
    """
    Function that calls the signal-cli `listIdentities` command and returns the entire result as a string
    """
    proc = subprocess.run(
        ["signal-cli", "-u", str(env.BOT_NUMBER), "listIdentities"],
        capture_output=True,
        text=True,
    )
    if proc.stderr:
        log.warning(f"STDERR: {proc.stderr}")
    if proc.stdout:
        return proc.stdout.split("\n")
    else:
        return []


def trust_identity(phone_number: str, safety_number: str):
    """
    Function that calls the signal-cli `trust` command for the provided phone + safety numbers
    """
    proc = subprocess.run(
        [
            "signal-cli",
            "-u",
            str(env.BOT_NUMBER),
            "trust",
            phone_number,
            "-v",
            f'"{safety_number}"',
        ],
        capture_output=False,
        text=True,
    )
    if proc.stderr:
        log.error(f"STDERR: {proc.stderr}")
    if proc.returncode != 0:
        log.error(f"Trust call return code: {proc.returncode}")


def send_message(message: str, recipient: str):
    """
    High level function to send a Signal message to a specified recipient.
    """
    group = _check_group(recipient)
    recipient_args = ["-g", recipient] if group else [recipient]

    log.debug("Sending message")
    proc = subprocess.run(
        [
            "signal-cli",
            "-u",
            str(env.BOT_NUMBER),
            "send",
            "-m",
            message,
            *recipient_args,
        ],
        capture_output=True,
        text=True,
    )
    if proc.stdout:
        log.info(f"STDOUT: {proc.stdout}")
    if proc.stderr:
        log.warning(f"STDERR: {proc.stderr}")


################################################################################
# Panic?!?!?!?!
################################################################################
def panic(err: Exception) -> None:
    # We don't really care if this succeeds, particularly if there's an issue
    # with the signal config
    log.info(f"Panicing, attempting to call home at {env.ADMIN_CONTACT}")
    message = f"BOT FAILURE: {err}\n{traceback.format_exc(limit=4)}"
    send_message(message, env.ADMIN_CONTACT)
