import asyncio
import os
from datetime import datetime, timedelta

import click
from sqlite_vec import serialize_float32
from tqdm import tqdm

from nh_planner.cli.utils import (ValidationCheck, create_movie_dicts,
                                  display_movie, display_table, parse_date,
                                  validate_date, validate_duration,
                                  validate_title)
from nh_planner.db.data_models import MovieCard, MovieFilterResult
from nh_planner.db.database import DatabaseManager
from nh_planner.db.dynamic_scrapper import scrape_and_load_movies_into_db
from nh_planner.db.queries import (GET_MOVIE_ID_FOR_EMDED, INSERT_VECTOR,
                                   SELECT_MOVIES_ABOVE_THRESHOLD,
                                   SELECT_MOVIES_WITH_LESS_THAN_N_SCREENINGS)
from nh_planner.db.utils import (DateFilter, DirectorFilter, DurationFilter,
                                 Filter, TitleFilter, build_filter_query)
from nh_planner.llm.utils import process_texts, sync_embed


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
@click.pass_obj
@click.argument("days_ahead", type=int, default=12)
@click.option("--force", "-f", is_flag=True, help="Force refresh even if data for given date exists")
def refresh(cli_obj, days_ahead, force):
    """Scrape movie data from cinema website and load into database"""
    asyncio.run(scrape_and_load_movies_into_db(days_ahead, force_scrape=force))
    movies_id_for_embedd = cli_obj.execute_query(GET_MOVIE_ID_FOR_EMDED)
    movie_ids = [movie[0] for movie in movies_id_for_embedd if movie[1]]
    descriptions = [movie[1] for movie in movies_id_for_embedd if movie[1]]
    embeddings = asyncio.run(process_texts(descriptions))
    for movie_id, vector in tqdm(zip(movie_ids, embeddings)):
        cli_obj.insert_query(INSERT_VECTOR, (movie_id, serialize_float32(vector)))


@cli.command()
@click.pass_obj
@click.option(
    "--start-date", "-s", type=str, default=None, help="Start date (YYYY-MM-DD HH:MM)"
)
@click.option(
    "--end-date", "-e", type=str, default=None, help="End date (YYYY-MM-DD HH:MM)"
)
@click.option(
    "--title", "-t", type=str, default=None, help="Movie titles for filtering"
)
@click.option(
    "--director", "-d", type=str, default=None, help="Movie director for filtering"
)
@click.option(
    "--search-type",
    "-st",
    type=click.Choice(["fuzzy", "exact"], case_sensitive=False),
    default="fuzzy",
    help="Search type for title and director",
)
def filter(cli_obj, start_date, end_date, title, director, search_type):
    """Filter movies by title, director and date"""
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
    if title is not None:
        title_validation = validate_title(title)
        if title_validation.result == ValidationCheck.INVALID:
            click.echo(title_validation.message)
            return
        title = title.split(",")
    if director is not None:
        director_validation = validate_title(director)
        if director_validation.result == ValidationCheck.INVALID:
            click.echo(director_validation.message)
            return
        director = director.split(",")
    query = build_filter_query(
        Filter(
            title=TitleFilter(title=title, search_type=search_type) if title else None,
            date=DateFilter(start_date=start_date, end_date=end_date),
            director=DirectorFilter(director=director, search_type=search_type)
            if director
            else None,
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
@click.option(
    "--horizon", "-h", type=int, default=10, help="Number of days to look ahead"
)
def filter_by_duration(cli_obj, min_duration, max_duration, horizon):
    """Filter movies by duration"""
    validation = validate_duration([min_duration, max_duration])
    if validation.result == ValidationCheck.INVALID:
        click.echo(validation.message)
        return
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    end_date = (datetime.now() + timedelta(days=horizon)).strftime("%Y-%m-%d %H:%M")
    query = build_filter_query(
        Filter(
            duration=DurationFilter(
                min_duration=min_duration, max_duration=max_duration
            ),
            date=DateFilter(start_date=today, end_date=end_date),
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


@cli.command()
@click.pass_obj
@click.argument("user_descr", type=str)
@click.option("-k", type=int, default=5, help="Number of recommendations")
def recommend(cli_obj, user_descr, k):
    """Recommend movies based on user description"""
    user_vec = sync_embed(user_descr)
    results = cli_obj.execute_query(
        SELECT_MOVIES_ABOVE_THRESHOLD,
        (serialize_float32(user_vec), k),
    )
    movie_details = create_movie_dicts(results, MovieCard)
    for movie in movie_details:
        display_movie(movie)
