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
    if not filename.endswith(".py"):
        filename += ".py"
    if pathlib.Path(filename).exists():
        print(f"File '{filename}' already exists, avoiding overwriting.")
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

import matplotlib.pyplot as plt
import numpy as np
import scipy

import boiler
from fpfind.lib import parse_timestamps as parser

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
'''

    texts = [text1, text2]
    filecontents = "\n\n".join([t.strip("\n") for t in texts])
    with open(filename, "w") as f:
        f.write(filecontents)
    print(f"File '{filename}' successfully written.")
    sys.exit(0)
