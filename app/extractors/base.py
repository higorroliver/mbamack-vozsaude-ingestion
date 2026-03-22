"""
Classe base abstrata para todos os extractors do projeto.

Define o contrato que cada extractor deve seguir:
    - extract(): lógica de extração dos dados da fonte
    - save_raw(): persistência dos dados brutos
    - run(): orquestra extract + save_raw com logging e tratamento de erros
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd

from app.utils.logger import get_logger
from app.utils.http_client import HttpClient


class BaseExtractor(ABC):
    """Classe base para extractors de dados públicos."""

    # Nome identificador da fonte (sobrescrito em cada subclasse)
    source_name: str = "base"

    def __init__(self) -> None:
        self.logger = get_logger(f"extractor.{self.source_name}")
        self.http = HttpClient()
        self._data: Any = None

    # ------------------------------------------------------------------
    # Contrato abstrato
    # ------------------------------------------------------------------
    @abstractmethod
    def extract(self) -> Any:
        """Executa a lógica de extração e retorna os dados obtidos."""
        ...

    @abstractmethod
    def save_raw(self, data: Any) -> Path:
        """Persiste os dados brutos e retorna o caminho do arquivo salvo."""
        ...

    # ------------------------------------------------------------------
    # Orquestração
    # ------------------------------------------------------------------
    def run(self) -> Path | None:
        """
        Pipeline completo: extrai e salva os dados brutos.

        Retorna o caminho do arquivo salvo ou None em caso de falha.
        """
        self.logger.info("═" * 60)
        self.logger.info("Iniciando extração: %s", self.source_name.upper())
        self.logger.info("═" * 60)

        try:
            data = self.extract()
            self._validate(data)
            saved_path = self.save_raw(data)
            self.logger.info(
                "Extração concluída com sucesso: %s → %s",
                self.source_name.upper(),
                saved_path,
            )
            return saved_path

        except Exception as exc:
            self.logger.error(
                "Falha na extração [%s]: %s", self.source_name.upper(), exc, exc_info=True
            )
            return None

    # ------------------------------------------------------------------
    # Validação genérica
    # ------------------------------------------------------------------
    def _validate(self, data: Any) -> None:
        """Validação básica dos dados extraídos."""
        if data is None:
            raise ValueError(f"[{self.source_name}] Dados retornados são None.")

        if isinstance(data, pd.DataFrame) and data.empty:
            raise ValueError(f"[{self.source_name}] DataFrame retornado está vazio.")

        if isinstance(data, (list, dict)) and len(data) == 0:
            raise ValueError(f"[{self.source_name}] Dados retornados estão vazios.")

        self.logger.info("Validação OK — dados não vazios.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _log_record_count(self, data: Any) -> None:
        """Loga a quantidade de registros extraídos."""
        if isinstance(data, pd.DataFrame):
            count = len(data)
        elif isinstance(data, list):
            count = len(data)
        elif isinstance(data, dict) and "features" in data:
            count = len(data["features"])
        else:
            count = "N/A"
        self.logger.info("Registros extraídos: %s", count)
