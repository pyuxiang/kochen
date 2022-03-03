import importlib
import sys

class Print_Suppressed:
    """ Suppress print messages during module importing """
    def __enter__(self): self.restore, sys.stdout = sys.stdout, None
    def __exit__(self, *args): sys.stdout = self.restore
    
def import_pyfile(filepath):
    if not filepath.is_file(): raise FileNotFoundError(f'{filepath} does not exist.')        
    sys.path.insert(0, filepath.parent)
    with Print_Suppressed():
        try:
            module = importlib.import_module(filepath.name)
        except:
            raise RuntimeError(f'{filepath.name} cannot be imported properly.')
    # To import specific module functionality, use the getattr function
    # and check for AttributeError
    return module