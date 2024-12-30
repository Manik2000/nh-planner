import os
from datetime import datetime, timedelta

import click
from rich.console import Console
from rich.table import Table
from rich import box

from src.db import init_db, execute_sql_query
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

    def get_movies_by_date_range(self, start_date: str, end_date: str):
        query = """
        SELECT 
            m.title,
            m.duration,
            m.director,
            m.genre,
            m.production,
            GROUP_CONCAT(ms.screening_date) as screening_dates
        FROM movies m
        JOIN movies_screenings ms ON m.id = ms.movie_id
        WHERE ms.screening_date BETWEEN ? AND ?
        GROUP BY m.id
        ORDER BY ms.screening_date
        """
        return execute_sql_query(query, (start_date, end_date))

    def display_movies(self, start_date: str, end_date: str):
        console = Console()
        movies = self.get_movies_by_date_range(start_date, end_date)
        
        table = Table(
            show_header=True,
            header_style="bold magenta",
            box=box.ROUNDED,
            title=f"Movies from {start_date} to {end_date}",
            title_style="bold cyan"
        )
        
        table.add_column("Title", style="cyan", no_wrap=True)
        table.add_column("Duration", style="green")
        table.add_column("Director", style="yellow")
        table.add_column("Genre", style="blue")
        table.add_column("Production", style="magenta")
        table.add_column("Screening Dates", style="red")
        
        for movie in movies:
            title, duration, director, genre, production, screening_dates = movie
            table.add_row(
                title,
                f"{duration} min" if duration else "N/A",
                director or "N/A",
                genre or "N/A",
                production or "N/A",
                screening_dates.replace(",", "\n")
            )
        
        console.print(table)


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


@cli.command()
@click.pass_obj
@click.option('--start-date', '-s', type=str, default=None, 
              help='Start date (YYYY-MM-DD)')
@click.option('--end-date', '-e', type=str, default=None,
              help='End date (YYYY-MM-DD)')
def show(cli_obj, start_date, end_date):
    """Display movies between specified dates"""
    if not start_date:
        start_date = datetime.now().strftime('%Y-%m-%d')
    if not end_date:
        end_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
    cli_obj.display_movies(start_date, end_date)
