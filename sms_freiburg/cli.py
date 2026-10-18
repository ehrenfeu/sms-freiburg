"""Command line entry points for the sms-freiburg package."""

from pathlib import Path

import click

from .chore import load_config, scrape_and_publish, setup_logger


@click.command()
@click.option(
    "--config",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    help="Configuration file.",
    default=Path("config.yaml"),
    show_default=True,
)
@click.option(
    "--headless/--no-headless",
    help="Hide browser window. [default: true]",
    type=bool,
    default=True,
)
@click.option("--profile", help="Profile to use from config. [default: <ALL>]")
@click.option("-v", "--verbose", count=True, help="Log verbosity (repeat for more).")
def main(config: Path, headless: bool, profile: str | None, verbose: int) -> None:
    """Parse configuration and CLI flags, run the scraper, publish results."""
    setup_logger(verbose)
    settings, profiles = load_config(config, headless, profile)

    for cur_profile in profiles:
        scrape_and_publish(settings=settings, profile=cur_profile)
