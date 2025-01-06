import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

import sqlite_vec

from nh_planner.core.config import DB_PATH
from nh_planner.core.models import Movie, MovieWithScreenings, Screening


logger = logging.getLogger(__name__)


INIT_SCHEMA = """
    CREATE TABLE IF NOT EXISTS movies (
        id INTEGER PRIMARY KEY,
        title TEXT,
        duration INTEGER,
        director TEXT,
        genre TEXT,
        production TEXT,
        description TEXT,
        href TEXT,
        UNIQUE(title, director)
    );

    CREATE TABLE IF NOT EXISTS screenings (
        id INTEGER PRIMARY KEY,
        movie_id INTEGER,
        screening_date TEXT,
        FOREIGN KEY(movie_id) REFERENCES movies(id),
        UNIQUE(movie_id, screening_date)
    );

    CREATE TABLE IF NOT EXISTS scraped_dates (
        id INTEGER PRIMARY KEY,
        date TEXT UNIQUE
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS embeddings using vec0(
        movie_id integer primary key,
        embedding float[1024]
    );
    """


class Database:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(INIT_SCHEMA)

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            yield conn
            conn.commit()
        except Exception as e:
            logger.error(f"Database error: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_movie(self, title: str) -> Optional[int]:
        query = """
        SELECT m.id
        FROM movies m INNER JOIN screenings s ON m.id = s.movie_id
        WHERE title = ? AND ABS(CAST(JULIANDAY('now') AS INTEGER) - CAST(JULIANDAY(screening_date) AS INTEGER)) < 5
        ORDER BY ABS(CAST(JULIANDAY('now') AS INTEGER) - CAST(JULIANDAY(screening_date) AS INTEGER))
        LIMIT 1;
        """
        with self.connect() as conn:
            result = conn.execute(query, (title,)).fetchone()
            return result[0] if result else None

    def add_movie(self, movie: Movie) -> int:
        query = """
        INSERT INTO movies (title, duration, director, genre, production, description, href)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(title, director) DO UPDATE SET
            duration=excluded.duration,
            genre=excluded.genre,
            production=excluded.production,
            description=excluded.description,
            href=excluded.href
        RETURNING id
        """
        with self.connect() as conn:
            movie_id = conn.execute(
                query,
                (
                    movie.title,
                    movie.duration,
                    movie.director,
                    movie.genre,
                    movie.production,
                    movie.description,
                    movie.href,
                ),
            ).fetchone()[0]
            return movie_id

    def clear_date_screenings(self, date: str) -> None:
        """Clear all screenings for a specific date"""
        query = """
        DELETE FROM screenings 
        WHERE DATE(screening_date) = DATE(?);
        """
        with self.connect() as conn:
            conn.execute(query, (date,))

    def clear_scraped_date(self, date: str) -> None:
        """Remove date from scraped_dates table"""
        query = "DELETE FROM scraped_dates WHERE date = ?;"
        with self.connect() as conn:
            conn.execute(query, (date,))

    def add_screenings(self, screenings: list[Screening]) -> None:
        query = """
        INSERT INTO screenings (movie_id, screening_date)
        VALUES (?, ?)
        ON CONFLICT(movie_id, screening_date) DO NOTHING
        """
        with self.connect() as conn:
            conn.executemany(query, [(s.movie_id, s.date) for s in screenings])

    def is_date_scraped(self, date: str) -> bool:
        query = "SELECT 1 FROM scraped_dates WHERE date = ?"
        with self.connect() as conn:
            result = conn.execute(query, (date,)).fetchone()
            return bool(result)

    def mark_date_scraped(self, date: str) -> None:
        query = (
            "INSERT INTO scraped_dates (date) VALUES (?) ON CONFLICT(date) DO NOTHING"
        )
        with self.connect() as conn:
            conn.execute(query, (date,))

    def filter_movies(
        self, where_clause: str, params: tuple
    ) -> list[MovieWithScreenings]:
        query = f"""
        SELECT DISTINCT
            m.title,
            m.duration,
            m.director,
            m.genre,
            m.production,
            m.description,
            m.href,
            GROUP_CONCAT(s.screening_date, '\n') as screening_dates
        FROM movies m
        LEFT JOIN screenings s ON m.id = s.movie_id
        WHERE {where_clause}
        GROUP BY m.title, m.duration, m.director, m.genre, m.production, m.description, m.href
        """

        with self.connect() as conn:
            results = conn.execute(query, params).fetchall()

        movies = [
            MovieWithScreenings(
                **{
                    key: row[i]
                    for i, key in enumerate(MovieWithScreenings.model_fields.keys())
                }
            )
            for row in results
        ]
        return movies

    def get_movies_needing_embeddings(self) -> list[tuple[int, str]]:
        query = """
        SELECT id, CONCAT('Gatunek: ', genre, ' Reżyser: ', director, ' Opis: ', description)
        FROM movies 
        WHERE NOT EXISTS (
            SELECT 1 FROM embeddings WHERE movie_id = id
        );
        """
        with self.connect() as conn:
            return conn.execute(query).fetchall()

    def add_movie_embedding(self, movie_id: int, embedding: list[float]) -> None:
        query = """
        INSERT INTO embeddings (movie_id, embedding)
        VALUES (?, ?);
        """
        with self.connect() as conn:
            conn.execute(query, (movie_id, sqlite_vec.serialize_float32(embedding)))

    def get_similar_movies(self, embedding: list[float], limit: int = 5) -> list[MovieWithScreenings]:
        query = """
        SELECT title, duration, director, genre, production, description, href, GROUP_CONCAT(s.screening_date, '\n') as screenings
        FROM movies m
        JOIN embeddings d ON m.id = d.movie_id
        LEFT JOIN screenings s ON m.id = s.movie_id
        WHERE embedding MATCH ?
        AND k = ?
        GROUP BY m.title, m.duration, m.director, m.genre, m.production, m.description, href
        ORDER BY distance;
        """
        with self.connect() as conn:
            results = conn.execute(
                query, (sqlite_vec.serialize_float32(embedding), limit)
            ).fetchall()
            return [
                MovieWithScreenings(
                    **{
                        key: row[i]
                        for i, key in enumerate(MovieWithScreenings.model_fields.keys())
                    }
                )
                for row in results
            ]

    def get_limited_movies(self, limit: int = 5) -> list[MovieWithScreenings]:
        query = f"""
        SELECT title, duration, director, genre, production, description, href, screening as screenings
        FROM movies m inner join (
            SELECT m.id, GROUP_CONCAT(screening_date) as screening, count(*)
            FROM movies m INNER JOIN screenings s ON m.id = s.movie_id
            WHERE screening_date >= CURRENT_DATE
            GROUP BY m.id
            HAVING count(*) <= {limit}
        ) t ON m.id = t.id
        GROUP BY title, duration, director, production, description, href
        """
        with self.connect() as conn:
            results = conn.execute(query).fetchall()

        movies = [
            MovieWithScreenings(
                **{
                    key: row[i]
                    for i, key in enumerate(MovieWithScreenings.model_fields.keys())
                }
            )
            for row in results
        ]
        return movies

    def get_detailed_stats(self) -> dict:
        query = """
        WITH stats AS (
            SELECT 
                COUNT(DISTINCT m.id) as total_movies,
                COUNT(DISTINCT CASE 
                    WHEN s.screening_date >= date('now') 
                    THEN m.id 
                END) as future_movies,
                COUNT(CASE WHEN s.screening_date >= date('now') THEN 1 END) as future_screenings,
                MAX(sd.date) as last_scraped_date
            FROM movies m
            LEFT JOIN screenings s ON m.id = s.movie_id
            CROSS JOIN (SELECT MAX(date) as date FROM scraped_dates) sd
        ),
        popular_movie AS (
            SELECT 
                m.title,
                COUNT(*) as screening_count
            FROM movies m
            JOIN screenings s ON m.id = s.movie_id
            WHERE s.screening_date >= date('now')
            GROUP BY m.id, m.title
            ORDER BY screening_count DESC
            LIMIT 1
        )
        SELECT 
            stats.*,
            pm.title as most_popular,
            pm.screening_count
        FROM stats, popular_movie pm;
        """
        with self.connect() as conn:
            row = conn.execute(query).fetchone()
            return {
                'total_movies': row[0],
                'future_movies': row[1],
                'future_screenings': row[2],
                'last_scraped': row[3],
                'popular_movie': row[4],
                'popular_screenings': row[5]
            }
