"""Console script for signal_scanner_bot."""
import sys

import click


@click.command()
def main(args=None):
    """Console script for signal_scanner_bot."""
    click.echo(
        "Replace this message by putting your code into " "signal_scanner_bot.cli.main"
    )
    click.echo("See click documentation at https://click.palletsprojects.com/")
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
