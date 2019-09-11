import pkg_resources

from . import helper
#from . import Andrew

# lift some files up in the namespace

from ._version import get_versions
__full_version__ = get_versions()
__version__ = __full_version__['version']
del get_versions
