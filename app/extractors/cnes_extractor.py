"""
Extractor de dados de estabelecimentos de saúde — CNES / DATASUS.

Fonte: API pública de Dados Abertos do DATASUS
Endpoint: https://apidadosabertos.saude.gov.br/cnes/estabelecimentos

Filtra UBS (tipo 05) no município de São Paulo (IBGE 355030).

Notas:
    - A API pagina os resultados; este extractor percorre todas as páginas.
    - Se a API estiver indisponível, o extractor registra o erro e falha de
      forma controlada.
    - Para expandir para outros tipos de unidade, altere CNES_TIPO_UNIDADE
      no settings.py ou passe via variável de ambiente.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.config.settings import (
    CNES_BASE_URL,
    CNES_MUNICIPIO_CODE,
    CNES_TIPO_UNIDADE,
    CNES_PAGE_LIMIT,
    CNES_RAW_DIR,
)
from app.extractors.base import BaseExtractor
from app.utils.paths import build_raw_filepath


class CnesExtractor(BaseExtractor):
    """Extrai dados de UBS a partir da API CNES / DATASUS."""

    source_name: str = "cnes"

    def __init__(
        self,
        municipio_code: str = CNES_MUNICIPIO_CODE,
        tipo_unidade: str = CNES_TIPO_UNIDADE,
    ) -> None:
        super().__init__()
        self.municipio_code = municipio_code
        self.tipo_unidade = tipo_unidade

    # ------------------------------------------------------------------
    # Extração
    # ------------------------------------------------------------------
    def extract(self) -> pd.DataFrame:
        """
        Consulta a API CNES paginando todos os resultados.

        Retorna um DataFrame consolidado com os estabelecimentos.
        """
        self.logger.info(
            "Consultando API CNES — município=%s, tipo=%s",
            self.municipio_code,
            self.tipo_unidade,
        )

        all_records: list[dict] = []
        offset = 0

        while True:
            params = {
                "codigo_municipio": self.municipio_code,
                "codigo_tipo_unidade": self.tipo_unidade,
                "limit": CNES_PAGE_LIMIT,
                "offset": offset,
            }

            response = self.http.get(CNES_BASE_URL, params=params)
            data = response.json()

            # A API retorna uma lista diretamente
            records = data if isinstance(data, list) else data.get("estabelecimentos", [])

            if not records:
                self.logger.info("Sem mais registros na página offset=%d.", offset)
                break

            all_records.extend(records)
            self.logger.info(
                "Página offset=%d — %d registros obtidos (total acumulado: %d)",
                offset,
                len(records),
                len(all_records),
            )

            # Se retornou menos que o limite, é a última página
            if len(records) < CNES_PAGE_LIMIT:
                break

            offset += CNES_PAGE_LIMIT

        df = pd.DataFrame(all_records)
        self._log_record_count(df)
        return df

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------
    def save_raw(self, data: pd.DataFrame) -> Path:
        """Salva o DataFrame bruto em CSV."""
        filepath = build_raw_filepath(
            output_dir=CNES_RAW_DIR,
            source=self.source_name,
            name="cnes_ubs",
            extension="csv",
        )
        data.to_csv(filepath, index=False, encoding="utf-8-sig")
        self.logger.info("Arquivo salvo: %s (%d registros)", filepath, len(data))
        return filepath
