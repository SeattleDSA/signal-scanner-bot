import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

from .filters import SIGNAL_FILTERS, message_timestamp

log = logging.getLogger(__name__)


def process_message(blob: Dict) -> Optional[Tuple[str, datetime]]:
    log.debug(f"Got message: {blob}")
    envelope = blob.get("envelope", {})
    if not envelope or "dataMessage" not in envelope:
        log.error(f"Malformed message: {blob}")

    data = envelope.get("dataMessage") or {}
    for filter_ in SIGNAL_FILTERS:
        filt_value = filter_(data)
        log.debug(f"{filter_}={filt_value}")
        if filt_value:
            return None

    message = data["message"]
    timestamp = message_timestamp(data, convert=True)
    log.info(f"{timestamp.isoformat()}: '{message}'")
    return message, timestamp
