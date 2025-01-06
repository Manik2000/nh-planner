from rich import box
from rich.console import Console
from rich.table import Table

from nh_planner.core.models import MovieWithScreenings


STYLES = ["cyan", "green", "yellow", "blue", "magenta", "red"]
N = len(STYLES)


def format_value(key: str, value: any) -> str:
    if key == "duration":
        return f"{value}'"
    return str(value) if value is not None else "N/A"


def display_movie(movie: MovieWithScreenings) -> None:
    console = Console()
    console.print("\n" + "=" * 50 + "\n")
    
    fields = {k: v for k, v in movie.model_dump().items()}
    
    for i, (key, value) in enumerate(fields.items()):
        style = STYLES[i % N]
        formatted_value = format_value(key, value)
        
        if key == "href":
            console.print(f"[{style}]{key}: {formatted_value}[/{style}]")
        elif key == "screenings":
            console.print(f"[{style}]{key.capitalize()}:")
            console.print(formatted_value)
        else:
            console.print(f"[{style}]{key.capitalize()}: {formatted_value}[/{style}]")
    
    console.print("\n")


def display_table(movies: list[MovieWithScreenings]) -> None:
    if not movies:
        Console().print("No movies found")
        return

    console = Console()
    table = Table(
        show_header=True,
        header_style="bold magenta",
        box=box.ROUNDED,
    )
    
    fields = [i for i in movies[0].model_fields.keys() if i != "description"]
    
    for i, field in enumerate(fields):
        style = STYLES[i % N]
        column_name = field if field == "href" else field.capitalize()
        table.add_column(column_name, style=style)

    for movie in movies:
        row_values = []
        for field in fields:
            if field == "description":
                continue
            value = getattr(movie, field)
            row_values.append(format_value(field, value))
        
        table.add_row(*row_values)
        table.add_row()

    console.print(table)
