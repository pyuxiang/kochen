# IPC utilities

This idea was borne from the need to interact with (multiple) devices connected on (separate) remote hosts. These classes are available by running:

```python
from kochen.ipcutil import Client, Server
```

## Vanilla usage

The server can be initialized as follows. Note all the connection parameters must be supplied as a keyword argument. An optional symmetric secret string can be provided to add an encryption layer.

```python
# Server-side
s = Server(address="localhost", port=9999, secret="waktu")
```

The server can run local code, by registering the function with the server. The command name will automatically be inferred from the function name. Finally, bind the server to the interface, so that clients can connect to it. Ensure that the same firewall port is also opened.

```python
def hello(name="world"):
    return f"Hello {name}!"

s.register(hello)
s.run()
```

On the client side, connect to the server using the same connection parameters, then make a call.

```python
# Client-side
c = Client(address="localhost", port=9999, secret="waktu")
c.hello()  # returns "Hello world!"
c.hello("darkness my old friend")  # returns "Hello darkness my old friend!"
c.hello(name=24601)  # returns "Hello 24601!"
```

Once connection is done, the client can play nice and close the connection.

```python
c.close()
```

### Custom command names

Customized command names can be provided, to avoid conflicts with other similarly named functions. See below for an example where another `hello` function is registered.

```python
# Server-side
def hello():
    """Hides from the user."""
    return "Nothing to see!"

s.register(hello, "hello_world")

# Client-side
c.hello()  # returns "Hello world!"
c.hello_world()  # returns "Nothing to see!"
```

The available commands can be checked on the client-side using the `help` command, which will page any documentation served by the server:

```python
c.help()
# Available calls: ['hello', 'hello_world']
# Available properties: []

c.help("hello_world")
# Hides from the user.
```

Clients internally call the function `Client.call()` that handles the session and the communication. These four function calls are functionally equivalent:

```python
c.hello("pluto")
c.call("hello", "pluto")

# Using a keyword argument
c.hello(name="pluto")
c.call("hello", name="pluto")
```

This also means the server should avoid defining the `call` command.

### Server initialization syntax

Note that a faster equivalent is to supply the server with the desired functions directly, with optional custom names supplied in a 2-tuple. The example below registers the commands `hello` and `hello_world` that are tied to `hello()` and `hello2()` correspondingly.

```python
Server(hello, (hello2, "hello_world"), address=...).run()
```

### Session management

Session management is automatically handled by the client. In the event where the server is temporarily unavailable or restarted, the client will automatically recreate a fresh connection under-the-hood to query the server hosted at the same port. This includes scenarios where a client request is made:

* Before the server starts listening.
* After the server has restarted.
* While the server is busy serving another client.

### Service exposure

By default, the server is initialized with a default port of 4440 and listens on all interfaces, i.e. `0.0.0.0` or `*`. Upon calling `Server.run()`, a hint for clients connecting to the server is printed, which includes the IP address of the default interface that the server is likely reachable at:

```
Address: 0.0.0.0:4440 []
Registered calls: ['hello']
Auxiliary calls: ['help', 'close']

>>> from kochen.ipcutil import Client
>>> c = Client(address='192.168.1.10')
>>> c.help('hello')
>>> c.hello(...)

2025-07-25 15:05:38,900 INFO    run:135 | Server listening...
```

To expose the server to only localhost, use the `localhost` or `127.0.0.1` address. Clients by default also only connect to localhost.

## Advanced usage

One main intention of this client-server pair is to allow devices to be mocked on the local host. Consider the following workflow on the remote host:

```python
from qodevices.homemade.powermeter import Powermeter

device = "/dev/serial/by-id/usb-CQT-Powermeter-QO100"
pm = Powermeter(device=device)
pm.identity  # returns device identity (@property)
pm.range = 3  # sets sensitivity (@property.setter)
v = pm.read_voltage(samples=20)  # measures photodiode voltage, regular function
```

The corresponding remote workflow involves tagging the device to the server...

```python
# Server-side
from qodevices.homemade.powermeter import Powermeter

device = "/dev/serial/by-id/usb-CQT-Powermeter-QO100"
pm = Powermeter(device=device)
Server(pm, address="192.168.1.10").run()
```

...so that the client can behave functionally like the local device itself:

```python
# Client-side
from qodevices.homemade.powermeter import Powermeter

pm = Client(Powermeter, address="192.168.1.10")
pm.identity
pm.range = 3
v = pm.read_voltage(samples=20)
```

That's about it :)

### Class introspection by client

To emulate the device class behaviour, the class should be supplied to the client whenever possible. This has two main benefits:

* Argument checks can be done by the client itself without needing a server for validation.
* Properties can be picked up and directly exposed by the client.

Clients without access to the class can still query the server with the appropriate commands as usual. Property getters and setters are automatically exposed as the commands `get_{prop}()` and `set_{prop}(...)`.

```python
# Client-side
pm = Client(address="192.168.1.10")
pm.get_identity()
pm.set_range(3)
v = pm.read_voltage(samples=20)
```

### Multiple instances of the same device class

The same server hosting multiple devices of the same class will cause conflicts in the command names. This also similarly applies when two device classes share the same function name. Either of three methods can be used to side-step this issue:

#### 1. Add unique prefix to each device

Note that for instances, the `name` argument is treated as a prefix instead (since the class would likely have more than one method/property).

```python
# Server-side
pm1 = Powermeter(device="/dev/ttyACM0")
pm2 = Powermeter(device="/dev/ttyACM1")
Server((pm1, "pump_"), (pm2, "signal_"), address="192.168.1.10").run()
```

This transforms the calls at the client to:

```python
# Client-side
pm = Client((Powermeter, "pump_"), (Powermeter, "signal_"), address="192.168.1.10")

pm.pump_identity
pm.pump_range = 3
pm.pump_read_voltage(samples=20)

pm.get_signal_identity()  # using direct call
pm.set_signal_range(3)
pm.signal_read_voltage(samples=20)
```

#### 2. Assign devices to unique client-server pairs

Servers must be initialized in separate scripts with unique `(address, port)`.

```python
# Server script 1
pm1 = Powermeter(device="/dev/ttyACM0")
Server(pm1, address="192.168.1.10", port=4440).run()

# Server script 2
pm2 = Powermeter(device="/dev/ttyACM1")
Server(pm2, address="192.168.1.10", port=4441).run()
```

The same client script can talk to both servers:

```python
# Client-side
pm1 = Client(Powermeter, address="192.168.1.10", port=4440)
pm2 = Client(Powermeter, address="192.168.1.10", port=4441)
```

#### 3. Implement custom functions using vanilla method

Custom functions can be implemented to distinguish/batch distinct calls, thus completely bypassing the need to mock the class:

```python
# Server-side
pm1 = Powermeter(device="/dev/ttyACM0")
pm2 = Powermeter(device="/dev/ttyACM1")

def read_voltages():
    return pm1.read_voltage(), pm2.read_voltage()

Server(read_voltages, address="192.168.1.10").run()
```

## Miscellaneous

### Data specification and flow control

Messages between server and client are encoded as a pickled tuple of type `(CtrlMsg, Any)`. Control messages plays a similar role to ICMP alongside IP, and is used to provide hints for local client behaviour, e.g. `CtrlMsg.ERROR` indicates that the data is an error message to be displayed to the user.

Client requests are processed by the server serially. Every client request will be responded with a server response as a form of ACK - requests that do not require a return value are generally responded with `(CtrlMsg.OK, None)`. Only one client may connect to the server at any one time - this avoids concurrency issues such as ambiguous device states. Serving multiple clients involve all the clients playing nice, i.e. closing connections after every query.

Session management is and should be automatically handled by the client, by means of repeated polling to establish a new connection.

### Motivation

The initial direct method is to:

1. Open an SSH connection to the remote host (e.g. with 'paramiko' in Python).
2. Run a setup script to connect to the device.
3. Query device and print to stdout/stderr, which is piped back to the local host.

This of course has associated difficulties:

1. Local user access increases the vulnerability surface, as well as overhead from establishing SSH connection.
2. Devices need to be initialized with every connection, which adds unnecessary overhead.
3. Additional parsing is needed to encode/decode the text/binary stream.

These were slowly mitigated over time:

* 2021: Running a simplified service for some 2ns timestamp cards that incurred a 1s setup timeout with every initialization, on a separate local thread in Jupyter. A simple locking mechanism was used to allow concurrent access from different plotting GUIs.
* 2023: Exposing a small bespoke TCP server querying a powermeter, for fast readout (~100ms) on remote GUIs. Custom functions had to be written to abstract between data collection and return. Data is pickled for transmission and receipt to remove need for parsing.
* 2025: Exposing multiple devices on the same server: adding automatic method loading, typing support on client. Devices now can be queried directly as if it were hosted locally.

And here we are :)
