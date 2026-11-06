# DCC Tools — Guia de acesso à API para LLMs

**Versão:** 1.2
**Atualizado em:** 06/11/2026
**Público:** usuários, desenvolvedores e assistentes de IA (ChatGPT, Claude, Gemini, Copilot, agentes de código).
**Idioma:** português (pt-BR).

> **Importante — ambiente de intranet:** as URLs do DCC Tools são internas e normalmente **não são
> acessíveis** pelo assistente de IA. Este guia foi feito para ser **anexado ou colado** na conversa.
> Baixe o arquivo `llm_doc.md` em `/dcc/llm_doc.md` (ou use o botão **Copiar documentação**
> em `/dcc/llm_doc`) e envie o conteúdo junto com o seu pedido.

> Este documento foi escrito para ser lido por uma LLM. Ele reúne o que um assistente precisa para
> montar requisições, gerar o JSON de entrada, interpretar as respostas e evitar erros comuns.
> A documentação detalhada de cada campo do JSON está na página `/dcc/api_doc` do próprio serviço.

---

## 1. O que é o DCC Tools

O **DCC Tools** é um serviço do Inmetro (Dimci/Diele/Lampe) para gerar e processar
**Certificados de Calibração Digital (DCC)** no modelo do PTB (<https://www.ptb.de/dcc>).

O fluxo principal é:

```text
JSON de entrada  ──POST /dcc/generate──▶  XML DCC
XML DCC          ──POST /dcc/validate_xml──▶  resultado da validação
XML DCC + PDF    ──POST /dcc/pdf_attach──▶  PDF com o XML embutido
```

A API é síncrona, usa HTTP/1.1 e trafega JSON na entrada e XML (ou HTML/PDF) na saída.

---

## 2. Como usar esta documentação (instruções para o usuário)

### 2.1 Passo a passo

1. **Obtenha uma API-KEY.** Cadastre-se em `/dcc/register` ou faça login em `/dcc/login` e copie a
   chave exibida em **Perfil** (`/dcc/perfil`). O cadastro exige e-mail institucional
   `@inmetro.gov.br` e senha com pelo menos 8 caracteres.
2. **Baixe ou copie esta documentação.** Na intranet, abra `/dcc/llm_doc` e use **Baixar .md** ou
   **Copiar documentação**; alternativamente, baixe `/dcc/llm_doc.md`. A URL é interna e **não deve
   ser enviada ao assistente como se ele pudesse acessá-la**.
3. **Anexe o arquivo ou cole o conteúdo no assistente.** No ChatGPT/Claude/Gemini/Copilot, use o
   upload de arquivo ou cole o texto completo desta documentação. Não peça ao modelo para "abrir a
   URL"; ele não tem acesso à intranet.
4. **Descreva a tarefa.** Use um dos prompts da seção 2.3, preenchendo os campos entre colchetes.
5. **Revise antes de executar.** Confira o JSON, as unidades e o código gerado. **Nunca cole sua
   API-KEY real no chat**; use uma variável de ambiente no código.

### 2.2 O que enviar ao assistente

Quanto mais contexto, melhor:

- o arquivo `.md` desta documentação (ou o conteúdo colado); **não apenas a URL interna**;
- os dados de entrada (JSON, planilha ou XML);
- o resultado esperado (XML, PDF, relatório, script, revisão);
- restrições (linguagem, versão do schema, formato das incertezas, limites do laboratório).

Dicas por assistente:

- **ChatGPT:** use o clipe de anexo e envie o arquivo `.md`; se não aceitar, cole o conteúdo.
- **Claude:** anexe o `.md` na conversa ou adicione ao conhecimento do projeto.
- **Gemini:** use o botão de anexar arquivo ou cole o conteúdo.
- **Copilot e agentes de código:** cole o conteúdo no chat ou salve o `.md` no repositório do projeto
  e referencie o caminho no prompt.

### 2.3 Sugestões de prompt

**1. Gerar um cliente em Python**

```text
Use a documentação do DCC Tools que anexei (llm_doc.md) para escrever um script
Python 3.11 que leia meus dados de calibração de um CSV, monte o JSON aceito por POST /dcc/generate,
envie a requisição com a API-KEY lida da variável de ambiente DCC_API_KEY e salve o XML retornado.
Valide o XML antes de salvar e trate os erros 400, 401 e 500. Inclua um CSV de exemplo.
```

**2. Montar um JSON de exemplo**

```text
Com base na documentação do DCC Tools que anexei (llm_doc.md), gere um JSON completo para
um certificado de calibração de [instrumento], com [N] pontos de medição, incerteza [absoluta/relativa]
e versão de schema [3.3.0/3.2.0]. Explique cada campo e liste os campos obrigatórios.
```

**3. Revisar um JSON existente**

```text
Revise o JSON abaixo usando as regras da documentação do DCC Tools que anexei (llm_doc.md).
Verifique campos obrigatórios, unidades D-SI, coerência entre "indices" e "resultados" e as regras de
"nueff". Responda com uma lista de problemas e com o JSON corrigido.

<cole aqui o JSON>
```

**4. Criar um cliente em outra linguagem**

```text
Usando a documentação do DCC Tools que anexei (llm_doc.md), escreva um cliente em
[Node.js/Java/C#/PHP] que faça POST /dcc/generate com X-API-Key, salve o XML e mostre mensagens de
erro amigáveis. Não invente endpoints nem campos.
```

**5. Validar e anexar ao PDF**

```text
Crie um fluxo que primeiro valide o XML em POST /dcc/validate_xml e, se o status for 200, envie o XML
e o PDF para POST /dcc/pdf_attach usando multipart/form-data. Mostre exemplos em curl e em Python.
Explique como interpretar a resposta HTML da validação.
```

**6. Diagnosticar um erro**

```text
Recebi a resposta abaixo ao chamar a API do DCC Tools. Consulte a documentação do DCC Tools que anexei
(llm_doc.md), explique a causa provável e mostre como corrigir a requisição.

<cole aqui o status HTTP, os cabeçalhos e o corpo da resposta>
```

**7. Preencher a planilha Excel**

```text
Explique como preencher a planilha modelo do DCC Tools para um certificado de [instrumento] e escreva
um script que converta essa planilha no JSON aceito por POST /dcc/generate. Use também o guia da
planilha que anexei (ou o conteúdo de `/dcc/excel_guide`, se eu colar aqui).
```

**8. Atuar como revisor metrológico**

```text
Atue como revisor de certificados de calibração. Compare o JSON abaixo com a documentação do DCC Tools
que anexei (llm_doc.md) e aponte inconsistências de unidades, incertezas, fator de
abrangência, graus de liberdade efetivos e dados do cliente. Não altere os valores sem justificar.
```

### 2.4 Prompt base reutilizável

Copie o bloco abaixo e complete a tarefa:

```text
Você vai me ajudar a usar a API do DCC Tools.

Documentação: arquivo llm_doc.md anexado a esta conversa
Base URL: [URL da intranet, ex.: http://servidor-interno:9099]

Regras:
- Use somente endpoints e campos documentados; se faltar informação, pergunte.
- Envie a API-KEY no cabeçalho X-API-Key, nunca no corpo nem em URLs.
- Trate o XML como texto/binário e verifique o status HTTP antes de usá-lo.
- Preserve os valores numéricos como strings para não perder precisão.
- Nunca invente unidades; use o formato D-SI documentado.

Tarefa: [descreva aqui o que você quer]
Dados de entrada: [cole o JSON, CSV ou descreva os dados]
Restrições: [linguagem, versão do schema, formato de saída]
```

### 2.5 Instruções para o próprio modelo (system prompt)

```text
Você é um assistente especializado no DCC Tools. Consulte a documentação do DCC Tools anexada a esta
conversa (llm_doc.md) antes de responder. Gere apenas requisições para os
endpoints documentados. Nunca inclua uma API-KEY real em exemplos; use a variável de ambiente
DCC_API_KEY. Ao gerar JSON, use os nomes de campo em português exatamente como documentado e
represente unidades no formato D-SI (por exemplo, "\volt", "\micro\volt\volt\tothe{-1}",
"\degreecelsius"). Se a documentação não cobrir o caso, diga o que falta em vez de inventar.
```

---

## 3. Visão geral do serviço

| Item | Valor |
| --- | --- |
| Base URL (intranet) | `http://<host-da-intranet>:<porta>` (ex.: `http://servidor-interno:9099`) |
| Base URL (local) | `http://localhost:9099` |
| Protocolo | HTTP/1.1, HTTPS recomendado |
| Autenticação da API | cabeçalho `X-API-Key: dcc_...` |
| Alternativa de autenticação | cookie de sessão da interface web |
| Codificação | UTF-8 |
| Schema DCC | `3.3.0` (padrão) e `3.2.0` |
| Formato de entrada | JSON ou `multipart/form-data` |
| Formato de saída | XML DCC, HTML, PDF ou JSON de erro |

Todos os exemplos usam:

```bash
BASE_URL="http://servidor-interno:9099"
DCC_API_KEY="dcc_SUA_CHAVE"
```

> Troque `BASE_URL` pelo endereço da sua instância na intranet. O caminho das rotas (`/dcc/...`) não
> muda. O assistente não precisa acessar essa URL: ele gera o JSON/código que você executa localmente.

---

## 4. Autenticação

### 4.1 Cadastro e obtenção da API-KEY

```http
POST /dcc/register
Content-Type: application/json
```

```json
{
  "username": "nome_usuario",
  "email": "nome_usuario@inmetro.gov.br",
  "password": "senha_com_no_minimo_8_caracteres"
}
```

Resposta `201`:

```json
{
  "username": "nome_usuario",
  "email": "nome_usuario@inmetro.gov.br",
  "api_key": "dcc_...",
  "created_at": "2026-11-06T12:00:00+00:00"
}
```

Regras do cadastro:

- `username`: 1 a 64 caracteres; letras, números e `. _ @ -`.
- `email`: obrigatório, único e do domínio `@inmetro.gov.br`.
- `password`: mínimo de 8 caracteres.
- Duplicidade, e-mail fora do domínio ou senha curta retornam `400` com `{"error": "..."}`.

> Se você não tem e-mail `@inmetro.gov.br`, peça a criação da conta ao administrador do serviço.

### 4.2 Uso da API-KEY

Envie em **todas** as chamadas aos endpoints protegidos:

```http
X-API-Key: dcc_SUA_CHAVE
```

- Sem chave, chave inválida ou revogada: `401`.
- A chave pode ser consultada em `/dcc/perfil` após login.
- Para gerar uma nova chave (a anterior deixa de funcionar), use o botão de regeneração em
  `/dcc/perfil` (`POST /dcc/perfil/regenerar`).
- A chave é secreta: não a coloque em URLs, logs, prints ou repositórios públicos.

### 4.3 Sessão da interface web

A interface web usa login por usuário e senha (`POST /dcc/login`, formulário HTML) e um cookie de
sessão assinado. Nesse caso, a API-KEY não é necessária nas páginas e formulários web. Para
integrações automáticas, prefira a API-KEY.

### 4.4 Resposta de não autorizado

Para clientes de API, o `401` retorna XML (não JSON):

```xml
<?xml version='1.0' encoding='utf-8'?>
<autenticacaoNecessaria xmlns="https://inmetro.gov.br/dcc/api">
  <codigo>401</codigo>
  <mensagem lang="pt">A partir de agora o uso da API do DCC Generator requer cadastro e API-KEY.</mensagem>
  <mensagem lang="en">Using the DCC Generator API now requires registration and an API-KEY.</mensagem>
  <cadastro>...</cadastro>
  <uso>
    <cabecalho>X-API-Key</cabecalho>
    <exemploCurl>curl -X POST "..." -H "X-API-Key: dcc_SUA_CHAVE" ...</exemploCurl>
  </uso>
  <documentacao>https://HOST/dcc/api_doc</documentacao>
</autenticacaoNecessaria>
```

Navegadores que acessam uma página protegida são redirecionados para
`/dcc/login?auth_required=1`.

---

## 5. Início rápido

### 5.1 Gerar um DCC com curl

```bash
curl -X POST "$BASE_URL/dcc/generate" \
  -H "X-API-Key: $DCC_API_KEY" \
  -H "Content-Type: application/json" \
  --data @dados.json \
  -o dcc.xml
```

### 5.2 Gerar um DCC com Python

```python
import os
import requests

BASE_URL = os.environ.get("DCC_BASE_URL", "http://servidor-interno:9099")
API_KEY = os.environ["DCC_API_KEY"]

payload = {
    "nome_lab": "Laboratório de Metrologia em Padronização Elétrica",
    "sigla_lab": "Lampe",
    "nome_div": "Divisão de Metrologia Elétrica",
    "sigla_div": "Diele",
    "num_certif": "0856/2024",
    "num_processo": "0052600.003988/2023-06",
    "tipo_item": "Padrão de Transferência AC-DC",
    "fabricante": "Fluke",
    "modelo": "792A",
    "num_serie": "6515002",
    "cod_identificacao": "PT-030",
    "caracteristicas_item": "Função: Transferência Térmica de Tensão AC-DC",
    "data_calibracao": "2024-08-07",
    "cmc": True,
    "chefe_div": "Edson Afonso",
    "chefe_lab": "Gean Marcos Geronymo",
    "tecnico_executor": "Gean Marcos Geronymo",
    "desc_tecnico_executor": "Técnico Executor",
    "cliente": {
        "nome": "Inmetro/Dimci/Diele/Lacel",
        "email": "test@example.com",
        "cidade": "Duque de Caxias",
        "pais": "BR",
        "cep": "25250-020",
        "uf": "RJ",
        "endereco": "Av. Nossa Senhora das Graças",
        "numero": "50",
    },
    "informacoes_pertinentes": [
        {"name": "Temperatura", "value": "23.2", "unc": "1.0", "unit": "\\degreecelsius"},
        {"name": "Umidade relativa", "value": "49", "unc": "10", "unit": "\\percent"},
    ],
    "declaracao_rastreabilidade": "Os resultados são rastreados ao SI.",
    "declaracao_incerteza": "As incertezas expandidas são declaradas para p=95,45%.",
    "metodo_medicao": ["As entradas de tensão foram conectadas em paralelo."],
    "mensurando": [
        {
            "label": "acdc",
            "name": "Diferença AC-DC em tensão",
            "col_name": "\\delta_u",
            "unit": "\\micro\\volt\\volt\\tothe{-1}",
            "unc_relativa": False,
        }
    ],
    "indices": [
        {"mensurando": "acdc", "label": "frequency", "name": "Frequência", "unit": "\\kilo\\hertz"}
    ],
    "resultados": [
        {"mensurando": "acdc", "frequency": "0.01", "value": "-280", "unc": "44", "k": "2.13"},
        {"mensurando": "acdc", "frequency": "0.02", "value": "3", "unc": "37", "k": "2.28"},
    ],
}

response = requests.post(
    f"{BASE_URL}/dcc/generate",
    json=payload,
    headers={"X-API-Key": API_KEY},
    timeout=60,
)

if response.status_code == 200:
    with open("dcc.xml", "wb") as f:
        f.write(response.content)
else:
    print(response.status_code, response.text)
```

---

## 6. Endpoints

| Método | Rota | Autenticação | Entrada | Saída |
| --- | --- | --- | --- | --- |
| `POST` | `/dcc/generate` | API-KEY ou sessão | JSON | XML DCC (`text/xml`) |
| `POST` | `/dcc/upload_json` | API-KEY ou sessão | `multipart` (`json_file`) | XML DCC |
| `POST` | `/dcc/upload_xls` | API-KEY ou sessão | `multipart` (`xls_file`) | XML DCC |
| `POST` | `/dcc/pdf_attach` | API-KEY ou sessão | `multipart` (`pdf_file`, `xml_file`) | PDF |
| `GET/POST` | `/dcc/validate_xml` | aberta | `multipart` (`xml_file`) | HTML de validação |
| `POST` | `/dcc/visualizar_dcc` | aberta | `multipart` (`xml_file`) | HTML legível |
| `POST` | `/dcc/register` | aberta | JSON | JSON com `api_key` |
| `GET` | `/dcc/perfil` | sessão | — | HTML com a API-KEY |
| `POST` | `/dcc/perfil/regenerar` | sessão | — | redireciona ao perfil |

---

## 7. Detalhamento dos endpoints

### 7.1 `POST /dcc/generate` — principal

Gera o XML DCC a partir do JSON.

**Cabeçalhos da requisição**

| Cabeçalho | Valor |
| --- | --- |
| `Content-Type` | `application/json` |
| `X-API-Key` | `dcc_...` |

**Resposta de sucesso (`200`)**

| Item | Valor |
| --- | --- |
| `Content-Type` | `text/xml` |
| `Content-Disposition` | `attachment; filename="CC_DIMCI_<num_certif>.xml"` |
| Corpo | XML DCC completo |

O nome do arquivo usa `num_certif` com `/` substituído por `_`. O XML inclui
`uniqueIdentifier = "DIMCI " + num_certif`; portanto, **não** envie o prefixo `DIMCI` no campo
`num_certif`.

**Exemplo de resposta (trecho)**

```xml
<?xml version='1.0' encoding='utf-8'?>
<dcc:digitalCalibrationCertificate
    xmlns:dcc="https://ptb.de/dcc"
    xmlns:si="https://ptb.de/si"
    schemaVersion="3.3.0">
  <dcc:administrativeData>
    <dcc:coreData>
      <dcc:uniqueIdentifier>DIMCI 0856/2024</dcc:uniqueIdentifier>
      ...
    </dcc:coreData>
  </dcc:administrativeData>
  <dcc:measurementResults>
    ...
  </dcc:measurementResults>
</dcc:digitalCalibrationCertificate>
```

**Erros**

| Código | Situação | Corpo |
| --- | --- | --- |
| `400` | JSON ausente | `{"error": "No JSON provided"}` |
| `400` | JSON inválido | `{"error": "Invalid JSON: ..."}` |
| `400` | Falha de validação (ex.: `nueff` inválido) | `{"error": "<mensagem>"}` |
| `401` | API-KEY ausente/inválida/revogada | XML `<autenticacaoNecessaria>` |
| `500` | Erro inesperado | `{"error": "Erro ao gerar o DCC: ..."}` |

> Observação: campos obrigatórios ausentes podem resultar em `500` com
> `{"error": "Erro ao gerar o DCC: ..."}` (e, para `num_certif`, em um erro `500` genérico antes da
> validação). Valide o payload localmente antes de enviar.

Versão do schema: o campo `dcc_version` (ou o alias `schema_version`) aceita `3.2.0` e `3.3.0`.
Se ausente ou não reconhecido, o padrão é `3.3.0`.

### 7.2 `POST /dcc/upload_json`

Conveniência web: recebe um arquivo `.json` e encaminha internamente para `/dcc/generate`.

```bash
curl -X POST "$BASE_URL/dcc/upload_json" \
  -H "X-API-Key: $DCC_API_KEY" \
  -F "json_file=@dados.json" \
  -o dcc.xml
```

- Campo multipart: `json_file` (obrigatório, extensão `.json`).
- Sucesso: XML como anexo.
- Erros desta rota são retornados como **texto simples** (não JSON), por exemplo
  `Invalid JSON format` ou `API Error: 400 - ...`.
- Para integrações, prefira `POST /dcc/generate`, que tem contrato JSON/XML mais claro.
  As rotas de upload são conveniências da interface web e podem variar conforme a implantação.

### 7.3 `POST /dcc/upload_xls`

Conveniência web: recebe uma planilha `.xlsx`, converte para JSON e gera o XML.

```bash
curl -X POST "$BASE_URL/dcc/upload_xls" \
  -H "X-API-Key: $DCC_API_KEY" \
  -F "xls_file=@planilha.xlsx" \
  -o dcc.xml
```

- Campo multipart: `xls_file` (obrigatório, extensão `.xlsx`).
- A estrutura da planilha está descrita em `/dcc/excel_guide`.
- Erros também são retornados como texto simples.
- Para controle total do JSON, use `POST /dcc/generate` diretamente.

### 7.4 `POST /dcc/pdf_attach`

Anexa o XML DCC a um PDF, gerando um PDF com o XML embutido e um arquivo `SHA256SUM.txt` como
anexo de integridade.

```bash
curl -X POST "$BASE_URL/dcc/pdf_attach" \
  -H "X-API-Key: $DCC_API_KEY" \
  -F "pdf_file=@certificado.pdf" \
  -F "xml_file=@dcc.xml" \
  -o certificado_com_dcc.pdf
```

- Campos multipart: `pdf_file` (PDF) e `xml_file` (XML).
- Sucesso: `application/pdf` como anexo, com o nome do PDF original.
- Erros de arquivo ausente/inválido: `400` com `{"error": "..."}`.
- O PDF de entrada deve ser compatível com PDF/A-3B para que o resultado preserve a conformidade.
- Anexos gerados: o XML DCC e `SHA256SUM.txt`.

### 7.5 `GET|POST /dcc/validate_xml`

Valida um XML DCC contra o schema indicado no atributo `xsi:schemaLocation` do próprio XML.

```bash
curl -X POST "$BASE_URL/dcc/validate_xml" \
  -F "xml_file=@dcc.xml" \
  -o resultado_validacao.html
```

- Sem autenticação.
- Campo multipart: `xml_file`.
- A resposta é uma **página HTML**, não JSON:
  - `200`: XML válido;
  - `400`: XML inválido (a página lista os erros);
  - `500`: erro interno.
- O download do schema é restrito a hosts confiáveis (`DCC_ALLOWED_SCHEMA_HOSTS`, padrão
  `ptb.de,w3.org`) e a um tamanho máximo (`DCC_MAX_SCHEMA_BYTES`, padrão 5 MiB).
- Para automação, verifique o status HTTP e, se necessário, faça parsing do HTML. Se preferir um
  resultado estruturado, valide localmente com `lxml` usando o XSD do PTB.

### 7.6 `POST /dcc/visualizar_dcc`

Converte o XML em uma visualização HTML legível (transformação XSLT).

```bash
curl -X POST "$BASE_URL/dcc/visualizar_dcc" \
  -F "xml_file=@dcc.xml" \
  -o dcc.html
```

- Sem autenticação.
- Campo multipart: `xml_file` (somente `.xml`).
- Sucesso: HTML.
- Erro: JSON `{"error": "..."}` com `400`/`500`.
- A página de upload correspondente é `GET /dcc/upload_xml_hr`.

### 7.7 `POST /dcc/register`

Cadastro aberto (com a restrição de e-mail institucional descrita na seção 4.1). Retorna a API-KEY
em texto puro **uma única vez** na resposta; depois, ela pode ser consultada no perfil.

```bash
curl -X POST "$BASE_URL/dcc/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"meu_usuario","email":"meu_usuario@inmetro.gov.br","password":"minha_senha_longa"}'
```

### 7.8 Perfil e sessão

- `GET /dcc/perfil`: exige sessão; mostra a API-KEY e o e-mail do usuário.
- `POST /dcc/perfil/regenerar`: gera uma nova API-KEY; a anterior é invalidada imediatamente.
- `POST /dcc/login`: login por formulário (`username`, `password`), cria o cookie de sessão.
- `GET /dcc/logout`: encerra a sessão.
- `GET|POST /dcc/perfil/senha`: troca de senha (exige a senha atual).
- `GET|POST /dcc/esqueci-senha`: solicita recuperação por e-mail.
- `GET|POST /dcc/redefinir-senha?token=...`: define a nova senha a partir do token.

---

## 8. Modelo de dados JSON

O JSON representa os dados do certificado. As chaves estão em **português** e devem ser mantidas
exatamente como abaixo, incluindo acentos. A ordem das chaves é irrelevante.

### 8.1 Campos de metadados

| Chave | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `nome_lab` | string | sim | Nome completo do laboratório. |
| `sigla_lab` | string | sim | Sigla do laboratório. |
| `nome_div` | string | sim | Nome da divisão. |
| `sigla_div` | string | sim | Sigla da divisão. |
| `num_certif` | string | sim | Número do certificado, sem o prefixo `DIMCI`. |
| `num_processo` | string | sim | Número do processo Inmetro. |
| `tipo_item` | string | sim | Tipo/descrição do item calibrado. |
| `fabricante` | string | sim | Fabricante do item. |
| `modelo` | string | sim | Modelo do item. |
| `num_serie` | string | sim | Número de série. |
| `cod_identificacao` | string | sim | Código de identificação interno. |
| `caracteristicas_item` | string | sim | Características adicionais do item. |
| `data_calibracao` | string | sim | Data da calibração (`YYYY-MM-DD`). |
| `data_emissao` | string | não | Data de emissão (`YYYY-MM-DD`). Se omitida, o XML usa a declaração de assinatura eletrônica. |
| `cmc` | boolean | sim | Indica se o certificado possui CMC. |
| `chefe_div` | string | sim | Nome do chefe da divisão. |
| `desc_chefe_div` | string | não | Cargo do chefe da divisão. |
| `chefe_lab` | string | sim | Nome do chefe do laboratório. |
| `desc_chefe_lab` | string | não | Cargo do chefe do laboratório. |
| `tecnico_executor` | string | sim | Nome do técnico executor. |
| `desc_tecnico_executor` | string | sim | Cargo/descrição do técnico executor. |
| `dcc_version` | string | não | `3.3.0` (padrão) ou `3.2.0`. |
| `schema_version` | string | não | Alias de `dcc_version`. |

### 8.2 Blocos aninhados

| Chave | Tipo | Obrigatório | Conteúdo |
| --- | --- | --- | --- |
| `cliente` | objeto | sim | `nome`, `email`, `cidade`, `pais`, `cep`, `uf`, `endereco`, `numero`. |
| `informacoes_pertinentes` | array | sim (pode ser vazio) | Condições ambientais: `name`, `value` ou `value_min`/`value_max` ou `text`, `unc`, `k`, `unit`, `refType`. |
| `declaracao_rastreabilidade` | string | sim | Texto da declaração de rastreabilidade. |
| `tabela_rastreabilidade` | array | não | `name`, `origem`, `certificado`, `cod_id`. |
| `declaracao_incerteza` | string | sim | Texto da declaração de incerteza. |
| `metodo_medicao` | array de strings | sim | Uma ou mais descrições do método. |
| `metodo_medicao_equation` | array de strings | não | Equações em LaTeX, alinhadas por índice a `metodo_medicao`. |
| `mensurando` | array | sim (≥ 1) | `label`, `name`, `col_name`, `unit`, `unc_relativa`, `refType`, `relative_uncertainty_in_dcc`, `relative_unc_unit`. |
| `indices` | array | não | `mensurando`, `label`, `name`, `unit`, `refType`. |
| `resultados` | array | sim | `mensurando`, `value`, `unc`, `k`, uma chave por índice e `nueff` opcional. |
| `observacoes` | array de strings | não | Cada item vira um statement "Observação N". |
| `software` | array | não | `name`, `version` de softwares adicionais. |
| `refTypeDefinitions` | array | não | `name`, `description`, `namespace`, `link`. |

### 8.3 Exemplo mínimo completo

```json
{
  "nome_lab": "Laboratório de Metrologia em Padronização Elétrica",
  "sigla_lab": "Lampe",
  "nome_div": "Divisão de Metrologia Elétrica",
  "sigla_div": "Diele",
  "num_certif": "0856/2024",
  "num_processo": "0052600.003988/2023-06",
  "tipo_item": "Padrão de Transferência AC-DC",
  "fabricante": "Fluke",
  "modelo": "792A",
  "num_serie": "6515002",
  "cod_identificacao": "PT-030",
  "caracteristicas_item": "Função: Transferência Térmica de Tensão AC-DC",
  "data_calibracao": "2024-08-07",
  "cmc": true,
  "chefe_div": "Edson Afonso",
  "chefe_lab": "Gean Marcos Geronymo",
  "tecnico_executor": "Gean Marcos Geronymo",
  "desc_tecnico_executor": "Técnico Executor",
  "cliente": {
    "nome": "Inmetro/Dimci/Diele/Lacel",
    "email": "test@example.com",
    "cidade": "Duque de Caxias",
    "pais": "BR",
    "cep": "25250-020",
    "uf": "RJ",
    "endereco": "Av. Nossa Senhora das Graças",
    "numero": "50"
  },
  "informacoes_pertinentes": [
    { "name": "Temperatura", "value": "23.2", "unc": "1.0", "unit": "\\degreecelsius" },
    { "name": "Umidade relativa", "value": "49", "unc": "10", "unit": "\\percent" }
  ],
  "declaracao_rastreabilidade": "Os resultados da calibração são rastreados ao Sistema Internacional de Unidades (SI).",
  "declaracao_incerteza": "As incertezas expandidas de medição (U) são declaradas para p=95,45%.",
  "metodo_medicao": ["As entradas de tensão foram conectadas em paralelo."],
  "mensurando": [
    {
      "label": "acdc",
      "name": "Diferença AC-DC em tensão",
      "col_name": "\\delta_u",
      "unit": "\\micro\\volt\\volt\\tothe{-1}",
      "unc_relativa": false
    }
  ],
  "indices": [
    { "mensurando": "acdc", "label": "frequency", "name": "Frequência", "unit": "\\kilo\\hertz" }
  ],
  "resultados": [
    { "mensurando": "acdc", "frequency": "0.01", "value": "-280", "unc": "44", "k": "2.13" },
    { "mensurando": "acdc", "frequency": "0.02", "value": "3", "unc": "37", "k": "2.28" }
  ]
}
```

### 8.4 Regras importantes

- Envie metadados como **string**, exceto `cmc` e `unc_relativa` (booleanos).
- `value`, `unc`, `k` e `nueff` podem ser string ou número; prefira string para preservar a
  representação decimal exata.
- Cada `resultados[]` deve referenciar um `mensurando` existente pelo `label`.
- Cada índice definido em `indices` deve existir nos resultados daquele mensurando.
- Para múltiplos mensurandos, repita o bloco em `mensurando`, referencie os índices em `indices` e
  agrupe os resultados por `mensurando`.
- Quando `mensurando[].unc_relativa` é `true`, o valor de `unc` é tratado como relativo (ppm) e
  convertido para absoluto com dois algarismos significativos.
- A documentação completa, campo a campo, está em `/dcc/api_doc`.

---

## 9. Unidades no formato D-SI

As unidades seguem o formato usado pelo schema PTB:

- Prefixo com barra invertida: `\volt`, `\ohm`, `\ampere`, `\hertz`, `\pascal`, `\watt`, `\one`.
- Potências: `\tothe{expoente}` — por exemplo, `\volt\tothe{-1}`.
- Prefixos SI: `\micro`, `\milli`, `\kilo`, `\nano`.
- Multiplicação por justaposição: `\micro\volt\volt\tothe{-1}`.
- Temperatura: `\degreecelsius`.
- Percentual: `\percent`.
- Adimensional: `\one`.

Em JSON, a barra invertida deve ser escapada:

```json
{ "unit": "\\micro\\volt\\volt\\tothe{-1}" }
```

---

## 10. Graus de liberdade efetivos (`nueff`)

Campo opcional por linha de resultado, que representa νeff.

Regras:

1. Se `nueff` estiver presente em um resultado, **todos** os resultados do mesmo mensurando devem
   informá-lo.
2. O número de valores deve ser igual ao número de resultados do mensurando.
3. Os valores devem ser numéricos e estritamente positivos (`> 0`); valores fracionários são aceitos.
4. `+∞` pode ser representado por `"inf"` (string) ou `Infinity`/`+Infinity`. No XML, é serializado
   como `inf`.
5. São rejeitados (`400`): `0`, negativos, `-inf`, `null`, string vazia, `NaN` e valores não numéricos.
6. Se `nueff` não for informado, nenhuma quantidade adicional é gerada.

Exemplo:

```json
"resultados": [
  { "mensurando": "acdc", "frequency": "0.01", "value": "-280", "unc": "44", "k": "2.13", "nueff": "58.4" },
  { "mensurando": "acdc", "frequency": "0.02", "value": "3", "unc": "37", "k": "2.28", "nueff": "inf" }
]
```

No XML, é adicionada uma `dcc:quantity` com `dcc:charsXMLList` ao final da mesma `dcc:list`:

```xml
<dcc:quantity>
  <dcc:name>
    <dcc:content lang="pt">Graus de liberdade efetivos</dcc:content>
  </dcc:name>
  <dcc:charsXMLList>58.4 inf</dcc:charsXMLList>
</dcc:quantity>
```

---

## 11. Erros e solução de problemas

| Sintoma | Causa provável | Como corrigir |
| --- | --- | --- |
| `401` com XML `<autenticacaoNecessaria>` | API-KEY ausente, inválida ou revogada. | Confira o cabeçalho `X-API-Key` e gere/consulte a chave em `/dcc/perfil`. |
| `400` `{"error": "No JSON provided"}` | Corpo vazio ou `Content-Type` errado. | Envie JSON e defina `Content-Type: application/json`. |
| `400` `{"error": "Invalid JSON: ..."}` | JSON malformado. | Valide o JSON; lembre-se de escapar `\` nas unidades D-SI. |
| `400` `{"error": "<mensagem>"}` | Regra de validação violada (ex.: `nueff` inválido). | Leia a mensagem e ajuste o campo indicado. |
| `500` `{"error": "Erro ao gerar o DCC: ..."}` | Campo obrigatório ausente, tipo inesperado ou falha interna. | Confira a seção 8 e os campos obrigatórios; se persistir, contate o administrador com o payload e o horário. |
| `/dcc/validate_xml` retorna HTML com erros | XML inválido, `schemaLocation` ausente ou schema em host não confiável. | Confira o XML e o `xsi:schemaLocation`; o schema precisa estar em `ptb.de`/`w3.org` (ou na allowlist). |
| `/dcc/upload_json` retorna texto simples | Comportamento esperado dessa rota de conveniência. | Prefira `/dcc/generate` para respostas JSON/XML consistentes. |
| PDF anexado perde conformidade PDF/A-3 | PDF de entrada não era PDF/A-3B. | Use um PDF/A-3B de entrada e valide o resultado. |

---

## 12. Boas práticas para LLMs e agentes

1. **Não invente endpoints nem campos.** Use apenas o que está neste documento.
2. **Autentique sempre** nos endpoints protegidos e nunca exponha a chave em logs ou exemplos.
3. **Verifique o status HTTP** antes de interpretar o corpo; erros nem sempre são JSON.
4. **Trate a resposta como binária** ao salvar XML/PDF (`response.content`, não `response.text`).
5. **Preserve precisão:** represente números como strings no JSON.
6. **Respeite o schema:** não envie o prefixo `DIMCI` em `num_certif`.
7. **Use unidades D-SI** e escape as barras invertidas no JSON.
8. **Valide antes de anexar:** chame `/dcc/validate_xml` antes de `/dcc/pdf_attach`.
9. **Seja idempotente:** reenvie apenas em caso de falha transitória (`5xx`); para `4xx`, corrija a
   requisição.
10. **Peça confirmação humana** antes de gerar certificados reais ou sobrescrever arquivos.

---

## 13. Links úteis

- Página inicial: `/dcc/`
- Documentação completa da API (HTML): `/dcc/api_doc`
- Guia da planilha Excel: `/dcc/excel_guide`
- Exemplos de DCC: `/dcc/exemplos`
- Perguntas frequentes: `/dcc/faq`
- Publicações: `/dcc/publications`
- Código-fonte: <https://github.com/gmgeronymo/dcc_tools>
- Modelo DCC do PTB: <https://www.ptb.de/dcc>

---

## 14. Versionamento deste documento

| Versão | Data | Alteração |
| --- | --- | --- |
| 1.0 | 06/11/2026 | Criação do guia de acesso à API para LLMs, com instruções de uso e prompts. |
| 1.1 | 06/11/2026 | Ajuste para ambiente de intranet: baixar/anexar o `.md` em vez de depender da URL interna. |
| 1.2 | 06/11/2026 | Nome do arquivo unificado para `llm_doc.md`, igual ao caminho de download. |
