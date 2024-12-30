import os
from typing import TypedDict


DB_PATH = os.path.expanduser("~/.config/kinonh/kinonh.db")


class MovieLink(TypedDict):
    title: str
    href: str
    screenings: list[str]


class MovieDetails(TypedDict):
    title: str
    duration: int
    director: str
    genre: str
    production: str
    description: str
