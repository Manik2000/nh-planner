import click

from nh_planner.cli.commands.utils import display_movie
from nh_planner.services.database import Database


@click.command()
@click.option("--limit", "-k", type=int, default=5, help="Number of remaining screenings of a movie")
def list_limited(limit: int):
    """Show movies with less than K screenings"""
    db = Database()
    try:
        movies = db.get_limited_movies(limit)
        for movie in movies:
            display_movie(movie)
    except Exception as e:
        click.echo(f"Error: {e}")
