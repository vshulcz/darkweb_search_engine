import logging
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "crawler.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filemode="a",
)


def log(msg, level="info"):
    if level == "info":
        logging.info(msg)
    elif level == "error":
        logging.error(msg)
    elif level == "debug":
        logging.debug(msg)
