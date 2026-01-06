from typing import TYPE_CHECKING, Any, List, Union

import numpy as np
import numpy.typing as npt
import polars as pl

from kochen.datautil.latest import filecache, CollectorList, BaseCollector
from kochen.versioning import deprecated_after


# Buggy implementation!
# f.__name__ renames the decorating wrapper instead of the actual function,
# so this function actually doesn't work as advertised.
@deprecated_after("0.2026.4")
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

    f.__name__ = name  # this implementation is bugger
    return f()


# This version of Collector allows for nested Collectors, which is cool
# to implement, but makes for slightly more buggy code, since code should
# implement guardrails to check whether the return type is a Collector or
# list. Removing this feature to simplify the class.
#
# Also fixes buggy assignment when passing lists between collectors.
@deprecated_after("0.2026.6")
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


@deprecated_after("0.2026.6")
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

    # Enforce signature for frozen collectors whose attributes are dynamically defined.
    if TYPE_CHECKING:
        # Use forward reference
        def __getattr__(self, name: str) -> Union[List[Any], "FrozenCollector"]:  # pyright: ignore[reportGeneralTypeIssues]
            return getattr(self, name)

        def __setattr__(self, name: str, value: Any) -> None:
            return None


@deprecated_after("0.2026.6")
class FrozenNumpyCollector(BaseCollector):
    """Frozen equivalent of Collector, with numpy array values.

    Similar to 'FrozenCollector', but with attributes casted into numpy arrays
    for downstream processing.

    Bypass allowed for dictionaries of lists, e.g.
    FrozenNumpyCollector({"col1": [1, 2], "col2": [2, 3]})
    """

    def __init__(self, collector):
        # Dictionary bypass to avoid copies
        if isinstance(collector, dict):
            self.__attributes = list(collector.keys())
            for attr, value in collector.items():
                setattr(self, attr, np.asarray(value))
            return

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

    # Enforce signature for frozen collectors whose attributes are dynamically defined.
    if TYPE_CHECKING:
        # Use forward reference
        def __getattr__(
            self, name: str
        ) -> Union[npt.NDArray[Any], "FrozenNumpyCollector"]:  # pyright: ignore[reportGeneralTypeIssues]
            return getattr(self, name)

        def __setattr__(self, name: str, value: Any) -> None:
            return None


@deprecated_after("0.2026.6")
class CollectorUtil:
    @staticmethod
    def freeze(collector: BaseCollector, np: bool = True) -> BaseCollector:
        cls = FrozenNumpyCollector if np else FrozenCollector
        return cls(collector)

    @staticmethod
    def from_pl(df: pl.DataFrame, freeze: bool = True) -> BaseCollector:
        if freeze:
            d = {}
            for column in df.columns:
                d[column] = df[column].to_numpy()
            return FrozenNumpyCollector(d)

        c = Collector()
        for column in df.columns:
            series = df[column].to_list()
            getattr(c, column).extend(series)
        return c

    @staticmethod
    def assert_list(value: Union[BaseCollector, List[Any]]) -> List[Any]:
        """Used for type-checking assertion."""
        if isinstance(value, BaseCollector):
            raise ValueError("input is not a list.")
        return value

    @staticmethod
    def assert_array(value: Union[BaseCollector, npt.NDArray[Any]]) -> npt.NDArray[Any]:
        """Used for type-checking assertion."""
        if isinstance(value, BaseCollector):
            raise ValueError("input is not an array.")
        return value

    @staticmethod
    def assert_collector(
        value: Union[BaseCollector, npt.NDArray[Any]],
    ) -> BaseCollector:
        """Used for type-checking assertion."""
        if not isinstance(value, BaseCollector):
            raise ValueError("input is not a Collector.")
        return value
