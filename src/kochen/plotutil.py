#!/usr/bin/env python3
"""Quick commands for matplotlib figures"""

import matplotlib.axes as maxes
import matplotlib.dates as mdates


def set_angled_dtimes(ax: maxes.Axes, angle=30, format="%-d %b, %-I%P"):
    dformat = mdates.DateFormatter(format)  # e.g. "7 Jun, 4am"
    ax.xaxis.set_major_formatter(dformat)
    labels = ax.get_xticklabels()  # pyright: ignore[reportCallIssue]
    ax.set_xticklabels(labels, rotation=angle, ha="right", rotation_mode="anchor")  # pyright: ignore[reportCallIssue]
