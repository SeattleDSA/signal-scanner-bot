import asyncio
import logging

import click

from signal_scanner_bot import env
from signal_scanner_bot.transport import signal_to_twitter, twitter_to_signal


log = logging.getLogger(__name__)

logging.basicConfig(
    format="[%(asctime)s - %(name)s - %(lineno)3d][%(levelname)s] %(message)s",
    level=logging.INFO,
)


@click.command()
@click.option("-d", "--debug", is_flag=True)
def cli(debug: bool) -> None:
    if debug or env.DEBUG:
        logging.getLogger().setLevel(logging.DEBUG)
        env.log_vars()

        # These are super noisy
        for _log in ["requests", "oauthlib", "requests_oauthlib", "urllib3"]:
            logging.getLogger(_log).setLevel(logging.INFO)

    log.info("Listening...")

    loop = asyncio.get_event_loop()
    loop.create_task(signal_to_twitter())
    loop.create_task(twitter_to_signal())
    loop.run_forever()


if __name__ == "__main__":
    cli()
