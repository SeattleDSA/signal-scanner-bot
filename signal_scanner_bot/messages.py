import logging
from typing import Dict, Optional

from .filters import FILTERS, message_timestamp

log = logging.getLogger(__name__)


def process_message(blob: Dict) -> Optional[str]:
    log.debug(f"Got message: {blob}")
    envelope = blob.get("envelope", {})
    if not envelope or "dataMessage" not in envelope:
        log.error(f"Malformed message: {blob}")

    data = envelope.get("dataMessage") or {}
    for filter_ in FILTERS:
        if filter_(data):
            return

    message = data["message"]
    timestamp = message_timestamp(data)
    log.info(f"{timestamp.isoformat()}: '{message}'")
    return f"{message} @ {timestamp.strftime('%l:%M:%S%p')}"
