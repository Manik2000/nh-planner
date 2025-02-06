from datetime import datetime, timedelta

import click

from nh_planner.cli.commands.utils import display_table
from nh_planner.services.database import Database
from nh_planner.services.filters import MovieFilter
from nh_planner.services.get_next_day_date import get_next_day_date


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
@click.option(
    "--day", type=str, default=None, help="Filter by day of week (e.g., Monday, Tue)"
)
def filter(
    title, director, min_duration, max_duration, start_date, end_date, use_fuzzy, day
):
    """Filter movies by various criteria"""
    db = Database()

    if day:
        start_date = get_next_day_date(day)
        if not start_date:
            click.echo(f"Invalid day: {day}")
            return
        end_date = (
            datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=1)
        ).strftime("%Y-%m-%d")

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
