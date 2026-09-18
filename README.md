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
- Suporte opcional aos graus de liberdade efetivos (`νeff`, campo `nueff`) nos resultados
- Cadastro de usuários com API-KEY e proteção das funções de geração/upload

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

### Configuração de autenticação (produção)

Os segredos ficam em `flask/.env` (não versionado). Crie a partir do modelo:

```bash
cd flask
cp .env.example .env
chmod 600 .env
```

Gere o valor e preencha o `.env`:

```bash
python3 -c "import secrets; print('DCC_SECRET_KEY=' + secrets.token_hex(32))"
docker compose up -d
```

- `DCC_SECRET_KEY` (**obrigatória**): assina a sessão da interface web. Sem ela, cada worker usa uma
  chave efêmera e as sessões são invalidadas a cada reinício.
- `DCC_DB_PATH`: caminho do banco SQLite (padrão `/app/dcc_auth.db`, persistido em `flask/app/`).
- `DCC_SESSION_HOURS`: duração da sessão web em horas (padrão `8`).
- `DCC_ALLOWED_SCHEMA_HOSTS`: hosts confiáveis para download de schemas na validação de XML (padrão
  `ptb.de,w3.org`), mitigando SSRF. `DCC_MAX_SCHEMA_BYTES` limita o tamanho do schema (padrão 5 MiB).

Os usuários se cadastram em `/dcc/register` (usuário + senha) e fazem login em `/dcc/login`. Cada
usuário recebe uma API-KEY, consultável na área de perfil (`/dcc/perfil`) e usada no cabeçalho
`X-API-Key` da API REST. Na interface web, a autorização é transparente via sessão.

Atenção:
- Sirva a aplicação via **HTTPS** (proxy reverso com TLS): a senha, a API-KEY e o cookie de sessão
  trafegam na requisição.
- Faça backup do arquivo SQLite (`flask/app/dcc_auth.db`).

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
- Optional support for effective degrees of freedom (`νeff`, field `nueff`) in results
- User registration with API-KEY and protection of generation/upload functions

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

### Authentication configuration (production)

Secrets are kept in `flask/.env` (not versioned). Create it from the template:

```bash
cd flask
cp .env.example .env
chmod 600 .env
```

Generate the value and fill in `.env`:

```bash
python3 -c "import secrets; print('DCC_SECRET_KEY=' + secrets.token_hex(32))"
docker compose up -d
```

- `DCC_SECRET_KEY` (**required**): signs the web session. Without it, each worker uses an ephemeral key
  and sessions are invalidated on every restart.
- `DCC_DB_PATH`: SQLite database path (default `/app/dcc_auth.db`, persisted in `flask/app/`).
- `DCC_SESSION_HOURS`: web session lifetime in hours (default `8`).
- `DCC_ALLOWED_SCHEMA_HOSTS`: trusted hosts for schema downloads during XML validation (default
  `ptb.de,w3.org`), mitigating SSRF. `DCC_MAX_SCHEMA_BYTES` caps the schema size (default 5 MiB).

Users register at `/dcc/register` (username + password) and log in at `/dcc/login`. Each user receives
an API-KEY, available in the profile area (`/dcc/perfil`) and used in the `X-API-Key` header of the REST
API. On the web interface, authorization is transparent via the session.

Notes:
- Serve the application over **HTTPS** (TLS-terminating reverse proxy): the password, API-KEY and session
  cookie travel in the request.
- Back up the SQLite file (`flask/app/dcc_auth.db`).

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
