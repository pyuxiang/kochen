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
import json
import logging
import pathlib
import re
import sys
import time
import tqdm
import warnings
from itertools import product

import configargparse
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy

# Personal maintained libraries
# import boiler
# from fpfind.lib import parse_timestamps as tparser

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
'''

    text2 = '''
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(
    logging.Formatter(
        fmt="{asctime} {levelname:<8s} {funcName}:{lineno} | {message}",
        datefmt="%Y%m%d_%H%M%S",
        style="{",
    )
)
logger.addHandler(handler)


def main(args):
    pass

def check_args(args):
    pass


if __name__ == "__main__":
    filename = pathlib.Path(__file__).name
    parser = configargparse.ArgumentParser(
        default_config_files=[f"{filename}.default.conf"],
        description="",
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
