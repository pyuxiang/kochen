import signal


class PostponeTermination:
    """Catches existing signals, then reraise at end of context.

    Useful for cases where the current process absolutely cannot be interrupted,
    e.g., buffer or status writes. This is particularly useful for devices that
    interface over pyUSB, which may cause some weird race conditions and glitched
    USB registers.

    Examples:
        >>> with PostponeTermination():
        ...     pass  # uninterruptible execution here
    """

    def handler(self, signum, frame):
        self.recv_signal = signum

    def __init__(self):
        self.recv_signal = None

    def __enter__(self):
        self.SIGINT_handler = signal.signal(signal.SIGINT, self.handler)
        self.SIGTERM_handler = signal.signal(signal.SIGTERM, self.handler)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signal.signal(signal.SIGINT, self.SIGINT_handler)
        signal.signal(signal.SIGTERM, self.SIGTERM_handler)
        if self.recv_signal is not None:
            signal.raise_signal(self.recv_signal)
