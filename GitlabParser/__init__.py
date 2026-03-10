from importlib.metadata import version
from .gitlab import Find
from .logger import Logger

__version__ = version("GitlabParser")
__all__ = ['Find', 'Logger']
