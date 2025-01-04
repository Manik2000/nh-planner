import asyncio
import logging
import time

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from tqdm.asyncio import tqdm_asyncio

from nh_planner.config import BASE_LINK, PROGRAMME_LINK
from nh_planner.db.data_models import MovieDetails, MovieLink
from nh_planner.db.database import DatabaseScrapingManager

logging.basicConfig(
    level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

LOGGER = logging.getLogger(__name__)


async def get_movies_from_page(html: str) -> list[MovieLink]:
    soup = BeautifulSoup(html, "html.parser")
    movies = []
    for movie_div in soup.find_all("div", "boks ilustracja-left mala-ilustr wyzszy"):
        link = movie_div.find("a", class_="tyt")
        movies.append(
            {
                "title": link.text.strip(),
                "href": BASE_LINK + link.get("href", ""),
                "screenings": [
                    a.text for a in movie_div.find_all("a", class_="xseans")
                ],
            }
        )
    return movies


async def extract_movie_details(html: str, title: str, href: str) -> dict[MovieDetails]:
    soup = BeautifulSoup(html, "html.parser")

    duration = next(
        (
            div.text.replace("czas:", "").strip()
            for div in soup.find_all("div", class_="crrow")
            if "czas:" in div.text
        ),
        None,
    )
    duration = int("".join(c for c in duration if c.isdigit())) if duration else None

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
    description = (
        " ".join(i.text.strip() for i in opisf.find_all("p"))
        if opisf and opisf.find_all("p")
        else None
    )

    return {
        "title": title,
        "duration": duration,
        "director": director,
        "genre": genre,
        "production": production,
        "description": description,
        "href": href,
    }


async def process_movie(
    page, movie: MovieDetails, date: str, db_manager: DatabaseScrapingManager
):
    title = movie["title"]
    screenings = [date + " " + s for s in movie["screenings"]]

    if not await asyncio.to_thread(db_manager.movie_exists_in_db, title):
        await page.goto(movie["href"])
        await page.wait_for_selector(".opisf")

        html = await page.content()
        movie_details = await extract_movie_details(html, title, movie["href"])

        try:
            await asyncio.to_thread(db_manager.insert_movie, movie_details)
        except Exception as e:
            LOGGER.error(f"Error inserting movie {title}: {e}")

    if screenings:
        try:
            movie_id = await asyncio.to_thread(db_manager.get_movie_id, title)
            await asyncio.to_thread(db_manager.insert_screenings, movie_id, screenings)
        except Exception as e:
            LOGGER.error(f"Error inserting screenings for {title}: {e}")


async def process_date(
    page, date: str, db_manager: DatabaseScrapingManager, force_scrape: bool
):
    if await asyncio.to_thread(db_manager.is_scraped, date) and not force_scrape:
        return

    DD_MM_YYYY = "-".join(date.split("-")[::-1])
    await page.goto(f"{PROGRAMME_LINK}{DD_MM_YYYY}")
    await page.wait_for_selector(".tyt")

    html = await page.content()
    movies = await get_movies_from_page(html)

    for movie in movies:
        await process_movie(page, movie, date, db_manager)

    await asyncio.to_thread(db_manager.insert_scraped_date, date)


async def scrape_and_load_movies_into_db(
    days_ahead: int = 12, force_scrape: bool = False
):
    db_manager = DatabaseScrapingManager()
    scrape_dates = [
        time.strftime("%Y-%m-%d", time.localtime(time.time() + 60 * 60 * 24 * i))
        for i in range(1, days_ahead + 1)
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        for date in tqdm_asyncio(scrape_dates):
            await process_date(page, date, db_manager, force_scrape)

        await browser.close()
