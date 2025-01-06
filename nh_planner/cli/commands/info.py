import random

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns

from nh_planner.services.database import Database


ASCII_OPTIONS = {
    "projector": """
    ═══╗ ♦     
   [===]███)   
    ═══╝ ▀     
     ║    ▀    
    ═╩═       
    """,
    
    "theater": """
     ▄▄▄▄▄▄▄▄▄▄
    ██ NH CINEMA
    ██  ▀▀▀▀▀▀  
    ██ ▐▀▀▀▀▌  
    ██ ▐▄▄▄▄▌  
    ▀▀▀▀▀▀▀▀▀▀
    """,
}


@click.command()
def info():
    """Display detailed statistics about movies and screenings"""
    db = Database()
    console = Console()
    
    try:
        stats = db.get_detailed_stats()
        
        ascii_image = Panel(random.choice(list(ASCII_OPTIONS.values())), style="cyan", box=box.MINIMAL)

        main_stats = Panel(
            f"[cyan]Total Movies:[/cyan] {stats['total_movies']}\n"
            f"[cyan]Future Movies:[/cyan] {stats['future_movies']}\n"
            f"[cyan]Total Future Screenings:[/cyan] {stats['future_screenings']}\n"
            f"[yellow]Last Scraped:[/yellow] {stats['last_scraped']}\n\n"
            f"[green]Most Popular:[/green] {stats['popular_movie']}\n"
            f"[green]└─ Screenings:[/green] {stats['popular_screenings']}\n",
            title="Stats",
            border_style="blue",
        )
                
        console.print(Columns([ascii_image, main_stats]))
        console.print("\n")
        
    except Exception as e:
        console.print(f"[red]Error retrieving statistics: {e}[/red]")
