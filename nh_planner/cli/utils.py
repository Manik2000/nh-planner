from datetime import datetime
from enum import Enum
from typing import Optional

from dateutil.parser import parse
from pydantic import BaseModel, Field
from rich import box
from rich.console import Console
from rich.table import Table

from nh_planner.db.data_models import MovieCard, MovieFilterResult

STYLES = ["cyan", "green", "yellow", "blue", "magenta", "red"]
N = len(STYLES)


class ValidationCheck(Enum):
    VALID = 0
    INVALID = 1


class ValidationResult(BaseModel):
    result: ValidationCheck
    message: Optional[str] = Field(None)


def create_movie_dicts(
    movies: list[tuple], dict_format: MovieCard | MovieFilterResult
) -> list[MovieCard | MovieFilterResult]:
    return [dict(zip(dict_format.__annotations__, movie)) for movie in movies]


def display_movie(movie: MovieCard):
    console = Console()
    for i, (key, value) in enumerate(movie.items()):
        if key == "duration":
            value = f"{value}'"
        console.print(f"[{STYLES[i % N]}]{key.capitalize()}: {value}[/{STYLES[i % N]}]")
    console.print("\n")


def display_table(movies: list[MovieCard]):
    console = Console()

    table = Table(
        show_header=True,
        header_style="bold magenta",
        box=box.ROUNDED,
    )

    for i, (key, _) in enumerate(movies[0].items()):
        table.add_column(key.capitalize(), style=STYLES[i % N])

    for movie in movies:
        table.add_row(*[str(value) for value in movie.values()])

    console.print(table)


def parse_date(date: str) -> str:
    """Parse date string to format 'YYYY-MM-DD HH:MM'"""
    return parse(date).strftime("%Y-%m-%d %H:%M")


def validate_date(dates: list[str]) -> ValidationResult:
    dates = [date for date in dates if date is not None]
    try:
        dates = [datetime.strptime(date, "%Y-%m-%d %H:%M") for date in dates]
        if len(dates) == 2:
            if dates[0] > dates[1]:
                return ValidationResult(
                    result=ValidationCheck.INVALID,
                    message="Start date cannot be after end date",
                )
        return ValidationResult(result=ValidationCheck.VALID)
    except ValueError:
        return ValidationResult(
            result=ValidationCheck.INVALID, message="Invalid date format"
        )


def validate_title(title: str) -> ValidationResult:
    if not isinstance(title, str):
        return ValidationResult(
            result=ValidationCheck.INVALID, message="Title must be a string"
        )
    return ValidationResult(result=ValidationCheck.VALID)


def validate_duration(durations: list[int]) -> ValidationResult:
    if not any(durations):
        return ValidationResult(
            result=ValidationCheck.INVALID, message="Duration cannot be empty"
        )
    not_none = [duration for duration in durations if duration is not None]
    for duration in not_none:
        if not isinstance(duration, int):
            return ValidationResult(
                result=ValidationCheck.INVALID, message="Duration must be an integer"
            )
        if duration < 0:
            return ValidationResult(
                result=ValidationCheck.INVALID,
                message="Duration must be a positive integer",
            )
    return ValidationResult(result=ValidationCheck.VALID)
