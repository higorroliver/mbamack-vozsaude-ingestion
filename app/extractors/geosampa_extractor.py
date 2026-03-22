"""
Extractor de distritos do município de São Paulo — GeoSampa (WFS).

Fonte: Portal GeoSampa — Web Feature Service (WFS)
URL: https://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs

Camada padrão: geoportal:deinfo_distrito

Notas:
    - O WFS retorna dados geoespaciais; este extractor salva em GeoJSON.
    - CRS padrão: EPSG:4326 (WGS-84).
    - Robusto contra timeout, falhas de conexão e respostas inválidas.
    - Pronto para uso futuro em join espacial com coordenadas de UBS.
"""

import json
from pathlib import Path
from typing import Any

import geopandas as gpd

from app.config.settings import (
    GEOSAMPA_WFS_URL,
    GEOSAMPA_LAYER,
    GEOSAMPA_RAW_DIR,
)
from app.extractors.base import BaseExtractor
from app.utils.paths import build_raw_filepath


class GeosampaExtractor(BaseExtractor):
    """Extrai a camada de distritos de São Paulo via WFS do GeoSampa."""

    source_name: str = "geosampa"

    def __init__(
        self,
        wfs_url: str = GEOSAMPA_WFS_URL,
        layer: str = GEOSAMPA_LAYER,
    ) -> None:
        super().__init__()
        self.wfs_url = wfs_url
        self.layer = layer

    # ------------------------------------------------------------------
    # Extração
    # ------------------------------------------------------------------
    def extract(self) -> gpd.GeoDataFrame:
        """
        Consulta o WFS do GeoSampa e retorna um GeoDataFrame.

        Utiliza requisição GetFeature com outputFormat GeoJSON.
        """
        self.logger.info("Consultando WFS GeoSampa — camada=%s", self.layer)

        params: dict[str, str] = {
            "service": "WFS",
            "version": "1.1.0",
            "request": "GetFeature",
            "typeName": self.layer,
            "outputFormat": "application/json",
            "srsName": "EPSG:4326",
        }

        response = self.http.get(self.wfs_url, params=params)
        geojson_data = response.json()

        self._validate_geojson(geojson_data)

        gdf = gpd.GeoDataFrame.from_features(
            geojson_data["features"],
            crs="EPSG:4326",
        )

        self.logger.info("CRS dos dados: %s", gdf.crs)
        self._log_record_count(gdf)
        return gdf

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------
    def save_raw(self, data: gpd.GeoDataFrame) -> Path:
        """Salva o GeoDataFrame bruto em GeoJSON."""
        filepath = build_raw_filepath(
            output_dir=GEOSAMPA_RAW_DIR,
            source=self.source_name,
            name="distritos",
            extension="geojson",
        )

        data.to_file(filepath, driver="GeoJSON")
        self.logger.info("Arquivo salvo: %s (%d feições)", filepath, len(data))

        # Salvar metadados
        meta_path = filepath.with_suffix(".meta.json")
        meta = {
            "crs": str(data.crs),
            "total_features": len(data),
            "columns": list(data.columns),
            "layer": self.layer,
            "wfs_url": self.wfs_url,
        }
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        self.logger.info("Metadados salvos: %s", meta_path)

        return filepath

    # ------------------------------------------------------------------
    # Validações específicas
    # ------------------------------------------------------------------
    def _validate_geojson(self, data: Any) -> None:
        """Valida a estrutura básica de um GeoJSON."""
        if not isinstance(data, dict):
            raise ValueError("Resposta WFS não é um dicionário JSON válido.")

        if "features" not in data:
            raise ValueError("Resposta WFS não contém a chave 'features'.")

        if len(data["features"]) == 0:
            raise ValueError("Resposta WFS retornou 0 feições.")

        self.logger.info("GeoJSON válido — %d feições encontradas.", len(data["features"]))
