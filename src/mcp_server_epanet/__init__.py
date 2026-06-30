import click
import logging
import sys


@click.command()
@click.option("-v", "--verbose", count=True)
def main(verbose: int) -> None:
    """MCP EPANET Server - EPANET simulation functionality for MCP"""
    logging_level = logging.WARN
    if verbose == 1:
        logging_level = logging.INFO
    elif verbose >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(level=logging_level, stream=sys.stderr)

    from .server import mcp
    mcp.run()


if __name__ == "__main__":
    main()
