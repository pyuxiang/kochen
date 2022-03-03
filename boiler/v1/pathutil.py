import pathlib
import pickle

def list_files(directory=".", callback=None, *search_patterns):
    """
    
    Args:
        directory: Path-like
        callback: Function taking in compatible filepath
        search_patterns: Multiple regex string for file search
    """
    results = []
    for filepath in pathlib.Path(directory).glob("*"):
        filename = filepath.name
        
        # Search for matching regexes
        if search_patterns:
            for pattern in search_patterns:
                if pattern.match(filename):
                    break
            else:
                continue
        
        if callback:
            results.append(callback(filepath))
    
    return results


### PICKLING ###
class FileDict:
    """ Direct interface with pickled dictionaries, primarily for
        Python configuration options. """

    def __init__(self, filepath):
        fp = pathlib.Path(filepath)
        if fp.suffix != '.obj':
            raise IOError("Expecting '.obj' file, not '{}'".format(fp.suffix))
        if not fp.exists():
            fp.touch()
            with open(filepath, "wb") as f:
                pickle.dump({}, f)
        with open(filepath, "rb") as f:
            try:
                super().__setattr__("_data", pickle.load(f))
            except:
                raise IOError("Incompatible object file.")
        assert type(self._data) is dict,\
               "Expecting pickled dict, not {}".format(type(self._data))

    def __getattr__(self, name):
        return getattr(self._data, name)

    def __setattr__(self, name, value):
        self._data[name] = value
        with open(filepath, "wb") as f:
            pickle.dump(self._data, f) # inefficient for large operations

    def __delattr__(self, name):
        del self._data[name]

    def __str__(self):
        return str(self._data)