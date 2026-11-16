# API DCC Generator — Referência para LLMs

Este documento descreve a API HTTP de geração de **Certificados de Calibração Digital (DCC)** do projeto
**DCC Tools** (Inmetro/Dimci/Diele/Lampe), com foco em permitir que um LLM (ou um agente de código)
implemente um cliente que consuma a API corretamente.

O gerador recebe um **JSON** e devolve um **XML DCC** compatível com o modelo do PTB
([Digital Calibration Certificate](https://www.ptb.de/dcc)).

> Para instruções de uso com assistentes de IA (ChatGPT, Claude, Gemini, Copilot) e prompts prontos,
> consulte o **Guia de acesso à API para LLMs**: `/dcc/llm_doc` (HTML) ou `/dcc/llm_doc.md`
> (Markdown). O arquivo fonte fica em `flask/app/docs/llm_doc.md`. Como o serviço roda em
> intranet, **baixe o `.md` e anexe-o ao assistente**; a URL interna normalmente não é acessível pela LLM.

---

## 1. Visão geral

- **Protocolo**: HTTP/1.1, JSON no corpo da requisição, XML na resposta.
- **Autenticação**: API-KEY de usuário no cabeçalho `X-API-Key` (ver §1.1).
- **Codificação**: UTF-8.
- **Schema DCC suportado**: `3.3.0` (padrão). O schema `3.2.0` não é mais aceito para geração.

### Endpoint principal

```
POST /dcc/generate
```

| Item | Valor |
| --- | --- |
| `Content-Type` da requisição | `application/json` |
| `Content-Type` da resposta | `text/xml` |
| `Content-Disposition` da resposta | `attachment; filename="CC_DIMCI_<num_certif>.xml"` |
| Autenticação | `X-API-Key: <api-key de usuário>` |
| Sucesso | `200` com o XML DCC no corpo |
| Não autorizado | `401` com JSON `{"error": "<mensagem>"}` |
| Erro de validação | `400` com JSON `{"error": "<mensagem>"}` |
| Erro interno | `500` com JSON `{"error": "<mensagem>"}` |

**Base URL** (exemplo; o serviço roda em ambiente de intranet): `https://sig-dimci.inmetro.gov.br/dcc/generate`.
O caminho da rota é sempre `/dcc/generate`; o host pode variar conforme o ambiente.

### 1.1 Autenticação por API-KEY

Os endpoints de geração e upload exigem uma **API-KEY de usuário**, enviada no cabeçalho HTTP:

```
X-API-Key: dcc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

- Sem chave, chave inválida ou revogada → `401`.
- Cada usuário cadastrado recebe uma API-KEY, que pode ser consultada na área de perfil da interface
  web (`/dcc/perfil`) ou pelo administrador (`python manage_auth.py list-users`).
- Na interface web, a autenticação é transparente: o usuário faz login e a sessão autoriza as funções;
  não é necessário informar a API-KEY na tela.

**Transição para clientes antigos:** clientes de API que ainda não enviam a API-KEY recebem, em vez de
um JSON, uma **resposta XML** (`401`) com instruções de cadastro e de ajuste do software. É emitida
quando a requisição não é uma navegação de página (por exemplo, `POST` com `Accept: */*` ou
`application/xml`). Navegadores são redirecionados para `/dcc/login?auth_required=1`.

```xml
<?xml version='1.0' encoding='utf-8'?>
<autenticacaoNecessaria xmlns="https://inmetro.gov.br/dcc/api">
  <codigo>401</codigo>
  <mensagem lang="pt">A partir de agora o uso da API do DCC Generator requer cadastro e API-KEY.</mensagem>
  <mensagem lang="en">Using the DCC Generator API now requires registration and an API-KEY.</mensagem>
  <cadastro>
    <url>https://HOST/dcc/register</url>
    <metodo>POST</metodo>
    <contentType>application/json</contentType>
    <corpoExemplo>{"username":"meu_usuario","password":"minha_senha","email":"eu@exemplo.com"}</corpoExemplo>
    <respostaExemplo>{"username":"meu_usuario","api_key":"dcc_..."}</respostaExemplo>
    <orientacao lang="pt">Cadastre-se uma vez para obter a API-KEY. A chave também fica disponível na área de perfil após o login na interface web.</orientacao>
  </cadastro>
  <uso>
    <cabecalho>X-API-Key</cabecalho>
    <instrucao lang="pt">Ajuste o seu software para enviar o cabeçalho X-API-Key com a sua API-KEY em todas as requisições.</instrucao>
    <exemploCurl>curl -X POST "https://HOST/dcc/generate" -H "X-API-Key: dcc_SUA_CHAVE" -H "Content-Type: application/json" --data @dados.json</exemploCurl>
  </uso>
  <documentacao>https://HOST/dcc/api_doc</documentacao>
</autenticacaoNecessaria>
```

### 1.2 Cadastro de usuário (auto-cadastro)

```
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
  "created_at": "2026-09-18T12:00:00+00:00"
}
```

- A `password` é obrigatória (mínimo de 8 caracteres) e armazenada com hash.
- O `email` é **obrigatório**, **único** e deve ser do domínio **`@inmetro.gov.br`**.
- A `api_key` é gerada automaticamente; pode ser consultada depois na área de perfil.
- `username` deve ser único (até 64 caracteres: letras, números e `. _ @ -`).
- Duplicidade (usuário ou e-mail), nome inválido, e-mail fora do domínio ou senha curta → `400` com
  `{"error": "<mensagem>"}`.

### 1.3 Interface web

- `GET /dcc/login`: formulário de login (campos `username` e `password`).
- `POST /dcc/login`: autentica usuário e senha e cria uma sessão (cookie assinado por `DCC_SECRET_KEY`).
- `GET /dcc/perfil`: área de perfil do usuário logado, onde a **API-KEY** fica disponível (com opção de
  gerar uma nova).
- `GET|POST /dcc/perfil/senha`: troca de senha (exige a senha atual).
- `GET|POST /dcc/esqueci-senha`: solicita recuperação de senha por e-mail.
- `GET|POST /dcc/redefinir-senha?token=...`: define uma nova senha usando o token do e-mail.
- `GET /dcc/logout`: encerra a sessão.
- Acesso não autenticado a uma função protegida redireciona para `/dcc/login?auth_required=1`, que
  avisa que a função requer autenticação e aponta para login e cadastro.
- Páginas informativas (início, introdução, FAQ, exemplos, documentação) permanecem abertas.

### 1.4 Configuração (variáveis de ambiente)

| Variável | Descrição |
| --- | --- |
| `DCC_SECRET_KEY` | Chave para assinar a sessão da interface web. Obrigatória em produção. |
| `DCC_DB_PATH` | Caminho do banco SQLite (padrão: `flask/app/dcc_auth.db`). |
| `DCC_SESSION_HOURS` | Duração da sessão da interface web, em horas (padrão: `8`). |
| `DCC_ALLOWED_SCHEMA_HOSTS` | Hosts confiáveis para download de schemas na validação de XML (padrão: `ptb.de,w3.org`; lista separada por vírgulas, cobre domínio e subdomínios). |
| `DCC_MAX_SCHEMA_BYTES` | Tamanho máximo de um schema baixado na validação, em bytes (padrão: `5242880`). |
| `DCC_EMAIL_ENABLED` | Habilita o envio de e-mail (padrão: `true`). |
| `SMTP_HOST` | Host SMTP do servidor de e-mail (definido no `.env`; sem padrão no código). |
| `SMTP_PORT` | Porta SMTP (padrão: `587`). |
| `SMTP_FROM` | Remetente dos e-mails (definido no `.env`; sem padrão no código). |
| `SMTP_USE_AUTH` / `SMTP_USERNAME` / `SMTP_PASSWORD` | Autenticação SMTP (padrão: sem autenticação). |
| `SMTP_USE_TLS` | STARTTLS (padrão: `false`). |
| `SMTP_TIMEOUT` | Timeout da conexão SMTP, em segundos (padrão: `15`). |
| `APP_BASE_URL` | URL base oficial usada no link de recuperação (padrão: `https://sig-dimci.inmetro.gov.br`). |
| `DCC_RESET_TOKEN_MINUTES` | Validade do token de recuperação, em minutos (padrão: `60`). |

### 1.5 Gerenciamento (CLI)

A partir de `flask/app/`:

```bash
python manage_auth.py init-db
python manage_auth.py create-user <username> --email <email> [--password <senha>]
python manage_auth.py set-password <username> [--password <senha>]
python manage_auth.py list-users
python manage_auth.py revoke <username>
python manage_auth.py activate <username>
```

---

## 2. Corpo da requisição (JSON de entrada)

O JSON representa os dados de um certificado de calibração. As chaves estão em **português** e
devem ser mantidas exatamente como abaixo (incluindo acentos).

### 2.1 Campos de metadados principais

| Chave | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `nome_lab` | string | sim | Nome completo do laboratório. |
| `sigla_lab` | string | sim | Sigla do laboratório. |
| `nome_div` | string | sim | Nome da divisão. |
| `sigla_div` | string | sim | Sigla da divisão. |
| `num_certif` | string | sim | Número do certificado (sem o prefixo "DIMCI"). |
| `num_processo` | string | sim | Número do processo Inmetro. |
| `tipo_item` | string | sim | Tipo/descrição do item calibrado. |
| `fabricante` | string | sim | Fabricante do item. |
| `modelo` | string | sim | Modelo do item. |
| `num_serie` | string | sim | Número de série. |
| `cod_identificacao` | string | sim | Código de identificação interno. |
| `caracteristicas_item` | string | não | Características adicionais do item. Opcional: se omitido/vazio, o statement "Características do Item" não é emitido. Pode ser omitido quando `valor_nominal` é informado. |
| `valor_nominal` | objeto ou string | não | Valor nominal estruturado do item em `dcc:itemQuantities/dcc:itemQuantity` com `refType="basic_nominalValue"`. Formato recomendado: `{"valor": "100", "unidade": "\\ohm", "nome": "Valor nominal", "descricao": "..."}`. Também aceita o formato legado `valor_nominal` escalar + `valnom_unit`. Ver §2.14. |
| `valnom_unit` | string | não | Unidade do valor nominal no formato legado (usada quando `valor_nominal` é escalar). Prefira `valor_nominal.unidade`. |
| `data_calibracao` | string | sim | Data da calibração, ISO 8601 (`YYYY-MM-DD`). |
| `data_emissao` | string | não | Data de emissão (`YYYY-MM-DD`). Se omitida, o XML inclui a declaração "Ver data da assinatura eletrônica presente no certificado". |
| `cmc` | boolean | sim | Indica se o certificado possui a declaração de CMC (MRA/CIPM). Quando `true`, o `dcc:statement` de CMC é emitido no formato estruturado `basic_isInCMC`. |
| `cmc_padrao` | boolean | não | Valor de cobertura de CMC aplicado aos resultados que não informam `in_cmc`. Se omitido, o padrão é `false`. |
| `cmc_declaracao` | objeto | não | Personaliza a declaração estruturada `basic_isInCMC`. Ver §2.13. |
| `chefe_div` | string | sim | Nome do chefe da divisão. |
| `desc_chefe_div` | string | não | Cargo do chefe da divisão. Se fornecido, é sufixado com `" da " + nome_div`; senão usa `"Chefe da " + nome_div`. |
| `chefe_lab` | string | sim | Nome do chefe do laboratório. |
| `desc_chefe_lab` | string | não | Cargo do chefe do laboratório. Se fornecido, é sufixado com `" do " + nome_lab`; senão usa `"Chefe do " + nome_lab`. |
| `tecnico_executor` | string | sim | Nome do técnico executor. |
| `desc_tecnico_executor` | string | sim | Cargo/descrição do técnico executor. |
| `dcc_version` | string | não | Versão do schema. Único valor aceito: `3.3.0`. Padrão: `3.3.0`. |
| `schema_version` | string | não | Alias alternativo para `dcc_version`. |

> A versão de schema é resolvida na ordem: `dcc_version` → `schema_version` → `3.3.0`.
> `3.2.0` e valores desconhecidos retornam **400**. Certificados 3.2.0 já emitidos
> continuam válidos para validação e visualização.
>
> `caracteristicas_item` é opcional. Recomenda-se informar `caracteristicas_item` **ou**
> `valor_nominal` para manter a seção "Características do Item" na visualização. Se ambos forem
> omitidos, o XML continua válido, mas a seção não é exibida.

### 2.2 `software` (opcional)

Array de objetos com software adicional (o gerador sempre inclui a si mesmo).

```json
"software": [
  { "name": "SYS-LAMPE", "version": "v2.3-69-3526f2d" }
]
```

| Chave | Tipo | Descrição |
| --- | --- | --- |
| `name` | string | Nome do software. |
| `version` | string | Versão do software. |

### 2.3 `refTypeDefinitions` (opcional)

Array com definições de RefTypes adicionais.

```json
"refTypeDefinitions": [
  {
    "name": "Namespace for RefTypes of the Temperature",
    "description": "The 'temperature' namespace contains RefTypes for temperature quantities.",
    "namespace": "temperature",
    "link": "https://digilab.ptb.de/dkd/refType/vocab/index.php?tema=117"
  },
  {
    "name": "Namespace for RefTypes of Electromagnetism",
    "description": "The 'electromagnetic' namespace contains RefTypes for electromagnetic quantities.",
    "namespace": "electromagnetic",
    "link": "https://digilab.ptb.de/dkd/refType/vocab/index.php?tema=389"
  }
]
```

| Chave | Tipo | Descrição |
| --- | --- | --- |
| `name` | string | Nome do namespace. |
| `description` | string | Descrição do namespace. |
| `namespace` | string | Identificador do namespace. |
| `link` | string | URL da definição do namespace. |

> **Definição do namespace:** o `dcc_tools` não infere nem adiciona definições de refType.
> Se o payload usar um `refType` do namespace `electromagnetic`, o cliente deve enviar também
> a entrada correspondente em `refTypeDefinitions` (por exemplo, `namespace: "electromagnetic"` e
> o link do vocabulário). Se o cliente não enviar a definição, ela não é usada.

### 2.4 `cliente` (obrigatório)

```json
"cliente": {
  "nome": "Inmetro/Dimci/Diele/Lacel",
  "email": "test@example.com",
  "cidade": "Duque de Caxias",
  "pais": "BR",
  "cep": "25250-020",
  "uf": "RJ",
  "endereco": "Av. Nossa Senhora das Graças",
  "numero": "50"
}
```

| Chave | Tipo | Descrição |
| --- | --- | --- |
| `nome` | string | Nome do cliente. |
| `email` | string | E-mail. |
| `cidade` | string | Cidade. |
| `pais` | string | Código do país ISO 3166-1 (2 letras). |
| `cep` | string | CEP. |
| `uf` | string | UF/estado. |
| `endereco` | string | Logradouro. |
| `numero` | string | Número do endereço. |

### 2.5 `informacoes_pertinentes` (obrigatório; conteúdo opcional)

Array com condições/informações pertinentes (ex.: temperatura, umidade). Cada item usa **um** dos três
formatos: valor único, intervalo ou texto.

```json
"informacoes_pertinentes": [
  { "name": "Temperatura", "value": "23.2", "unc": "1.0", "k": "2", "unit": "\\degreecelsius", "refType": "basic_temperature" },
  { "name": "Umidade relativa", "value": "49", "unc": "10", "unit": "\\percent" },
  { "name": "Temperatura (intervalo)", "value_min": "20", "value_max": "25", "unc": "1.0", "unit": "\\degreecelsius" },
  { "name": "Exemplo textual", "text": "Texto descritivo." }
]
```

| Chave | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `name` | string | sim | Nome da informação. |
| `value` | string | sim (formato único) | Valor numérico único. |
| `value_min` | string | sim (formato intervalo) | Limite inferior. |
| `value_max` | string | sim (formato intervalo) | Limite superior. |
| `unc` | string | não | Incerteza expandida. |
| `k` | string | não | Fator de abrangência (padrão `2`). |
| `unit` | string | sim (formatos numéricos) | Unidade no formato D-SI (ver §5). |
| `text` | string | sim (formato texto) | Texto livre. |
| `refType` | string | não | RefType da informação. |
| `refType_min` | string | não | RefType do limite inferior (intervalo). |
| `refType_max` | string | não | RefType do limite superior (intervalo). |

### 2.6 `declaracao_rastreabilidade` e `tabela_rastreabilidade`

- `declaracao_rastreabilidade` (string, **obrigatória**): texto da declaração de rastreabilidade metrológica.
- `tabela_rastreabilidade` (array, **opcional**): padrões utilizados.

```json
"tabela_rastreabilidade": [
  {
    "name": "Conversor Térmico PMJTC",
    "origem": "PTB",
    "certificado": "PTB 27812/2020",
    "cod_id": "PR 394",
    "hash_sha256": "e14f080fcc4a8b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef012345"
  }
]
```

| Chave | Tipo | Descrição |
| --- | --- | --- |
| `name` | string | Nome do padrão. |
| `origem` | string | Origem do padrão. |
| `certificado` | string | Número do certificado do padrão (para DCC, o `uniqueIdentifier`). |
| `cod_id` | string | Código de identificação do padrão. |
| `hash_sha256` | string | Opcional. Hash SHA-256 do arquivo XML do DCC do padrão, com 64 caracteres hexadecimais. Quando informado, o gerador preenche `dcc:value` com o hash e `dcc:procedure` com `sha256` (ou com `hash_procedure`). Quando omitido ou vazio, usa `analogue` em ambos. |
| `hash_procedure` | string | Opcional. Procedimento gravado em `dcc:procedure`. Padrão `sha256`. Para digest proveniente de assinatura XML, use `c14n-sha256` ou `enveloped-c14n-sha256`. Só tem efeito quando `hash_sha256` é informado. |

**Certificado do padrão que também é DCC**

O elemento `dcc:certificate` (tipo `dcc:hashType`) identifica o certificado do padrão. O PTB
recomenda que `dcc:procedure` informe o método de transformação e o algoritmo de hash, separados
por hífen, e que `dcc:value` contenha o digest. Para o hash do arquivo XML inteiro, use `sha256`;
para digest extraído de assinatura XML, inclua a canonicalização/transformação, por exemplo
`c14n-sha256` ou `enveloped-c14n-sha256`. Para certificados analógicos, use `analogue` nos dois
campos.

O cliente deve calcular o SHA-256 sobre os bytes do arquivo XML do DCC referenciado e enviar o
digest hexadecimal em `hash_sha256`. O gerador normaliza o valor para minúsculas e emite:

```xml
<dcc:certificate>
  <dcc:referral>
    <dcc:content lang="pt">PTB</dcc:content>
  </dcc:referral>
  <dcc:referralID>PTB 27812/2020</dcc:referralID>
  <dcc:procedure>sha256</dcc:procedure>
  <dcc:value>e14f080fcc4a8b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef012345</dcc:value>
</dcc:certificate>
```

Referências: DCC 3.3.0, `dcc:hashType`; DCC Wiki — <https://wiki.dcc.ptb.de/en/dcchashType>.

### 2.7 `declaracao_incerteza` (obrigatória)

String com a declaração textual da incerteza de medição.

### 2.8 `metodo_medicao` (obrigatório) e `metodo_medicao_equation` (opcional)

- `metodo_medicao`: array de strings (uma ou mais descrições do método).
- `metodo_medicao_equation`: array de strings com equações em **LaTeX**, alinhado por índice ao array
  `metodo_medicao` (opcional).

```json
"metodo_medicao": ["Descrição do método..."],
"metodo_medicao_equation": ["\\delta_u = \\dfrac{U_{ac} - U_{dc}}{U_{dc}}"]
```

### 2.9 `mensurando` (obrigatório, pelo menos um)

Array que define os mensurandos (as tabelas de resultados).

```json
"mensurando": [
  {
    "label": "acdc",
    "name": "Diferença AC-DC em tensão",
    "col_name": "\\delta_u",
    "unit": "\\micro\\volt\\volt\\tothe{-1}",
    "unc_relativa": false
  }
]
```

| Chave | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `label` | string | sim | Identificador único do mensurando (referenciado em `indices` e `resultados`). |
| `name` | string | sim | Título da tabela de resultados. |
| `col_name` | string | sim | Nome da coluna de resultados. |
| `unit` | string | sim | Unidade do resultado (D-SI). |
| `unc_relativa` | boolean | sim | `true` se a incerteza de entrada é relativa (ppm); `false` se absoluta. |
| `refType` | string | não | RefType do resultado. |
| `relative_uncertainty_in_dcc` | boolean | não | Se `true`, adiciona também o bloco `dcc:relativeUncertainty`. **Exige `unc_relativa=true`**; caso contrário, a API retorna **400**. |
| `relative_unc_unit` | string | não | Unidade da incerteza relativa no bloco `dcc:relativeUncertainty`. Padrão: `\\micro\\one`. |

> Comportamento da incerteza relativa: quando `unc_relativa` é `true`, cada `unc` de entrada (em ppm) é
> convertida para valor absoluto com **dois algarismos significativos**
> (`unc_abs = unc * 1e-6 * value`). O resultado absoluto é sempre incluído em
> `si:measurementUncertaintyUnivariateXMLList/si:expandedMUXMLList`; o valor relativo original é
> preservado opcionalmente em `dcc:relativeUncertainty`.
>
> O bloco relativo só pode ser emitido quando a incerteza de entrada também é relativa. A combinação
> `unc_relativa=false` com `relative_uncertainty_in_dcc=true` é inconsistente e retorna **400**.
> Referência: <https://wiki.dcc.ptb.de/dccrelativeUncertainty>.

### 2.10 `indices` (opcional)

Array com os parâmetros adicionais (colunas de índice) que categorizam os resultados.

```json
"indices": [
  { "mensurando": "acdc", "label": "faixa", "name": "Faixa", "unit": "\\volt" },
  { "mensurando": "acdc", "label": "frequency", "name": "Frequência", "unit": "\\kilo\\hertz" },
  { "mensurando": "rstdc", "label": "current", "name": "Corrente", "unit": "\\ampere", "refType": "electromagnetic_measuringCurrent" }
]
```

| Chave | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `mensurando` | string | sim | `label` do mensurando ao qual o índice pertence. |
| `label` | string | sim | Identificador único do índice. |
| `name` | string | sim | Nome legível do índice. |
| `unit` | string | não | Unidade do índice (D-SI). Sem `unit`, o índice é tratado como rótulo (label). |
| `refType` | string | não | RefType do índice. |

> **Corrente de medição:** o gerador não aplica `refType` automaticamente ao índice `current`.
> Se o cliente quiser identificar a corrente de medição, deve enviar
> `refType: "electromagnetic_measuringCurrent"` no índice e a definição do namespace
> `electromagnetic` em `refTypeDefinitions`.

### 2.11 `resultados` (obrigatório)

Array de medições. Cada item referencia um `mensurando`, possui `value`/`unc`/`k` e uma chave para cada
índice do mensurando, além do campo opcional `nueff`.

```json
"resultados": [
  {
    "mensurando": "acdc",
    "faixa": "0.022",
    "voltage": "0.002",
    "frequency": "0.01",
    "value": "-280",
    "unc": "44",
    "k": "2.13",
    "nueff": "58.4"
  }
]
```

| Chave | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `mensurando` | string | sim | `label` do mensurando. |
| `value` | string/number | sim | Valor do resultado. |
| `unc` | string/number | sim | Incerteza expandida. |
| `k` | string/number | sim | Fator de abrangência. |
| `<índice>` | string/number | depende | Uma chave para cada índice definido do mensurando (ex.: `faixa`, `voltage`, `frequency`). |
| `nueff` | string/number | não | Graus de liberdade efetivos (νeff). Ver §6. |
| `in_cmc` | boolean | não | `true` se o ponto está coberto pela CMC; `false` se está fora. Se omitido, usa `cmc_padrao` (padrão `false`). Ver §2.13. |

> Os valores são convertidos internamente para string na saída XML. Recomenda-se enviar como string para
> preservar a representação exata (ex.: `"2.13"`).

### 2.12 `observacoes` (opcional)

Array de strings. Cada item vira um statement "Observação N" no XML.

### 2.13 Marcação de pontos dentro/fora da CMC (`in_cmc`)

O schema DCC 3.3.0 **não possui campo nativo de CMC**. O gerador implementa o mecanismo definido pelo
*Good Practice* DKD‑E 7‑2, §4.5, e pelo vocabulário `basic_isInCMC` do DKD/PTB:

1. adapta o `dcc:statement` de CMC já emitido quando `cmc=true`, dando-lhe `id` estável e
   `refType="basic_isInCMC"` em `administrativeData/statements` — não há um segundo statement;
2. em cada `dcc:quantity` de resultado, adiciona
   `dcc:measurementMetaData/dcc:metaData[@refId="<id>"]`;
3. usa `dcc:valid` para um ponto único ou `dcc:validXMLList` para vários pontos, com um booleano por
   valor, na mesma ordem de `si:valueXMLList`.

**Campos de entrada**

| Chave | Onde | Tipo | Descrição |
| --- | --- | --- | --- |
| `in_cmc` | cada item de `resultados` | boolean | Cobertura de CMC daquele ponto. Aceita `true`/`false`, `1`/`0`, `yes`/`no` ou `Sim`/`Não`. |
| `cmc_padrao` | raiz | boolean | Valor aplicado aos resultados sem `in_cmc`. Ausente = `false`. |
| `cmc_declaracao` | raiz | objeto | Personaliza `id`, `nome`, `referencia`, `link`, `descricao`, `autoridade` (`nome`, `cidade`, `pais`) e, opcionalmente, `cmc_id` (texto ou lista) para referenciar a CMC no KCDB. Ver §2.13.1. |

**Ativação e valor padrão**

- O `dcc:statement` de CMC é emitido quando `cmc=true` **ou** quando ao menos um resultado informa
  `in_cmc` **ou** quando `cmc_padrao` é informado. Em todos os casos há um único statement de CMC.
- Os vínculos por ponto (`dcc:measurementMetaData`) só são gerados quando há `in_cmc` ou
  `cmc_padrao`. Com `cmc=true` e sem marcação, o statement fica apenas declarativo.
- A ausência de marcação em um ponto vinculado significa `false`, conforme o vocabulário. Por isso,
  para indicar **apenas as exceções**, use `cmc_padrao: true` e marque com `in_cmc: false` os pontos
  fora da CMC.
- `in_cmc` ausente com `cmc_padrao` ausente resulta em `false`.
- `cmc` controla a emissão do statement de CMC; `in_cmc` controla a cobertura ponto a ponto. Quando
  `cmc=true`, a declaração textual do MRA/CIPM é preservada dentro de `dcc:declaration` no mesmo
  statement.

**Exemplo — todos cobertos, exceto dois pontos**

```json
{
  "cmc": true,
  "cmc_padrao": true,
  "resultados": [
    { "mensurando": "acdc", "frequency": "0.01", "value": "-280", "unc": "44", "k": "2.13", "in_cmc": true },
    { "mensurando": "acdc", "frequency": "0.02", "value": "3", "unc": "37", "k": "2.28", "in_cmc": false },
    { "mensurando": "acdc", "frequency": "0.03", "value": "12", "unc": "40", "k": "2.10", "in_cmc": false }
  ]
}
```

**Exemplo — personalização da declaração (laboratório acreditado)**

```json
{
  "cmc_padrao": false,
  "cmc_declaracao": {
    "id": "escopoRBC",
    "nome": "Cgcre/RBC",
    "referencia": "Escopo de acreditação RBC 1234",
    "link": "https://www.gov.br/inmetro/pt-br/acesso-a-informacao/acreditacao",
    "descricao": "Cobertura conforme o escopo acreditado.",
    "autoridade": { "nome": "Cgcre/Inmetro", "cidade": "Duque de Caxias", "pais": "BR" }
  },
  "resultados": [
    { "mensurando": "acdc", "value": "10", "unc": "1", "k": "2", "in_cmc": true }
  ]
}
```

**Referência à CMC no KCDB (`cmc_id`)**

O statement pode referenciar uma ou mais entradas do KCDB. Informe apenas o(s) identificador(es)
em `cmc_declaracao.cmc_id` — um texto ou uma lista de textos:

```json
{
  "cmc": true,
  "cmc_padrao": true,
  "cmc_declaracao": {
    "cmc_id": ["SIM-EM-BR-000008UK-2", "EURAMET-EM-CH-00000GFB-7"]
  },
  "resultados": [
    { "mensurando": "acdc", "value": "10", "unc": "1", "k": "2", "in_cmc": true }
  ]
}
```

Regras:

- O sufixo `-X` (dígito) indica a **versão** da CMC e é removido: `SIM-EM-BR-000008UK-2` →
  `SIM-EM-BR-000008UK` no XML e no link.
- O identificador é normalizado para maiúsculas e validado no formato `RMO-Área-País-ID`.
- O link permanente é sempre derivado do ID (não há campo para enviar links):
  `https://si-digital-framework.org/kcdb-cmc/<ID>`.
- Um `dcc:reference` e um `dcc:link` são emitidos por ID, na ordem informada.
- Os IDs exigem `cmc=true`, `in_cmc` ou `cmc_padrao`; caso contrário a geração retorna `400`.
- Sem `cmc_id`, o comportamento anterior é mantido (referência e link genéricos).

XML gerado (trecho) com um CMC ID:

```xml
<dcc:statement id="inCMC" refType="basic_isInCMC">
  <dcc:name><dcc:content lang="pt">CIPM-MRA</dcc:content></dcc:name>
  <dcc:description><dcc:content lang="pt">...</dcc:content></dcc:description>
  <dcc:reference>CIPM-MRA — Apêndice C / KCDB</dcc:reference>
  <dcc:reference>SIM-EM-BR-000008UK</dcc:reference>
  <dcc:link>https://si-digital-framework.org/kcdb-cmc/SIM-EM-BR-000008UK</dcc:link>
  <dcc:declaration><dcc:content lang="pt">...</dcc:content></dcc:declaration>
  <dcc:respAuthority>...</dcc:respAuthority>
</dcc:statement>
```

**XML gerado (trecho)**

```xml
<dcc:statement id="inCMC" refType="basic_isInCMC">
  <dcc:name>
    <dcc:content lang="pt">CIPM-MRA</dcc:content>
  </dcc:name>
  <dcc:description>
    <dcc:content lang="pt">Todos os resultados são acompanhados por um elemento dcc:valid ...</dcc:content>
  </dcc:description>
  <dcc:reference>CIPM-MRA — Apêndice C / KCDB</dcc:reference>
  <dcc:link>https://www.bipm.org/kcdb/</dcc:link>
  <dcc:declaration>
    <dcc:content lang="pt">Este certificado é consistente com as Capacidades de Medição e Calibração (CMCs)...</dcc:content>
  </dcc:declaration>
  <dcc:respAuthority>
    <dcc:name><dcc:content lang="pt">BIPM</dcc:content></dcc:name>
    <dcc:location>
      <dcc:city>Paris</dcc:city>
      <dcc:countryCode>FR</dcc:countryCode>
    </dcc:location>
  </dcc:respAuthority>
</dcc:statement>
```

```xml
<dcc:quantity refType="basic_measuredValue">
  <dcc:name><dcc:content lang="pt">\delta_u</dcc:content></dcc:name>
  <si:realListXMLList>...</si:realListXMLList>
  <dcc:measurementMetaData>
    <dcc:metaData refId="inCMC">
      <dcc:validXMLList>true false false</dcc:validXMLList>
    </dcc:metaData>
  </dcc:measurementMetaData>
</dcc:quantity>
```

Quando o mensurando tem um único ponto, o gerador usa `<dcc:valid>true</dcc:valid>` (ou `false`) em
vez de `validXMLList`.

O namespace `basic` é declarado automaticamente em `administrativeData/refTypeDefinitions` quando o
statement de CMC é emitido e o usuário não o declarou em `refTypeDefinitions`.

**Critério metrológico:** um ponto só deve receber `true` quando (a) o valor está dentro da faixa
coberta pela CMC aplicável e (b) a incerteza declarada é maior ou igual à incerteza da CMC,
comparadas na mesma base estatística (mesmo `k` ou ambas convertidas para incerteza padrão). A
marcação é uma afirmação sobre o resultado declarado, não sobre a adequação do instrumento ao uso.
Referência: DKD‑E 7‑2, §4.5, e vocabulário de `refType` do DKD/PTB.

> Não use `dcc:conformity` para indicar CMC: ele declara conformidade com requisito, não cobertura de
> CMC. Também não coloque `dcc:valid` dentro do `dcc:statement`; o `valid` pertence aos vínculos
> (`metaData`).

**Visualização human-readable.** Em `POST /dcc/visualizar_dcc`, as tabelas de resultados com
`measurementMetaData` recebem a coluna **CMC** (`Sim`/`Não`) alinhada a cada ponto. Quando há pontos
`false`, a última seção (**Observações**) recebe uma observação numerada, após as observações do
certificado, informando que esses pontos não estão cobertos pela CMC do laboratório no âmbito do
CIPM MRA, embora a rastreabilidade esteja garantida da mesma forma que sustenta a dos demais pontos.
Certificados sem marcação não mostram a coluna nem a observação. Valores `inf` (por exemplo, em
`nueff`) são exibidos como `∞`.

### 2.14 Valor nominal estruturado do item (`valor_nominal`)

O DCC 3.3.0 permite registrar quantidades do item em
`administrativeData/items/item/itemQuantities/itemQuantity`. Seguindo o DKD-E 1-1, o valor nominal
(valor de placa/impresso) é declarado com `refType="basic_nominalValue"`.

**Formato recomendado**

```json
"valor_nominal": {
  "valor": "100",
  "unidade": "\\kilo\\ohm",
  "nome": "Valor nominal",
  "descricao": "Valor impresso no item"
}
```

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `valor` | string/número | sim | Valor nominal. |
| `unidade` | string | sim | Unidade D-SI (ex.: `\\ohm`). |
| `nome` | string | não | Rótulo do itemQuantity; padrão `Valor nominal`. |
| `descricao` | string | não | Descrição adicional. |

**Formato legado (compatibilidade)**

```json
"valor_nominal": "100",
"valnom_unit": "\\kilo\\ohm"
```

**XML gerado**

```xml
<dcc:item>
  <!-- ... -->
  <dcc:identifications>...</dcc:identifications>
  <dcc:itemQuantities>
    <dcc:itemQuantity refType="basic_nominalValue">
      <dcc:name>
        <dcc:content lang="pt">Valor nominal</dcc:content>
      </dcc:name>
      <dcc:description>
        <dcc:content lang="pt">Valor impresso no item</dcc:content>
      </dcc:description>
      <si:real>
        <si:value>100</si:value>
        <si:unit>\kilo\ohm</si:unit>
      </si:real>
    </dcc:itemQuantity>
  </dcc:itemQuantities>
</dcc:item>
```

- O campo é opcional; sem ele, nenhum `dcc:itemQuantities` é gerado.
- `caracteristicas_item` também é opcional: se omitido/vazio, o statement "Características do Item"
  não é emitido; a visualização ainda exibe o valor nominal em uma seção própria.
- O namespace `basic` é declarado automaticamente em `refTypeDefinitions` quando o valor nominal
  (ou a marcação CMC) é emitido e o usuário não o declarou.
- A visualização human-readable exibe o valor em **Características do Item** como
  `Valor nominal: 100 kΩ`.
- O valor nominal não recebe incerteza de medição; ele documenta o valor de placa/impresso.
- Referência: DKD-E 1-1 (Normalwiderstände), seção 3.4.

---

## 3. Exemplo mínimo completo

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
  "valor_nominal": {
    "valor": "100",
    "unidade": "\\kilo\\ohm"
  },
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

---

## 4. Resposta (XML DCC)

A resposta é um XML válido contra `https://www.ptb.de/dcc/v3.3.0/dcc.xsd`. Elementos principais:

- `dcc:digitalCalibrationCertificate` (raiz, com `schemaVersion`).
- `dcc:administrativeData` (software, coreData, items, calibrationLaboratory, respPersons, customer, statements).
- `dcc:measurementResults` → `dcc:measurementResult` → `dcc:results` → `dcc:result` → `dcc:data` → `dcc:list`.

Na tabela de resultados (`dcc:list`), cada coluna é uma `dcc:quantity` com `si:realListXMLList`
(`si:valueXMLList` + `si:unitXMLList`), exceto a coluna opcional de `nueff`, que usa `dcc:charsXMLList`
(ver §6). A coluna de resultado inclui também
`si:measurementUncertaintyUnivariateXMLList` → `si:expandedMUXMLList`
(`si:valueExpandedMUXMLList`, `si:coverageFactorXMLList`, `si:coverageProbabilityXMLList`).

- `si:coverageProbabilityXMLList` é fixo em `0.9545`.
- Quando `nueff` está presente, uma `dcc:quantity` adicional é adicionada ao final da mesma `dcc:list`
  (ver §6).
- Quando `in_cmc`/`cmc_padrao` estão presentes, a `dcc:quantity` de resultado recebe
  `dcc:measurementMetaData/dcc:metaData[@refId]` com `dcc:valid` ou `dcc:validXMLList`, e o
  `administrativeData/statements` recebe o `dcc:statement` com `refType="basic_isInCMC"` (ver §2.13).

### Detalhes fixos do certificado

- `countryCodeISO3166_1` = `BR`; `usedLangCodeISO639_1`/`mandatoryLangCodeISO639_1` = `pt`.
- `uniqueIdentifier` = `"DIMCI " + num_certif`.
- Local do laboratório, contatos e declarações fixas do Inmetro/Dimci são embutidos pelo gerador.

---

## 5. Formato de unidades (D-SI)

As unidades seguem o formato D-SI usado pelo schema PTB:

- Prefixo com barra invertida: `\volt`, `\ohm`, `\ampere`, `\hertz`, `\pascal`, `\watt`, `\one`.
- Potências: `\tothe{expoente}` (ex.: `\volt\tothe{-1}`).
- Prefixos SI: `\micro`, `\milli`, `\kilo`, `\nano`, etc.
- Multiplicação por justaposição: `\micro\volt\volt\tothe{-1}`.
- Temperatura: `\degreecelsius`; percentual: `\percent`.
- Adimensional: `\one`.

---

## 6. Graus de liberdade efetivos (`nueff`)

Campo **opcional** por linha de resultado. Representa os graus de liberdade efetivos (νeff) associados à
incerteza do resultado.

**Regras:**

1. **Presença**: se `nueff` estiver presente em um resultado, todos os resultados do mesmo mensurando
   devem informá-lo.
2. **Comprimento**: o número de valores de `nueff` deve ser igual ao número de resultados do mensurando.
3. **Valores**: numéricos e **estritamente positivos** (`> 0`); aceita valores fracionários (ex.: `12.7`).
4. **Infinito**: `νeff = +∞` pode ser representado por `"inf"` (string) ou `Infinity`/`+Infinity`.
   No XML, é serializado como `inf`.
5. **Valores rejeitados** (geram erro `400`): `0`, negativos, `-inf`, `null`, string vazia, `NaN` e
   valores não numéricos.
6. **Ausência**: se `nueff` não for informado, nenhuma quantidade adicional é gerada (comportamento anterior preservado).

**Resultado no XML**: uma `dcc:quantity` adicional na mesma `dcc:list`, com:

```xml
<dcc:quantity>
  <dcc:name>
    <dcc:content lang="pt">Graus de liberdade efetivos</dcc:content>
  </dcc:name>
  <dcc:charsXMLList>58.4 62.1 inf</dcc:charsXMLList>
</dcc:quantity>
```

A nova quantidade usa `dcc:charsXMLList` (representação textual, sem unidade) e **não** inclui
`dcc:description` nem `si:unitXMLList`.

O bloco de incerteza absoluta usa o formato D-SI 2.2.1
(`si:measurementUncertaintyUnivariateXMLList` → `si:expandedMUXMLList`). O bloco opcional de
`nueff` não interfere nessa estrutura.

---

## 7. Erros

A rota `/dcc/generate` retorna:

| Código | Situação | Corpo |
| --- | --- | --- |
| `401` | API-KEY ausente, inválida ou revogada | XML `<autenticacaoNecessaria>` com instruções (ver §1.1); navegadores são redirecionados |
| `400` | JSON ausente ou inválido | `{"error": "No JSON provided"}` / `{"error": "Invalid JSON: ..."}` |
| `400` | Falha de validação (ex.: `nueff` inválido) | `{"error": "<mensagem clara>"}` |
| `400` | Versão de schema não suportada (`3.2.0` ou desconhecida) | `{"error": "O schema DCC 3.2.0 não é mais suportado..."}` |
| `400` | `relative_uncertainty_in_dcc=true` com `unc_relativa=false` | `{"error": "relative_uncertainty_in_dcc=true exige unc_relativa=true..."}` |
| `400` | `in_cmc` ou `cmc_padrao` com valor não booleano | `{"error": "Valor inválido para 'in_cmc': ... Use true/false (ou Sim/Não)."}` |
| `400` | `cmc_declaracao` inválida (tipo, `id` ou `cmc_id`) | `{"error": "O campo 'cmc_declaracao' deve ser um objeto."}` / `{"error": "CMC ID inválido em 'cmc_declaracao': ..."}` / `{"error": "'cmc_declaracao.cmc_id' exige cmc=True, in_cmc ou cmc_padrao."}` |
| `400` | `tabela_rastreabilidade[].hash_sha256` inválido | `{"error": "Valor inválido para 'tabela_rastreabilidade[].hash_sha256': ..."}` |
| `400` | `tabela_rastreabilidade[].hash_procedure` inválido | `{"error": "Valor inválido para 'tabela_rastreabilidade[].hash_procedure': ..."}` |
| `500` | Erro inesperado na geração | `{"error": "Erro ao gerar o DCC: ..."}` |

Mensagens de erro de `nueff` (exemplos):

- `O número de valores de 'nueff' (N) deve ser igual ao número de resultados associados (M).`
- `Valor inválido para 'nueff': '0'. Os graus de liberdade efetivos devem ser positivos.`
- `Valor inválido para 'nueff': 'nan'. Não são aceitos NaN.`
- `Valor inválido para 'nueff': '-inf'. Não são aceitos -inf.`

---

## 8. Outros endpoints

Além do gerador, a aplicação expõe:

| Endpoint | Método | Autenticação | Descrição |
| --- | --- | --- | --- |
| `/dcc/generate` | POST | API-KEY | JSON → XML DCC (principal). |
| `/dcc/upload_json` | GET/POST | API-KEY ou sessão web | Upload de arquivo JSON; encaminha para `/dcc/generate` e baixa o XML. |
| `/dcc/upload_xls` | GET/POST | API-KEY ou sessão web | Upload de planilha `.xlsx`; converte para JSON e gera o XML. |
| `/dcc/pdf_attach` | POST | API-KEY ou sessão web | Anexa um XML DCC a um PDF (PDF/A-3), recebendo `pdf_file` e `xml_file` (multipart). |
| `/dcc/validate_xml` | GET/POST | aberta | Valida um XML DCC contra o schema informado no próprio XML; o download do schema é restrito a hosts confiáveis (`DCC_ALLOWED_SCHEMA_HOSTS`). |
| `/dcc/visualizar_dcc` | POST | aberta | Converte XML em HTML legível (upload de `xml_file`), com capa no modelo NIE-Dimci-014 e coluna CMC (`Sim`/`Não`) por ponto quando houver marcação `basic_isInCMC`. |
| `/dcc/register` | POST | aberta | Cadastro de usuário (usuário, senha, e-mail `@inmetro.gov.br`); devolve a API-KEY. |
| `/dcc/login` | GET/POST | aberta | Login na interface web com usuário e senha. |
| `/dcc/logout` | GET | — | Encerra a sessão da interface web. |
| `/dcc/perfil` | GET | sessão web | Área de perfil: exibe a API-KEY do usuário. |
| `/dcc/perfil/senha` | GET/POST | sessão web | Troca de senha (exige a senha atual). |
| `/dcc/perfil/regenerar` | POST | sessão web | Gera uma nova API-KEY (a anterior deixa de funcionar). |
| `/dcc/esqueci-senha` | GET/POST | aberta | Solicita recuperação de senha por e-mail (resposta genérica). |
| `/dcc/redefinir-senha` | GET/POST | aberta | Define nova senha com o token enviado por e-mail. |

Rotas de interface web informativas (abertas): `/dcc/`, `/dcc/api_doc`, `/dcc/excel_guide`,
`/dcc/exemplos`, `/dcc/faq`, `/dcc/publications`, `/dcc/introducao`.

Rotas de interface web funcionais (exigem sessão): `/dcc/form_dcc`, `/dcc/upload_json`,
`/dcc/upload_xls`, `/dcc/upload_xml`.

Rotas de ferramentas abertas: `/dcc/upload_xml_hr` (visualizar DCC) e `/dcc/validate_xml` (validar XML).

---

## 9. Notas de implementação para um cliente

- Cadastre-se em `POST /dcc/register` e envie a API-KEY recebida no cabeçalho `X-API-Key` em todas as
  chamadas aos endpoints de geração/upload.
- Envie todos os campos de metadados como **string**, exceto `cmc`, `cmc_padrao`, `in_cmc` e
  `unc_relativa` (booleanos).
- `resultados[].value`, `unc`, `k` e `nueff` podem ser string ou número; use string para preservar o valor exato.
- Para marcar apenas os pontos fora da CMC, use `cmc_padrao: true` e `in_cmc: false` nos pontos
  correspondentes; a ausência de `in_cmc` sem `cmc_padrao` significa `false`.
- A ordem das chaves no JSON é irrelevante.
- Para múltiplos mensurandos, repita o bloco em `mensurando`, referencie os índices em `indices` e
  agrupe os resultados por `mensurando` em `resultados`.
- A conversão da incerteza relativa para absoluta (ppm → absoluta) ocorre apenas quando
  `mensurando[].unc_relativa` é `true`.
- `tabela_rastreabilidade[].hash_sha256` identifica certificados de padrão que também são DCC:
  informe o SHA-256 do arquivo XML (64 hexadecimais); o gerador escreve `sha256` (ou `hash_procedure`) em
  `dcc:procedure` e o digest em `dcc:value`. Sem o campo, usa `analogue`/`analogue`.
- `relative_uncertainty_in_dcc=true` só é aceito com `unc_relativa=true`; a combinação contrária
  retorna `400`.

---

## 10. Referências oficiais

- `dcc:relativeUncertainty` (PTB DCC Wiki):
  <https://wiki.dcc.ptb.de/dccrelativeUncertainty>
- `dcc:quantityType` (PTB DCC Wiki):
  <https://wiki.dcc.ptb.de/en/dccquantityType>
- `dcc:hashType` / `dcc:certificate` / `dcc:previousReport` (PTB DCC Wiki):
  <https://wiki.dcc.ptb.de/en/dcchashType>
- D-SI 2.2.1 (schema usado pelo DCC 3.3.0):
  <https://ptb.de/si/v2.2.1/SI_Format.xsd>
- DCC 3.3.0:
  <https://www.ptb.de/dcc/v3.3.0/dcc.xsd>
- Modelo DCC do PTB:
  <https://www.ptb.de/dcc>
- `basic_isInCMC` — DKD-E 7-2, §4.5:
  <https://doi.org/10.7795/550.20240119B>
- Vocabulário de `refType` do DKD/PTB (`isInCMC`):
  <https://digilab.ptb.de/dkd/refType/vocab/index.php?tema=250>
- `dcc:validXMLList` (PTB DCC Wiki):
  <https://wiki.dcc.ptb.de/en/dccvalidXMLList>
