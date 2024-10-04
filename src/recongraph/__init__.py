import logging


logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
formatter = logging.Formatter('{levelname:8s} [{name:40s}]::\t{message}', style='{')

logger.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
logger.addHandler(ch)