#!/usr/bin/env python3
"""

Examples:
    > python3 -m boiler.importutil my_new_python_script

"""

import sys

# Create boilerplate code, the original purpose of this module
if __name__ == "__main__":

    import datetime as dt
    import pathlib
    import sys

    # Obtain desired filename
    if len(sys.argv) <= 1:
        print("Please supply desired filename for new Python template script.")
        sys.exit(1)
    filename = sys.argv[1]
    filepath = pathlib.Path(filename)
    if filepath.suffix != ".py":
        filepath = filepath.with_suffix(filepath.suffix + ".py")
    if filepath.exists():
        print(f"File '{filepath}' already exists, avoiding overwriting.")
        sys.exit(1)

    text1 = f'''
#!/usr/bin/env python3
"""___MODULE_INFORMATION___

Changelog:
    {dt.datetime.now().strftime("%Y-%m-%d")} Justin: Init

References:
    [1]:
"""

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

logger = logging.getLogger(__name__)
'''

    text2 = '''
if not logger.handlers:
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt="{asctime}\t{levelname:<8s}\t{funcName}:{lineno} | {message}",
            datefmt="%Y%m%d_%H%M%S",
            style="{",
        )
    )
    logger.addHandler(handler)
    logger.propagate = False


def main(args):
    pass

def check_args(args):

    # Set logging level
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    args.verbose = min(args.verbose, len(levels)-1)
    logger.setLevel(levels[args.verbose])

    # Print out arguments
    logger.debug("Arguments: %s", args)

def _parse_path(path, type=None):
    """Checks if path is of specified type, and returns wrapper to Path."""

    def elog(msg):
        logger.error(msg)
        raise ValueError(msg)

    assert type in (None, "f", "d", "p")  # file, directory, pipe
    path = Path(path)

    # If no filetype specified
    # Useful for when path is expected to exist, or when it
    # doesn't make sense to create them, e.g. devices/sockets
    if type is None:
        if not path.exists():
            elog(f"Path '{path}' does not exist")
        return path

    # Filetype has been specified -> check if type matches
    if path.exists():
        if type == "f" and not path.is_file():
            elog(f"Path '{path}' is not a file")
        if type == "d" and not path.is_dir():
            elog(f"Path '{path}' is not a directory")
        if type == "p" and not path.is_fifo():
            elog(f"Path '{path}' is not a pipe")
        return path

    # Filetype specified but path does not exist -> create
    if type == "f":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    elif type == "d":
        path.mkdir(parents=True)
    elif type == "p":
        os.mkfifo(str(path))
    return path

if __name__ == "__main__":
    parser = configargparse.ArgumentParser(
        default_config_files=[f"{Path(__file__).name}.default.conf"],
        description=__doc__.partition("\\n")[0],
    )

    # Boilerplate
    parser.add_argument(
        "--config", is_config_file_arg=True,
        help="Path to configuration file")
    parser.add_argument(
        "--save", is_write_out_config_file_arg=True,
        help="Path to configuration file for saving, then immediately exit")
    parser.add_argument(
        "--verbose", "-v", action="count", default=0,
        help="Specify debug verbosity, e.g. -vv for more verbosity")
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress errors, but will not block logging")

    # Script arguments
    # parser.add_argument(
    #     "--ARG",
    #     help="")

    # Arguments
    if len(sys.argv) > 1:
        args = parser.parse_args()
        check_args(args)
        main(args)
'''

    texts = [text1, text2]
    filecontents = "\n\n".join([t.strip("\n") for t in texts])
    with open(filepath, "w") as f:
        f.write(filecontents)
    print(f"File '{filepath}' successfully written.")

    # Write default configuration file as well
    configpath = filepath.with_suffix(filepath.suffix + ".default.conf")
    configpath.touch(exist_ok=True)
    sys.exit(0)
