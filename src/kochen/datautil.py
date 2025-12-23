#!/usr/bin/env python3
# Justin, 2022-12-20
"""Provides helper functions for data management."""

__all__ = ["pprint", "read_log"]

import datetime as dt
import enum
import functools
import io
import json
import pathlib
import pickle
import re
import sys
from collections import defaultdict
from typing import Callable, Iterable, Optional, Type, Any, Union

import numpy as np
import polars as pl
import tqdm

from kochen.lib.typing import PathLike

# For pprint to accept NaN values
NOVALUE = np.iinfo(np.int64).min


def pprint(
    *values,
    width: int = 7,
    out: Optional[str] = None,
    pbar: Optional[Type[tqdm.tqdm]] = None,
    stdout: bool = True,
):
    """Prints right-aligned columns of fixed width.

    Saved data is enforced to be tab-delimited to save storage space
    (typically not directly printed into console anyway, but post-processed).

    Args:
        out: Optional filepath to save data.
        pbar: tqdm.ProgressBar.
        print: Determines if should write to console.

    Note:
        The default column width of 7 is predicated on the fact that
        10 space-separated columns can be comfortably squeezed into a
        80-width terminal (with an extra buffer for newline depending
        on the shell).

        Not released.

        Integrates with tqdm.ProgressBar.

        Conflicts with Python's pprint module, which is implemented
        for pretty-printing of data structures instead of plain tabular data.
    """
    array = [(str(value) if value != NOVALUE else " ") for value in values]

    # Checks if progress bar is supplied - if so, update that instead
    if pbar:
        line = " ".join(array)
        pbar.set_description(line)

    # Prints line delimited to console
    elif stdout:
        line = " ".join([f"{value: >{width}s}" for value in array])
        print(line)

    # Write to file if filepath provided
    if out:
        line = "\t".join(array) + "\n"
        with open(out, "a") as f:
            f.write(line)

    return


def pprint_progressbar(value, lower=0, upper=1, width=80):
    """Prints multi-level progress bar for single valued representation.

    Visual representation of the magnitude of a single number is
    useful for fast optimization, as opposed to a numeric stream.

    TODO:
        Clean up code for reuse.
    """
    assert upper >= lower
    value = float(value)

    # Set lower and upper bounds
    bounds = [
        (0.5, 2.5),  # \u2588
        (0.2, 0.5),  # \u2593
        (0.1, 0.2),  # \u2592
        (0, 0.1),  # \u2591
    ]
    lefts = [0]
    for bound in bounds:
        lower, upper = bound
        percent = (value - lower) / (upper - lower)
        percent = max(0, min(1, percent))
        left = int(round(percent * (width - 7)))
        lefts.append(left)
    lefts.append(width - 7)

    # Print blocks
    blocks = [
        "\u2588",
        "\u2593",
        "\u2592",
        "\u2591",
        " ",
    ]
    line = "{:6.4f}\u2595".format(round(value, 4))
    for i in range(1, len(lefts)):
        amt = max(0, min(width - 7, lefts[i] - lefts[i - 1]))
        line += blocks[i - 1] * amt
    line += "\u258f"
    print(line)


class Datatype(enum.Enum):
    DATETIME = enum.auto()
    TIME = enum.auto()
    IGNORE = enum.auto()


def reconstruct_schema(
    line,
    schema: Union[list, dict, None] = None,
    default: Union[Callable, Datatype, None] = None,
    has_datetime_field: Union[bool, None] = None,
) -> list:
    """
    'default' has special meanings depending on whether a mapping or sequence
    was provided for 'schema'. For mapping-based 'schema', default behaviour
    is to ignore the field. For sequence-based 'schema', default behaviour is
    to not parse the field (i.e. remain as str).

    'has_datetime_field' is only effective for mapping-based schema or if no
    schema is specified, to avoid confusion!
    """

    # Handle special schema
    def convert_time_factory():
        convert_time_day_overflow = (
            0  # allow time conversions to cycle into the next day
        )
        convert_time_prevtime = dt.datetime(1900, 1, 1, 0, 0, 0)

        def convert_time(s):
            nonlocal convert_time_prevtime
            nonlocal convert_time_day_overflow
            result = dt.datetime.strptime(s, "%H%M%S")  # default date is 1 Jan 1900
            if result < convert_time_prevtime:
                convert_time_day_overflow += 1
            convert_time_prevtime = result
            result += dt.timedelta(days=convert_time_day_overflow)
            return result

        return convert_time

    convert_time = convert_time_factory()

    def convert_datetime(s):
        return dt.datetime.strptime(s, "%Y%m%d_%H%M%S")

    # For mapping-based schema, default to ignore
    # For sequence-based schema, default to not parse
    def identity(x):
        return x

    def generate_default_schema():
        schema = [default] * len(line)
        # Guess datetime, check if parseable
        if has_datetime_field is None:
            try:
                convert_datetime(line[0])
                schema[0] = Datatype.DATETIME
            except Exception:
                pass
        elif has_datetime_field:
            schema[0] = Datatype.DATETIME
        return schema

    if default is None:
        default = None if isinstance(schema, dict) else identity

    if schema is None:
        schema = generate_default_schema()

    # Convert mapping to list
    if isinstance(schema, dict):
        _schema = generate_default_schema()
        for idx, convertor in schema.items():
            _schema[idx] = convertor
        schema = _schema

    # Check schema length
    schema = list(schema)
    if len(schema) != len(line):
        raise ValueError(
            f"Schema has wrong length: expected {len(line)}, got {len(schema)}"
        )

    # Parse special (hardcoded) types
    for i, dtype in enumerate(schema):
        if dtype is Datatype.TIME:
            schema[i] = convert_time
        elif dtype is Datatype.DATETIME:
            schema[i] = convert_datetime
        elif dtype is Datatype.IGNORE:
            schema[i] = None

    return schema


def _parse(data: str, delimiters: str = " \t") -> list:
    data = re.sub(rf"[{delimiters}]+", " ", data)  # squash whitespace
    tokens = [line.strip() for line in data.split("\n")]
    tokens = [line.split(" ") for line in tokens if line != ""]
    return tokens


def _load(
    data: str,
    schema: Union[list, dict, None] = None,
    default: Union[Callable, Datatype, None] = None,
    delimiters: str = " \t",
    headers: Union[Iterable, None] = None,
    has_datetime_field: Union[bool, None] = None,
) -> pl.DataFrame:
    sdata = _parse(data, delimiters)
    schema = reconstruct_schema(sdata[-1], schema, default, has_datetime_field)

    result = []
    for line in sdata:
        try:
            # Equivalent to Pandas's 'applymap'
            # Note this cannot be run in parallel due to 'convert_time' implementation
            row = [f(v) for f, v in zip(schema, line) if f is not None]
            result.append(row)
        except Exception:
            # If fails, assume is string header
            if headers is None:
                headers = [v for f, v in zip(schema, line) if f is not None]

    if headers is None:
        headers = [f"column_{x + 1}" for x in range(len(sdata[-1]))]

    # Merge columns
    result = list(zip(*result))
    items = dict(zip(headers, result))
    return pl.DataFrame(items)


def load(
    filename: PathLike,
    schema: Union[list, dict, None] = None,
    default: Union[Callable, Datatype, None] = None,
    delimiters: str = " \t",
    headers: Union[Iterable, None] = None,
    has_datetime_field: Union[bool, None] = None,
) -> pl.DataFrame:
    with open(filename, "r", encoding="utf8") as f:
        data = f.read()
        result = _load(data, schema, default, delimiters, headers, has_datetime_field)
    return result


def dump(
    f: Union[PathLike, io.TextIOBase],
    *fields,
    delimiter: str = "\t",
    has_datetime_field: bool = True,
):
    is_filename = isinstance(f, PathLike)
    if is_filename:
        f = open(f, "a", encoding="utf8")

    # Generate field entries
    fields = list(fields)
    if has_datetime_field:
        now = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        fields = [now] + fields

    # Write
    line = delimiter.join(fields) + "\n"
    f.write(line)  # type: ignore

    # Optionally close
    if is_filename:
        f.close()  # type: ignore


def read_log(filename: str, schema: list, merge: bool = False):
    """Parses a logfile into a dictionary of columns.

    Convenience method to read out logfiles generated by the script.
    This is not filename-aware (i.e. date and schema version is not
    extracted from the filename) since these are not rigorously
    set-in-stone yet.

    If "time" is used, rows are assumed to be in chronological order,
    i.e. monotonically increasing, so timing overflows will be
    assumed to mean the next day. 'None' is also a valid datatype,
    i.e. ignored.

    Args:
        filename: Filename of log file.
        schema: List of datatypes to parse each column in logfile.
        merge:
            Whether multiple logging runs in the same file should
            be merged into a single list, or as a list-of-lists.

    Note:
        This code assumes tokens in columns do not contain spaces,
        including headers.

    TODO(Justin):
        Consider usage of PEP557 dataclasses for type annotations.
        Change the argument type of filename to include Path-like objects.
        Implement non-merge functionality.

        Not released.
    """

    convert_time_day_overflow = 0  # allow time conversions to cycle into the next day
    convert_time_prevtime = dt.datetime(1900, 1, 1, 0, 0, 0)

    def convert_time(s):
        nonlocal convert_time_prevtime
        nonlocal convert_time_day_overflow
        result = dt.datetime.strptime(s, "%H%M%S")  # default date is 1 Jan 1900
        if result < convert_time_prevtime:
            convert_time_day_overflow += 1
        convert_time_prevtime = result
        result += dt.timedelta(days=convert_time_day_overflow)
        return result

    def convert_datetime(s):
        return dt.datetime.strptime(s, "%Y%m%d_%H%M%S")

    # Parse schema
    _maps = []
    for dtype in schema:
        # Parse special (hardcoded) types
        if isinstance(dtype, str):
            if dtype == "time":
                _map = convert_time
            elif dtype == "datetime":
                _map = convert_datetime
            else:
                raise ValueError(f"Unrecognized schema value - '{dtype}'")
        elif dtype is None:  # ignore column
            _map = None
        # Treat everything else as regular Python datatypes
        elif isinstance(dtype, type):
            _map = dtype
        else:
            raise ValueError(f"Unrecognized schema value - '{dtype}'")
        _maps.append(_map)

    # Read file
    is_header_logged = False
    _headers = []
    _data = []
    print(_maps)
    with open(filename, "r") as f:
        for row_str in f:
            # Squash all intermediate spaces
            row = re.sub(r"\s+", " ", row_str.strip()).split(" ")
            try:
                # Equivalent to Pandas's 'applymap'
                # Note this cannot be run in parallel due to 'convert_time' implementation
                row = [f(v) for f, v in zip(_maps, row) if f is not None]
                _data.append(row)
            except Exception:
                # If fails, assume is string header
                if not is_header_logged:
                    _headers = [v for f, v in zip(_maps, row) if f is not None]
                    is_header_logged = True

    if not is_header_logged:
        raise ValueError("Logfile does not contain a header.")

    # Merge headers
    _data = list(zip(*_data))
    _items = tuple(zip(_headers, _data))
    return dict(_items)


class DataEncoder(json.JSONEncoder):
    """Usage: json.dump(..., cls=data_encoder)"""

    @staticmethod
    def _dt2str(x):
        return x.strftime("%Y%m%d_%H%M%S.%f")

    def default(self, obj):
        if isinstance(obj, dt.datetime):
            return {"_dt": obj.strftime("%Y%m%d_%H%M%S.%f")}
        if isinstance(obj, np.ndarray):
            if len(obj) > 0 and isinstance(obj[0], dt.datetime):
                return {"_dt_np": list(map(DataEncoder._DT2STR, obj))}
            else:
                return {"_np": obj.tolist()}
        return super().default(obj)


def data_decoder(dct):
    """Usage: json.load(..., object_hook=datetime_decoder)"""

    def _str2dt(x):
        return dt.datetime.strptime(x, "%Y%m%d_%H%M%S.%f")

    if "_dt" in dct:
        return _str2dt(dct["_dt"])
    if "_np" in dct:
        return np.array(dct["_np"])
    if "_dt_np" in dct:
        return np.array(list(map(_str2dt, dct["_dt_np"])))
    return dct


def filecache(
    f=None,
    *,
    path=None,
    overwrite: bool = False,
    backend: str = "pickle",
    recursive: bool = False,
):
    """Decorator for function memoization, backed by the filesystem.

    Intermediate results for recursive functions can also be cached when
    'recursive' to True. This is an expensive operation and should be avoided
    where reasonably possible.

    Args:
        f: Function to enable caching for.
        path: Path to cache.
        overwrite: Whether to ignore existing and load new values into cache.
        backend: Backend cache format, one of {"pickle", "json"}.
        recursive: Whether to reload updated cache after every evaluation.

    Examples:
        >>> @filecache
        ... def f(x):
        ...     return x**2
        >>> @filecache(path="hey", overwrite=True)
        ... def g(x):
        ...     return x**3

    Note:
        Recursive caching is generally more effective when the recursive
        relation is written in terms of its subproblems, i.e. the function

            def repeat(f, x, n=1):
                if n == 0:
                    return x
                return repeat(f, f(x), n-1))

        caches 'repeat(f, f(...f(x)...), 0...n)' which is not immediately
        useful. This is better rewritten as

            def repeat(f, x, n=1):
                if n == 0:
                    return x
                return f(repeat(f, x, n-1))

        which caches 'repeat(f, x, 0...n)' instead. In other words, avoid
        the use of the accumulation pattern found in tail-recursion (which
        CPython does not support anyway).

        Recursive caching is not optimal due to the need to reload the cache
        prior to memoization to avoid cache misses, e.g. cache updates from
        other memoized functions.
    """

    def read_cache(path, backend):
        try:
            if backend == "pickle":
                with open(path, "rb") as cache:
                    table = pickle.load(cache)
            elif backend == "json":
                with open(path, "r") as cache:
                    table = json.load(cache, object_hook=data_decoder)
            else:
                raise RuntimeError()
        except Exception:
            return None

        if not isinstance(table, dict):
            return None
        return table

    def write_cache(path, backend, table):
        if backend == "pickle":
            with open(path, "wb") as cache:
                pickle.dump(table, cache)
        elif backend == "json":
            with open(path, "w") as cache:
                json.dump(table, cache, cls=DataEncoder)
        else:
            raise RuntimeError()

    def wrapper(f):
        @functools.wraps(f)
        def cacher(*args, **kwargs):
            fname = f.__name__
            key = (args, frozenset(kwargs.items()))
            if backend == "json":
                key = str(key)

            # Check for memoized value
            table = read_cache(path, backend)
            if table is not None:
                if not overwrite and fname in table and key in table[fname]:
                    return table[fname][key]

            # Evaluate
            result = f(*args, **kwargs)

            # Memoize
            if recursive:
                table = read_cache(path, backend)
            if table is None:
                table = defaultdict(dict)
            table[fname][key] = result
            write_cache(path, backend, table)
            return result

        return cacher

    if backend not in ("pickle", "json"):
        raise ValueError(f"Unrecognized backend '{backend}'")

    if path is None:
        if len(sys.argv) == 0:
            raise ValueError(
                "Script name could not be determined - please supply 'path' argument."
            )
        suffix = ".cache.json" if backend == "json" else ".cache"
        path = pathlib.Path(sys.argv[0]).name + suffix

    if f is not None:  # function was directly passed
        return wrapper(f)
    return wrapper


def datacache(
    data=None,
    name="~~adhocdatastorage~~",  # must be invalid function name
    path=None,
    backend: str = "pickle",
):
    """Analog to 'filecache' but for data.

    Examples:
        >>> if (data := datacache()) is None:
        ...     data = 42  # generate data, i.e. expensive
        ...     datacache(data)
        >>> datacache()
        42
    """
    overwrite = data is not None

    # Use the same filecache mechanism
    @filecache(path=path, overwrite=overwrite, backend=backend)
    def f():
        return data

    f.__name__ = name
    return f()


def get_datetime_parser(format):
    def parse_datetime(v):
        """
        Examples:
            >>> dtype = {
            ...     "names": ("timestamp", "value"),
            ...     "formats": ("datetime64[ns]", "i16"),
            ... }
            >>> np.loadtxt(
            ...     filename,
            ...     dtype=dtype,
            ...     convertors={0: get_datetime_parser(FMT_DATE_SECONDS)},
            ... )
        """
        return np.datetime64(dt.datetime.strptime(v, format))

    return parse_datetime


FMT_DATE_DAY = "%Y%m%d"
FMT_TIME_SECONDS = "%H%M%S"
FMT_DATE_SECONDS = f"{FMT_DATE_DAY}_{FMT_TIME_SECONDS}"
FMT_TIME_MICROSECONDS = f"{FMT_TIME_SECONDS}.%f"
FMT_DATE_MICROSECONDS = f"{FMT_DATE_DAY}_{FMT_TIME_MICROSECONDS}"


class CollectorList(list):
    pass


class BaseCollector:
    pass


def Collector():
    class Collector(BaseCollector):
        """Syntactic sugar to make collecting arbitrary data easier.

        See examples below for a clearer description. Having a simplified
        aggregation structure minimizes unnecessary field name repetitions
        and makes for much cleaner code.

        This class cannot be pickled; wrap with 'FrozenCollector' before
        serialization.

        Examples:

            # Given some arbitrary data processing/parsing function
            >>> def get_signal():
            ...     return (3, 4.0, 8)

            # Typical boilerplate that can be expected when aggregating data
            # can look like the following
            >>> indices = []
            >>> signals = []
            >>> errors = []
            >>> index, signal, error = get_signal()  # first
            >>> indices.append(index)
            >>> signals.append(signal)
            >>> errors.append(error)
            >>> index, signal, error = get_signal()  # second
            >>> indices.append(index)
            >>> signals.append(signal)
            >>> errors.append(error)
            >>> indices
            [3, 3]

            # Using defaultdict only lets you skip the initialization
            >>> d = collections.defaultdict(list)
            >>> index, signal, error = get_signal()  # first
            >>> d["indices"].append(index)
            ...

            # This class provides the following equivalent statements
            >>> c = Collector()
            >>> c.indices, c.signals, c.errors = get_signal()  # first
            >>> c.indices, c.signals, c.errors = get_signal()  # second
            >>> c.indices
            [3, 3]

            # They both behave identical to lists
            >>> indices.extend([4, 5])
            >>> c.indices.extend([4, 5])

            # To delete the attribute(s), use the 'del' syntax
            >>> del c.indices, c.signals, c.errors

        Note:
            The internal list returned by this class is actually a subclass
            of list, to avoid unexpected behaviour when assigning lists, e.g.
            multidimensional data. This introduces a minimal subclass overhead
            when serializing to Python's pickle format, about 3 bytes/attr.
        """

        def __init__(self):
            # TODO: Fix 'help(self)' and other default attributes, see below.
            # super().__setattr__("__name__", "collector")
            super().__setattr__("__qualname__", "collector")
            super().__setattr__("__origin__", None)

        @property
        def __name__(self):
            return "collector"

        def __getattr__(self, name: str):
            internal_name = f"-{name}"  # field with '-' is rarely user-defined
            setattr(self, internal_name, CollectorList())  # create new list

            def fget(self):
                return getattr(self, internal_name)

            def fset(self, value):
                getattr(self, internal_name).append(value)

            def fdel(self):
                delattr(Collector, name)  # remove property first
                delattr(self, internal_name)

            setattr(Collector, name, property(fget, fset, fdel))
            return getattr(self, name)

        def __setattr__(self, name: str, value: Any) -> None:
            if isinstance(value, (CollectorList, BaseCollector)):
                return super().__setattr__(name, value)  # initialize field
            getattr(self, name).append(value)

        def __attributes(self):
            d = self.__dict__
            keys = [
                attr[1:]
                for attr in d.keys()
                if (isinstance(d[attr], CollectorList) and len(d[attr]) != 0)
            ]
            keys += [attr for attr in d.keys() if (isinstance(d[attr], BaseCollector))]
            return keys

        def __repr__(self):
            return f"Collector[{', '.join(self.__attributes())}]"

    return Collector()


collector = Collector()  # generic default for simple usage


class FrozenCollector(BaseCollector):
    """Frozen equivalent of Collector.

    Due to the need to override the properties of Collector, the Collector
    class must be a closure, which also means it cannot be pickled. This
    class freezes the collected attributes from Collector, and exposes them
    in the same way as Collector, while allowing for pickling.

    Note that the attributes are no longer protected, i.e. these attributes
    can be directly overwritten/deleted.

    Examples:
        # Regular collector
        >>> c = Collector()
        >>> c.data = 3
        >>> c
        Collector[data]
        >>> c.data
        [3]
        >>> pickle.dumps(c)  # fails
        AttributeError: Can't get local object 'Collector.<locals>.Collector'

        # Frozen collector
        >>> f = FrozenCollector(c)
        >>> f
        FrozenCollector[data]
        >>> f.data
        [3]
        >>> pickle.dumps(f)  # okay
        ...
    """

    def __init__(self, collector, copy: bool = False):
        """
        Args:
            collector: Collector object to freeze.
            copy: Whether to perform a copy of attributes.
        """
        if not hasattr(collector, "_Collector__attributes"):
            raise ValueError("Argument is not of class 'Collector'")

        self.__attributes = collector._Collector__attributes()
        for key in self.__attributes:
            value = getattr(collector, key)
            if isinstance(value, BaseCollector):
                value = FrozenCollector(value)
            elif copy:
                from copy import deepcopy

                value = deepcopy(list(value))
            setattr(self, key, value)

    def __repr__(self):
        return f"FrozenCollector[{', '.join(self.__attributes)}]"


class FrozenNumpyCollector(BaseCollector):
    """Frozen equivalent of Collector, with numpy array values.

    Similar to 'FrozenCollector', but with attributes casted into numpy arrays
    for downstream processing.
    """

    def __init__(self, collector):
        if not hasattr(collector, "_Collector__attributes") and not hasattr(
            collector, "_FrozenCollector__attributes"
        ):
            raise ValueError("Argument is not of class 'Collector'")

        if hasattr(collector, "_Collector__attributes"):
            self.__attributes = collector._Collector__attributes()
        else:
            self.__attributes = collector._FrozenCollector__attributes()
        for key in self.__attributes:
            value = getattr(collector, key)
            if isinstance(value, BaseCollector):
                value = FrozenNumpyCollector(value)
            else:
                value = np.asarray(value)
            setattr(self, key, value)

    def __repr__(self):
        return f"FrozenNumpyCollector[{', '.join(self.__attributes)}]"
