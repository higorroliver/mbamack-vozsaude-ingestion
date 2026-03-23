"""
Módulo de persistência genérica de arquivos.

Centraliza funções de leitura e escrita que podem ser reaproveitadas
por diferentes extractors ou camadas do pipeline.

Preparado para futura integração com S3 / Data Lake.
"""

from pathlib import Path
from typing import Any

import pandas as pd

from app.utils.logger import get_logger

logger = get_logger(__name__)


def save_dataframe_csv(
    df: pd.DataFrame,
    filepath: Path,
    encoding: str = "utf-8-sig",
    index: bool = False,
) -> Path:
    """Salva um DataFrame em CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath, index=index, encoding=encoding)
    logger.info("CSV salvo: %s (%d registros)", filepath, len(df))
    return filepath


def save_dataframe_parquet(
    df: pd.DataFrame,
    filepath: Path,
    index: bool = False,
) -> Path:
    """Salva um DataFrame em Parquet (requer pyarrow)."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(filepath, index=index, engine="pyarrow")
    logger.info("Parquet salvo: %s (%d registros)", filepath, len(df))
    return filepath


def load_csv(filepath: Path, **kwargs: Any) -> pd.DataFrame:
    """Carrega um CSV em DataFrame."""
    logger.info("Carregando CSV: %s", filepath)
    df = pd.read_csv(filepath, **kwargs)
    logger.info("CSV carregado: %d registros", len(df))
    return df


def load_parquet(filepath: Path, **kwargs: Any) -> pd.DataFrame:
    """Carrega um Parquet em DataFrame."""
    logger.info("Carregando Parquet: %s", filepath)
    df = pd.read_parquet(filepath, **kwargs)
    logger.info("Parquet carregado: %d registros", len(df))
    return df


# ---------------------------------------------------------------------------
# Futuro: integração com S3
# ---------------------------------------------------------------------------
# def save_to_s3(filepath: Path, bucket: str, key: str) -> str:
#     """Upload de arquivo local para S3."""
#     import boto3
#     s3 = boto3.client("s3")
#     s3.upload_file(str(filepath), bucket, key)
#     s3_path = f"s3://{bucket}/{key}"
#     logger.info("Arquivo enviado para S3: %s", s3_path)
#     return s3_path
