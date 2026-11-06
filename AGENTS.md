# AGENTS.md — Guia para agentes de código no DCC Tools

Este arquivo descreve o projeto, suas convenções e o fluxo esperado para modificações. Ele é
destinado a agentes de IA e desenvolvedores que forem trabalhar neste repositório.

> **Regra obrigatória:** sempre que algo novo for implementado ou um comportamento existente for
> alterado, atualize **no mesmo commit** tanto a **documentação padrão** quanto a **documentação para
> LLMs**. Considere a tarefa incompleta enquanto as duas não estiverem atualizadas. Veja a seção
> [Política de documentação](#política-de-documentação).

---

## 1. Visão geral

O **DCC Tools** é uma aplicação do Inmetro (Dimci/Diele/Lampe) para gerar e processar
**Certificados de Calibração Digital (DCC)** no modelo do PTB (<https://www.ptb.de/dcc>).

- Implementação ativa: aplicação web **Flask** em `flask/`.
- Execução recomendada: **Docker Compose** com uWSGI + nginx.
- Ambiente de produção: **intranet**; as URLs internas não são acessíveis por assistentes externos.
- Versões de schema DCC suportadas: `3.3.0` (padrão) e `3.2.0`.
- Licença: GPL-2.0-or-later.
- Idioma do domínio e da documentação: português (pt-BR).

Principais fluxos:

```text
JSON de entrada  ──POST /dcc/generate──▶  XML DCC
Planilha .xlsx  ──POST /dcc/upload_xls──▶  JSON → XML DCC
PDF + XML       ──POST /dcc/pdf_attach──▶  PDF com XML embutido
XML             ──POST /dcc/validate_xml──▶  HTML de validação
XML             ──POST /dcc/visualizar_dcc──▶  HTML legível
```

---

## 2. Mapa do projeto

```text
.
├── AGENTS.md                     # este guia
├── README.md                     # visão geral, instalação, configuração e rotas
├── LICENSE                       # GPL-2.0-or-later
├── .gitignore
│
├── doc/                          # documentação técnica "padrão"
│   ├── api_dcc_generator.md      # referência detalhada do JSON → XML (/dcc/generate)
│   ├── implementacao_nueff_dccGenerator.md
│   ├── documentacao_api.odt
│   ├── documentacao_api.pdf
│   └── paper.pdf
│
├── flask/                        # aplicação ativa
│   ├── Dockerfile
│   ├── docker-compose.yml        # serviço dccgenerator; volume ./app:/app; porta 9099:80
│   ├── build.sh                  # docker build -t dccgenerator .
│   ├── .env.example              # modelo das variáveis de ambiente
│   └── app/
│       ├── main.py               # aplicação Flask, rotas e lógica DCC (~1.900 linhas)
│       ├── auth.py               # usuários, senhas, API-KEYs, sessão e reset por e-mail
│       ├── email_service.py      # envio SMTP
│       ├── manage_auth.py        # CLI de administração de usuários
│       ├── requirements.txt
│       ├── uwsgi.ini             # module=main, callable=app, 4 processos, py-autoreload
│       ├── dcc_auth.db*          # SQLite local (ignorado pelo git; não versionar)
│       ├── docs/
│       │   └── llm_doc.md        # documentação para LLMs (fonte servida pelo app)
│       ├── static/
│       │   ├── css/, js/, webfonts/
│       │   ├── examples/          # JSON, XML, PDF, XLSX de exemplo e XSLT human-readable
│       │   └── papers/            # publicações e mídia
│       ├── templates/             # Jinja2
│       │   ├── base.html          # layout principal (Bootstrap local + Font Awesome)
│       │   ├── nav_fragment.html  # navbar usado pelas páginas HTML antigas
│       │   ├── landing.html
│       │   ├── api_documentation.html
│       │   ├── llm_doc.html
│       │   ├── excel_guide.html
│       │   ├── form_dcc.html
│       │   ├── upload_*.html, validate_xml.html
│       │   └── login.html, register.html, perfil.html, ...
│       └── test_auth.py, test_nueff.py, test_validation.py
│
└── aws_lambda/                   # implementações legadas/referência em AWS Lambda
    ├── dccGenerator/
    ├── dccPdfAttach/
    ├── dccSpreadsheet/
    ├── dccSpreadsheetFrontend/
    ├── curl_scripts/
    └── examples/
```

### Observações sobre o mapa

- `flask/app/main.py` é o núcleo da aplicação ativa. Ele concentra rotas, geração de XML, conversão
  de Excel, anexação em PDF, XSLT e validação de schema.
- `flask/app/docs/llm_doc.md` é a **fonte** da documentação para LLMs. Ela é servida por
  `/dcc/llm_doc.md` e exibida em `/dcc/llm_doc`.
- `aws_lambda/` é legado/referência. Não é usado pela aplicação Flask. Só altere se a tarefa for
  explicitamente sobre as Lambdas. Evite editar `*.zip`, `deploy.zip` e layers manualmente; eles são
  artefatos de build.
- `doc/` contém documentos técnicos. `documentacao_api.pdf` e `.odt` parecem artefatos publicados;
  mantenha a fonte em Markdown/HTML atualizada e regenere os artefatos apenas se o fluxo de
  publicação exigir.

### Como localizar código rapidamente

```bash
# todas as rotas
grep -n "@app.route" flask/app/main.py

# funções e classes do núcleo
grep -n "^def \|^class " flask/app/main.py

# onde a documentação para LLMs é referenciada
grep -rn "llm_doc" flask/app README.md doc

# variáveis de ambiente usadas no código
grep -rn "os.environ" flask/app/*.py

# testes existentes
grep -rn "def test_" flask/app/test_*.py
```

---

## 3. Stack e dependências

- Python 3.11+
- Flask
- uWSGI (imagem `tiangolo/uwsgi-nginx-flask:python3.11`)
- lxml (XML, XSD, XSLT)
- pikepdf (PDF/A-3)
- pandas + openpyxl (planilhas Excel)
- requests (download de schemas e chamadas internas)
- SQLite (autenticação)
- Bootstrap e Font Awesome locais em `static/` (não há build de frontend)

Dependências Python ficam em `flask/app/requirements.txt`. Se alterar dependências, atualize esse
arquivo e rebuilde a imagem Docker (`flask/build.sh`).

---

## 4. Arquitetura de execução

### Docker Compose (recomendado)

```bash
cd flask
./build.sh
docker compose up -d
```

- Serviço: `dccgenerator`.
- Imagem: `dccgenerator`.
- Volume: `./app:/app` — o código da aplicação vem do host, então alterações em `flask/app/` são
  refletidas no container após reiniciar o processo/container.
- Porta: `9099:80`.
- Variáveis de ambiente: lidas de `flask/.env` (não versionado). Crie a partir de
  `flask/.env.example`.
- `DCC_SECRET_KEY` é obrigatória em produção; sem ela, cada worker usa uma chave efêmera.
- A aplicação fica atrás de um proxy; `ProxyFix` trata `X-Forwarded-For/Host/Proto`.
- Sirva por HTTPS em produção (proxy reverso com TLS).

### Execução local sem Docker

```bash
cd flask/app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

A aplicação inicia na porta `80` quando executada diretamente (veja o final de `main.py`).

### Banco de dados

- SQLite, caminho padrão `flask/app/dcc_auth.db` (ou `DCC_DB_PATH`).
- Tabelas criadas/migradas por `auth.init_db()`; não há Alembic.
- O arquivo do banco e seus `-wal`/`-shm` são ignorados pelo git.
- Em produção, faça backup do arquivo SQLite.
- CLI (a partir de `flask/app/`):

```bash
python manage_auth.py init-db
python manage_auth.py create-user <username> --email <email> [--password <senha>]
python manage_auth.py set-password <username> [--password <senha>]
python manage_auth.py list-users
python manage_auth.py revoke <username>
python manage_auth.py activate <username>
```

---

## 5. Módulos e responsabilidades

### `flask/app/main.py`

Responsável por quase toda a lógica da aplicação:

| Área | Funções/constantes principais |
| --- | --- |
| Configuração DCC | `DEFAULT_DCC_VERSION`, `SUPPORTED_DCC_VERSIONS`, `nsmap`, `schemaLocation` |
| Geração XML | `dccGen`, `declaracoes`, `resolve_dcc_version`, `campo_name`, `campo_texto`, `campo_conteudo_multilingue` |
| Incerteza relativa | `format_two_sig_scientific` |
| `nueff` | `is_positive_infinite`, `serialize_nueff`, `validate_nueff` |
| Excel | `excel_to_json` |
| PDF/A-3 | `attach_stream`, `attach_xml_to_pdfa3b`, `sha256sum` |
| XSLT | `transform_xml_to_html` |
| Validação XSD | `is_allowed_schema_url`, `download_file`, `validate_dcc_xml_upload`, `process_xsd_dependencies`, `validate_with_xsd` |
| Upload/arquivos | `allowed_file` |
| Rotas Flask | funções decoradas com `@app.route` (ver tabela abaixo) |

### `flask/app/auth.py`

- Cadastro, autenticação e sessão da interface web.
- Geração/regeneração de API-KEY (`dcc_...`); a chave é guardada em texto no SQLite para exibição
  no perfil e também como hash SHA-256 para busca.
- E-mail institucional `@inmetro.gov.br` e senha mínima de 8 caracteres.
- Recuperação de senha por token com validade e limite de solicitações.
- `require_auth`: aceita `X-API-Key` ou sessão web; para clientes de API retorna XML `401`, para
  navegadores redireciona ao login.
- `authentication_required_xml`: resposta XML com instruções de cadastro/uso.

### `flask/app/email_service.py`

- Envio SMTP configurado por variáveis de ambiente.
- `DCC_EMAIL_ENABLED=false` desabilita o envio (usado nos testes).
- `SMTP_HOST` e `SMTP_FROM` não têm padrão no código; sem eles o envio fica desabilitado.

### `flask/app/manage_auth.py`

- CLI administrativa para criar/ativar/revogar usuários e redefinir senhas.
- Sempre chama `auth.init_db()` antes das operações.

### Templates

Há dois padrões no projeto:

1. **Páginas novas** (ex.: `landing.html`, `llm_doc.html`) estendem `base.html`.
2. **Páginas HTML antigas** (ex.: `api_documentation.html`, `faq.html`, `exemplos.html`,
   `publications.html`, `introducao.html`, `excel_guide.html`) são documentos HTML completos e
   incluem `nav_fragment.html`.

Prefira estender `base.html` em páginas novas. Não refatore páginas antigas sem necessidade e sem
testar a navegação.

### `flask/app/docs/llm_doc.md`

- Documentação para LLMs, mantida em Markdown.
- Servida por `GET /dcc/llm_doc.md` (com `Content-Disposition: inline; filename=llm_doc.md`).
- Exibida em `GET /dcc/llm_doc`, que lê o arquivo e oferece “Baixar .md” e “Copiar documentação”.
- O texto deve assumir ambiente de intranet: a LLM **não** acessa a URL; o usuário precisa baixar ou
  copiar o conteúdo e anexar/colar no assistente.

---

## 6. Rotas

### Páginas públicas

| Método | Rota | Template/função |
| --- | --- | --- |
| GET | `/dcc/` | `landing.html` |
| GET | `/dcc/introducao` | `introducao.html` |
| GET | `/dcc/api_doc` | `api_documentation.html` |
| GET | `/dcc/llm_doc` | `llm_doc.html` |
| GET | `/dcc/llm_doc.md` | `docs/llm_doc.md` (Markdown) |
| GET | `/dcc/excel_guide` | `excel_guide.html` |
| GET | `/dcc/exemplos` | `exemplos.html` |
| GET | `/dcc/faq` | `faq.html` |
| GET | `/dcc/publications` | `publications.html` |
| GET/POST | `/dcc/register` | `register.html`; JSON retorna `201` com `api_key` |
| GET/POST | `/dcc/login` | `login.html` |
| GET | `/dcc/logout` | encerra a sessão |
| GET/POST | `/dcc/esqueci-senha` | recuperação por e-mail |
| GET/POST | `/dcc/redefinir-senha` | token do e-mail |

### Páginas/rotas protegidas (sessão web ou `X-API-Key`)

| Método | Rota | Observação |
| --- | --- | --- |
| GET | `/dcc/perfil` | exibe a API-KEY |
| POST | `/dcc/perfil/regenerar` | invalida a chave anterior |
| GET/POST | `/dcc/perfil/senha` | troca de senha |
| GET | `/dcc/form_dcc` | formulário interativo |
| GET/POST | `/dcc/upload_json` | upload de `.json` |
| GET/POST | `/dcc/upload_xls` | upload de `.xlsx` |
| GET | `/dcc/upload_xml` | upload de XML para PDF |
| POST | `/dcc/pdf_attach` | multipart `pdf_file` + `xml_file` |
| POST | `/dcc/generate` | JSON → XML (API principal) |

### Ferramentas abertas

| Método | Rota | Observação |
| --- | --- | --- |
| GET | `/dcc/upload_xml_hr` | formulário de visualização |
| GET/POST | `/dcc/validate_xml` | validação; resposta é HTML, não JSON |
| POST | `/dcc/visualizar_dcc` | XML → HTML via XSLT |

> Rotas protegidas usam `@auth.require_auth`. Requisições de API sem autenticação recebem XML
> `<autenticacaoNecessaria>` com status `401`; navegadores são redirecionados para
> `/dcc/login?auth_required=1`.

---

## 7. Contrato principal: `POST /dcc/generate`

- Entrada: JSON com chaves em português (acentos preservados).
- Saída: XML DCC (`text/xml`) com `Content-Disposition: attachment; filename="CC_DIMCI_<num_certif>.xml"`.
- Autenticação: `X-API-Key` ou sessão.
- Erros:
  - `400` JSON ausente/inválido ou validação de `nueff`;
  - `500` erro na geração (campos obrigatórios ausentes, tipos inesperados etc.);
  - `401` XML de autenticação.
- `dcc_version` / `schema_version`: `3.3.0` (padrão) ou `3.2.0`; valores desconhecidos caem no
  padrão.
- `num_certif` não deve incluir o prefixo `DIMCI` (o XML adiciona).
- Unidades seguem D-SI (`\volt`, `\micro\volt\volt\tothe{-1}`, `\degreecelsius`, etc.).
- A referência completa de campos está em `doc/api_dcc_generator.md` e em `/dcc/api_doc`.

### Regras de `nueff`

- Opcional por resultado.
- Se presente em um resultado, todos os resultados do mesmo mensurando devem informá-lo.
- Valores numéricos e positivos; `inf`/`Infinity` representam `+∞`.
- Rejeitar `0`, negativos, `-inf`, `null`, vazio, `NaN` e não numéricos.

---

## 8. Segurança e tratamento de erros

- Nunca versione `flask/.env`, `dcc_auth.db*`, chaves, senhas ou tokens.
- A API-KEY é secreta; não a coloque em URLs, logs ou mensagens de erro.
- Uploads: valide extensões (`allowed_file`) e use diretórios temporários; remova temporários no
  `finally` quando aplicável.
- Validação de XML: o download de schemas é restrito por `DCC_ALLOWED_SCHEMA_HOSTS`
  (padrão `ptb.de,w3.org`) e por `DCC_MAX_SCHEMA_BYTES`; não remova essas proteções. A validação
  bloqueia IPs privados/loopback/link-local e credenciais embutidas.
- PDF: a anexação usa pikepdf e adiciona XML + `SHA256SUM.txt`; preserve o comportamento PDF/A-3.
- Senhas usam hash do Werkzeug; API-KEYs ficam em texto no SQLite para exibição no perfil e também
  como hash SHA-256 para busca.
- Não introduza `debug=True` em produção.
- Evite `eval`, `exec`, comandos de shell com entrada do usuário e paths construídos sem validação.

---

## 9. Configuração (variáveis de ambiente)

Arquivo modelo: `flask/.env.example` (copiar para `flask/.env`).

| Variável | Uso |
| --- | --- |
| `DCC_SECRET_KEY` | Assina a sessão web; obrigatória em produção. |
| `DCC_DB_PATH` | Caminho do SQLite (padrão `/app/dcc_auth.db` no container). |
| `DCC_SESSION_HOURS` | Duração da sessão web (padrão 8). |
| `DCC_ALLOWED_SCHEMA_HOSTS` | Hosts confiáveis para download de schemas (padrão `ptb.de,w3.org`). |
| `DCC_MAX_SCHEMA_BYTES` | Tamanho máximo de schema (padrão 5 MiB). |
| `DCC_EMAIL_ENABLED` | Habilita/desabilita envio de e-mail. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM` | Servidor e remetente SMTP. |
| `SMTP_USE_AUTH`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `SMTP_TIMEOUT` | Autenticação/TLS/timeout SMTP. |
| `APP_BASE_URL` | URL base usada no link de recuperação de senha. |
| `DCC_RESET_TOKEN_MINUTES` | Validade do token de recuperação (padrão 60). |

Se adicionar uma variável, atualize **`.env.example`**, `README.md`, `docker-compose.yml` (quando
necessário) e a documentação para LLMs.

---

## 10. Desenvolvimento e testes

### Verificações rápidas

```bash
cd flask/app
python -m py_compile main.py auth.py email_service.py manage_auth.py
```

### Testes automatizados

Os testes usam `unittest` e configuram banco temporário/ambiente isolado antes de importar a app.

```bash
cd flask/app
python -m unittest test_auth.py -v
python -m unittest test_nueff.py -v
python -m unittest test_validation.py -v
```

Ou todos:

```bash
cd flask/app
python -m unittest discover -v
```

### Smoke test manual da aplicação

```bash
cd flask/app
python main.py
# em outro terminal:
curl -I http://localhost:80/dcc/
curl -I http://localhost:80/dcc/llm_doc
curl -I http://localhost:80/dcc/llm_doc.md
```

Ou, com Docker:

```bash
cd flask
docker compose up -d
curl -I http://localhost:9099/dcc/
curl -I http://localhost:9099/dcc/llm_doc
curl -I http://localhost:9099/dcc/llm_doc.md
```

### Testes com `Flask test_client`

Ao adicionar uma rota, inclua um teste que:
- verifique o status HTTP esperado;
- verifique o `Content-Type` (HTML, XML, JSON, Markdown, PDF);
- confirme autenticação/redirect quando a rota for protegida;
- valide o corpo mínimo (por exemplo, campo obrigatório ausente → erro claro).

---

## 11. Convenções de código

- Python: 4 espaços, nomes em `snake_case`, funções pequenas quando possível.
- `main.py` é um monólito histórico. Prefira adicionar funções/rotas ali a fazer refatorações
  amplas não solicitadas. Refatorações grandes devem ser commits separados e cobertas por testes.
- Chaves JSON do DCC são **contrato público** e estão em português; nunca renomeie/remova campos sem
  atualizar API, testes e documentação.
- Preserve acentos e a representação exata de números; no JSON, prefira strings para valores
  decimais.
- Rotas novas devem usar `url_for`, `render_template` e o padrão de autenticação existente.
- Para respostas de API, mantenha o padrão atual:
  - JSON `{"error": "..."}` para erros de validação;
  - XML para `401` de autenticação;
  - `text/xml` para XML;
  - HTML para páginas de validação/visualização.
- Não introduza dependências de frontend/CDN: o projeto usa Bootstrap/Font Awesome locais.
- Não adicione novos artefatos gerados (`__pycache__`, DB, `.env`, zips de deploy). Os zips
  existentes em `aws_lambda/` são legado e não devem ser editados manualmente.

---

## 12. Política de documentação

### 12.1 Regra obrigatória

Sempre que implementar ou alterar algo, atualize **no mesmo commit**:

1. a **documentação padrão** aplicável;
2. a **documentação para LLMs** (`flask/app/docs/llm_doc.md` e `flask/app/templates/llm_doc.html`).

Se a mudança afetar API, schema JSON, rota, autenticação, configuração, dependências, fluxo de
planilha, PDF, validação ou comportamento operacional, a tarefa **não está concluída** sem essa
atualização.

### 12.2 O que é “documentação padrão”

Atualize o que for aplicável:

| Arquivo | Quando atualizar |
| --- | --- |
| `README.md` | Visão geral, instalação, configuração, rotas, variáveis de ambiente, deploy. |
| `AGENTS.md` | Estrutura do projeto, comandos, rotas, convenções e política de documentação. |
| `doc/api_dcc_generator.md` | Contrato do `/dcc/generate`, campos JSON, exemplos, erros, `nueff`. |
| `flask/app/templates/api_documentation.html` | Página HTML pública da API; mantenha coerente com o contrato. |
| `flask/app/templates/excel_guide.html` | Estrutura da planilha Excel e conversão para JSON. |
| `flask/app/templates/faq.html` | Dúvidas frequentes impactadas pela mudança. |
| `flask/app/templates/introducao.html` | Conceitos/fluxo apresentados ao usuário. |
| `.env.example` | Nova variável de ambiente ou mudança de configuração. |
| `doc/implementacao_nueff_dccGenerator.md` | Regras/representação de `nueff`. |
| `doc/documentacao_api.pdf` / `.odt` | Apenas se o fluxo de publicação exigir regeneração; mantenha a fonte Markdown/HTML atualizada. |

### 12.3 O que é “documentação para LLMs”

Atualize **sempre os dois**:

- `flask/app/docs/llm_doc.md` — fonte Markdown, servida em `/dcc/llm_doc.md`.
- `flask/app/templates/llm_doc.html` — página `/dcc/llm_doc`, incluindo textos de instrução e
  prompts sugeridos.

Regras específicas:

- A documentação para LLMs deve ser **autossuficiente**: a LLM não acessa a intranet. O usuário baixa
  ou copia o `.md` e anexa/cola no assistente.
- Não use URLs internas como se a LLM pudesse abri-las; quando necessário, use placeholders como
  `http://servidor-interno:9099`.
- Mantenha o nome do arquivo como `llm_doc.md` (rota, download e prompts devem ser coerentes).
- Ao adicionar um endpoint, campo, regra de validação ou erro novo, inclua:
  - descrição do endpoint/comportamento;
  - exemplo de requisição e resposta;
  - códigos de erro;
  - impacto nos prompts e no modelo de dados;
  - atualização da tabela de versionamento e da versão no topo do arquivo.
- Se a mudança afetar o fluxo de uso, ajuste também os prompts em `llm_doc.html`.
- A página `/dcc/llm_doc` lê o Markdown e oferece “Baixar .md”/“Copiar documentação”; mantenha esse
  fluxo funcionando.

### 12.4 Checklist de conclusão

Antes de considerar a tarefa concluída:

- [ ] Código implementado e testado.
- [ ] Testes automatizados relevantes passando.
- [ ] Smoke test das rotas alteradas.
- [ ] Documentação padrão atualizada (README, `doc/`, páginas HTML aplicáveis).
- [ ] `flask/app/docs/llm_doc.md` atualizado.
- [ ] `flask/app/templates/llm_doc.html` atualizado (se o fluxo/prompt mudou).
- [ ] Versão da documentação para LLMs atualizada.
- [ ] Nenhum segredo, DB, `.env` ou artefato gerado incluído no commit.
- [ ] Mensagem de commit descritiva.

---

## 13. Armadilhas conhecidas

- **Não renomeie chaves JSON** (`nome_lab`, `num_certif`, `mensurando`, `resultados`, `nueff` etc.):
  são contrato público e afetam exemplos, planilha, testes e documentação.
- **`num_certif`**: não inclua o prefixo `DIMCI`; o XML gera `uniqueIdentifier = "DIMCI " + num_certif`.
- **Unidades D-SI**: barras invertidas exigem escape no JSON (`"\\degreecelsius"`).
- **`nueff`**: se presente, deve existir para todos os resultados do mesmo mensurando; não aceite
  `NaN`, `0`, negativos ou `-inf`.
- **`/dcc/validate_xml`**: retorna HTML, não JSON. Para automação, verifique o status e faça parsing
  do HTML ou valide localmente com lxml.
- **`/dcc/upload_json` e `/dcc/upload_xls`**: são conveniências web; a chamada interna para
  `/dcc/generate` atualmente não repassa `X-API-Key`. Para integrações, prefira `/dcc/generate`.
- **Autenticação**: `require_auth` aceita API-KEY ou sessão. Clientes de API sem chave recebem XML
  `401`; navegadores recebem redirect.
- **Templates antigos**: várias páginas não estendem `base.html` e incluem `nav_fragment.html`.
  Teste a navegação ao alterar menus.
- **Docker**: o código é montado via volume; após alterações, reinicie o container. Se mudar
  `requirements.txt`, rebuilde a imagem.
- **Produção é intranet**: não publique URLs internas em documentação destinada a LLMs externas.
- **AWS Lambda**: `aws_lambda/` é legado; não altere artefatos `.zip` manualmente.

---

## 14. Fluxo recomendado para uma alteração

1. Leia esta seção e o código relacionado em `flask/app/main.py`, `auth.py` ou no template certo.
2. Procure testes existentes e exemplos em `static/examples/`.
3. Implemente a menor mudança possível, preservando contratos existentes.
4. Atualize testes ou adicione um novo.
5. Atualize a documentação padrão aplicável.
6. Atualize `flask/app/docs/llm_doc.md` e, se necessário, `llm_doc.html`; incremente a versão do guia.
7. Rode os testes e o smoke test.
8. Revise `git diff` e confirme que não há segredos/artefatos.
9. Faça commit com mensagem clara (ex.: `feat: ...`, `fix: ...`, `docs: ...`).
