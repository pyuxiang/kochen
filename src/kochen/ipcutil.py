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

import inspect
import logging
import socket
import warnings
from multiprocessing.connection import Listener, Client as _Client

# Set up logging facilities if not available
_LOGGING_FMT = "{asctime}\t{levelname:<7s}\t{funcName}:{lineno}\t| {message}"
logging.basicConfig(level=logging.DEBUG, format=_LOGGING_FMT, style="{")
logger = logging.getLogger(__name__)


def convert_to_bytes(secret):
    if secret is not None and not isinstance(secret, bytes):
        secret = str(secret).encode()
    return secret


HEALTHCHECK_OK = "200"


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


class ServerUnavailable(OSError):
    pass


class ServerClosed(OSError):
    pass


class Server:
    """A simple server class to open ports and assign function calls.

    The nice feature about multiprocessing.connection is the use of
    pickle-encoding, so almost arbitrary Python objects can be transmitted.

    Examples:
        # Server-side
        >>> def hello(name):
        ...     return "hi {}!".format(name)
        >>> s = Server("localhost", secret=1234)
        >>> s.register(hello)
        >>> s.run()

        # Client-side
        >>> c = Client("localhost", secret=1234)
        >>> c.call("hello bob")
        "hi bob!"
        >>> c.call("close")
    """

    def __init__(self, address="0.0.0.0", port=7378, secret=None):
        secret = convert_to_bytes(secret)
        if address is None or address == "*":
            address = "0.0.0.0"  # aliases for all addresses
        self.address = address
        self.port = port
        self.secret = secret
        self.restart = True
        self.registered_calls = {
            "healthcheck": None,
            "close": None,  # special message
        }

    def run(self):
        try:
            self.restart = True
            while self.restart:
                self.listener = Listener((self.address, self.port), authkey=self.secret)
                logger.debug("Server listening...")
                connection = self.listener.accept()  # blocking
                logger.debug("Accepted connection from %s", self.listener.last_accepted)
                try:
                    self._run(connection)
                finally:
                    self.listener.close()
        except KeyboardInterrupt:
            logger.debug("Server interrupted")

    def _run(self, connection):
        """Main loop while connection is maintained."""
        while True:
            # Read message
            try:
                message = connection.recv()
            except EOFError:
                logger.debug("Connection terminated by client.")
                break
            except ConnectionResetError:
                logger.debug("Connection reset by client.")
                break

            # Process message
            command, args, kwargs = message
            command = command.lower()
            is_help = False
            if command == "close":
                self.restart = False
                connection.close()
                logger.debug("Server terminated by client.")
                break
            if command == "healthcheck":
                connection.send(HEALTHCHECK_OK)
                continue
            if command == "help":
                is_help = True
                if len(args) == 0:
                    logger.info("No command provided to help.")
                    continue
                command = args[0]

            func = self.registered_calls.get(command, None)
            if func is None:
                logger.info("Command '%s' does not exist.", command)
                connection.send(f"Invalid command: '{command}'")
                continue

            if is_help:
                connection.send(func.__doc__)
                continue

            try:
                result = func(*args, **kwargs)
                if result is not None:
                    connection.send(result)
            except Exception as e:
                logger.info("Function threw error: %s", e)
                connection.send(f"Error: '{e}'")

    def register(self, name_or_func, func=None) -> bool:
        # Extract name via function inspection
        if func is None:
            name = name_or_func.__name__
            if name == "<lambda>":
                logger.error("Names must be given for anonymous functions.")
                return False
            func = name_or_func
        else:
            name = name_or_func

        name = name.lower()
        if name in self.registered_calls:
            logger.error("Function '%s' already registered.", name)
            return False

        self.registered_calls[name] = func
        return True

    def unregister(self, name):
        if name == "close":
            return
        if name not in self.registered_calls:
            logger.error("Function '%s' not registered.", name)
        del self.registered_calls[name]

    def help(self):
        """Prints client usage help."""
        aux_calls = ["help", "healthcheck", "close"]
        calls = list(map(str, self.registered_calls.keys()))
        calls = sorted(k for k in calls if k not in aux_calls)
        ip = get_ip_address()
        text = [
            f"Address: {self.address}:{self.port}",
            f"Registered calls: {calls}",
            f"Auxiliary calls: {aux_calls}",
            "",
            ">>> from kochen.ipcutil import Client",
            f">>> c = Client('{ip}', port={self.port})",
            ">>> c.healthcheck()",
        ]
        if len(calls) > 0:
            text.append(f">>> c.help('{calls[0]}')")
        if self.secret is not None:
            secret = self.secret.decode()  # convert back from bytes
            text[0] += f" (secret: {secret})"
            text[5] = text[5][:-1] + f", secret='{secret}')"

        print("\n".join(text + [""]))


class ClientInternal:
    """Only way to check if really down is to send a message."""

    def __init__(self, address="localhost", port=7378, secret=None):
        secret = convert_to_bytes(secret)
        self.address = address
        self.port = port
        self.secret = secret
        self.connection = None

    # LOW-LEVEL INTERFACES

    def read(self, blocking=True):
        if self.connection and (blocking or self.connection.poll()):
            return self.connection.recv()

    def drain(self):
        while self.connection and self.connection.poll():
            self.connection.recv()

    def is_alive(self) -> bool:
        if self.connection and not self.connection.closed:
            if self.connection.poll():
                return True
            self.connection.send(["healthcheck", (), {}])
            return self.read() == HEALTHCHECK_OK
        return False

    def connect(self):
        if self.is_alive():
            return True
        try:
            self.connection = _Client((self.address, self.port), authkey=self.secret)
            return True
        except ConnectionRefusedError:
            return False

    def close(self, server=False):
        if server:
            if self.connect():
                self.connection.send(["close", (), {}])
        if self.connection and not self.connection.closed:
            self.connection.close()

    # HIGH-LEVEL INTERFACES

    def call(self, command: str, *args, sendonly=False, **kwargs):
        if command.lower() == "close":
            sendonly = True
        if self.connect():
            self.connection.send([command, args, kwargs])
            if not sendonly:
                return self.connection.recv()

    def send(self, command: str, *args, **kwargs):
        return self.call(command, *args, sendonly=True, **kwargs)

    def receive(self, blocking=True):
        if self.connect():
            return self.read(blocking)

    def __getattr__(self, name):
        def f(*args, **kwargs):
            return self.call(name, *args, **kwargs)  # defer to remote server

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

    def __init__(self, address="localhost", port=7378, secret=None, devices=()):
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
            def create_f(name):
                def f(*args, **kwargs):
                    return getattr(self.__client, name)(*args, **kwargs)

                f.__signature__ = inspect.signature(method)
                f.__doc__ = inspect.getdoc(method)
                f.__name__ = name
                f.__qualname__ = f"{device.__name__}.{name}"
                return f

            setattr(self, name, create_f(name))

    def __repr__(self):
        names = [device.__name__ for device in self.__devices]
        pretty_names = f"[{', '.join(names)}]"
        address = f"{self.__client.address}:{self.__client.port}"
        return f"{type(self).__name__}({address}, devices={pretty_names})"

    def __getattr__(self, name):
        return getattr(self.__client, name)  # defer to internal client
