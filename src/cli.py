import os

import click

from src.db import init_db
from src.dynamic_scrapper import scrape_and_load_movies_into_db


class CLI:
    def __init__(self):
        self.db_path = os.path.expanduser("~/.config/kinonh/kinonh.db")
        self._ensure_db()

    def _ensure_db(self):
        if not os.path.exists(self.db_path):
            init_db()

    def refresh(self, days_ahead: int):
        scrape_and_load_movies_into_db(days_ahead)


@click.group()
@click.pass_context
def cli(ctx):
    ctx.obj = CLI()


@cli.command()
@click.pass_obj
@click.argument("days_ahead", type=int, default=12)
def refresh(cli_obj, days_ahead: int):
    """Refresh movie data from website"""
    cli_obj.refresh(days_ahead)
