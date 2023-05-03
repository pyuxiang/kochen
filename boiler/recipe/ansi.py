#/usr/bin/env python3
# Justin, 2023-05-03
# Experiments with cross-platform ANSI colors
#
# 4-bit color support only, using ANSI escapes, i.e.
#   Colors: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE (+ RESET)
#     - Extended: LIGHT{{color}}_EX 
#   Styles: DIM, NORMAL, BRIGHT (+ RESET_ALL)
#   Positioning: UP, DOWN, FORWARD, BACK, POS
#
# Note this may conflict with accessibility requirements, e.g.
# VSCode may change the colors to achieve a minimum contrast ratio, see:
# https://github.com/microsoft/vscode/issues/146168#issuecomment-1080762526

import re

import colorama

try:
    colorama.just_fix_windows_console()
    COLORAMA_INIT = False
except AttributeError:
    colorama.init()
    COLORAMA_INIT = True

RE_ANSIESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

def style(text, fg=None, bg=None, style=None, clear=False, up=0):
    """Returns text with ANSI wrappers for each line.
    
    Special note on newlines, where lines are broken up to apply
    formatting on individual lines, excluding the newline character.

    Position of start of print can be controlled using the 'up' arg.

    Usage:
        >>> print(s("hello\nworld", fg="red", style="dim"))
        hello
        world
    """
    # Construct formatting
    fmt = ""
    for c, cls in zip((fg, bg), (colorama.Fore, colorama.Back)):
        if c:
            c = c.upper()
            if c.startswith("LIGHT"):
                c += "_EX"
            fmt += getattr(cls, c)
    if style:
        fmt += getattr(colorama.Style, style.upper())

    # Force clear lines
    if clear:
        fmt = colorama.ansi.clear_line() + fmt
    
    # Break by individual lines to apply formatting
    lines = text.split("\n")
    lines = [f"{fmt}{line}{colorama.Style.RESET_ALL}" for line in lines]
    text = "\n".join(lines)

    # Apply move and restore position
    # Assuming Cursor.DOWN will stop at bottom of current terminal printing
    # Non-positive numbers are treated strangely.
    if up > 0:
        text = colorama.Cursor.UP(up) + text + colorama.Cursor.DOWN(up)
    return text

def strip_ansi(text):
    return RE_ANSIESCAPE.sub("", text)

def len_ansi(text):
    """Returns length after removing ANSI codes."""
    return len(strip_ansi(text))
