import sys
import logging


def setup_logging(level=logging.INFO):
    """
    Set up logging configuration for the application.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(processName)s: %(process)d] [%(threadName)s: %(thread)d] [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
