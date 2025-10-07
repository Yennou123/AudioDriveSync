# logger_utils.py
import logging, os
from paths import get_log_dir

def setup_logger(name, filename):
    log_dir = get_log_dir()
    log_path = os.path.join(log_dir, filename)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:  # éviter doublons
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        logger.addHandler(ch)

    logger.info(f"=== Logger {name} initialisé, fichier : {log_path} ===")
    return logger
