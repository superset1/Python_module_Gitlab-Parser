from importlib.metadata import version
from .gitlab import Find

__version__ = version("GitlabParser")
__all__ = ['Find']
