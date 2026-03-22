"""
Extractor de dados demograficos do IBGE via API SIDRA.

Fonte: API SIDRA do IBGE
URL: https://apisidra.ibge.gov.br/
Documentacao: https://apisidra.ibge.gov.br/home/ajuda

Tabelas prioritarias:
    - 4714: Populacao residente, area territorial e densidade demografica
    - 4711: Domicilios recenseados
    - 4712: Domicilios particulares permanentes ocupados, moradores e media

Notas:
    - A granularidade disponivel no SIDRA para essas tabelas e municipal
      (nivel n6). Quando a granularidade por distrito nao estiver
      disponivel, o extractor registra isso em log e segue com municipio.
    - O extractor e parametrizavel: aceita qualquer tabela, variaveis,
      periodo e localidade.
    - Os dados sao salvos em JSON bruto e CSV/Parquet tratados.
    - Preparado para expansao futura com outras tabelas do Censo 2022.
"""

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

from app.config.settings import (
    IBGE_SIDRA_PROCESSED_DIR,
    IBGE_SIDRA_RAW_DIR,
    SIDRA_BASE_URL,
    SIDRA_LOCALIDADE,
    SIDRA_PERIODO,
    SIDRA_TABELAS_PRIORITARIAS,
)
from app.extractors.base import BaseExtractor
from app.utils.paths import build_raw_filepath, ensure_dir


# ------------------------------------------------------------------
# Funcoes auxiliares (desacopladas do extractor)
# ------------------------------------------------------------------

def build_sidra_url(
    base_url: str,
    tabela: str,
    localidade: str,
    variaveis: str,
    periodo: str,
    nivel: str = "n6",
) -> str:
    """
    Monta a URL completa para consulta a API SIDRA.

    Formato:
        {base_url}/t/{tabela}/{nivel}/{localidade}/v/{variaveis}/p/{periodo}

    Args:
        base_url: URL base da API SIDRA.
        tabela: Numero da tabela (ex: "4714").
        localidade: Codigo IBGE da localidade (ex: "3550308").
        variaveis: Variaveis a consultar ("allxp" para todas, ou IDs).
        periodo: Periodo temporal ("last", "2022", etc).
        nivel: Nivel territorial ("n6" = municipio, "n10" = distrito).

    Returns:
        URL completa formatada.
    """
    return (
        f"{base_url}"
        f"/t/{tabela}"
        f"/{nivel}/{localidade}"
        f"/v/{variaveis}"
        f"/p/{periodo}"
    )


def parse_sidra_response(
    raw_data: list[dict[str, Any]],
    tabela: str,
) -> pd.DataFrame:
    """
    Processa a resposta JSON da API SIDRA em DataFrame padronizado.

    A API retorna uma lista de dicionarios onde o primeiro elemento
    contem os cabecalhos (metadados) e os demais sao registros.

    Campos de saida padronizados:
        - fonte
        - tabela_sidra
        - ano
        - id_municipio_ibge
        - nome_municipio
        - variavel
        - valor
        - unidade
        - nivel_territorial

    Args:
        raw_data: Resposta JSON bruta da API SIDRA.
        tabela: Numero da tabela consultada.

    Returns:
        DataFrame com colunas padronizadas.

    Raises:
        ValueError: Se a resposta nao contem dados suficientes.
    """
    if not raw_data or len(raw_data) < 2:
        raise ValueError(
            f"Resposta da API SIDRA para tabela {tabela} sem dados "
            f"suficientes (recebeu {len(raw_data) if raw_data else 0} "
            f"registros)."
        )

    # Primeiro registro = cabecalhos/metadados
    headers = raw_data[0]
    records = raw_data[1:]

    # Mapeamento dos codigos SIDRA para nomes padronizados
    # As chaves variam por tabela, mas os campos basicos sao consistentes
    rows: list[dict[str, Any]] = []
    for record in records:
        row = {
            "fonte": "IBGE/SIDRA",
            "tabela_sidra": tabela,
            "ano": record.get("D3N", record.get("D3C", "")),
            "id_municipio_ibge": record.get("D1C", ""),
            "nome_municipio": record.get("D1N", ""),
            "variavel": record.get("D2N", ""),
            "valor": record.get("V", ""),
            "unidade": record.get("MN", ""),
            "nivel_territorial": record.get("NN", ""),
        }
        rows.append(row)

    return pd.DataFrame(rows)


def normalize_column_name(col: str) -> str:
    """
    Normaliza nome de coluna para snake_case sem acentos.

    Args:
        col: Nome da coluna original.

    Returns:
        Nome normalizado em snake_case.
    """
    nfkd = unicodedata.normalize("NFKD", col)
    ascii_text = nfkd.encode("ASCII", "ignore").decode("ASCII")
    clean = re.sub(r"[^\w\s]", "", ascii_text)
    clean = re.sub(r"\s+", "_", clean.strip())
    return clean.lower()


class IbgeSidraExtractor(BaseExtractor):
    """
    Extrai dados demograficos do IBGE via API SIDRA.

    Suporta multiplas tabelas em uma unica execucao. Por padrao,
    extrai as tabelas prioritarias definidas em settings.py:
        - 4714 (populacao, area, densidade)
        - 4711 (domicilios recenseados)
        - 4712 (domicilios ocupados, moradores, media)
    """

    source_name: str = "ibge_sidra"

    def __init__(
        self,
        localidade: str = SIDRA_LOCALIDADE,
        periodo: str = SIDRA_PERIODO,
        tabelas: dict[str, dict[str, str]] | None = None,
    ) -> None:
        """
        Args:
            localidade: Codigo IBGE do municipio.
            periodo: Periodo temporal ("last", "2022", etc).
            tabelas: Dicionario de tabelas a extrair. Se None, usa
                     SIDRA_TABELAS_PRIORITARIAS do settings.py.
        """
        super().__init__()
        self.localidade = localidade
        self.periodo = periodo
        self.tabelas = tabelas or SIDRA_TABELAS_PRIORITARIAS
        self._raw_results: dict[str, list[dict[str, Any]]] = {}

    # ------------------------------------------------------------------
    # Extracao de uma tabela individual
    # ------------------------------------------------------------------
    def _extract_table(
        self,
        tabela_id: str,
        tabela_config: dict[str, str],
    ) -> pd.DataFrame:
        """
        Extrai dados de uma tabela especifica do SIDRA.

        Tenta primeiro no nivel municipal (n6). Registra em log
        quando a granularidade por distrito nao esta disponivel.

        Args:
            tabela_id: Numero da tabela SIDRA.
            tabela_config: Configuracao com "nome" e "variaveis".

        Returns:
            DataFrame com dados padronizados da tabela.
        """
        nome_tabela = tabela_config["nome"]
        variaveis = tabela_config["variaveis"]

        self.logger.info(
            "Extraindo tabela %s (%s) — variaveis=%s, localidade=%s",
            tabela_id,
            nome_tabela,
            variaveis,
            self.localidade,
        )

        # Granularidade municipal (n6) — unica disponivel para essas tabelas
        self.logger.info(
            "Granularidade: municipal (n6). Tabelas do Censo 2022 "
            "no SIDRA nao possuem desagregacao por distrito para "
            "estas variaveis."
        )

        url = build_sidra_url(
            base_url=SIDRA_BASE_URL,
            tabela=tabela_id,
            localidade=self.localidade,
            variaveis=variaveis,
            periodo=self.periodo,
            nivel="n6",
        )
        self.logger.info("URL SIDRA montada: %s", url)

        response = self.http.get(url)
        raw_data: list[dict[str, Any]] = response.json()

        # Guardar dados brutos por tabela
        self._raw_results[tabela_id] = raw_data

        df = parse_sidra_response(raw_data, tabela_id)
        self.logger.info(
            "Tabela %s: %d registro(s) extraido(s).",
            tabela_id,
            len(df),
        )
        return df

    # ------------------------------------------------------------------
    # Extracao principal
    # ------------------------------------------------------------------
    def extract(self) -> pd.DataFrame:
        """
        Extrai todas as tabelas prioritarias e concatena em um
        unico DataFrame.

        Returns:
            DataFrame com dados de todas as tabelas concatenados.
        """
        self.logger.info(
            "Iniciando extracao SIDRA — %d tabela(s): %s",
            len(self.tabelas),
            ", ".join(self.tabelas.keys()),
        )

        all_dataframes: list[pd.DataFrame] = []
        errors: list[str] = []

        for tabela_id, tabela_config in self.tabelas.items():
            try:
                df = self._extract_table(tabela_id, tabela_config)
                all_dataframes.append(df)
            except Exception as exc:
                self.logger.error(
                    "Erro na extracao da tabela %s: %s",
                    tabela_id,
                    exc,
                )
                errors.append(f"Tabela {tabela_id}: {exc}")

        if not all_dataframes:
            raise RuntimeError(
                f"Nenhuma tabela foi extraida com sucesso. "
                f"Erros: {'; '.join(errors)}"
            )

        if errors:
            self.logger.warning(
                "Algumas tabelas falharam: %s", "; ".join(errors),
            )

        combined = pd.concat(all_dataframes, ignore_index=True)
        combined.columns = [normalize_column_name(c) for c in combined.columns]

        self.logger.info(
            "Total combinado: %d registro(s) de %d tabela(s).",
            len(combined),
            len(all_dataframes),
        )
        self._log_record_count(combined)
        return combined

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------
    def save_raw(self, data: pd.DataFrame) -> Path:
        """
        Salva dados em multiplos formatos:
        1. JSON bruto (resposta completa por tabela) em raw/
        2. CSV tratado (consolidado) em processed/
        3. Parquet tratado (consolidado) em processed/

        Retorna o caminho do CSV principal.
        """
        # 1. JSON bruto por tabela
        for tabela_id, raw_data in self._raw_results.items():
            json_path = build_raw_filepath(
                output_dir=IBGE_SIDRA_RAW_DIR,
                source=self.source_name,
                name=f"sidra_t{tabela_id}",
                extension="json",
            )
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(raw_data, f, ensure_ascii=False, indent=2)
            self.logger.info(
                "JSON bruto salvo: %s (tabela %s, %d registros)",
                json_path,
                tabela_id,
                len(raw_data) - 1,  # desconta cabecalho
            )

        # 2. CSV tratado (consolidado)
        csv_path = build_raw_filepath(
            output_dir=ensure_dir(IBGE_SIDRA_PROCESSED_DIR),
            source=self.source_name,
            name="demografia_consolidado",
            extension="csv",
        )
        data.to_csv(csv_path, index=False, encoding="utf-8-sig")
        self.logger.info(
            "CSV tratado salvo: %s (%d registros)", csv_path, len(data),
        )

        # 3. Parquet tratado (consolidado)
        parquet_path = build_raw_filepath(
            output_dir=IBGE_SIDRA_PROCESSED_DIR,
            source=self.source_name,
            name="demografia_consolidado",
            extension="parquet",
        )
        data.to_parquet(parquet_path, index=False, engine="pyarrow")
        self.logger.info(
            "Parquet tratado salvo: %s (%d registros)",
            parquet_path,
            len(data),
        )

        self._log_record_count(data)
        return csv_path
