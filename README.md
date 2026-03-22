# Vozes da Saúde — Pipeline de Ingestão de Dados

Pipeline modular em Python para **extração automatizada** de bases de dados públicas utilizadas no projeto Vozes da Saúde.

## Fontes de Dados

| Fonte | Descrição | Formato |
|-------|-----------|---------|
| **CNES** (DATASUS) | Estabelecimentos de saúde — UBS de São Paulo | CSV |
| **GeoSampa** (WFS) | Distritos do município de São Paulo | GeoJSON |
| **IBGE / SIDRA** | Dados demográficos por município | CSV |
| **IPVS** (SEADE) | Índice Paulista de Vulnerabilidade Social | CSV |

## Estrutura do Projeto

```text
project/
│
├── app/
│   ├── config/
│   │   └── settings.py          # Configurações centrais (URLs, paths, timeouts)
│   ├── extractors/
│   │   ├── base.py              # Classe base abstrata para extractors
│   │   ├── cnes_extractor.py    # Extrator CNES / DATASUS
│   │   ├── geosampa_extractor.py # Extrator GeoSampa (WFS)
│   │   ├── ibge_extractor.py    # Extrator IBGE / SIDRA
│   │   └── ipvs_extractor.py    # Extrator IPVS / SEADE
│   ├── loaders/
│   │   └── file_loader.py       # Funções de persistência (CSV, Parquet)
│   ├── utils/
│   │   ├── logger.py            # Logging estruturado
│   │   ├── http_client.py       # Cliente HTTP com retry (tenacity)
│   │   └── paths.py             # Utilitários de caminhos e nomes de arquivos
│   └── main.py                  # Ponto de entrada com argparse
│
├── data/
│   ├── raw/                     # Dados brutos por fonte
│   │   ├── cnes/
│   │   ├── geosampa/
│   │   ├── ibge/
│   │   └── ipvs/
│   └── processed/               # Dados processados (camada Silver)
│
├── requirements.txt
└── README.md
```

## Pré-requisitos

- Python 3.10+
- pip

## Instalação

```bash
# Clone o repositório
git clone https://github.com/higorroliver/mbamack-vozsaude-ingestion.git
cd mbamack-vozsaude-ingestion

# Crie um ambiente virtual (recomendado)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Instale as dependências
pip install -r requirements.txt
```

## Execução

### Extrair todas as fontes

```bash
python -m app.main --source all
```

### Extrair uma fonte específica

```bash
python -m app.main --source cnes
python -m app.main --source geosampa
python -m app.main --source ibge
python -m app.main --source ipvs
```

## Configuração

As configurações ficam em `app/config/settings.py` e podem ser sobrescritas via variáveis de ambiente:

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `HTTP_TIMEOUT` | Timeout HTTP em segundos | `60` |
| `HTTP_RETRIES` | Número de tentativas | `3` |
| `CNES_MUNICIPIO_CODE` | Código IBGE do município | `355030` |
| `CNES_TIPO_UNIDADE` | Tipo de unidade CNES | `05` |
| `GEOSAMPA_LAYER` | Camada WFS do GeoSampa | `geoportal:deinfo_distrito` |
| `SIDRA_TABLE` | Tabela do SIDRA | `4714` |
| `SIDRA_LOCALIDADE` | Código IBGE do município | `3550308` |
| `IPVS_DOWNLOAD_URL` | URL de download do IPVS | URL padrão SEADE |
| `IPVS_INPUT_DIR` | Diretório de entrada manual IPVS | `data/raw/ipvs/input` |
| `LOG_LEVEL` | Nível de log | `INFO` |

## Arquitetura

```text
UBS (CNES)
   ↓
Distrito (GeoSampa)
   ↓
Demografia (IBGE)
   ↓
Vulnerabilidade (IPVS)
```

Cada extractor herda de `BaseExtractor` e implementa:
- `extract()` — lógica de extração específica da fonte
- `save_raw()` — persistência dos dados brutos
- `run()` — orquestração com logging e tratamento de erros (herdado)

## Padrões e Boas Práticas

- **Retry automático** em chamadas HTTP com backoff exponencial (via `tenacity`)
- **Timeout configurável** para todas as requisições
- **Validação de resposta** — dados vazios, colunas ausentes, GeoJSON inválido
- **Logging estruturado** — início, progresso, contagem de registros, erros
- **Type hints** em todo o código
- **Separação de responsabilidades** — config, extração, persistência, utils
- **Nomes de arquivo com data** — ex: `cnes_ubs_2026-03-22.csv`

## Próximos Passos / Evolução

### Integração com S3 / Data Lake
- Adicionar `boto3` ao `requirements.txt`
- Implementar upload para S3 no `file_loader.py` (já há esqueleto comentado)
- Configurar buckets para camadas Bronze (raw) e Silver (processed)
- Adicionar variáveis `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET`

### Transformações (camada Silver)
- Implementar transformers para limpeza e padronização de cada fonte
- Aplicar join espacial entre UBS (CNES) e Distritos (GeoSampa)
- Cruzar dados demográficos (IBGE) e vulnerabilidade (IPVS) por distrito

### Orquestração
- Integrar com Apache Airflow ou Prefect para agendamento
- Adicionar monitoramento e alertas

### Qualidade de dados
- Implementar validação com Great Expectations ou Pandera
- Adicionar testes unitários e de integração
