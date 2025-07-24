#!/usr/bin/env python3
"""Opens socket for intercomputer communication.

References:
    1. <https://zeromq.org/>
    2. <https://rpyc.readthedocs.io/en/latest/index.html>
    3. <https://stackoverflow.com/questions/6920858/interprocess-communication-in-python?rq=1>

Changelog:
    2021-08-18, Justin: Init for timestamp g2 queries.
    2024-02-20, Justin: Generalize.
    2025-07-24, Justin: Allow clients/servers to directly proxy classes/instances.
"""

import enum
import inspect
import logging
import socket
import sys
import time
import warnings
from multiprocessing.connection import Listener, Client as _Client
from pydoc import pager

# Set up logging facilities if not available
logger = logging.getLogger(__name__)

DEFAULT_PORT = 4440
RECONNECTION_TIMEOUT = 1


class CtrlMsg(enum.Enum):
    OK = 200
    ERROR = 400
    ERROR_FORWARDED = 500
    INFO = 100


class BadRequest(ValueError):
    pass


def convert_to_bytes(secret):
    if secret is not None and not isinstance(secret, bytes):
        secret = str(secret).encode()
    return secret


def get_ip_address():
    # Copied from <https://stackoverflow.com/a/28950776>
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        s.connect(("10.254.254.254", 1))  # does not need to be reachable
        ip = s.getsockname()[0]
    except:  # noqa: E722
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def parse_ip_address(address):
    """
    Raises:
        ValueError: Invalid IP address.
    """
    if address is None or address == "*":
        return "0.0.0.0"
    if address == "localhost":
        return "127.0.0.1"
    return address


def extract_methods(cls):
    # Extract using the class to avoid triggering property getter calls
    namedmethods = inspect.getmembers(cls, predicate=inspect.isfunction)
    for name, method in namedmethods:
        if name.startswith("__"):
            continue
        yield name, name, method

    # Extract properties
    namedprops = inspect.getmembers(cls, predicate=lambda x: isinstance(x, property))
    for name, prop in namedprops:
        if name.startswith("__"):
            continue
        for prefix in ("get", "set", "del"):
            _name = f"{prefix}_{name}"
            _method = getattr(prop, f"f{prefix}")
            if _method is None:
                continue
            yield _name, name, _method  # replacement, original, function


class ServerInternal:
    """See documentation for 'Server' instead.

    Notes:
        The nice feature about multiprocessing.connection is the use of
        pickle-encoding, so almost arbitrary Python objects can be transmitted.
    """

    def __init__(self, address: str = "*", port: int = DEFAULT_PORT, secret=None):
        self.address = parse_ip_address(address)
        self.port = port
        self.secret = convert_to_bytes(secret)
        self.restart = True
        self.registered_calls = {}
        self.auxiliary_calls = {
            "help": None,
            "close": None,  # special message
        }

        # Configure default logger if no handler provided downstream, for ease of use
        if not logger.hasHandlers():
            _LOGGING_FMT = (
                "{asctime}\t{levelname:<7s}\t{funcName}:{lineno}\t| {message}"
            )
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(fmt=_LOGGING_FMT, style="{"))
            logger.setLevel(logging.DEBUG)
            logger.addHandler(handler)

    def run(self, help: bool = True) -> None:
        """Starts the server."""
        if help:
            self.help_server()
        try:
            self.restart = True
            while self.restart:
                self.listener = Listener((self.address, self.port), authkey=self.secret)
                logger.info("Server listening...")
                connection = self.listener.accept()  # blocking
                logger.info("Connected: %s", self.listener.last_accepted)
                try:
                    self._r(connection)
                finally:
                    self.listener.close()
        except KeyboardInterrupt:
            logger.info("Server interrupted.")

    def _r(self, connection) -> None:
        """Main loop while connection is maintained. Do not call directly."""

        # Unwrapper for control status codes, to reduce communication overhead
        def send(ctrl_msg: CtrlMsg, data=None):
            status_code = ctrl_msg.value
            connection.send((status_code, data))

        while True:
            # Read message
            try:
                message = connection.recv()
            except EOFError:
                logger.info("Connection terminated by client.")
                break
            except ConnectionResetError:
                logger.info("Connection reset by client.")
                break

            # Process message
            command, args, kwargs = message
            command = command.lower()
            is_help = False

            # Terminate server
            if command == "close":
                self.restart = False
                connection.close()
                logger.info("Server terminated by client.")
                break

            # Send to client help information
            if command == "help":
                if len(args) == 0:  # show server registered calls
                    send(CtrlMsg.INFO, self.help_client())
                    continue

                is_help = True
                command = args[0]

            # Lookup client command call from both registered and aux tables
            f = self.registered_calls.get(
                command, self.auxiliary_calls.get(command, None)
            )
            if f is None:
                reply = f"Command '{command}' is not registered."
                if is_help:
                    reply = f"{reply}\n{self.help_client()}"
                    send(CtrlMsg.INFO, reply)
                    continue
                send(CtrlMsg.ERROR, reply)
                continue

            # Process valid command recognized by the server
            if is_help:
                doc = f.__doc__
                if doc is None:
                    doc = "No help available."
                send(CtrlMsg.INFO, doc)
                continue
            try:
                result = f(*args, **kwargs)
                send(CtrlMsg.OK, result)
            except Exception as e:
                logger.debug("Command '%s' threw error: %s", command, e)
                send(CtrlMsg.ERROR_FORWARDED, e)

    def has_registered(self, name: str) -> bool:
        return name in self.registered_calls

    def register(self, f, name=None) -> bool:
        """Registers function with the server, and returns success state.

        If the function is a lambda, a name should be provided for it.

        Examples:
            >>> def square(x):
            ...     return x**2
            >>> server.register(square)

            # Lambda functions must be given an explicit name
            >>> cube = lambda x: x**3
            >>> server.register(cube, "cube")
        """
        # Extract name via function inspection
        if name is None:
            name = f.__name__
            if name == "<lambda>":
                raise ValueError("Name must be given for anonymous functions.")

        name = name.lower()
        if self.has_registered(name):
            logger.warning("Command '%s' already registered - ignored.", name)
            return False

        self.registered_calls[name] = f
        return True

    def unregister(self, name_or_func) -> bool:
        """Removes registered function from server, and returns success state."""
        name = name_or_func
        if inspect.isfunction(name_or_func):
            name = name_or_func.__name__
            if name == "<lambda>":
                raise ValueError(
                    "Name assigned to anonymous function must be provided."
                )

        if name in self.auxiliary_calls:
            logger.warning(
                "Command '%s' is a core command that cannot be unregisterd.", name
            )
            return False
        if name not in self.registered_calls:
            logger.warning("Command '%s' already not registered - ignored.", name)
            return False

        del self.registered_calls[name]
        return True

    def help_server(self):
        """Prints client usage help.

        This is useful to provide a quick-start guide to connecting clients to
        the server.
        """
        text = self.get_help_server()
        block = "\n".join([""] + text + [""])
        # Assume interactive: avoid using logger and just directly pipe to stderr
        print(block, file=sys.stderr)

    def get_help_server(self):
        calls = list(map(str, self.registered_calls.keys()))
        calls = sorted(k for k in calls if k not in self.auxiliary_calls)
        args = []
        if self.address != "127.0.0.1":
            args.append(f"'{get_ip_address()}'")
        if self.port != DEFAULT_PORT:
            args.append(f"port={self.port}")
        _ipport = ", ".join(args)
        text = [
            f"Address: {self.address}:{self.port}",
            f"Registered calls: {calls}",
            f"Auxiliary calls: {list(self.auxiliary_calls.keys())}",
            "",
            ">>> from kochen.ipcutil import Client",
            f">>> c = Client({_ipport})",
        ]
        if len(calls) > 0:
            text.append(f">>> c.help('{calls[0]}')")
            text.append(f">>> c.{calls[0]}(...)")
        if self.secret is not None:
            secret = self.secret.decode()  # convert back from bytes
            text[0] += f" (secret: {secret})"
            text[5] = text[5][:-1] + f", secret='{secret}')"
        return text

    def help_client(self):
        calls = list(map(str, self.registered_calls.keys()))
        return f"Available commands: {calls}"


class Server(ServerInternal):
    """A simple server class to open ports and assign function calls.

    Args:
        address: IPv4 address of listening interface
        port: Listen port of interface
        secret: Symmetric key for optional encryption
        proxy: List of proxied instances for introspection (see examples below)

    Examples:

        # Create a server for client to communicate with
        >>> def hello(name):
        ...     return "hi {}!".format(name)
        >>> server = Server("localhost", port=3000)
        >>> server
        Server(127.0.0.1:3000, proxy=[])
        >>> server.register(hello)
        >>> server.run()

        # Servers can be optionally supplied with classes, which allow
        # their methods to be reverse proxied by the server.
        >>> pm = Powermeter(...)
        >>> pm = Server("localhost", port=3000, proxy=[pm])
        >>> pm
        Server(127.0.0.1:3000, proxy=[Powermeter])
        >>> pm.get_voltage
        <function Powermeter.get_voltage>
        >>> pm.run()
        >>> Client("localhost", port=3000).get_voltage()
        1.000
    """

    def __init__(self, address="*", port=DEFAULT_PORT, secret=None, proxy=()):
        super().__init__(address, port, secret)
        self.registered_props = set()

        # Auto-wrap single objects
        if type(proxy) not in (list, tuple):
            proxy = [proxy]

        self._instances = set()  # needed for server to display current proxies
        for instance in proxy:
            self.register(instance)

    def register(self, func_or_instance, name: str = None):
        if inspect.isfunction(func_or_instance):
            return super().register(func_or_instance, name)

        instance = func_or_instance
        if instance in self._instances:
            raise ValueError(f"Instance '{instance}' already registered.")

        # Extract using the class to avoid triggering property getter calls
        cls = instance.__class__
        for command, name, method in extract_methods(cls):
            f = self.__create_closure(instance, name, method)
            super().register(f, command)

            # Register property names as well
            if command != name and name not in self.registered_props:
                self.registered_props.add(name)
        self._instances.add(instance)

    def unregister(self, name_or_func_or_instance):
        if isinstance(name_or_func_or_instance, str) or inspect.isfunction(
            name_or_func_or_instance
        ):
            return super().unregister(name_or_func_or_instance)

        instance = name_or_func_or_instance
        if instance not in self._instances:
            raise ValueError(f"Instance '{instance}' not registered.")

        cls = instance.__class__
        for command, name, method in extract_methods(cls):
            super().unregister(command)

            # Unregister property names as well
            if command != name and name in self.registered_props:
                self.registered_props.remove(name)
        self._instances.remove(instance)

    def get_help_server(self):
        text = super().get_help_server()
        calls, props = self.__help_available_commands()
        text[1] = f"Registered calls: {calls}"
        if props:
            text.insert(2, f"Registered properties: {props}")

        # Dirty hack to print proxied classes
        names = [instance.__class__.__name__ for instance in self._instances]
        text[0] += f" (proxy=[{','.join(names)}])"
        return text

    def help_client(self):
        calls, props = self.__help_available_commands()
        return f"Available calls: {calls}\nAvailable properties: {props}"

    def __help_available_commands(self):
        _calls = list(map(str, self.registered_calls.keys()))
        props = list(map(str, self.registered_props))
        calls = []
        for call in _calls:
            if call.startswith("get_") and call[4:] in props:
                continue
            if call.startswith("set_") and call[4:] in props:
                continue
            calls.append(call)
        return calls, props

    def __create_closure(self, instance, name, method):
        signature = inspect.signature(method)
        doc = inspect.getdoc(method)

        def f(*args, **kwargs):
            signature.bind(instance, *args, **kwargs)  # emits TypeError if no match
            return method(instance, *args, **kwargs)

        f.__signature__ = signature
        f.__doc__ = doc
        f.__name__ = name
        f.__qualname__ = f"{instance.__class__.__name__}.{name}"
        return f

    def __repr__(self):
        names = [instance.__class__.__name__ for instance in self._instances]
        pretty_names = f"[{', '.join(names)}]"
        address = f"{self.address}:{self.port}"
        return f"{type(self).__name__}({address}, proxy={pretty_names})"


class ClientInternal:
    """See documentation for 'Client' instead."""

    def __init__(self, address="localhost", port=DEFAULT_PORT, secret=None):
        self.address = parse_ip_address(address)
        self.port = port
        self.secret = convert_to_bytes(secret)
        self.connection = None

    # TRANSPORT LAYER

    def read_raw(self, blocking=True):
        """Reads from connection directly.

        If non-blocking read is triggered, a read will be attempted only if
        there is available data to be read. Note connection needs to be
        initialized first via 'connect()'.
        """
        if not blocking and not self.connection.poll():
            return None
        return self.connection.recv()

    def write(self, command: str, *args, **kwargs):
        """Writes to connection directly."""
        self.connection.send([command, args, kwargs])

    def drain(self):
        """Clears connection message queue."""
        while self.connection.poll():
            self.connection.recv()

    def read(self, blocking=True):
        """Read result from server, raising errors if necessary.

        This user-facing call is transparent to the status messages.
        """
        if (data := self.read_raw(blocking)) is None:
            return None

        status_code, result = data
        status = CtrlMsg(status_code)
        if status is CtrlMsg.OK:
            return result
        if status is CtrlMsg.INFO:
            pager(result)
            return None

        # Error sent by server
        if status is CtrlMsg.ERROR:
            raise BadRequest(result)
        elif status is CtrlMsg.ERROR_FORWARDED:
            raise result
        else:
            raise RuntimeError(f"Unexpected status code: '{status}'")

    # SESSION LAYER

    def is_closed(self):
        return self.connection is None or self.connection.closed

    def connect(self) -> bool:
        """Checks if connection is opened, or create it otherwise."""
        # Assume available connection is always valid
        if not self.is_closed():
            return True

        # ConnectionRefusedError: server cannot be reached
        try:
            self.connection = _Client(
                (self.address, self.port),
                authkey=self.secret,
            )
            return True
        except ConnectionRefusedError:
            return False

    def close(self, server: bool = False):
        """Closes the session, and optionally terminate the server."""
        if server and self.connect():
            self.write("close")  # terminate server
        if not self.is_closed():
            self.connection.close()  # terminate client

    # APPLICATION LAYER

    def call(self, command: str, *args, **kwargs):
        """Returns result of command sent to the server.

        This call will always return a result, even if no output is expected
        from the command (which is, in this case, 'None').
        """
        while True:
            # Reattempt connection when closed
            if not self.connect():
                time.sleep(RECONNECTION_TIMEOUT)
                continue

            # BrokenPipeError: server dropped connection
            try:
                self.write(command, *args, **kwargs)
            except BrokenPipeError:
                self.close()
                continue

            # EOFError: server terminated
            # ConnectionResetError: server dropped connection (nicely)
            try:
                return self.read()
            except (EOFError, ConnectionResetError):
                self.close()
                continue

    def __getattr__(self, name):
        # Methods unknown to the client are deferred to the remote server
        def f(*args, **kwargs):
            return self.call(name, *args, **kwargs)

        return f


class Client:
    """A simple client class to call server-side commands.

    Args:
        address: IPv4 address of remote server
        port: Listen port of remote server
        secret: Symmetric key for optional encryption
        proxy: List of proxied classes for introspection (see below)

    Examples:

        # Create a client to communicate with the remote server
        >>> client = Client("localhost", port=3000)
        >>> client
        Client(localhost:3000, proxy=[])
        >>> client.get_voltage()  # if server defines 'get_voltage()'
        1.000

        # Clients can be optionally supplied with classes, which allow
        # for additional introspection
        >>> pm = Client("localhost", port=3000, proxy=[Powermeter])
        >>> pm
        Client(localhost:3000, proxy=[Powermeter])
        >>> pm.get_voltage
        <function Powermeter.get_voltage>
        >>> help(pm.get_voltage)
        get_voltage(self, size=20)
            ...
        >>> pm.get_voltage()
        1.000

    Note:
        This is a higher-level client that wraps the internal '_Client' class,
        for two main purposes:

            1. Accepts a set of classes, whose methods can be exposed by
               'dir(Client(...))' and inspected using 'help', as if it were a
               local instance of the class. This includes signature checking.

            2. It hides the internal abstraction of '_Client', but its methods
               can still be called as fallback.
    """

    def __init__(self, address="localhost", port=DEFAULT_PORT, secret=None, proxy=()):
        self.__client = ClientInternal(address, port, secret)

        # Auto-wrap single objects
        if type(proxy) not in (list, tuple):
            proxy = [proxy]

        self.__classes = set(proxy)  # needed for server to display current proxies
        for cls in self.__classes:
            self.__load_class_methods(cls)

    def __load_class_methods(self, cls):
        """
        Note:
            We want to expose the internal methods, so that it looks functionally
            the same as the original class this client wrapper is shadowing, which
            allows users to inspect it using the usual 'dir' methods. This means
            just storing a table of signatures from 'inspect.signature(method)' is
            not a complete solution.

            Since only hidden methods (i.e. starting with "__") are defined for this
            class, there is no concern of shadowing.
        """
        namedmethods = inspect.getmembers(cls, predicate=inspect.isfunction)
        for name, method in namedmethods:
            if name.startswith("__"):
                continue  # no point forwarding magic methods

            # Warn if new method will shadow previously implemented methods
            if name in vars(Client):
                warnings.warn(
                    f"'{name}' was reimplemented by '{cls.__name__}' - ignored."
                )

            setattr(self, name, self.__create_closure(cls, name, method))

        namedprops = inspect.getmembers(
            cls, predicate=lambda x: isinstance(x, property)
        )
        for name, prop in namedprops:
            if name.startswith("__"):
                continue
            # Warn if new method will shadow previously implemented methods
            if name in vars(self):
                warnings.warn(
                    f"'{name}' was reimplemented by '{cls.__name__}' - ignored."
                )

            fget = fset = None
            if prop.fget is not None:
                fget = self.__create_closure(cls, f"get_{name}", prop.fget, True)
            if prop.fset is not None:
                fset = self.__create_closure(cls, f"set_{name}", prop.fset, True)
            f = property(fget, fset)
            setattr(Client, name, f)

    def __create_closure(self, cls, name, method, class_binding=False):
        signature = inspect.signature(method)
        doc = inspect.getdoc(method)

        def f(*args, **kwargs):
            if class_binding:
                args = args[1:]  # ignore first 'self' argument
            signature.bind(None, *args, **kwargs)  # emits TypeError if no match
            return getattr(self.__client, name)(*args, **kwargs)

        f.__signature__ = signature
        f.__doc__ = doc
        f.__name__ = name
        f.__qualname__ = f"{cls.__name__}.{name}"
        return f

    def __repr__(self):
        names = [cls.__name__ for cls in self.__classes]
        pretty_names = f"[{', '.join(names)}]"
        address = f"{self.__client.address}:{self.__client.port}"
        return f"{type(self).__name__}({address}, proxy={pretty_names})"

    def __getattr__(self, name):
        return getattr(self.__client, name)  # defer to internal client
