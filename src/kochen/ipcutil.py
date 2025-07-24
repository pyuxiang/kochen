#!/usr/bin/env python3
"""Opens socket for intercomputer communication.

References:
    1. <https://zeromq.org/>
    2. <https://rpyc.readthedocs.io/en/latest/index.html>
    3. <https://stackoverflow.com/questions/6920858/interprocess-communication-in-python?rq=1>

Changelog:
    2021-08-18, Justin: Init for timestamp g2 queries.
    2024-02-20, Justin: Generalize.
"""

import enum
import inspect
import logging
import socket
import sys
import time
import warnings
from multiprocessing.connection import Listener, Client as _Client

# Set up logging facilities if not available
logger = logging.getLogger(__name__)

DEFAULT_PORT = 4440
RECONNECTION_TIMEOUT = 1


class CtrlMsg(enum.Enum):
    OK = 200
    ERROR = 400
    ERROR_FORWARDED = 500
    MESSAGE = 1


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
            "healthcheck": None,
            "close": None,  # special message
        }

        # Configure root logger if no handler provided downstream, for ease of use
        # TODO: Check if the logging setup logic is correct.
        if not logger.hasHandlers():
            _LOGGING_FMT = (
                "{asctime}\t{levelname:<7s}\t{funcName}:{lineno}\t| {message}"
            )
            logging.basicConfig(level=logging.DEBUG, format=_LOGGING_FMT, style="{")

    def run(self, help: bool = True) -> None:
        """Starts the server."""
        if help:
            self.help()
        try:
            self.restart = True
            while self.restart:
                self.listener = Listener((self.address, self.port), authkey=self.secret)
                logger.info("Server listening...")
                connection = self.listener.accept()  # blocking
                logger.info("Connected: %s", self.listener.last_accepted)
                try:
                    self._run(connection)
                finally:
                    self.listener.close()
        except KeyboardInterrupt:
            logger.info("Server interrupted.")

    def _run(self, connection) -> None:
        """Main loop while connection is maintained. Do not call directly."""
        # Cache message containing available calls
        calls = list(map(str, self.registered_calls.keys()))
        cmd_text = f"Available commands: {calls}"

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
                    connection.send((CtrlMsg.MESSAGE, cmd_text))
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
                    reply = f"{reply}\n{cmd_text}"
                    connection.send((CtrlMsg.MESSAGE, reply))
                    continue
                connection.send((CtrlMsg.ERROR, reply))
                continue

            # Process valid command recognized by the server
            if is_help:
                connection.send((CtrlMsg.MESSAGE, f.__doc__))
                continue
            try:
                result = f(*args, **kwargs)
                connection.send((CtrlMsg.OK, result))
            except Exception as e:
                logger.debug("Command '%s' threw error: %s", command, e)
                connection.send((CtrlMsg.ERROR_FORWARDED, e))

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

    def help(self):
        """Prints client usage help.

        This is useful to provide a quick-start guide to connecting clients to
        the server.
        """
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
            ">>> c.healthcheck()",
        ]
        if len(calls) > 0:
            text.append(f">>> c.help('{calls[0]}')")
        if self.secret is not None:
            secret = self.secret.decode()  # convert back from bytes
            text[0] += f" (secret: {secret})"
            text[5] = text[5][:-1] + f", secret='{secret}')"
        block = "\n".join([""] + text + [""])

        # Assume interactive: avoid using logger and just directly pipe to stderr
        print(block, file=sys.stderr)


class Server(ServerInternal):
    """A simple server class to open ports and assign function calls.

    Args:
        address: IPv4 address of listening interface
        port: Listen port of interface
        secret: Symmetric key for optional encryption
        devices: List of initialized devices for introspection (see below)

    Examples:

        # Create a server for client to communicate with
        >>> def hello(name):
        ...     return "hi {}!".format(name)
        >>> server = Server("localhost", port=3000)
        >>> server
        Server(127.0.0.1:3000, devices=[])
        >>> server.register(hello)
        >>> server.run()

        # Servers can be optionally supplied with device classes, which allow
        # their methods to be reverse proxied by the server.
        >>> pm = Powermeter(...)
        >>> pm = Server("localhost", port=3000, devices=[pm])
        >>> pm
        Server(127.0.0.1:3000, devices=[Powermeter])
        >>> pm.get_voltage
        <function Powermeter.get_voltage>
        >>> pm.run()
        >>> Client("localhost", port=3000).get_voltage()
        1.000
    """

    def __init__(self, address="*", port=DEFAULT_PORT, secret=None, devices=()):
        super().__init__(address, port, secret)
        self._devices = set(devices)
        for device in devices:
            self.register(device)

    def register(self, func_or_device, name: str = None):
        # TODO: Check if __class__ can be used for direct checking
        if inspect.isfunction(func_or_device):
            return super().register(func_or_device, name)

        device = func_or_device
        if device in self._devices:
            raise ValueError(f"Device '{device}' already registered.")

        namedmethods = inspect.getmembers(device, predicate=inspect.ismethod)
        for name, method in namedmethods:
            if name.startswith("__"):
                continue  # no point forwarding magic methods

            # Warn if new method will shadow previously implemented methods
            if self.has_registered(name):
                logger.warning("Command '%s' already registered - ignored.", name)
            super().register(method, name)
        self._devices.add(device)

    def unregister(self, name_or_func_or_device):
        if isinstance(name_or_func_or_device, str) or inspect.isfunction(
            name_or_func_or_device
        ):
            return super().unregister(name_or_func_or_device)

        device = name_or_func_or_device
        if device not in self._devices:
            raise ValueError(f"Device '{device}' not registered.")

        namedmethods = inspect.getmembers(device, predicate=inspect.ismethod)
        for name, _ in namedmethods:
            if name.startswith("__"):
                continue
            super().unregister(name)
        self._devices.remove(device)

    def __repr__(self):
        names = [device.__class__.__name__ for device in self._devices]
        pretty_names = f"[{', '.join(names)}]"
        address = f"{self.address}:{self.port}"
        return f"{type(self).__name__}({address}, devices={pretty_names})"


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

        status, result = data
        if status == CtrlMsg.OK:
            return result
        if status == CtrlMsg.MESSAGE:
            print(result, file=sys.stderr)  # TODO: Do a pager
            return None

        # Error sent by server
        if status == CtrlMsg.ERROR:
            raise BadRequest(result)
        else:  # CtrlMsg.ERROR_FORWARDED
            raise result

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
    """A simple client class to communicate with servers hosting devices.

    Args:
        address: IPv4 address of remote server
        port: Listen port of remote server
        secret: Symmetric key for optional encryption
        devices: List of device classes for introspection (see below)

    Examples:

        # Create a client to communicate with the remote server
        >>> client = Client("localhost", port=3000)
        >>> client
        Client(localhost:3000, devices=[])
        >>> client.get_voltage()  # if server defines 'get_voltage()'
        1.000

        # Clients can be optionally supplied with device classes, which allow
        # for additional introspection
        >>> pm = Client("localhost", port=3000, devices=[Powermeter])
        >>> pm
        Client(localhost:3000, devices=[Powermeter])
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

            1. Accepts a set of device classes, whose methods can be exposed by
               'dir(Client(...))' and inspected using 'help', as if it were a
               local instance of the class.

            2. It hides the internal abstraction of '_Client', but its methods
               can still be called as fallback.

        Currently TypeError is not emitted if kwargs not existent. To fix this.
    """

    def __init__(self, address="localhost", port=DEFAULT_PORT, secret=None, devices=()):
        self.__client = ClientInternal(address, port, secret)
        self.__devices = devices
        for device in devices:
            self.__load_device_methods(device)

    def __load_device_methods(self, device):
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
        namedmethods = inspect.getmembers(device, predicate=inspect.isfunction)
        for name, method in namedmethods:
            if name.startswith("__"):
                continue  # no point forwarding magic methods

            # Warn if new method will shadow previously implemented methods
            if name in vars(Client):
                warnings.warn(f"'{name}' was reimplemented by '{device.__name__}'.")

            # Create an internal function with closure
            def create_f(name, signature):
                def f(*args, **kwargs):
                    # signature.bind(*args, **kwargs)  # emits TypeError if no match
                    return getattr(self.__client, name)(*args, **kwargs)

                f.__signature__ = signature
                f.__doc__ = inspect.getdoc(method)
                f.__name__ = name
                f.__qualname__ = f"{device.__name__}.{name}"
                return f

            setattr(self, name, create_f(name, inspect.signature(method)))

    def __repr__(self):
        names = [device.__name__ for device in self.__devices]
        pretty_names = f"[{', '.join(names)}]"
        address = f"{self.__client.address}:{self.__client.port}"
        return f"{type(self).__name__}({address}, devices={pretty_names})"

    def __getattr__(self, name):
        return getattr(self.__client, name)  # defer to internal client
