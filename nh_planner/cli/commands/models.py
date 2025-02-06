import asyncio

import click
from ollama import Client

from nh_planner.services.database import Database
from nh_planner.services.embeddings import (
    EmbeddingService,
    load_models_config,
    save_models_config,
)


async def ensure_model(model: str) -> bool:
    client = Client()
    try:
        client.show(model=model)
        return True
    except Exception:
        click.echo(f"Model {model} not found. Installing...")
        try:
            await client.pull(model=model)
            return True
        except Exception as e:
            click.echo(f"Failed to install model {model}: {str(e)}")
            return False


@click.group()
def models():
    """Manage Ollama models for chat and embeddings"""
    pass


@models.command()
def show():
    """Show current models configuration"""
    config = load_models_config()
    click.echo(f"Chat model: {config['chat_model']}")
    click.echo(f"Embedding model: {config['embed_model']}")


@models.command()
@click.option("--chat", help="Set chat model")
@click.option("--embed", help="Set embedding model")
@click.option("--force-recalc", is_flag=True, help="Force recalculation of embeddings")
def set(chat: str, embed: str, force_recalc: bool):
    """Set models and optionally recalculate embeddings"""
    config = load_models_config()
    changed = False

    if chat:
        if not asyncio.run(ensure_model(chat)):
            click.echo("Aborting due to chat model installation failure")
            return
        config["chat_model"] = chat
        changed = True
        click.echo(f"Chat model set to {chat}")

    if embed:
        if not asyncio.run(ensure_model(embed)):
            click.echo("Aborting due to embedding model installation failure")
            return
        old_embed = config["embed_model"]
        config["embed_model"] = embed
        changed = True
        click.echo(f"Embedding model set to {embed}")

        if old_embed != embed or force_recalc:
            click.echo("Recalculating embeddings...")

            db = Database()
            with db.connect() as conn:
                conn.execute("DELETE FROM embeddings")

            embedding_service = EmbeddingService(db)
            asyncio.run(embedding_service.process_pending_embeddings())
            click.echo("Embeddings recalculated successfully")

    if changed:
        save_models_config(config)
