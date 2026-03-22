"""
Extractor de distritos oficiais do IBGE via API de Localidades.

Fonte: API de Localidades do IBGE
URL: https://servicodados.ibge.gov.br/api/v1/localidades
Documentacao: https://servicodados.ibge.gov.br/api/docs/localidades

Este extractor consulta a rota de distritos por municipio e retorna
os distritos oficiais do IBGE para uso como dimensao territorial de
referencia no projeto Vozes da Saude.

Campos extraidos:
    - id_distrito_ibge
    - nome_distrito_ibge
    - id_municipio_ibge
    - nome_municipio
    - sigla_uf

Notas:
    - Sera usado para padronizar nomes de distrito e apoiar o
      relacionamento entre GeoSampa, IPVS e UBS.
    - A normalizacao textual remove acentos e converte para minusculas
      para facilitar comparacoes futuras.
"""

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

from app.config.settings import (
    IBGE_LOCALIDADES_BASE_URL,
    IBGE_LOCALIDADES_PROCESSED_DIR,
    IBGE_LOCALIDADES_RAW_DIR,
    IBGE_MUNICIPIO_ID,
)
from app.extractors.base import BaseExtractor
from app.utils.paths import build_raw_filepath, ensure_dir


class IbgeLocalidadesExtractor(BaseExtractor):
    """Extrai distritos oficiais do IBGE via API de Localidades."""

    source_name: str = "ibge_localidades"

    def __init__(
        self,
        municipio_id: str = IBGE_MUNICIPIO_ID,
    ) -> None:
        super().__init__()
        self.municipio_id = municipio_id

    # ------------------------------------------------------------------
    # Consulta a API
    # ------------------------------------------------------------------
    def get_districts_by_municipality(
        self, municipio_id: int | str,
    ) -> list[dict[str, Any]]:
        """
        Consulta a API de Localidades do IBGE para obter distritos
        de um municipio.

        Args:
            municipio_id: Codigo IBGE do municipio (ex: 3550308).

        Returns:
            Lista de dicionarios com os dados brutos dos distritos.

        Raises:
            ValueError: Se a resposta estiver vazia.
            requests.HTTPError: Se a API retornar erro HTTP.
        """
        url = (
            f"{IBGE_LOCALIDADES_BASE_URL}"
            f"/municipios/{municipio_id}/distritos"
        )
        self.logger.info(
            "Consultando API de Localidades IBGE: %s", url,
        )

        response = self.http.get(url)
        raw_data: list[dict[str, Any]] = response.json()

        if not raw_data:
            raise ValueError(
                f"API de Localidades retornou lista vazia para "
                f"municipio {municipio_id}."
            )

        self.logger.info(
            "API retornou %d distrito(s) para municipio %s.",
            len(raw_data),
            municipio_id,
        )
        return raw_data

    # ------------------------------------------------------------------
    # Parsing e transformacao
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_districts(raw_data: list[dict[str, Any]]) -> pd.DataFrame:
        """
        Transforma a resposta bruta da API em DataFrame com colunas
        padronizadas.

        Campos resultantes:
            - id_distrito_ibge
            - nome_distrito_ibge
            - id_municipio_ibge
            - nome_municipio
            - sigla_uf
        """
        records: list[dict[str, Any]] = []
        for district in raw_data:
            municipio = district.get("municipio", {})
            # Navega pela hierarquia para obter a UF
            microrregiao = municipio.get("microrregiao", {})
            mesorregiao = microrregiao.get("mesorregiao", {})
            uf = mesorregiao.get("UF", {})

            records.append({
                "id_distrito_ibge": district.get("id"),
                "nome_distrito_ibge": district.get("nome"),
                "id_municipio_ibge": municipio.get("id"),
                "nome_municipio": municipio.get("nome"),
                "sigla_uf": uf.get("sigla"),
            })

        return pd.DataFrame(records)

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normaliza texto para comparacao: remove acentos, converte para
        minusculas e remove caracteres especiais.

        Util para join entre GeoSampa, IPVS e IBGE por nome de distrito.

        Args:
            text: Texto a ser normalizado.

        Returns:
            Texto normalizado (sem acentos, minusculo, sem caracteres
            especiais).
        """
        if not text:
            return ""
        # Remove acentos via NFKD
        nfkd = unicodedata.normalize("NFKD", text)
        ascii_text = nfkd.encode("ASCII", "ignore").decode("ASCII")
        # Minusculas e remove caracteres especiais
        clean = re.sub(r"[^\w\s]", "", ascii_text)
        clean = re.sub(r"\s+", " ", clean.strip())
        return clean.lower()

    def _add_normalized_name(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adiciona coluna com nome normalizado para comparacao."""
        df["nome_distrito_normalizado"] = df["nome_distrito_ibge"].apply(
            self.normalize_text
        )
        return df

    # ------------------------------------------------------------------
    # Extracao
    # ------------------------------------------------------------------
    def extract(self) -> pd.DataFrame:
        """
        Extrai distritos do municipio configurado e retorna DataFrame
        tratado.
        """
        self.logger.info(
            "Iniciando extracao de distritos — municipio_id=%s",
            self.municipio_id,
        )

        raw_data = self.get_districts_by_municipality(self.municipio_id)

        # Guarda dados brutos para persistencia JSON
        self._raw_json = raw_data

        df = self._parse_districts(raw_data)
        df = self._add_normalized_name(df)

        self._log_record_count(df)
        return df

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------
    def save_raw(self, data: pd.DataFrame) -> Path:
        """
        Salva dados em tres formatos:
        1. JSON bruto (resposta completa da API) em raw/
        2. CSV tratado em processed/
        3. Parquet tratado em processed/

        Retorna o caminho do JSON bruto (arquivo principal raw).
        """
        # 1. JSON bruto
        json_path = build_raw_filepath(
            output_dir=IBGE_LOCALIDADES_RAW_DIR,
            source=self.source_name,
            name="distritos",
            extension="json",
        )
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self._raw_json, f, ensure_ascii=False, indent=2)
        self.logger.info(
            "JSON bruto salvo: %s (%d distritos)",
            json_path,
            len(self._raw_json),
        )

        # 2. CSV tratado
        csv_path = build_raw_filepath(
            output_dir=ensure_dir(IBGE_LOCALIDADES_PROCESSED_DIR),
            source=self.source_name,
            name="distritos",
            extension="csv",
        )
        data.to_csv(csv_path, index=False, encoding="utf-8-sig")
        self.logger.info(
            "CSV tratado salvo: %s (%d registros)", csv_path, len(data),
        )

        # 3. Parquet tratado
        parquet_path = build_raw_filepath(
            output_dir=IBGE_LOCALIDADES_PROCESSED_DIR,
            source=self.source_name,
            name="distritos",
            extension="parquet",
        )
        data.to_parquet(parquet_path, index=False, engine="pyarrow")
        self.logger.info(
            "Parquet tratado salvo: %s (%d registros)",
            parquet_path,
            len(data),
        )

        self._log_record_count(data)
        return json_path
