import logging
from datetime import datetime
from typing import Dict

from . import env

log = logging.getLogger(__name__)


def process_message(blob: Dict) -> None:
    log.debug(f"Got message: {blob}")
    envelope = blob.get("envelope", {})
    if not envelope or "dataMessage" not in envelope:
        log.error(f"Malformed message: {blob}")

    data = envelope.get("dataMessage") or {}
    if any(
        [
            # No actual message contents
            not data.get("message"),
            # If listen group is defined and there's not group info
            (env.LISTEN_GROUP and "groupInfo" not in data),
            # Listen group is defined but ID doesn't match
            (
                "groupInfo" in data
                and data["groupInfo"]
                and env.LISTEN_GROUP
                and data["groupInfo"].get("groupId") != env.LISTEN_GROUP
            ),
        ]
    ):
        return

    message = data["message"]
    timestamp = datetime.fromtimestamp(data["timestamp"] / 1000.0)
    log.info(f"{timestamp.isoformat()}: '{message}'")
