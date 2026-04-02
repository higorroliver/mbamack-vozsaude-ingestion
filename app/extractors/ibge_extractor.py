"""
Extractor de dados demográficos — IBGE / SIDRA.

Fonte: API SIDRA do IBGE
URL: https://apisidra.ibge.gov.br/

Tabela padrão: 4714 — População residente, por sexo e idade (Censo 2022)
Localidade padrão: São Paulo (código IBGE 3550308)

Notas:
    - A API do SIDRA aceita consultas parametrizadas por tabela, variáveis,
      classificações, período e localidade.
    - Este extractor é desacoplado: funções auxiliares montam a query,
      processam a resposta e padronizam colunas.
    - Para consultar outras tabelas, basta ajustar os parâmetros no
      settings.py ou instanciar com valores diferentes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.config.settings import (
    SIDRA_BASE_URL,
    SIDRA_TABLE,
    SIDRA_LOCALIDADE,
    SIDRA_VARIABLES,
    SIDRA_PERIODO,
    IBGE_RAW_DIR,
)
from app.extractors.base import BaseExtractor
from app.utils.paths import build_raw_filepath


class IbgeExtractor(BaseExtractor):
    """Extrai dados demográficos do IBGE via API SIDRA."""

    source_name: str = "ibge"

    def __init__(
        self,
        table: str = SIDRA_TABLE,
        localidade: str = SIDRA_LOCALIDADE,
        variables: str = SIDRA_VARIABLES,
        periodo: str = SIDRA_PERIODO,
    ) -> None:
        super().__init__()
        self.table = table
        self.localidade = localidade
        self.variables = variables
        self.periodo = periodo

    # ------------------------------------------------------------------
    # Montagem da URL da API SIDRA
    # ------------------------------------------------------------------
    def _build_api_url(self) -> str:
        """
        Monta a URL completa da API SIDRA.

        Formato:
            /t/{tabela}/n6/{localidade}/v/{variáveis}/p/{período}
        
        Onde:
            - t = tabela
            - n6 = nível geográfico (município)
            - v = variáveis
            - p = período
        
        Documentação: https://apisidra.ibge.gov.br/home/ajuda
        """
        url = (
            f"{SIDRA_BASE_URL}"
            f"/t/{self.table}"
            f"/n6/{self.localidade}"
            f"/v/{self.variables}"
            f"/p/{self.periodo}"
        )
        self.logger.info("URL SIDRA montada: %s", url)
        return url

    # ------------------------------------------------------------------
    # Processamento da resposta
    # ------------------------------------------------------------------
    @staticmethod
    def _process_response(raw_data: list[dict[str, Any]]) -> pd.DataFrame:
        """
        Processa a resposta JSON da API SIDRA.

        A API retorna uma lista de dicionários onde o primeiro elemento
        contém os cabeçalhos e os demais são os dados.
        """
        if not raw_data or len(raw_data) < 2:
            raise ValueError("Resposta da API SIDRA sem dados suficientes.")

        headers = raw_data[0]
        records = raw_data[1:]

        df = pd.DataFrame(records)

        # Renomear colunas usando os cabeçalhos da primeira linha
        column_mapping = {k: v for k, v in headers.items() if k in df.columns}
        df = df.rename(columns=column_mapping)

        return df

    @staticmethod
    def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
        """
        Padroniza nomes de colunas para snake_case e remove acentos.

        Garante consistência entre diferentes consultas ao SIDRA.
        """
        import unicodedata
        import re

        def normalize_col(col: str) -> str:
            # Remove acentos
            nfkd = unicodedata.normalize("NFKD", col)
            ascii_text = nfkd.encode("ASCII", "ignore").decode("ASCII")
            # Converte para snake_case
            clean = re.sub(r"[^\w\s]", "", ascii_text)
            clean = re.sub(r"\s+", "_", clean.strip())
            return clean.lower()

        df.columns = [normalize_col(c) for c in df.columns]
        return df

    # ------------------------------------------------------------------
    # Extração
    # ------------------------------------------------------------------
    def extract(self) -> pd.DataFrame:
        """
        Consulta a API SIDRA e retorna um DataFrame padronizado.
        """
        self.logger.info(
            "Consultando SIDRA — tabela=%s, localidade=%s, variáveis=%s",
            self.table,
            self.localidade,
            self.variables,
        )

        url = self._build_api_url()
        response = self.http.get(url)
        raw_data = response.json()

        df = self._process_response(raw_data)
        df = self._standardize_columns(df)

        self._log_record_count(df)
        return df

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------
    def save_raw(self, data: pd.DataFrame) -> Path:
        """Salva o DataFrame bruto em CSV."""
        filepath = build_raw_filepath(
            output_dir=IBGE_RAW_DIR,
            source=self.source_name,
            name="demografia",
            extension="csv",
        )
        data.to_csv(filepath, index=False, encoding="utf-8-sig")
        self.logger.info("Arquivo salvo: %s (%d registros)", filepath, len(data))
        return filepath
