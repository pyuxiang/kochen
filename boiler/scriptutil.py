import argparse
import pathlib
import sys

import configargparse

# https://stackoverflow.com/a/23941599
class ArgparseCustomFormatter(argparse.HelpFormatter):

    RAW_INDICATOR = "rawtext|"

    def _format_action_invocation(self, action):
        if not action.option_strings:
            _ = self._metavar_formatter(action, action.dest)(1)
            print(action, _)
            metavar, = _
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
                    #parts.append('%s %s' % (option_string, args_string))
                    parts.append('%s' % option_string)
                parts[-1] += ' %s'%args_string
            return ', '.join(parts)

    def _split_lines(self, text, width):
        marker = ArgparseCustomFormatter.RAW_INDICATOR
        if text.startswith(marker):
            return text[len(marker):].splitlines()
        return super()._split_lines(text, width)

def generate_default_parser(moduledoc):
    script_name = pathlib.Path(sys.argv[0]).name
    parser = configargparse.ArgumentParser(
        default_config_files=[f"{script_name}.default.conf"],
        description=moduledoc.partition("Changelog:")[0],
        formatter_class=ArgparseCustomFormatter,
        add_help=False,
    )
    return parser


def parse_args_or_help(parser):
    """Boilerplate to parse arguments and print help if needed."""
    # Parse arguments - this must come before 'parser.get_source...'
    args = parser.parse_args()

    # Check whether options have been supplied, and print help otherwise
    args_sources = parser.get_source_to_settings_dict().keys()
    config_supplied = any(map(lambda x: x.startswith("config_file"), args_sources))
    if getattr(args, "help", None) or \
            (len(sys.argv) == 1 and not config_supplied):
        parser.print_help(sys.stderr)
        sys.exit(1)

    return args