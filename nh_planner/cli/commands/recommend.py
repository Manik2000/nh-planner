import click

from nh_planner.cli.commands.utils import display_movie
from nh_planner.services.database import Database
from nh_planner.services.embeddings import EmbeddingService


@click.command()
@click.argument("description")
@click.option("-k", "--limit", default=5, help="Number of recommendations")
def recommend(description: str, limit: int):
    """Recommend movies based on description"""
    db = Database()
    embedding_service = EmbeddingService(db)

    try:
        click.echo(f"\nFinding {limit} movies matching: {description}")
        movies = embedding_service.find_similar_movies(description, limit)

        if not movies:
            click.echo("No matching movies found.")
            return

        for movie in movies:
            display_movie(movie)
            click.echo("\n")

    except Exception as e:
        click.echo(f"Error: {e}")
