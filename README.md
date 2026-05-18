# DCC Tools

## Português (pt-BR)

Ferramentas open source para gerar e processar Certificados de Calibração Digital (DCC), com base no modelo DCC do PTB.

### Sistema atual

A implementação ativa é uma aplicação web Flask em `flask/`, conteinerizada com Docker.

Principais funcionalidades:
- Gerar DCC XML a partir de JSON (`/dcc/generate`)
- Gerar DCC XML via upload de planilha Excel (`/dcc/upload_xls`)
- Embutir XML em PDF/A-3 (`/dcc/pdf_attach`)
- Validar XML DCC contra schema (`/dcc/validate_xml`)
- Visualizar DCC em formato legível por humanos (`/dcc/visualizar_dcc`)
- Interface web com documentação, exemplos, FAQ e publicações (`/dcc/`)

Versões de schema DCC suportadas:
- `3.3.0` (padrão)
- `3.2.0`

### Estrutura do projeto

```text
.
├── flask/
│   ├── app/
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   ├── templates/
│   │   └── static/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── build.sh
├── doc/
└── README.md
```

### Execução com Docker (recomendado)

A partir de `flask/`:

```bash
./build.sh
docker compose up -d
```

URL padrão:
- `http://localhost:9099/dcc/`

Observações:
- A porta do host está em `flask/docker-compose.yml` (`9099:80`).
- Você pode alterar a porta externa nesse arquivo.

### Desenvolvimento local (sem Docker)

Requisitos: Python 3.11+

A partir de `flask/app/`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Ao executar diretamente, a aplicação inicia na porta `80` (ver `main.py`).

### Rotas principais

Rotas de interface:
- `GET /dcc/`
- `GET /dcc/api_doc`
- `GET /dcc/excel_guide`
- `GET /dcc/exemplos`
- `GET /dcc/faq`
- `GET /dcc/publications`
- `GET /dcc/form_dcc`

Rotas de processamento/API:
- `POST /dcc/generate` (JSON -> DCC XML)
- `POST /dcc/pdf_attach` (PDF + XML -> PDF com XML embutido)
- `GET|POST /dcc/validate_xml`
- `GET|POST /dcc/upload_json`
- `GET|POST /dcc/upload_xls`
- `POST /dcc/visualizar_dcc`

### Licença

Este projeto é licenciado sob GPL-2.0-or-later. Consulte `LICENSE` para mais detalhes.

## English

Open-source tools for generating and handling Digital Calibration Certificates (DCC), based on the PTB DCC model.

### Current system

The active implementation is a Flask web application in `flask/`, containerized with Docker.

Main capabilities:
- Generate DCC XML from JSON (`/dcc/generate`)
- Generate DCC XML from Excel template upload (`/dcc/upload_xls`)
- Embed XML into PDF/A-3 (`/dcc/pdf_attach`)
- Validate DCC XML against schema (`/dcc/validate_xml`)
- Render human-readable DCC from XML (`/dcc/visualizar_dcc`)
- Web UI with documentation, examples, FAQ, and publications (`/dcc/`)

Supported DCC schema versions:
- `3.3.0` (default)
- `3.2.0`

### Project structure

```text
.
├── flask/
│   ├── app/
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   ├── templates/
│   │   └── static/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── build.sh
├── doc/
└── README.md
```

### Running with Docker (recommended)

From `flask/`:

```bash
./build.sh
docker compose up -d
```

Default URL:
- `http://localhost:9099/dcc/`

Notes:
- The host port is configured in `flask/docker-compose.yml` (`9099:80`).
- You can change the external port in that file.

### Local development (without Docker)

Requirements: Python 3.11+

From `flask/app/`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

When running directly, the app starts on port `80` (see `main.py`).

### Main routes

UI routes:
- `GET /dcc/`
- `GET /dcc/api_doc`
- `GET /dcc/excel_guide`
- `GET /dcc/exemplos`
- `GET /dcc/faq`
- `GET /dcc/publications`
- `GET /dcc/form_dcc`

Processing/API routes:
- `POST /dcc/generate` (JSON -> DCC XML)
- `POST /dcc/pdf_attach` (PDF + XML -> PDF with XML embedded)
- `GET|POST /dcc/validate_xml`
- `GET|POST /dcc/upload_json`
- `GET|POST /dcc/upload_xls`
- `POST /dcc/visualizar_dcc`

### License

This project is licensed under GPL-2.0-or-later. See `LICENSE` for details.
