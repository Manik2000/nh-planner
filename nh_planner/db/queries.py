# Create the database tables
CREATE_MOVIES_TABLE = """
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
    """

CREATE_MOVIES_SCREENINGS_TABLE = """
    CREATE TABLE IF NOT EXISTS movies_screenings (
        id INTEGER PRIMARY KEY,
        movie_id INTEGER,
        screening_date TEXT,
        FOREIGN KEY(movie_id) REFERENCES movies(id),
        UNIQUE(movie_id, screening_date)
    );
    """

CREATE_SCRAPED_DATES_TABLE = """
    CREATE TABLE IF NOT EXISTS scraped_dates (
        id INTEGER PRIMARY KEY,
        scraped_date TEXT,
        UNIQUE(scraped_date)
    );
    """

CREATE_EMBEDDINGS_TABLE = """
    CREATE VIRTUAL TABLE IF NOT EXISTS descr_vecs using vec0(
        movie_id integer primary key,
        descr_embedding float[1024]
    );
    """

# Queries for scraping
SELECT_IF_SCRAPED_DATES = """
    SELECT scraped_date FROM scraped_dates 
    WHERE scraped_date = ?
    """

GET_MOVIE_ID = """
    SELECT distinct(m.id) FROM movies m
    LEFT JOIN movies_screenings ms ON m.id = ms.movie_id
    WHERE title = ?
    AND ABS(current_date - COALESCE(ms.screening_date, current_date) < 7);
    """

INSERT_MOVIE = """
    INSERT INTO movies 
    (title, duration, director, genre, production, description, href) 
    VALUES (?, ?, ?, ?, ?, ?, ?) 
    ON CONFLICT(title, director) DO NOTHING
    """

INSERT_SCREENINGS = """
    INSERT INTO movies_screenings
    (movie_id, screening_date) VALUES (?, ?)
    ON CONFLICT(movie_id, screening_date) DO NOTHING
    """

INSERT_SCRAPED_DATE = """
    INSERT INTO scraped_dates
    (scraped_date) VALUES (?)
    ON CONFLICT(scraped_date) DO NOTHING
    """


# Queries for cli app commands
GET_MOVIE_ID_FOR_EMDED = """
    SELECT id, CONCAT('Gatunek: ', genre, 'Reżyser: ', director, description, ' ') FROM movies 
    WHERE NOT EXISTS (
        SELECT 1 FROM descr_vecs WHERE movie_id = id
    );
    """

INSERT_VECTOR = """
    INSERT INTO descr_vecs (movie_id, descr_embedding) VALUES (?, ?);
    """

SELECT_MOVIES_WITH_LESS_THAN_N_SCREENINGS = """
    SELECT m.title, duration, director, genre, production, description, screenings, href FROM (
        SELECT m.title, COUNT(ms.movie_id) AS number_of_screenings,
        GROUP_CONCAT(ms.screening_date, '\n') AS screenings
        FROM movies m
        JOIN movies_screenings ms ON m.id = ms.movie_id
        WHERE ms.screening_date > current_date
        GROUP BY m.title
        HAVING number_of_screenings <= ?
    ) t INNER JOIN movies m ON t.title = m.title
    """

SELECT_MOVIES_ABOVE_THRESHOLD = """
    SELECT m.title, duration, director, genre, production, description, screenings, href FROM (
        SELECT m.title, COUNT(ms.movie_id) AS number_of_screenings,
        GROUP_CONCAT(ms.screening_date, '\n') AS screenings
        FROM movies m
        JOIN movies_screenings ms ON m.id = ms.movie_id
        WHERE ms.screening_date > current_date
        GROUP BY m.title
    ) t INNER JOIN movies m ON t.title = m.title
    INNER JOIN descr_vecs d ON m.id = d.movie_id
    WHERE descr_embedding MATCH ?
    AND k = ?
    ORDER BY distance;
    """
