import os
import sqlite3
from contextlib import contextmanager
from typing import Any

from src.constants import DB_PATH, MovieDetails


@contextmanager
def get_cursor():
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        yield c
    finally:
        conn.commit()
        conn.close()


CREATE_MOVIES_TABLE = """
    CREATE TABLE IF NOT EXISTS movies (
        id INTEGER PRIMARY KEY,
        title TEXT,
        duration INTEGER,
        director TEXT,
        genre TEXT,
        production TEXT,
        description TEXT,
        UNIQUE(title)
    );
"""

CREATE_MOVIES_SCREENINGS_TABLE = """
    CREATE TABLE IF NOT EXISTS movies_screenings (
        id INTEGER PRIMARY KEY,
        movie_id INTEGER,
        screening_date TEXT,
        FOREIGN KEY(movie_id) REFERENCES movies(id)
        UNIQUE(movie_id, screening_date)
    );
"""

CREATE_SCRAPED_DATES_TABLE = """
    CREATE TABLE IF NOT EXISTS scraped_dates (
        id INTEGER PRIMARY KEY,
        scraped_date TEXT
    );
"""


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_cursor() as c:
        c.execute(CREATE_MOVIES_TABLE)
        c.execute(CREATE_MOVIES_SCREENINGS_TABLE)
        c.execute(CREATE_SCRAPED_DATES_TABLE)


def is_scraped(date: str) -> bool:
    with get_cursor() as c:
        c.execute("SELECT * FROM scraped_dates WHERE scraped_date = ?", (date,))
        return c.fetchone() is not None


def movie_exists_in_db(title: str) -> bool:
    with get_cursor() as c:
        c.execute("SELECT * FROM movies WHERE title = ?", (title,))
        return c.fetchone() is not None


def insert_movie(movie_details: MovieDetails) -> None:
    with get_cursor() as c:
        c.execute(
            "INSERT INTO movies (title, duration, director, genre, production, description) VALUES (?, ?, ?, ?, ?, ?)",
            (
                movie_details["title"],
                movie_details["duration"],
                movie_details["director"],
                movie_details["genre"],
                movie_details["production"],
                movie_details["description"],
            ),
        )


def get_movie_id(title: str) -> int:
    with get_cursor() as c:
        c.execute("SELECT id FROM movies WHERE title = ?", (title,))
        return c.fetchone()[0]


def insert_screenings(movie_id: int, dates: list[str]) -> None:
    with get_cursor() as c:
        c.executemany(
            "INSERT INTO movies_screenings (movie_id, screening_date) VALUES (?, ?)",
            [(movie_id, date) for date in dates],
        )


def insert_scraped_date(date: str) -> None:
    with get_cursor() as c:
        c.execute("INSERT INTO scraped_dates (scraped_date) VALUES (?)", (date,))


def execute_sql_query(sql_query: str, params: tuple[Any]) -> list[tuple[Any]]:
    with get_cursor() as c:
        c.execute(sql_query, params)
        return c.fetchall()
