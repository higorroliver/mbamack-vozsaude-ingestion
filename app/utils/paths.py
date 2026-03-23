"""
Utilitários para criação e padronização de caminhos de arquivos.
"""

from pathlib import Path

from app.config.settings import EXTRACTION_DATE
from app.utils.logger import get_logger

logger = get_logger(__name__)


def ensure_dir(path: Path) -> Path:
    """Cria o diretório se não existir e retorna o path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_raw_filename(
    source: str,
    name: str,
    extension: str = "csv",
    extraction_date: str | None = None,
) -> str:
    """
    Gera um nome de arquivo padronizado para dados brutos.

    Exemplo: cnes_ubs_2026-03-22.csv
    """
    dt = extraction_date or EXTRACTION_DATE
    filename = f"{name}_{dt}.{extension}"
    logger.debug("Nome de arquivo gerado: %s (fonte: %s)", filename, source)
    return filename


def build_raw_filepath(
    output_dir: Path,
    source: str,
    name: str,
    extension: str = "csv",
    extraction_date: str | None = None,
) -> Path:
    """Retorna o caminho completo para salvar um arquivo raw."""
    ensure_dir(output_dir)
    filename = build_raw_filename(source, name, extension, extraction_date)
    return output_dir / filename
