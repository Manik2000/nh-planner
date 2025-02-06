import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from bs4 import BeautifulSoup
from playwright.async_api import Page, async_playwright
from tqdm.asyncio import tqdm_asyncio

from nh_planner.core.config import BASE_URL, PROGRAMME_URL
from nh_planner.core.models import Movie, Screening
from nh_planner.services.database import Database

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logging.getLogger("asyncio").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


class Scraper:
    def __init__(self, db: Database):
        self.db = db

    async def get_movies_from_page(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")

        movies = []
        for movie_div in soup.find_all(
            "div", "boks ilustracja-left mala-ilustr wyzszy"
        ):
            try:
                link = movie_div.find("a", class_="tyt")
                if not link:
                    logger.warning("Found movie div without title link")
                    continue

                screenings = movie_div.find_all("a", class_="xseans")
                if not screenings:
                    logger.warning(f"No screenings found for movie {link.text.strip()}")
                    continue

                movies.append(
                    {
                        "title": link.text.strip(),
                        "href": BASE_URL + link.get("href", ""),
                        "screenings": [a.text for a in screenings],
                    }
                )
            except Exception as e:
                logger.error(f"Error processing movie div: {e}")
                movies.append(
                    {
                        "title": link.text.strip(),
                        "href": BASE_URL + link.get("href", ""),
                        "screenings": [
                            a.text for a in movie_div.find_all("a", class_="xseans")
                        ],
                    }
                )
        return movies

    async def extract_movie_details(
        self, html: str, title: str, href: str
    ) -> Optional[Movie]:
        try:
            soup = BeautifulSoup(html, "html.parser")

            duration = next(
                (
                    div.text.replace("czas:", "").strip()
                    for div in soup.find_all("div", class_="crrow")
                    if "czas:" in div.text
                ),
                None,
            )
            duration = (
                int("".join(c for c in duration if c.isdigit())) if duration else 0
            )

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

            return Movie(
                title=title,
                duration=duration,
                director=director,
                genre=genre,
                production=production,
                description=description,
                href=href,
            )
        except Exception as e:
            logger.error(f"Error extracting movie details from {href}: {e}")
            return None

    async def process_movie(self, page: Page, movie: dict, date: str):
        title = movie["title"]
        screenings = [date + " " + s for s in movie["screenings"]]

        result = await asyncio.to_thread(self.db.get_movie, title)
        if result:
            movie_id = result
        else:
            try:
                await page.goto(movie["href"])
                await page.wait_for_selector(".opisf", timeout=5_000)
                html = await page.content()
                movie_details = await self.extract_movie_details(
                    html, title, movie["href"]
                )

                if movie_details:
                    movie_id = await asyncio.to_thread(self.db.add_movie, movie_details)
            except Exception as e:
                logger.error(f"Error processing movie details for {title}: {e}")
                return

        if movie_id and screenings:
            try:
                screening_objects = [
                    Screening(movie_id=movie_id, date=s) for s in screenings
                ]
                await asyncio.to_thread(self.db.add_screenings, screening_objects)
            except Exception as e:
                logger.error(f"Error adding screenings for {title}: {e}")

    async def process_date(self, page: Page, date: str, force_scrape: bool = False):
        if force_scrape:
            await asyncio.to_thread(self.db.clear_date_screenings, date)
            await asyncio.to_thread(self.db.clear_scraped_date, date)
        if await asyncio.to_thread(self.db.is_date_scraped, date):
            logger.info(f"Date {date} already scraped, skipping...")
            return

        DD_MM_YYYY = "-".join(date.split("-")[::-1])
        await page.goto(f"{PROGRAMME_URL}{DD_MM_YYYY}")

        await page.wait_for_selector(".tyt", timeout=5_000)

        html = await page.content()
        movies = await self.get_movies_from_page(html)

        for movie in movies:
            await self.process_movie(page, movie, date)

        await asyncio.to_thread(self.db.mark_date_scraped, date)

    async def scrape_movies(
        self, days_ahead: int = 7, force_scrape: bool = False
    ) -> None:
        scrape_dates = [
            (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(1, days_ahead + 1)
        ]

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                for date in tqdm_asyncio(scrape_dates):
                    try:
                        await self.process_date(page, date, force_scrape)
                    except Exception as e:
                        logger.error(f"Failed to process date {date}: {e}")
                        try:
                            await page.close()
                        except Exception as e:
                            pass
                        page = await browser.new_page()
                        continue
            finally:
                await browser.close()
