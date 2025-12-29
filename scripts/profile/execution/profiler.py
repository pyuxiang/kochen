#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "gprof2dot",
# ]
# ///
"""Generate execution profile plot.

Similar to: 'import cProfile; cProfile.run("...")'.
"""

import subprocess

def run(cmd):
    subprocess.check_output(cmd, shell=True)

run("python -m cProfile -o main.prof main.py")
run("python -m gprof2dot -o main.dot -f pstats main.prof")
run("dot -Tpng -o profile.png main.dot -Gbgcolor=white")
