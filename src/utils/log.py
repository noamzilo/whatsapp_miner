import ujson as json
import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from logging import handlers
from typing import Union, Dict, Optional, Type, Any

import consts
import socket
import src.utils.repo_info as repo_info
from functools import wraps
import threading
import traceback

from src.utils.log_context_manager import logging_context_handler
from src.utils.strings import str2bool

_log_lock = threading.Lock()
_log_was_setup = False
_log_setup_location = ""


@dataclass
class OriginInfo:
    service: str
    version: str
    instance: str = socket.gethostname()


class UVJsonFormatter(logging.Formatter):
    def __init__(self, json_format: str, origin_info: Optional[OriginInfo] = None):
        super().__init__()
        self.json_keys_list = json_format.split(';')
        self.origin_info = origin_info
        self.uses_time = "asctime" in self.json_keys_list
        self.uses_exc_info = "exc_info" in self.json_keys_list

    def format(self, record: logging.LogRecord) -> str:
        exc_str = None
        if self.uses_exc_info and record.exc_info is not None:
            exc_str = self.formatException(record.exc_info)

        format_data = {k: str(v) for k, v in record.__dict__.items() if k in self.json_keys_list and v is not None }
        if self.uses_time and "asctime" not in format_data:
            format_data["asctime"] = self.formatTime(record, self.datefmt)
        if exc_str is not None:
            format_data["exc_info"] = exc_str

        extra_log_context = logging_context_handler.get_current_context()
        output = {**format_data, **extra_log_context, 'message': self._getMessage(record)}
        if self.origin_info:
            output["origin"] = self.origin_info.__dict__

        return json.dumps(output, escape_forward_slashes=False)

    def _getMessage(self, record: logging.LogRecord) -> Union[str, Dict]:
        return record.msg if isinstance(record.msg, Dict) else record.getMessage()


@contextmanager
def logging_context(logging_context_dataclass: Union[Any, Dict]):
    """
    usage:

    @dataclass
    class SpecificLoggerContext:
        arg_a: str = None
        arg_b: int = None

    logger = logging.getLogger(<LOGGER_NAME>)
    with logging_context(SpecificLoggerContext(arg_a='a', arg_b=2)):
        logger.info("hello")

    # outputs:
    # '<LOGGER_FORMAT_INFO> {"message": "hello", "arg_a": "a", "arg_b": 2}'

    """

    source_dict = logging_context_dataclass if \
        isinstance(logging_context_dataclass, dict) else logging_context_dataclass.__dict__

    filtered_dict = {}
    for k, v in source_dict.items():
        if v is not None:
            filtered_dict[k] = v
    logging_context_handler.add_context(**filtered_dict)
    yield
    logging_context_handler.remove_context()


def setup_logger(log_location=None,
                 log_name=None,
                 main_log_severity=logging.INFO,
                 console_log_severity=logging.INFO,
                 console_log_format: str=consts.LOCAL_LOGGING,
                 create_debug_log=False,
                 create_fs_log=True,
                 create_console_log=True,
                 create_remote_log=False,
                 remote_log_severity=logging.INFO,
                 origin_info: Optional[OriginInfo] = None):
    """ Configures root logger for the application. Can only be called once,
    additional calls will be ignored with a warning.

    The following environment variables can override function arguments:
     * UV_ENABLE_DEBUG_LOG (bool) - overrides create_debug_log
     * UV_ENABLE_LOCAL_LOG (bool) - overrides create_fs_log
     * UV_ENABLE_REMOTE_LOG (bool) - overrides create_remote_log
     * UV_LOCAL_LOG_SEVERITY (int) - overrides main_log_severity (WARNING - 30, INFO - 20, DEBUG - 10, etc.)
     * UV_REMOTE_LOG_SEVERITY (int) - remote_log_severity
     * LOGGING_FORMAT_ENV (str) - console_log_format

    :param log_location: Folder path where to store log files (default - `/uveye/logs/{repo_name}`
    :param log_name: File name base for the file-system based loggers (default - {repo_name})
    :param main_log_severity: Minimum severity for the local file-system based log
    :param console_log_severity: Minimum severity for the console log
    :param console_log_format: Format to use for console logging should be either `LOCAL` or `REMOTE`
    :param create_debug_log: Create additional debug-level file-system based log
    :param create_fs_log: Create human-readable file-system based log
    :param create_console_log: Create console-based log
    :param create_remote_log: Create json-based log file to be consumed by filebeat and uploaded to logz.io
    :param remote_log_severity: Minimum severity for the log to be uploaded to logz.io
    :param origin_info: Additional origin info to be appended to remote log
    """

    global _log_lock
    global _log_was_setup
    global _log_setup_location

    with _log_lock:
        if _log_was_setup:
            logging.root.warning(f"Logger was already set up, ignoring additional setup! "
                                 f"Previously initialized here: {_log_setup_location}")
            return
        logging.root.setLevel(logging.DEBUG)
        logzio_formatter = UVJsonFormatter(
            json_format='asctime;name;filename;lineno;threadName;levelname;message;exc_info',
            origin_info=origin_info)
        human_formatter = logging.Formatter('%(asctime)s - %(name)s - %(filename)s:%(lineno)d - %(thread)d - %(levelname)s - %(message)s')

        create_debug_log = str2bool(os.environ.get(consts.ENABLE_DEBUG_LOG, str(create_debug_log)))
        create_fs_log = str2bool(os.environ.get(consts.ENABLE_LOCAL_LOG, str(create_fs_log)))
        create_remote_log = str2bool(os.environ.get(consts.ENABLE_REMOTE_LOG, str(create_remote_log)))
        main_log_severity = int(os.environ.get(consts.LOCAL_LOG_MIN_SEVERITY, str(main_log_severity)))
        remote_log_severity = int(os.environ.get(consts.REMOTE_LOG_MIN_SEVERITY, str(remote_log_severity)))
        console_log_format = os.environ.get(consts.LOGGING_FORMAT_ENV, console_log_format)

        if console_log_format != consts.LOCAL_LOGGING and console_log_format != consts.REMOTE_LOGGING:
            raise Exception(f"Invalid value for console_log_format ({console_log_format}) should be either"
                            f"{consts.LOCAL_LOGGING} or {consts.REMOTE_LOGGING}")

        if create_fs_log:
            if not log_location:
                log_location = f"/uveye/logs/{repo_info.repo_name()}"

            if not log_name:
                log_name = repo_info.repo_name()

            if not os.path.isdir(log_location):
                os.makedirs(log_location)

            main_log_file = Path(log_location) / f"{log_name}.log"
            debug_log_file = Path(log_location) / f"{log_name}_debug.log"
            errors_log_file = Path(log_location) / f"{log_name}_errors.log"

            main_file_handler = handlers.RotatingFileHandler(main_log_file,
                                                             maxBytes=16 * 1024 * 1024,
                                                             backupCount=16)
            debug_file_handler = None
            if create_debug_log:
                debug_file_handler = handlers.RotatingFileHandler(debug_log_file,
                                                                  maxBytes=16 * 1024 * 1024,
                                                                  backupCount=16)
            errors_file_handler = handlers.RotatingFileHandler(errors_log_file,
                                                               maxBytes=16 * 1024 * 1024,
                                                               backupCount=16)

            if create_remote_log:
                logzio_file_handler = handlers.RotatingFileHandler(Path(log_location) / f"{log_name}_json.log",
                                                               maxBytes=4 * 1024 * 1024,
                                                               backupCount=2)
            else:
                logzio_file_handler = None

            main_file_handler.setLevel(main_log_severity)
            errors_file_handler.setLevel(logging.ERROR)
            if debug_file_handler:
                debug_file_handler.setLevel(logging.DEBUG)

            if debug_file_handler:
                debug_file_handler.setFormatter(human_formatter)
            main_file_handler.setFormatter(human_formatter)
            errors_file_handler.setFormatter(human_formatter)

            logging.root.addHandler(main_file_handler)
            if debug_file_handler:
                logging.root.addHandler(debug_file_handler)
            logging.root.addHandler(errors_file_handler)

            if logzio_file_handler:
                logzio_file_handler.setLevel(remote_log_severity)
                logzio_file_handler.setFormatter(logzio_formatter)
                logging.root.addHandler(logzio_file_handler)

        if create_console_log:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(console_log_severity)
            if console_log_format == consts.LOCAL_LOGGING:
                stream_handler.setFormatter(human_formatter)
            else:
                stream_handler.setFormatter(logzio_formatter)
            logging.root.addHandler(stream_handler)
        _log_setup_location = traceback.format_stack()
        _log_was_setup = True


def get_logger(logger_name=None):
    logger = logging.getLogger(logger_name or repo_info.repo_name())
    return logger


def log_in_out(logger=get_logger(), is_print_input=True, is_print_output=True, is_method=True, log_level=logging.DEBUG):
    """
    @param logger-
    @param is_print_input- toggle printing input arguments
    @param is_print_output- toggle printing output values
    @param is_method- True for methods, False for functions. Makes "self" not printed in case of is_print_input==True
    @param log_level-

    @returns- a decorator that logs to logger when entering or exiting the decorated function.
    Don't uglify your code!

    Usage:
    @log_in_out(is_method=False, is_print_input=False)
    def foo(a, b=5):
        return 3, a
    foo(2) --> prints
    Entered foo
    Exited foo with result (3, 2)

    class A():
        @log_in_out(is_print_output=False)
        def bar(self, c, m, y):
            return c, 6

    a = A()
    a.bar(1, 2, y=3) --> prints
    Entered bar with args=(1, 2), kwargs={y:3}
    Exited bar
    """

    def decor(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if is_print_input:
                logger.log(
                    msg=f"Entered {fn.__name__} with args={args[1:] if is_method else args}, kwargs={kwargs}",
                    level=log_level
                )
            else:
                logger.log(
                    msg=f"Entered {fn.__name__}",
                    level=log_level
                )

            result = fn(*args, **kwargs)

            if is_print_output and result is not None:
                logger.log(
                    msg=f"Exited {fn.__name__} with result {result}",
                    level=log_level,
                )
            else:
                logger.log(
                    msg=f"Exited {fn.__name__}",
                    level=log_level
                )

            return result

        return wrapper

    return decor
