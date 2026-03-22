"""
Ponto de entrada principal do pipeline de ingestão.

Uso:
    python -m app.main --source all
    python -m app.main --source cnes
    python -m app.main --source geosampa
    python -m app.main --source ibge
    python -m app.main --source ibge_localidades
    python -m app.main --source ibge_sidra
    python -m app.main --source ipvs
"""

import argparse
import sys
from pathlib import Path

from app.utils.logger import get_logger
from app.extractors.cnes_extractor import CnesExtractor
from app.extractors.geosampa_extractor import GeosampaExtractor
from app.extractors.ibge_extractor import IbgeExtractor
from app.extractors.ibge_localidades_extractor import IbgeLocalidadesExtractor
from app.extractors.ibge_sidra_extractor import IbgeSidraExtractor
from app.extractors.ipvs_extractor import IpvsExtractor

logger = get_logger("main")

# Mapeamento de fontes para seus respectivos extractors
EXTRACTORS: dict[str, type] = {
    "cnes": CnesExtractor,
    "geosampa": GeosampaExtractor,
    "ibge": IbgeExtractor,
    "ibge_localidades": IbgeLocalidadesExtractor,
    "ibge_sidra": IbgeSidraExtractor,
    "ipvs": IpvsExtractor,
}


def parse_args() -> argparse.Namespace:
    """Configura e processa argumentos de linha de comando."""
    parser = argparse.ArgumentParser(
        description="Pipeline de ingestão de dados — Vozes da Saúde",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python -m app.main --source all        Executa todas as extrações
  python -m app.main --source cnes       Extrai dados do CNES
  python -m app.main --source geosampa   Extrai distritos do GeoSampa
  python -m app.main --source ibge             Extrai dados demográficos do IBGE (legado)
  python -m app.main --source ibge_localidades  Extrai distritos via API Localidades IBGE
  python -m app.main --source ibge_sidra        Extrai demografia via API SIDRA (multiplas tabelas)
  python -m app.main --source ipvs              Extrai dados IPVS
        """,
    )
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        choices=["all", *EXTRACTORS.keys()],
        help="Fonte de dados a ser extraída (ou 'all' para todas).",
    )
    return parser.parse_args()


def run_extractor(name: str) -> Path | None:
    """Instancia e executa um extractor pelo nome."""
    extractor_class = EXTRACTORS.get(name)
    if not extractor_class:
        logger.error("Extractor desconhecido: %s", name)
        return None

    extractor = extractor_class()
    return extractor.run()


def main() -> None:
    """Função principal do pipeline."""
    args = parse_args()

    logger.info("=" * 70)
    logger.info("PIPELINE DE INGESTÃO — VOZES DA SAÚDE")
    logger.info("=" * 70)

    sources = list(EXTRACTORS.keys()) if args.source == "all" else [args.source]

    results: dict[str, Path | None] = {}

    for source in sources:
        logger.info("-" * 70)
        result = run_extractor(source)
        results[source] = result

    # Resumo final
    logger.info("=" * 70)
    logger.info("RESUMO DA EXTRAÇÃO")
    logger.info("=" * 70)

    success_count = 0
    fail_count = 0

    for source, path in results.items():
        if path:
            logger.info("  ✔ %s → %s", source.upper(), path)
            success_count += 1
        else:
            logger.error("  ✘ %s → FALHA", source.upper())
            fail_count += 1

    logger.info("-" * 70)
    logger.info("Total: %d sucesso(s), %d falha(s)", success_count, fail_count)
    logger.info("=" * 70)

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
