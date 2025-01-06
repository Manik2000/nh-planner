import click

from nh_planner.cli.commands.filter import filter
from nh_planner.cli.commands.get_limited import list_limited
from nh_planner.cli.commands.info import info
from nh_planner.cli.commands.recommend import recommend
from nh_planner.cli.commands.refresh import refresh


@click.group()
def cli():
    """NH Cinema movie planner"""
    pass


cli.add_command(info)
cli.add_command(refresh)
cli.add_command(filter)
cli.add_command(recommend)
cli.add_command(list_limited)
