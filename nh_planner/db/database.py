import sqlite3
from contextlib import contextmanager
from typing import Generator

from nh_planner.config import DB_PATH
from nh_planner.db.data_models import MovieDetails
from nh_planner.db.queries import (CREATE_MOVIES_SCREENINGS_TABLE,
                                   CREATE_MOVIES_TABLE,
                                   CREATE_SCRAPED_DATES_TABLE, GET_MOVIE_ID,
                                   INSERT_MOVIE, INSERT_SCRAPED_DATE,
                                   INSERT_SCREENINGS, SELECT_IF_SCRAPED_DATES)
from nh_planner.db.utils import create_levenshtein_function


class DatabaseManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    @contextmanager
    def get_cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        create_levenshtein_function(conn)
        try:
            c = conn.cursor()
            yield c
            conn.commit()
        finally:
            conn.commit()
            conn.close()

    def init_db(self) -> None:
        """Create the database tables"""
        with self.get_cursor() as cursor:
            cursor.execute(CREATE_MOVIES_TABLE)
            cursor.execute(CREATE_MOVIES_SCREENINGS_TABLE)
            cursor.execute(CREATE_SCRAPED_DATES_TABLE)

    def execute_query(self, query: str, params: tuple = ()) -> list:
        """Execute a query and return results"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def insert_query(self, query: str, params: tuple = ()) -> None:
        """Insert data into the database"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)


class DatabaseScrapingManager(DatabaseManager):
    def __init__(self):
        super().__init__()

    def is_scraped(self, date: str) -> bool:
        with self.get_cursor() as c:
            c.execute(SELECT_IF_SCRAPED_DATES, (date,))
            return c.fetchone() is not None

    def movie_exists_in_db(self, title: str) -> bool:
        with self.get_cursor() as c:
            c.execute(GET_MOVIE_ID, (title,))
            return c.fetchone() is not None

    def insert_movie(self, movie_details: MovieDetails) -> None:
        with self.get_cursor() as c:
            c.execute(
                INSERT_MOVIE,
                tuple(movie_details.values()),
            )

    def get_movie_id(self, title: str) -> int:
        with self.get_cursor() as c:
            c.execute(GET_MOVIE_ID, (title,))
            return c.fetchone()[0]

    def insert_screenings(self, movie_id: int, dates: list[str]) -> None:
        with self.get_cursor() as c:
            c.executemany(
                INSERT_SCREENINGS,
                [(movie_id, date) for date in dates],
            )

    def insert_scraped_date(self, date: str) -> None:
        with self.get_cursor() as c:
            c.execute(INSERT_SCRAPED_DATE, (date,))
