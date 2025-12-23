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

import kochen.scriptutil
import kochen.logging

logger = kochen.logging.get_logger(__name__)


def main():
    # fmt: off
    def make_parser(help_verbosity: int = 1):
        adv = kochen.scriptutil.get_help_descriptor(help_verbosity >= 2)  # noqa: PLR2004, F841
        advv = kochen.scriptutil.get_help_descriptor(help_verbosity >= 3)  # noqa: PLR2004, F841
        advvv = kochen.scriptutil.get_help_descriptor(help_verbosity >= 4)  # noqa: PLR2004, F841
        parser = kochen.scriptutil.generate_default_parser(
            __doc__, display_config=help_verbosity >= 2,  # noqa: PLR2004
        )

        # Boilerplate
        pgroup = parser.add_argument_group("display/configuration")
        pgroup.add_argument(
            "-h", "--help", action="count", default=0,
            help="Show this help message, with incremental verbosity, e.g. -hh")
        pgroup.add_argument(
            "-v", "--verbosity", action="count", default=0,
            help="Specify debug verbosity, e.g. -vv for more verbosity")
        pgroup.add_argument(
            "-L", "--logging", metavar="",
            help=adv("Log to file, if specified. Log level follows verbosity."))
        pgroup.add_argument(
            "--quiet", action="store_true",
            help=adv("Suppress errors, but will not block logging (default: False)"))
        pgroup.add_argument(
            "--config", metavar="", is_config_file_arg=True,
            help=adv("Path to configuration file"))
        pgroup.add_argument(
            "--save", metavar="", is_write_out_config_file_arg=True,
            help=adv("Path to configuration file for saving, then immediately exit"))

        # Add more script arguments
        # pgroup = parser.add_argument_group("")
        # pgroup.add_argument(
        #     "--ARG",
        #     help="")
        return parser
    # fmt: on

    # Parse arguments and configure logging
    parser = make_parser()
    args = kochen.scriptutil.parse_args_or_help(parser, parser_func=make_parser)
    kwargs = {}
    if args.quiet:
        kwargs["stream"] = None
    kochen.logging.set_default_handlers(logger, file=args.logging, **kwargs)
    kochen.logging.set_logging_level(logger, args.verbosity)
    logger.debug("%s", args)

    # Optional
    # args.path = kochen.scriptutil.parse_path(args.path, type="d")

    # Insert code here
    print("Hello world!")


if __name__ == "__main__":
    main()
