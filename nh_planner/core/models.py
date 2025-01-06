from typing import Optional

from pydantic import BaseModel, Field


class Movie(BaseModel):
    title: str = Field(..., min_length=1)
    duration: int = Field(...)
    director: Optional[str] = None
    genre: Optional[str] = None
    production: Optional[str] = None
    description: Optional[str] = None
    href: str = Field(..., min_length=1)


class Screening(BaseModel):
    movie_id: int = Field(...)
    date: str = Field(...)


class MovieWithScreenings(Movie):
    screenings: str = Field(...)
