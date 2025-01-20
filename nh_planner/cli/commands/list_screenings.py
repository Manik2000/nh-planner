import click

from nh_planner.cli.commands.utils import display_movie
from nh_planner.services.database import Database


@click.command()
@click.argument("k", type=int)
def list_screenings(k: int):
    """Show movies with k screenings"""
    db = Database()
    try:
        movies = db.get_movies_with_k_screenings(k)
        for movie in movies:
            display_movie(movie)
    except Exception as e:
        click.echo(f"Error: {e}")
