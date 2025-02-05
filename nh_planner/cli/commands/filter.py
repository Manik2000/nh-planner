from datetime import datetime

import click

from nh_planner.cli.commands.utils import display_table
from nh_planner.services.database import Database
from nh_planner.services.filters import MovieFilter


@click.command()
@click.option("--title", "-t", type=str, default=None, help="Filter by movie title")
@click.option("--director", "-d", type=str, default=None, help="Filter by director")
@click.option(
    "--min-duration", type=int, default=None, help="Minimum duration in minutes"
)
@click.option(
    "--max-duration", type=int, default=None, help="Maximum duration in minutes"
)
@click.option(
    "--start_date",
    "-s",
    type=str,
    default=datetime.now().strftime("%Y-%m-%d %H:%M"),
    help="Start date",
)
@click.option("--end_date", "-e", type=str, default=None, help="End date")
@click.option("--use-fuzzy", is_flag=True, help="Use fuzzy search")
def filter(
    title, director, min_duration, max_duration, start_date, end_date, use_fuzzy
):
    """Filter movies by various criteria"""
    db = Database()

    filter_params = MovieFilter(
        title=title,
        director=director,
        min_duration=min_duration,
        max_duration=max_duration,
        start_date=start_date,
        end_date=end_date,
        use_fuzzy=use_fuzzy,
    )

    try:
        movies = db.filter_movies(*filter_params.to_sql())
        display_table(movies)
    except Exception as e:
        click.echo(f"Error: {e}")
