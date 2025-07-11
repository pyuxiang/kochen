import argparse
import os
import pathlib
import re
import sys

import configargparse


# https://stackoverflow.com/a/23941599
class ArgparseCustomFormatter(argparse.RawDescriptionHelpFormatter):
    RAW_INDICATOR = "rawtext|"

    def _format_action_invocation(self, action):
        if not action.option_strings:
            (metavar,) = self._metavar_formatter(action, action.dest)(1)
            return metavar
        else:
            parts = []
            # if the Optional doesn't take a value, format is:
            #    -s, --long
            if action.nargs == 0:
                parts.extend(action.option_strings)

            # if the Optional takes a value, format is:
            #    -s ARGS, --long ARGS
            # change to
            #    -s, --long ARGS
            else:
                default = action.dest.upper()
                args_string = self._format_args(action, default)
                for option_string in action.option_strings:
                    # parts.append('%s %s' % (option_string, args_string))
                    parts.append("%s" % option_string)
                parts[-1] += " %s" % args_string
            return ", ".join(parts)

    def _split_lines(self, text, width):
        marker = ArgparseCustomFormatter.RAW_INDICATOR
        if text.startswith(marker):
            return text[len(marker) :].splitlines()
        return super()._split_lines(text, width)


def generate_default_parser(moduledoc, script_name=None, display_config=True):
    if script_name is None:
        script_name = pathlib.Path(sys.argv[0]).name
    parser = configargparse.ArgumentParser(
        add_config_file_help=display_config,
        default_config_files=[f"{script_name}.default.conf"],
        description=parse_docstring_description(moduledoc),
        formatter_class=ArgparseCustomFormatter,
        add_help=False,
    )
    return parser


def generate_default_parser_config(moduledoc, script_name=None, display_config=True):
    if script_name is None:
        script_name = pathlib.Path(sys.argv[0]).name
    default_config = f"{script_name}.default.conf"
    parser = configargparse.ArgumentParser(
        add_config_file_help=display_config,
        default_config_files=[default_config],
        description=parse_docstring_description(moduledoc),
        formatter_class=ArgparseCustomFormatter,
        add_help=False,
    )
    return parser, default_config


def add_boilerplate_arguments(parser):
    """
    Adds '-hvL --quiet --config --save'.
    """
    pgroup_config = parser.add_argument_group("display/configuration")
    pgroup_config.add_argument(
        "-h", "--help", action="store_true", help="Show this help message and exit"
    )
    pgroup_config.add_argument(
        "-v",
        "--verbosity",
        action="count",
        default=0,
        help="Specify debug verbosity, e.g. -vv for more verbosity",
    )
    pgroup_config.add_argument(
        "-L",
        "--logging",
        metavar="",
        help="Log to file, if specified. Log level follows verbosity.",
    )
    pgroup_config.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress errors, but will not block logging",
    )
    pgroup_config.add_argument(
        "--config",
        metavar="",
        is_config_file_arg=True,
        help="Path to configuration file",
    )
    pgroup_config.add_argument(
        "--save",
        metavar="",
        is_write_out_config_file_arg=True,
        help="Path to configuration file for saving, then immediately exit",
    )
    return pgroup_config


def get_help_descriptor(display=False):
    """Returns a descriptor that is suppressed if insufficient verbosity.

    Example:
        >>> adv  = get_suppressed_help_descriptor(help_verbosity >= 2)
        >>> advv = get_suppressed_help_descriptor(help_verbosity >= 3)
        >>> parser.add_argument("-h", action="count", default=0)
        >>> parser.add_argument("-a", help=adv("parameter a"))
        >>> parser.add_argument("-b", help=advv("parameter b"))

        user:~$ ./script -h    # shows help text for only parameter a
        user:~$ ./script -hh   # shows help text for both parameters a and b

    TODO:
        Give this function a better name...
    """

    def advanced_help(description):
        return description if display else configargparse.SUPPRESS

    return advanced_help


def parse_args_or_help(parser, ignore_unknown=False, parser_func=None):
    """Boilerplate to parse arguments and print help if needed."""
    # Parse arguments - this must come before 'parser.get_source...'
    if ignore_unknown:
        args, _ = parser.parse_known_args()
    else:
        args = parser.parse_args()

    # Check whether options have been supplied, and print help otherwise
    args_sources = parser.get_source_to_settings_dict().keys()
    config_supplied = any(map(lambda x: x.startswith("config_file"), args_sources))
    if getattr(args, "help", 0) or (len(sys.argv) == 1 and not config_supplied):
        if parser_func:
            help_verbosity = 1
            if hasattr(args, "help"):
                help_verbosity = getattr(args, "help")
            parser = parser_func(help_verbosity)
        parser.print_help(sys.stderr)
        sys.exit(1)

    return args


def guarantee_path(path, type=None):
    """Checks if path is of specified type, and returns wrapper to Path."""

    assert type in (None, "f", "d", "p")  # file, directory, pipe
    path = pathlib.Path(path)

    # If no filetype specified
    # Useful for when path is expected to exist, or when it
    # doesn't make sense to create them, e.g. devices/sockets
    if type is None:
        if not path.exists():
            raise ValueError(f"Path '{path}' does not exist")
        return path

    # Filetype has been specified -> check if type matches
    if path.exists():
        if type == "f" and not path.is_file():
            raise ValueError(f"Path '{path}' is not a file")
        if type == "d" and not path.is_dir():
            raise ValueError(f"Path '{path}' is not a directory")
        if type == "p" and not path.is_fifo():
            raise ValueError(f"Path '{path}' is not a pipe")
        return path

    # Filetype specified but path does not exist -> create
    if type == "f":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    elif type == "d":
        path.mkdir(parents=True)
    elif type == "p":
        os.mkfifo(str(path))
    return path


def parse_docstring_description(docstring):
    placeholder = "~~~PLACEHOLDER~~~"
    # Remove all changelog information
    d = docstring.partition("Changelog:")[0]

    # Replace all newlines except the first
    d = re.sub(r"\n+", placeholder, d, count=1)
    d = re.sub(r"\n+", " ", d)
    d = re.sub(placeholder, "\n\n", d)
    return d


def parse_path(path, type=None):
    """Checks if path is of specified type, and returns wrapper to Path."""

    assert type in (None, "f", "d", "p")  # file, directory, pipe
    path = pathlib.Path(path)

    # If no filetype specified
    # Useful for when path is expected to exist, or when it
    # doesn't make sense to create them, e.g. devices/sockets
    if type is None:
        if not path.exists():
            raise ValueError(f"Path '{path}' does not exist")
        return path

    # Filetype has been specified -> check if type matches
    if path.exists():
        if type == "f" and not path.is_file():
            raise ValueError(f"Path '{path}' is not a file")
        if type == "d" and not path.is_dir():
            raise ValueError(f"Path '{path}' is not a directory")
        if type == "p" and not path.is_fifo():
            raise ValueError(f"Path '{path}' is not a pipe")
        return path

    # Filetype specified but path does not exist -> create
    if type == "f":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    elif type == "d":
        path.mkdir(parents=True)
    elif type == "p":
        os.mkfifo(str(path))
    return path
