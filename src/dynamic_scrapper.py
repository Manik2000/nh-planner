import logging
import random
import time

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from tqdm import tqdm

from src.constants import MovieDetails, MovieLink
from src.db import (get_movie_id, insert_movie, insert_scraped_date,
                    insert_screenings, is_scraped, movie_exists_in_db)


BASE_LINK = "https://www.kinonh.pl/"
PROGRAMME_LINK = "https://www.kinonh.pl/#repertuar@"

LOGGER = logging.getLogger(__name__)


def get_movies_descriptions_links(programme_html: str) -> list[MovieLink]:
    soup = BeautifulSoup(programme_html, "html.parser")
    movies = []
    for movie_div in soup.find_all("div", "boks ilustracja-left mala-ilustr wyzszy"):
        link = movie_div.find("a", class_="tyt")
        title = link.text.strip()
        href = BASE_LINK + link.get("href", "")
        screenings = [a.text for a in movie_div.find_all("a", class_="xseans")]
        movies.append({"title": title, "href": href, "screenings": screenings})
    return movies


def extract_movie_details(move_title: str, html_content: str) -> MovieDetails:
    soup = BeautifulSoup(html_content, "html.parser")

    duration = next(
        (
            div.text.replace("czas:", "").strip()
            for div in soup.find_all("div", class_="crrow")
            if "czas:" in div.text
        ),
        None,
    )
    duration = int("".join([c for c in duration if c.isdigit()])) if duration else None

    director = next(
        (
            h4.text.replace("reż.", "").strip()
            for h4 in soup.find_all("h4")
            if "reż." in h4.text
        ),
        None,
    )

    genre = next(
        (
            h4.text.replace("gatunek:", "").strip()
            for h4 in soup.find_all("h4")
            if "gatunek:" in h4.text
        ),
        None,
    )
    genre = genre.split("kategoria wiekowa")[0].strip() if genre else None

    production = next(
        (
            div.text.replace("produkcja:", "").strip()
            for div in soup.find_all("div", class_="crrow")
            if "produkcja:" in div.text
        ),
        None,
    )

    opisf = soup.find("div", class_="opisf")
    description = opisf.find("p").text.strip() if opisf and opisf.find("p") else None

    return {
        "title": move_title,
        "duration": duration,
        "director": director,
        "genre": genre,
        "production": production,
        "description": description,
    }


def scrape_and_load_movies_into_db(days_ahead: int = 12) -> None:
    scrape_dates = [
        time.strftime("%d-%m-%Y", time.localtime(time.time() + 60 * 60 * 24 * i))
        for i in range(1, days_ahead + 1)
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        for date in tqdm(scrape_dates):
            page.goto(f"{PROGRAMME_LINK}{date}")
            if is_scraped(date):
                continue
            time.sleep(random.randint(2, 4))

            html = page.content()
            movies = get_movies_descriptions_links(html)

            for movie in movies:
                title = movie["title"]
                if not movie_exists_in_db(title):
                    page.goto(movie["href"])
                    time.sleep(random.randint(2, 3))
                    movie_html = page.content()
                    movie_details = extract_movie_details(title, movie_html)
                    screenings = [date + " " + s for s in movie["screenings"]]
                    try:
                        insert_movie(movie_details)
                    except Exception as e:
                        LOGGER.error(f"Error inserting movie {title}: {e}")
                try:
                    insert_screenings(get_movie_id(title), screenings)
                except Exception as e:
                    LOGGER.error(f"Error inserting screenings for {title}: {e}")
            insert_scraped_date(date)
        browser.close()
