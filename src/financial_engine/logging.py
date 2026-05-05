import logging

logger = logging.getLogger("financial_engine")
logger.setLevel(logging.INFO)


def log_inference(message: str):
    logger.info(message)
