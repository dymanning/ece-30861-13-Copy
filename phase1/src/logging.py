import logging
import os
import sys


def validate_log_file():
    log_file = os.getenv("LOG_FILE")

    if not log_file:
        print("ERROR: LOG_FILE environment variable is missing", file=sys.stderr)
        sys.exit(1)

    # 1. File must already exist
    if not os.path.isfile(log_file):
        print(f"ERROR: Log file does not exist: {log_file}", file=sys.stderr)
        sys.exit(1)

    # 2. Must be writable
    if not os.access(log_file, os.W_OK):
        print(f"ERROR: Log file is not writable: {log_file}", file=sys.stderr)
        sys.exit(1)

    return log_file


def setup_logger(log_file, log_level_str="0"):
    try:
        log_level = int(os.getenv("LOG_LEVEL", log_level_str))
    except ValueError:
        log_level = 0

    if log_level == 0:
        level = logging.CRITICAL
    elif log_level == 1:
        level = logging.INFO
    elif log_level == 2:
        level = logging.DEBUG
    else:
        level = logging.CRITICAL

    logging.basicConfig(
        filename=log_file,
        level=level,
        format="%(asctime)s : %(levelname)s : %(message)s"
    )

    logger = logging.getLogger("metric_logger")

    # Emit a sanity log message so tests see output
    if level == logging.INFO:
        logger.info("Logger initialized at INFO level")
    elif level == logging.DEBUG:
        logger.debug("Logger initialized at DEBUG level")

    return logger
