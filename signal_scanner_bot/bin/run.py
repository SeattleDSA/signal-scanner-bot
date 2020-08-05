import logging

from signal_scanner_bot.signal_scanner_bot import listen_and_print

log = logging.getLogger(__name__)


if __name__ == "__main__":
    logging.basicConfig(
        format="[%(asctime)s - %(name)s - %(lineno)3d][%(levelname)s] %(message)s",
        level=logging.DEBUG,
    )
    log.info("Listening...")
    listen_and_print()
