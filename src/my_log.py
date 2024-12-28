import os
import os.path
import sys
import logging
from logging.handlers import RotatingFileHandler

GLOBAL_LOGGER_FORMAT = '[%(asctime)s][%(name)s][%(thread)s][%(threadName)s][%(levelname)s]%(message)s (%(filename)s:%(lineno)d)'
GLOBAL_DATE_FMT = '%Y-%m-%d %H:%M:%S'


class ColorFormatter(logging.Formatter):
    if os.name == 'nt':
        white = "\x1b[97m"
        green = "\x1b[92m"
        yellow = "\x1b[93m"
        red = "\x1b[91m"
        reset = ""
    else:
        white = "\x1b[97m"
        green = "\x1b[38;20m"
        yellow = "\x1b[33;20m"
        red = "\x1b[31;20m"
        reset = "\x1b[0m"

    format = GLOBAL_LOGGER_FORMAT

    FORMATS = {
        logging.DEBUG: logging.Formatter(white + format + reset, datefmt=GLOBAL_DATE_FMT),
        logging.INFO: logging.Formatter(green + format + reset, datefmt=GLOBAL_DATE_FMT),
        logging.WARNING: logging.Formatter(yellow + format + reset, datefmt=GLOBAL_DATE_FMT),
        logging.ERROR: logging.Formatter(red + format + reset, datefmt=GLOBAL_DATE_FMT),
        logging.CRITICAL: logging.Formatter(red + format + reset, datefmt=GLOBAL_DATE_FMT),
    }

    default_formatter_when_not_found_level = FORMATS[logging.INFO]

    def format(self, record):
        formatter = self.FORMATS.get(record.levelno, self.default_formatter_when_not_found_level)
        return formatter.format(record)


def get_or_create_logger(
        name: str,
        std_color: bool = True,
        std_level: int = logging.DEBUG,
        abs_log_folder: str = None,
):
    logger = logging.getLogger(name)

    if logger.hasHandlers():
        return logger

    color_formatter = ColorFormatter()
    log_formatter = logging.Formatter(GLOBAL_LOGGER_FORMAT)

    std_handler = logging.StreamHandler(sys.stdout)
    std_handler.setLevel(std_level)
    std_handler.setFormatter(color_formatter if std_color else log_formatter)
    logger.addHandler(std_handler)

    if abs_log_folder is not None:
        abs_log_folder = os.path.abspath(abs_log_folder)
        if os.path.exists(abs_log_folder) is False:
            os.makedirs(abs_log_folder)

        info_log_path = os.path.join(abs_log_folder, 'InfoLog.txt')
        info_log_handle = RotatingFileHandler(info_log_path, maxBytes=2097152, delay=False, backupCount=10,
                                              encoding='utf-8')
        info_log_handle.setLevel(logging.INFO)
        info_log_handle.setFormatter(log_formatter)

        warning_log_path = os.path.join(abs_log_folder, 'WarningLog.txt')
        warning_log_handle = RotatingFileHandler(warning_log_path, maxBytes=2097152, delay=False, backupCount=10,
                                                 encoding='utf-8')
        warning_log_handle.setLevel(logging.WARNING)
        warning_log_handle.setFormatter(log_formatter)

        logger.addHandler(info_log_handle)
        logger.addHandler(warning_log_handle)

    logger.setLevel(std_level)

    return logger
