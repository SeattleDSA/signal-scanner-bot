import logging
import subprocess
import traceback
from typing import Optional

from signal_scanner_bot import env


log = logging.getLogger(__name__)


################################################################################
# Send message
################################################################################
def send_message(message: str, recipient: Optional[str]):
    recipient = recipient or ""
    if recipient.endswith("==") and len(recipient) == 24:
        # Heuristic: this is usually the pattern of group IDs
        group = True
    elif recipient.startswith("+"):
        # Heuristic: this is what phone numbers have to start with
        group = False
    else:
        raise ValueError(f"Supplied recipient is invalid: {recipient}")

    recipient_args = ["-g", recipient] if group else [recipient]
    log.debug("Acquiring signal lock to send")
    with env.SIGNAL_LOCK:
        log.debug("Send lock acquired")
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
        )
    if proc.stdout:
        log.info(f"STDOUT: {proc.stdout.decode('utf-8')}")
    if proc.stderr:
        log.warning(f"STDERR: {proc.stderr.decode('utf-8')}")


################################################################################
# Panic
################################################################################
def panic(err: Exception) -> None:
    # We don't really care if this succeeds, particularly if there's an issue
    # with the signal config
    log.info(f"Panicing, attempting to call home at {env.ADMIN_CONTACT}")
    message = f"BOT FAILURE: {err}\n{traceback.format_exc(limit=4)}"
    send_message(message, env.ADMIN_CONTACT)
