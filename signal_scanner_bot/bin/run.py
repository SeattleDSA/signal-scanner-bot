#!/usr/bin/env python
import asyncio
import logging

import click

from signal_scanner_bot import env
from signal_scanner_bot.transport import (
    signal_to_twitter,
    twitter_to_queue,
    queue_to_signal,
)


log = logging.getLogger(__name__)

logging.basicConfig(
    format="[%(asctime)s - %(name)s - %(lineno)3d][%(levelname)s] %(message)s",
    level=logging.INFO,
)


@click.command()
@click.option("-d", "--debug", is_flag=True)
def cli(debug: bool = False) -> None:
    if debug or env.DEBUG:
        logging.getLogger().setLevel(logging.DEBUG)
        env.log_vars()

        # These are super noisy
        for _log in ["requests", "oauthlib", "requests_oauthlib", "urllib3"]:
            logging.getLogger(_log).setLevel(logging.INFO)

    log.info(
        f"Loading Autoscan state: {'Enabled' if env.STATE.LISTENING else 'Disabled'}"
    )
    log.info("Listening...")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        asyncio.gather(
            signal_to_twitter(),
            queue_to_signal(),
            twitter_to_queue(),
            return_exceptions=True,
        )
    )


if __name__ == "__main__":
    cli()
