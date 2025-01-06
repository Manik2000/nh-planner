import click

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
            click.echo("\n" + "=" * 50)
            click.echo(f"Title: {movie[0]}")
            click.echo(f"Duration: {movie[1]} min")
            click.echo(f"Director: {movie[2]}")
            click.echo(f"Genre: {movie[3]}")
            if movie[4]:  # screenings
                click.echo("\nScreenings:")
                for screening in movie[4].split(","):
                    click.echo(f"  - {screening}")

    except Exception as e:
        click.echo(f"Error: {e}")
