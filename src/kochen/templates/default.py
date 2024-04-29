#!/usr/bin/env python3
"""___MODULE_INFORMATION___

Changelog:
    ~~~CURRENTDATE~~~, Justin: Init

References:
    [1]:
"""

# Remove as needed
import datetime as dt
import itertools
import logging
import os
import re
import sys
import time
from itertools import product
from pathlib import Path

import configargparse
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import tqdm
from uncertainties import ufloat

_LOGGING_FMT = "{asctime}\t{levelname:<7s}\t{funcName}:{lineno}\t| {message}"
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(
        logging.Formatter(fmt=_LOGGING_FMT, datefmt="%Y%m%d_%H%M%S", style="{")
    )
    logger.addHandler(handler)
    logger.propagate = False

def main():
    script_name = Path(sys.argv[0]).name
    parser = configargparse.ArgumentParser(
        default_config_files=[f"{script_name}.default.conf"],
        description=__doc__.partition("\n")[0],
        add_help=False,
    )

    # Boilerplate
    pgroup_config = parser.add_argument_group("display/configuration")
    pgroup_config.add_argument(
        "-h", "--help", action="store_true",
        help="Show this help message and exit")
    pgroup_config.add_argument(
        "-v", "--verbosity", action="count", default=0,
        help="Specify debug verbosity, e.g. -vv for more verbosity")
    pgroup_config.add_argument(
        "-L", "--logging", metavar="",
        help="Log to file, if specified. Log level follows verbosity.")
    pgroup_config.add_argument(
        "--quiet", action="store_true",
        help="Suppress errors, but will not block logging")
    pgroup_config.add_argument(
        "--config", metavar="", is_config_file_arg=True,
        help="Path to configuration file")
    pgroup_config.add_argument(
        "--save", metavar="", is_write_out_config_file_arg=True,
        help="Path to configuration file for saving, then immediately exit")

    # Add more script arguments
    # pgroup = parser.add_argument_group("")
    # pgroup.add_argument(
    #     "--ARG",
    #     help="")

    # Parse arguments
    args = parser.parse_args()

    # Check whether options have been supplied, and print help otherwise
    args_sources = parser.get_source_to_settings_dict().keys()
    config_supplied = any(map(lambda x: x.startswith("config_file"), args_sources))
    if args.help or (len(sys.argv) == 1 and not config_supplied):
        parser.print_help(sys.stderr)
        sys.exit(1)

    # Set logging level and log arguments
    if args.logging is not None:
        handler = logging.FileHandler(filename=args.logging, mode="w")
        handler.setFormatter(
            logging.Formatter(
                fmt=_LOGGING_FMT,
                datefmt="%Y%m%d_%H%M%S",
                style="{",
            )
        )
        logger.addHandler(handler)

    # Set logging level
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    verbosity = min(args.verbosity, len(levels)-1)
    logger.setLevel(levels[verbosity])
    logger.debug("%s", args)

    # Insert code here
    print("Hello world!")


if __name__ == "__main__":
    main()