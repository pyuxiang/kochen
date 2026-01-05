#!/usr/bin/env python3
"""Quick commands for matplotlib figures"""

from typing import Optional, List

import arrow
import matplotlib.axes as maxes
import matplotlib.dates as mdates


def set_angled_dtimes(
    ax: maxes.Axes, angle=30, format="%-d %b, %-I%P", ticks: Optional[List] = None
):
    dformat = mdates.DateFormatter(format)  # e.g. "7 Jun, 4am"
    ax.xaxis.set_major_formatter(dformat)
    if ticks is None:
        ticks = ax.get_xticks()  # pyright: ignore[reportCallIssue]
    else:
        assert len(ticks) > 0
        t = ticks[0]
        if isinstance(t, str):
            ticks = [arrow.get(t).datetime for t in ticks]
    ax.set_xticks(ticks)  # pyright: ignore[reportCallIssue]
    labels = ax.get_xticklabels()  # pyright: ignore[reportCallIssue]
    ax.set_xticklabels(labels, rotation=angle, ha="right", rotation_mode="anchor")  # pyright: ignore[reportCallIssue]
