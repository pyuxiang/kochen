#!/usr/bin/env python3
"""

Examples:
    $ python3 -m kochen.template my_new_python_script
"""

import datetime as dt
import pathlib
import re
import sys

TEMPLATE_DIR = "templates"
TEMPLATE_DEFAULT = "default"
MAPPING_DICT = {
    "~~~CURRENTDATE~~~": dt.datetime.now().strftime("%Y-%m-%d"),
}

# Create boilerplate code, the original purpose of this module
def main():

    # Obtain desired filename
    if len(sys.argv) <= 1:
        print("Please supply desired filename for new Python template script.")
        sys.exit(1)

    # Check if type of template supplied
    if len(sys.argv) == 2:
        template_type = ""
        filepath = pathlib.Path(sys.argv[1])
    else:
        template_type = sys.argv[1]
        filepath = pathlib.Path(sys.argv[2])
    if filepath.suffix != ".py":
        filepath = filepath.with_suffix(filepath.suffix + ".py")
    if filepath.exists():
        print(f"File '{filepath}' already exists, avoiding overwriting.")
        sys.exit(1)

    # Load default template
    src_dpath = pathlib.Path(__file__).parent / TEMPLATE_DIR
    src_fpath = src_dpath / f"{template_type}.py"
    if not src_fpath.exists():
        template_names = [path.stem for path in src_dpath.glob("*.py")]
        print(f"Template '{template_type}' not found, falling back to default.")
        print(f"Available templates: {template_names}")
        src_fpath = src_dpath / f"{TEMPLATE_DEFAULT}.py"
    with open(src_fpath, "r") as f:
        filecontents = f.read()

    for k, v in MAPPING_DICT.items():
        filecontents = re.sub(k, str(v), filecontents)

    with open(filepath, "w") as f:
        f.write(filecontents)
    print(f"File '{filepath}' successfully written.")

    # Write default configuration file as well
    configpath = filepath.with_suffix(filepath.suffix + ".default.conf")
    configpath.touch(exist_ok=True)
    sys.exit(0)

if __name__ == "__main__":
    main()
