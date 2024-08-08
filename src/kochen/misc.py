import json
import os

import yaml
from typing import Any, IO

# Honestly no idea where this came from, but I'll leave it here until dissected...

########################################
##  HACK TO RUN SCRIPT IN CWD : START ##
########################################
# Required to run module from within package directory itself, by obtaining
# reference to `orm` package using cd, then pipelining output using temp stdout
# Remember to delete this section before deployment
if __name__ == "__main__":
    pkg_name = "orm"
    import subprocess, pathlib, sys, os
    cwd = pathlib.Path.cwd()
    if cwd.stem == pkg_name: # currently still in package directory
        module_name = pathlib.Path(__file__).resolve().stem
        print(module_name)
        temp_stdout = "{}.out".format(module_name)
        with open(temp_stdout, "w") as outfile:
            cmd = "python -m {}.{}".format(pkg_name, module_name)
            subprocess.call(cmd.split(), cwd=cwd.parent, stdout=outfile)
        with open(temp_stdout, "r") as infile: print(infile.read())
        os.remove(temp_stdout)
    quit() # gracefully terminate thread
#######################################
##  HACK TO RUN SCRIPT IN CWD : END  ##
#######################################



### CLASS INSPECTION ###
import inspect
def findattr(obj, methods=True):
    # Prints all non-builtin methods/attributes of an object
    res = []
    for k in dir(obj):
        if k[0] == "_": continue # ignore built-in methods
        if (methods and inspect.isroutine(getattr(obj, k)))\
                or not (methods or inspect.isroutine(getattr(obj, k))): # attributes
            res.append(k)
    return res


# Testing Python function runtime
import timeit

def time():
    print(timeit.timeit(
        "combine(a,b)",
        "from __main__ import combine, a, b",
        number=10,
    ))
    


class Loader(yaml.SafeLoader):
    """YAML Loader with `!include` constructor.
    
    References:
    	[1]: Source, <https://gist.github.com/joshbode/569627ced3076931b02f>
    """
    def __init__(self, stream: IO) -> None:
        try:
            self._root = os.path.split(stream.name)[0]
        except AttributeError:
            self._root = os.path.curdir

        super().__init__(stream)


def construct_include(loader: Loader, node: yaml.Node) -> Any:
    filename = os.path.abspath(os.path.join(loader._root, loader.construct_scalar(node)))
    extension = os.path.splitext(filename)[1].lstrip('.')
    with open(filename, 'r') as f:
        if extension in ('yaml', 'yml'):
            return yaml.load(f, Loader)
        elif extension in ('json', ):
            return json.load(f)
        else:
            return ''.join(f.readlines())

yaml.add_constructor('!include', construct_include, Loader)
