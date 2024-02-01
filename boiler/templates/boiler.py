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

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import tqdm
from uncertainties import ufloat

import boiler.scriptutil
import boiler.logging

logger = logging.getLogger(__name__)

def main():
    parser = boiler.scriptutil.generate_default_parser(__doc__)

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

    # Parse arguments and configure logging
    args = boiler.scriptutil.parse_args_or_help(parser)
    boiler.logging.set_default_handlers(logger, file=args.logging)
    boiler.logging.set_logging_level(logger, args.verbosity)
    logger.debug("%s", args)

    # Insert code here
    print("Hello world!")


if __name__ == "__main__":
    main()