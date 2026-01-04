# kochen

Primarily a library of personal scripts and handy boilerplate, for scientific environments.

This library is additionally designed for [strong backward-compatibility](#strong-backward-compatibility): old scripts dependent on functionality in older library versions can still run, simply by performing a soft version pin in the script (whereas, traditionally, older versions of the library itself needs to be installed).

Licensed under GPLv2-or-later, because free software is best left open.

## Installation

Requires Python 3.8+ (versions below 3.8 often fail with modern tooling as of 2025).

```
pip install kochen
```

The base installation has very minimal dependencies. To use certain submodules that introduce additional dependencies, specify them as an extra:

* `datautil`: For data storage and parsing.
* `fitutil`: For curve fitting.
* `mathutil`: For general math manipulation.
* `plotutil`: For plotting.

```
pip install kochen[datautil,fitutil]
```

Or just install them all:

```
pip install kochen[all]
```

## Versioning

This library implements soft-versioning by means of version pinning in the script itself (how cool is that!). This prints `'latest'` without version pinning:

```python
import kochen.sampleutil
print(kochen.sampleutil.foo())
```

and prints `'v0.2025.8'` with version pinning, all without downgrading the library:

```python
import kochen.sampleutil  # v0.2025.8
print(kochen.sampleutil.foo())
```

## Usage

Most of the useful functionality is parked in the following submodules:
`datautil`, `mathutil`, `ipcutil`, `scriptutil`.

```python
import kochen.mathutil
kochen.mathutil.generate_simplex(...)
```

Some commonly used features are listed below.

### ipcutil

Client/Server for proxying Python instances over TCP ports.

```python
# server.py
from kochen.ipcutil import Server
from S15lib.instruments.powermeter import Powermeter

pm = Powermeter(...)
pm = Server(pm, address="192.168.1.2", port=3000)
pm.run()

# client.py
from kochen.ipcutil import Client
from S15lib.instruments.powermeter import Powermeter

pm = Client(Powermeter, address="192.168.1.2", port=3000)
print(pm.voltage)
```

### datautil

Data logging and reconstruction:

```python
from kochen.datautil import pprint

filename = "pv_curve.log"
pprint("volt_V", "power_W", "comment", out=filename)
pprint(1, 3, "first_line", out=filename)
pprint(1.5, 9, "second_line", out=filename)
#  volt_V power_W comment
#       1       3 first_line
#     1.5       9 second_line

print(load(filename, schema=[float, float, str]))
# shape: (2, 3)
# ┌────────┬─────────┬─────────────┐
# │ volt_V ┆ power_W ┆ comment     │
# │ ---    ┆ ---     ┆ ---         │
# │ f64    ┆ f64     ┆ str         │
# ╞════════╪═════════╪═════════════╡
# │ 1.0    ┆ 3.0     ┆ first_line  │
# │ 1.5    ┆ 9.0     ┆ second_line │
# └────────┴─────────┴─────────────┘
```

Data aggregation:

```python
from kochen.datautil import Collector

c = Collector()
c.indices, c.signals = (1, 2)
c.indices, c.signals = (3, 4)
c.indices, c.signals = (6, 7)

print(c.indices)  # [1, 3, 6]
```

Cache backed by file:

```python
import time
from kochen.datautil import filecache

@filecache(path="mycache", backend="json")
def initialize(duration):
    time.sleep(duration)
    return duration

print(initialize(1))  # 1 (sleeps for 1s)
print(initialize(1))  # 1 (no sleep)

with open("mycache") as f:
    print(f.read())  # {"initialize": {"((1,), frozenset())": 1}}
```

### template

Initialize a quick script boilerplate at `MYSCRIPT.py`:

```
python -m kochen.template MYSCRIPT
```

## Others

### Strong backward-compatibility?

Maybe not as strong as its proper definition implies (since it depends on the user properly deprecating functions in the first place), but it mostly does the job as advertised.

Unlike typical software engineering where application or library packages are created, one-off scripting is very common in scientific environments, since lots of prototyping and data exploration is performed.
A common practice includes installing the latest library in the system Python (or more sanely, in a global virtual environment / conda), then using it to develop scripts.
Superseding of old functions meant old scripts tend to fail to run, and hence the subsequent hesitation to upgrade the library/Python.

Allowing soft version pinning of the library should ideally fix this issue. See the [versioning](docs/versioning.md) writeup to see how this is implemented, and the old [design document](./docs/design.md) for the initial conception and reasoning.

> The alternative is of course to rely on [PEP-723](https://peps.python.org/pep-0723/#why-not-just-set-up-a-python-project-with-a-pyproject-toml) which provides a consistent way to define inline script dependencies but requires compatible tooling to run scripts in said manner. This also came out after this library was created.

### Why "kochen"?

The initial choice of library name `boiler` (since this was initially a boilerplate library) was unavailable on PyPI, and
so was the next choice `scribbles`.
The next obvious step is to pick something that is unlikely to clash with other packages, i.e. boiling in German,

> kochen [ˈkɔxn], verb:
> (Flüssigkeit, Speise) to boil [intransitive verb]

Nothing to do with Simon B. Kochen of the well-known Kochen-Specker theorem.
