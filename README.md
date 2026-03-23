# Vozes da Saúde — Pipeline de Ingestão de Dados

Pipeline modular em Python para **extração automatizada** de bases de dados públicas utilizadas no projeto Vozes da Saúde.

## Fontes de Dados

| Fonte | Descrição | Formato |
|-------|-----------|---------|
| **CNES** (DATASUS) | Estabelecimentos de saúde — UBS de São Paulo | CSV |
| **GeoSampa** (WFS) | Distritos do município de São Paulo | GeoJSON |
| **IBGE Localidades** | Distritos oficiais do IBGE (dimensão territorial) | JSON + CSV + Parquet |
| **IBGE SIDRA** | Demografia: população, domicílios, densidade (tabelas 4714, 4711, 4712) | JSON + CSV + Parquet |
| **IBGE / SIDRA** (legado) | Dados demográficos por município (tabela única) | CSV |
| **IPVS** (SEADE) | Índice Paulista de Vulnerabilidade Social | CSV |

## Estrutura do Projeto

```text
project/
│
├── app/
│   ├── config/
│   │   └── settings.py                  # Configurações centrais (URLs, paths, timeouts)
│   ├── extractors/
│   │   ├── base.py                      # Classe base abstrata para extractors
│   │   ├── cnes_extractor.py            # Extrator CNES / DATASUS
│   │   ├── geosampa_extractor.py        # Extrator GeoSampa (WFS)
│   │   ├── ibge_extractor.py            # Extrator IBGE / SIDRA (legado, tabela única)
│   │   ├── ibge_localidades_extractor.py # Extrator IBGE Localidades (distritos)
│   │   ├── ibge_sidra_extractor.py      # Extrator IBGE SIDRA (múltiplas tabelas)
│   │   └── ipvs_extractor.py            # Extrator IPVS / SEADE
│   ├── loaders/
│   │   └── file_loader.py               # Funções de persistência (CSV, Parquet)
│   ├── utils/
│   │   ├── logger.py                    # Logging estruturado
│   │   ├── http_client.py               # Cliente HTTP com retry (tenacity)
│   │   └── paths.py                     # Utilitários de caminhos e nomes de arquivos
│   └── main.py                          # Ponto de entrada com argparse
│
├── data/
│   ├── raw/                             # Dados brutos por fonte
│   │   ├── cnes/
│   │   ├── geosampa/
│   │   ├── ibge/
│   │   │   ├── localidades/             # JSON bruto dos distritos IBGE
│   │   │   └── sidra/                   # JSON bruto das tabelas SIDRA
│   │   └── ipvs/
│   └── processed/                       # Dados processados (camada Silver)
│       └── ibge/
│           ├── localidades/             # CSV + Parquet tratados dos distritos
│           └── sidra/                   # CSV + Parquet consolidados do SIDRA
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
python -m app.main --source cnes              # UBS via DATASUS
python -m app.main --source geosampa           # Distritos via WFS
python -m app.main --source ibge               # SIDRA tabela única (legado)
python -m app.main --source ibge_localidades   # Distritos oficiais IBGE
python -m app.main --source ibge_sidra         # Demografia SIDRA (3 tabelas)
python -m app.main --source ipvs               # IPVS / SEADE
```

## Configuração

As configurações ficam em `app/config/settings.py` e podem ser sobrescritas via variáveis de ambiente:

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `HTTP_TIMEOUT` | Timeout HTTP em segundos | `60` |
| `HTTP_RETRIES` | Número de tentativas | `3` |
| `CNES_MUNICIPIO_CODE` | Código IBGE do município | `355030` |
| `CNES_TIPO_UNIDADE` | Tipo de unidade CNES | `05` |
| `GEOSAMPA_LAYER` | Camada WFS do GeoSampa | `geoportal:distrito_municipal` |
| `IBGE_MUNICIPIO_ID` | Código IBGE do município (Localidades) | `3550308` |
| `SIDRA_TABLE` | Tabela do SIDRA (legado) | `4714` |
| `SIDRA_LOCALIDADE` | Código IBGE do município (SIDRA) | `3550308` |
| `SIDRA_PERIODO` | Período temporal do SIDRA | `last` |
| `SIDRA_4714_VARIABLES` | Variáveis da tabela 4714 | `allxp` |
| `SIDRA_4711_VARIABLES` | Variáveis da tabela 4711 | `allxp` |
| `SIDRA_4712_VARIABLES` | Variáveis da tabela 4712 | `allxp` |
| `IPVS_DOWNLOAD_URL` | URL de download do IPVS | URL padrão SEADE |
| `IPVS_INPUT_DIR` | Diretório de entrada manual IPVS | `data/raw/ipvs/input` |
| `LOG_LEVEL` | Nível de log | `INFO` |

## Arquitetura

```text
UBS (CNES)
   ↓
Distrito (GeoSampa) ←→ Distritos IBGE (Localidades)
   ↓
Demografia (IBGE SIDRA: tabelas 4714, 4711, 4712)
   ↓
Vulnerabilidade (IPVS)
```

Cada extractor herda de `BaseExtractor` e implementa:
- `extract()` — lógica de extração específica da fonte
- `save_raw()` — persistência dos dados brutos
- `run()` — orquestração com logging e tratamento de erros (herdado)

### Módulos IBGE

O IBGE é tratado em dois módulos independentes:

1. **IBGE Localidades** (`ibge_localidades_extractor.py`)
   - API: `servicodados.ibge.gov.br/api/v1/localidades`
   - Função: `get_districts_by_municipality(municipio_id)`
   - Retorna 96 distritos oficiais de São Paulo
   - Inclui normalização textual para joins futuros
   - Campos: `id_distrito_ibge`, `nome_distrito_ibge`, `id_municipio_ibge`, `nome_municipio`, `sigla_uf`, `nome_distrito_normalizado`

2. **IBGE SIDRA** (`ibge_sidra_extractor.py`)
   - API: `apisidra.ibge.gov.br/values`
   - Tabelas: 4714 (população/área/densidade), 4711 (domicílios), 4712 (domicílios ocupados/moradores/média)
   - Granularidade: municipal (n6) — registra em log quando distrito não está disponível
   - Campos: `fonte`, `tabela_sidra`, `ano`, `id_municipio_ibge`, `nome_municipio`, `variavel`, `valor`, `unidade`, `nivel_territorial`
   - Funções desacopladas: `build_sidra_url()`, `parse_sidra_response()`, `normalize_column_name()`

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
