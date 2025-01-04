import asyncio
import os
from datetime import datetime

import click

from nh_planner.cli.utils import (ValidationCheck, create_movie_dicts,
                                  display_movie, display_table, parse_date,
                                  validate_date, validate_duration,
                                  validate_title)
from nh_planner.db.data_models import MovieCard, MovieFilterResult
from nh_planner.db.database import DatabaseManager
from nh_planner.db.dynamic_scrapper import scrape_and_load_movies_into_db
from nh_planner.db.queries import SELECT_MOVIES_WITH_LESS_THAN_N_SCREENINGS
from nh_planner.db.utils import (DateFilter, DurationFilter, Filter,
                                 TitleFilter, build_filter_query)


class Database(DatabaseManager):
    def __init__(self):
        super().__init__()
        self._ensure_db()

    def _ensure_db(self):
        if not os.path.exists(self.db_path):
            self.init_db()


@click.group()
@click.pass_context
def cli(ctx):
    ctx.obj = Database()


@cli.command()
@click.argument("days_ahead", type=int, default=12)
@click.option("--force", "-f", is_flag=True, help="Force refresh")
def refresh(days_ahead, force):
    """Refresh movie data from website"""
    asyncio.run(scrape_and_load_movies_into_db(days_ahead, force_scrape=force))


@cli.command()
@click.pass_obj
@click.option(
    "--start-date", "-s", type=str, default=None, help="Start date (YYYY-MM-DD HH:MM)"
)
@click.option(
    "--end-date", "-e", type=str, default=None, help="End date (YYYY-MM-DD HH:MM)"
)
@click.option(
    "--titles", "-t", type=str, default=None, help="Movie titles for filtering"
)
def filter(cli_obj, start_date, end_date, titles):
    """Filter movies by title, date and duration"""
    if start_date is None:
        start_date = str(datetime.now().strftime("%Y-%m-%d %H:%M"))
    try:
        start_date = parse_date(start_date)
        if end_date is not None:
            end_date = parse_date(end_date)
    except ValueError:
        click.echo("Invalid date format")
        return
    date_validation = validate_date([start_date, end_date])
    if date_validation.result == ValidationCheck.INVALID:
        click.echo(date_validation.message)
        return
    if titles is not None:
        titles_validation = validate_title(titles)
        if titles_validation.result == ValidationCheck.INVALID:
            click.echo(titles_validation.message)
            return
        titles = titles.split(",")
    query = build_filter_query(
        Filter(
            title=TitleFilter(title=titles) if titles else None,
            date=DateFilter(start_date=start_date, end_date=end_date),
        )
    )
    results = cli_obj.execute_query(query)
    movie_details = create_movie_dicts(results, MovieFilterResult)
    display_table(movie_details)


@cli.command()
@click.pass_obj
@click.option(
    "--min-duration", "-min", type=int, default=None, help="Minimum movie duration"
)
@click.option(
    "--max-duration", "-max", type=int, default=None, help="Maximum movie duration"
)
def filter_by_duration(cli_obj, min_duration, max_duration):
    """Filter movies by duration"""
    validation = validate_duration([min_duration, max_duration])
    if validation.result == ValidationCheck.INVALID:
        click.echo(validation.message)
        return
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    query = build_filter_query(
        Filter(
            duration=DurationFilter(
                min_duration=min_duration, max_duration=max_duration
            ),
            date=DateFilter(start_date=today),
        )
    )
    results = cli_obj.execute_query(query)
    movie_details = create_movie_dicts(results, MovieFilterResult)
    display_table(movie_details)


@cli.command()
@click.pass_obj
@click.argument("custom_query", type=str)
def query(cli_obj, custom_query):
    """Execute a custom SQL query"""
    try:
        response = cli_obj.execute_query(custom_query)
        click.echo(response)
    except Exception as e:
        click.echo(f"Error executing query: {e}")


@cli.command()
@click.pass_obj
@click.option("-n", type=int, default=3, help="Number of remaining movie screenings")
def show_rare(cli_obj, n):
    """Display movies with less than n screenings"""
    results = cli_obj.execute_query(
        query=SELECT_MOVIES_WITH_LESS_THAN_N_SCREENINGS, params=(n,)
    )
    movie_details = create_movie_dicts(results, MovieCard)
    for movie in movie_details:
        display_movie(movie)
