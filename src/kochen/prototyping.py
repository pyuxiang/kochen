#!/usr/bin/env python3
# Imports useful functions for quick prototyping
# Justin, 2024-07-03
#
# We use lazy importing to avoid initial lag + overloading memory.
#
# Example:
#     >>> from kochen.prototyping import *

# Ignore unused imports + module import location
# ruff: noqa: F401, E402

import importlib.util
import sys
import warnings


class Profile:
    def __init__(self, title="profile"):
        self.title = title

    def __enter__(self, *args, **kwargs):
        self.start = time.time()

    def __exit__(self, *args, **kwargs):
        print(f"{self.title}:", time.time() - self.start)


class BlackHole:
    """Eats attribute calls, as an alternative to clean up."""

    def __init__(self, module):
        self.module = module

    def __getattribute__(self, name: str):
        return


def lazy_import(name):
    # Avoids duplicate module loading
    if name in sys.modules:
        return sys.modules[name]

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        spec = importlib.util.find_spec(name)

    if spec is None:
        print(f"Module '{name}' does not exist - not imported.")
        return BlackHole(name)

    loader = importlib.util.LazyLoader(spec.loader)
    spec.loader = loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def cleanup(globals):
    scheduled = []
    for k, v in globals.items():
        if type(v) is BlackHole:
            scheduled.append(k)
    for k in scheduled:
        del globals[k]


# Built-in libraries are generally fine
import datetime as dt
import itertools
import multiprocessing as mp
import os
import pathlib
import pickle
import pprint
import random
import re
import shutil
import struct
import subprocess
import time
import timeit

# Third-party libraries
# Ideally to sort them in DAG order, to avoid reloads
# Note: Functions cannot be lazy loaded (for now)
np = lazy_import("numpy")
scipy = lazy_import("scipy")
plt = lazy_import("matplotlib.pyplot")
pd = lazy_import("pandas")
serial = lazy_import("serial")
tqdm = lazy_import("tqdm")
u = lazy_import("uncertainties").ufloat
unp = lazy_import("uncertainties.unumpy")

# Personally maintained libraries
S15lib = lazy_import("S15lib")
fpfind = lazy_import("fpfind")
utils = lazy_import("fpfind.lib.utils")
tparser = lazy_import("fpfind.lib.parse_timestamps")
eparser = lazy_import("fpfind.lib.parse_epochs")
mathutil = lazy_import("kochen.mathutil")

cleanup(globals())
