from typing import TypedDict


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
    href: str


class MovieCard(TypedDict):
    title: str
    duration: int
    director: str
    genre: str
    production: str
    description: str
    screenings: list[str]
    href: str


class MovieFilterResult(TypedDict):
    title: str
    duration: int
    director: str
    genre: str
    production: str
    screenings: list[str]
    href: str
