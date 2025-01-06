import asyncio
import click

from nh_planner.services.database import Database
from nh_planner.services.scraper import Scraper
from nh_planner.services.embeddings import EmbeddingService


@click.command()
@click.argument("days", type=int, default=7)
@click.option("--force", "-f", is_flag=True, help="Force refresh even if data exists")
def refresh(days: int, force: bool):
    """Refresh movie data for the next N days"""
    db = Database()
    scraper = Scraper(db)
    embedding_service = EmbeddingService(db)
    try:
        asyncio.run(scraper.scrape_movies(days, force))
        click.echo(f"Successfully refreshed data for next {days} days")
    except Exception as e:
        click.echo(f"Error during refresh: {e}")
    try:
        asyncio.run(embedding_service.process_pending_embeddings())
        click.echo("Successfully updated embeddings")
    except Exception as e:
        click.echo(f"Error during embeddings update: {e}")
