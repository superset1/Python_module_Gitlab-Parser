import logging
import datetime
import inspect
import os

class Logger(object):
    '''Custom Logger - Singleton'''
    
    _instance = None
    _current_logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.frame = inspect.currentframe().f_back
            self.filename = self.frame.f_code.co_filename
            self.log_file_default = f"{os.path.basename(self.filename).split('.')[0]}_{datetime.datetime.now().strftime('%Y_%m_%dT%H_%M_%S')}.log"
            self.initialized = True

    def get_logger(self, *, log_file: str=None, verbose: bool=False):
        LOG_NAME = __name__

        if log_file is None:
            log_file = self.log_file_default

        if log_file != "":
            self.LOG_FILE_INFO = f"logs/{log_file}"
            log_dir = os.path.dirname(self.LOG_FILE_INFO)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
        else:
            self.LOG_FILE_INFO = ""

        if verbose:
            LOG_FORMAT = '%(asctime)s %(levelname)s: %(message)s Debug: %(name)s %(funcName)s %(lineno)d %(module)s %(process)d %(processName)s %(relativeCreated)d %(thread)d %(threadName)s %(taskName)s'
        else:
            LOG_FORMAT = '%(asctime)s %(levelname)s: %(message)s'

        logging.basicConfig(encoding='utf-8', level=logging.ERROR, filename=self.LOG_FILE_INFO, filemode='a', format=LOG_FORMAT)

        # custom logger
        logger = logging.getLogger(LOG_NAME)
        log_formatter = logging.Formatter(LOG_FORMAT)

        # console output
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(log_formatter)
        stream_handler.setLevel(logging.CRITICAL)

        if log_file != '':
            logger.addHandler(stream_handler)

        logger.setLevel(logging.INFO)

        self.__class__._current_logger = logger

        return logger
    
    @classmethod
    def get_current_logger(cls):
        '''Get current logger'''
        return cls._current_logger

def config(*args, **kwargs) -> logging.Logger:
    """Shortcut function to get configured logger"""
    return Logger().config(*args, **kwargs)
