import click

from nh_planner.cli.commands.filter import filter
from nh_planner.cli.commands.info import info
from nh_planner.cli.commands.list_screenings import list_screenings
from nh_planner.cli.commands.models import models
from nh_planner.cli.commands.recommend import recommend
from nh_planner.cli.commands.refresh import refresh


@click.group()
def cli():
    """NH Cinema movie planner"""
    pass


cli.add_command(info)
cli.add_command(refresh)
cli.add_command(filter)
cli.add_command(models)
cli.add_command(recommend)
cli.add_command(list_screenings)
