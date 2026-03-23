"""
Configuração centralizada de logging para o projeto.

Uso:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
"""

import logging
import sys

from app.config.settings import LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger configurado com formatação padronizada."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
        formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    return logger
