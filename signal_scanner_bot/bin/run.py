import logging

import click

from signal_scanner_bot.signal_scanner_bot import listen_and_print

log = logging.getLogger(__name__)

logging.basicConfig(
    format="[%(asctime)s - %(name)s - %(lineno)3d][%(levelname)s] %(message)s",
    level=logging.INFO,
)


@click.command()
@click.option("-d", "--debug", is_flag=True)
def cli(debug: bool) -> None:
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    log.info("Listening...")
    listen_and_print()


if __name__ == "__main__":
    cli()
