import logging
import subprocess
import traceback
from typing import Optional

from signal_scanner_bot import env


log = logging.getLogger(__name__)


################################################################################
# Send message
################################################################################
def send_message(message: str, recipient: Optional[str], group: bool = False):
    recipient_args = ["-g", str(recipient)] if group else [str(recipient)]
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
    log.info(f"Panicing, attempting to call home at {env.ADMIN_NUMBER}")
    message = f"BOT FAILURE: {err}\n{traceback.format_exc(limit=4)}"
    send_message(message, env.ADMIN_NUMBER)
