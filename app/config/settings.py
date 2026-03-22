"""
Configurações centrais do projeto de ingestão de dados.

Todas as URLs, timeouts, paths e parâmetros configuráveis ficam aqui.
Para variáveis sensíveis, utilize arquivo .env na raiz do projeto.
"""

import os
from pathlib import Path
from datetime import date

from dotenv import load_dotenv

# Carrega variáveis do arquivo .env (se existir)
load_dotenv()

# ---------------------------------------------------------------------------
# Diretórios do projeto
# ---------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
DATA_DIR: Path = PROJECT_ROOT / "data"
RAW_DIR: Path = DATA_DIR / "raw"
PROCESSED_DIR: Path = DATA_DIR / "processed"

# Subpastas por fonte
CNES_RAW_DIR: Path = RAW_DIR / "cnes"
GEOSAMPA_RAW_DIR: Path = RAW_DIR / "geosampa"
IBGE_RAW_DIR: Path = RAW_DIR / "ibge"
IBGE_LOCALIDADES_RAW_DIR: Path = RAW_DIR / "ibge" / "localidades"
IBGE_SIDRA_RAW_DIR: Path = RAW_DIR / "ibge" / "sidra"
IPVS_RAW_DIR: Path = RAW_DIR / "ipvs"

# Subpastas para dados processados
IBGE_LOCALIDADES_PROCESSED_DIR: Path = PROCESSED_DIR / "ibge" / "localidades"
IBGE_SIDRA_PROCESSED_DIR: Path = PROCESSED_DIR / "ibge" / "sidra"

# ---------------------------------------------------------------------------
# Data de extração (usada no nome dos arquivos)
# ---------------------------------------------------------------------------
EXTRACTION_DATE: str = date.today().isoformat()

# ---------------------------------------------------------------------------
# HTTP — configurações padrão
# ---------------------------------------------------------------------------
HTTP_TIMEOUT: int = int(os.getenv("HTTP_TIMEOUT", "60"))
HTTP_RETRIES: int = int(os.getenv("HTTP_RETRIES", "3"))
HTTP_RETRY_WAIT: int = int(os.getenv("HTTP_RETRY_WAIT", "5"))

# ---------------------------------------------------------------------------
# CNES / DATASUS
# ---------------------------------------------------------------------------
# API CNES via DATASUS — endpoint público de estabelecimentos
# Filtra por município de São Paulo (código IBGE 355030) e tipo UBS (tipo 05)
CNES_BASE_URL: str = os.getenv(
    "CNES_BASE_URL",
    "https://apidadosabertos.saude.gov.br/cnes/estabelecimentos",
)
CNES_MUNICIPIO_CODE: str = os.getenv("CNES_MUNICIPIO_CODE", "355030")
# Tipo de estabelecimento: 05 = Centro de Saúde / Unidade Básica de Saúde
CNES_TIPO_UNIDADE: str = os.getenv("CNES_TIPO_UNIDADE", "05")
# Limite de registros por página (máximo permitido pela API)
CNES_PAGE_LIMIT: int = int(os.getenv("CNES_PAGE_LIMIT", "200"))

# ---------------------------------------------------------------------------
# GeoSampa — WFS
# ---------------------------------------------------------------------------
GEOSAMPA_WFS_URL: str = os.getenv(
    "GEOSAMPA_WFS_URL",
    "https://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs",
)
GEOSAMPA_LAYER: str = os.getenv(
    "GEOSAMPA_LAYER",
    "geoportal:distrito_municipal",
)

# ---------------------------------------------------------------------------
# IBGE — Localidades
# ---------------------------------------------------------------------------
# API de Localidades do IBGE — distritos por município
# Documentação: https://servicodados.ibge.gov.br/api/docs/localidades
IBGE_LOCALIDADES_BASE_URL: str = os.getenv(
    "IBGE_LOCALIDADES_BASE_URL",
    "https://servicodados.ibge.gov.br/api/v1/localidades",
)
# Código IBGE do município de São Paulo (com dígito verificador)
IBGE_MUNICIPIO_ID: str = os.getenv("IBGE_MUNICIPIO_ID", "3550308")

# ---------------------------------------------------------------------------
# IBGE / SIDRA — Demografia
# ---------------------------------------------------------------------------
# API do SIDRA — dados demográficos (Censo 2022)
# Documentação: https://apisidra.ibge.gov.br/
SIDRA_BASE_URL: str = os.getenv(
    "SIDRA_BASE_URL",
    "https://apisidra.ibge.gov.br/values",
)
# Município de São Paulo (código IBGE 3550308, com dígito verificador)
SIDRA_LOCALIDADE: str = os.getenv("SIDRA_LOCALIDADE", "3550308")
# Período: último censo disponível
SIDRA_PERIODO: str = os.getenv("SIDRA_PERIODO", "last")

# Tabelas prioritárias do SIDRA para o projeto Vozes da Saúde
# Formato: {tabela_id: {"nome": str, "variaveis": str}}
# Variáveis: "allxp" = todas as variáveis da tabela
SIDRA_TABELAS_PRIORITARIAS: dict[str, dict[str, str]] = {
    "4714": {
        "nome": "População residente, área territorial e densidade demográfica",
        "variaveis": os.getenv("SIDRA_4714_VARIABLES", "allxp"),
    },
    "4711": {
        "nome": "Domicílios recenseados",
        "variaveis": os.getenv("SIDRA_4711_VARIABLES", "allxp"),
    },
    "4712": {
        "nome": "Domicílios particulares permanentes ocupados, moradores e média",
        "variaveis": os.getenv("SIDRA_4712_VARIABLES", "allxp"),
    },
}

# Manter compatibilidade com o extractor legado (ibge_extractor.py)
SIDRA_TABLE: str = os.getenv("SIDRA_TABLE", "4714")
SIDRA_VARIABLES: str = os.getenv("SIDRA_VARIABLES", "93")

# ---------------------------------------------------------------------------
# IPVS / SEADE
# ---------------------------------------------------------------------------
# URL para download do IPVS — pode ser atualizada conforme portal SEADE
IPVS_DOWNLOAD_URL: str = os.getenv(
    "IPVS_DOWNLOAD_URL",
    "https://repositorio.seade.gov.br/dataset/30c71093-4f5c-49f3-90d0-ba35e1bbbad6/resource/9d3f0546-e6f3-4a68-b26c-aa2a5a9c7704/download/ipvs_agsn_2010.csv",
)
# Diretório de entrada manual (fallback quando não há URL direta)
IPVS_INPUT_DIR: Path = Path(os.getenv("IPVS_INPUT_DIR", str(RAW_DIR / "ipvs" / "input")))
# Colunas mínimas esperadas no dataset IPVS
IPVS_EXPECTED_COLUMNS: list[str] = [
    "codigo_setor",
    "grupo_ipvs",
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT: str = "%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
