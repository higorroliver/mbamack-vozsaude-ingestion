"""
Extractor de dados de vulnerabilidade social — IPVS / SEADE.

Fonte: Fundação SEADE — Índice Paulista de Vulnerabilidade Social
URL: https://repositorio.seade.gov.br/

Notas:
    - O IPVS não possui API oficial simples; a extração é feita por download
      direto de arquivo CSV hospedado no portal do SEADE.
    - Este extractor é flexível:
        1. Tenta download automático pela URL configurada.
        2. Se falhar, busca arquivo colocado manualmente no diretório de entrada
           (IPVS_INPUT_DIR).
    - Colunas mínimas esperadas são validadas após a leitura.
    - Para atualizar a URL do IPVS, ajuste IPVS_DOWNLOAD_URL no settings.py
      ou via variável de ambiente.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.config.settings import (
    IPVS_DOWNLOAD_URL,
    IPVS_INPUT_DIR,
    IPVS_RAW_DIR,
    IPVS_EXPECTED_COLUMNS,
)
from app.extractors.base import BaseExtractor
from app.utils.paths import build_raw_filepath, ensure_dir


class IpvsExtractor(BaseExtractor):
    """Extrai dados IPVS por download direto ou leitura de arquivo local."""

    source_name: str = "ipvs"

    def __init__(
        self,
        download_url: str = IPVS_DOWNLOAD_URL,
        input_dir: Path = IPVS_INPUT_DIR,
    ) -> None:
        super().__init__()
        self.download_url = download_url
        self.input_dir = input_dir

    # ------------------------------------------------------------------
    # Extração
    # ------------------------------------------------------------------
    def extract(self) -> pd.DataFrame:
        """
        Estratégia de extração em duas etapas:
        1. Tenta download automático via URL.
        2. Se falhar, busca arquivo local no diretório de entrada.
        """
        df = self._try_download()
        if df is not None:
            return df

        df = self._try_local_file()
        if df is not None:
            return df

        raise RuntimeError(
            f"[{self.source_name}] Não foi possível obter dados do IPVS. "
            f"Verifique a URL ({self.download_url}) ou coloque o arquivo CSV "
            f"manualmente em: {self.input_dir}"
        )

    def _try_download(self) -> pd.DataFrame | None:
        """
        Tenta baixar o CSV do IPVS via URL configurada.

        Nota: o portal do SEADE (repositorio.seade.gov.br) pode bloquear
        requisições automatizadas via Cloudflare. Nesse caso, o extractor
        faz fallback para leitura de arquivo local colocado manualmente
        no diretório IPVS_INPUT_DIR.
        """
        self.logger.info("Tentando download do IPVS: %s", self.download_url)
        try:
            # Usa headers de navegador para evitar bloqueio por WAF/Cloudflare
            browser_headers = {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/csv,text/plain,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            }
            response = self.http.get(
                self.download_url, headers=browser_headers
            )

            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type:
                self.logger.warning(
                    "Resposta do IPVS retornou HTML (possível bloqueio Cloudflare). "
                    "Tentando arquivo local..."
                )
                return None

            from io import StringIO

            content = response.content.decode("utf-8", errors="replace")
            df = self._read_csv_flexible(StringIO(content))
            self.logger.info("Download IPVS concluído — %d registros.", len(df))
            return df

        except Exception as exc:
            self.logger.warning(
                "Falha no download do IPVS: %s. Tentando arquivo local...", exc
            )
            return None

    def _try_local_file(self) -> pd.DataFrame | None:
        """Busca arquivo CSV no diretório de entrada manual."""
        ensure_dir(self.input_dir)
        csv_files = list(self.input_dir.glob("*.csv"))

        if not csv_files:
            self.logger.warning(
                "Nenhum arquivo CSV encontrado em: %s", self.input_dir
            )
            return None

        # Usa o arquivo mais recente
        latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)
        self.logger.info("Lendo arquivo local: %s", latest_file)

        df = self._read_csv_flexible(latest_file)
        self.logger.info("Arquivo local lido — %d registros.", len(df))
        return df

    @staticmethod
    def _read_csv_flexible(source: object) -> pd.DataFrame:
        """
        Lê CSV tentando diferentes separadores e encodings.

        Tenta ';' primeiro (comum em bases brasileiras), depois ','.
        """
        for sep in [";", ","]:
            try:
                df = pd.read_csv(source, sep=sep, dtype=str)
                if len(df.columns) > 1:
                    return df
                # Se deu apenas 1 coluna, tenta o próximo separador
                if hasattr(source, "seek"):
                    source.seek(0)
            except Exception:
                if hasattr(source, "seek"):
                    source.seek(0)
                continue

        raise ValueError("Não foi possível ler o CSV com separadores ';' ou ','.")

    def _validate_columns(self, df: pd.DataFrame) -> None:
        """Valida presença de colunas mínimas esperadas."""
        df_cols_lower = [c.lower().strip() for c in df.columns]
        missing = [
            col for col in IPVS_EXPECTED_COLUMNS
            if col.lower() not in df_cols_lower
        ]
        if missing:
            self.logger.warning(
                "Colunas esperadas ausentes no IPVS: %s. "
                "Colunas encontradas: %s",
                missing,
                list(df.columns),
            )

    @staticmethod
    def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Padroniza nomes de colunas para snake_case minúsculo."""
        import re

        def normalize(col: str) -> str:
            clean = col.strip().lower()
            clean = re.sub(r"\s+", "_", clean)
            clean = re.sub(r"[^\w]", "", clean)
            return clean

        df.columns = [normalize(c) for c in df.columns]
        return df

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------
    def save_raw(self, data: pd.DataFrame) -> Path:
        """Salva o DataFrame bruto em CSV (versão raw)."""
        data = self._standardize_columns(data)
        self._validate_columns(data)

        filepath = build_raw_filepath(
            output_dir=IPVS_RAW_DIR,
            source=self.source_name,
            name="ipvs",
            extension="csv",
        )
        data.to_csv(filepath, index=False, encoding="utf-8-sig")
        self.logger.info("Arquivo salvo: %s (%d registros)", filepath, len(data))
        self._log_record_count(data)
        return filepath
