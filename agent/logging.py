from rich.console import Console
from rich.logging import RichHandler
import logging

console = Console()


def setup_logger(name: str = "agent"):
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
    )
    return logging.getLogger(name)
