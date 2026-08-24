# API DCC Generator — Referência para LLMs

Este documento descreve a API HTTP de geração de **Certificados de Calibração Digital (DCC)** do projeto
**DCC Tools** (Inmetro/Dimci/Diele/Lampe), com foco em permitir que um LLM (ou um agente de código)
implemente um cliente que consuma a API corretamente.

O gerador recebe um **JSON** e devolve um **XML DCC** compatível com o modelo do PTB
([Digital Calibration Certificate](https://www.ptb.de/dcc)).

---

## 1. Visão geral

- **Protocolo**: HTTP/1.1, JSON no corpo da requisição, XML na resposta.
- **Autenticação**: nenhuma (endpoints abertos na implementação atual).
- **Codificação**: UTF-8.
- **Schema DCC suportado**: `3.3.0` (padrão) e `3.2.0`.

### Endpoint principal

```
POST /dcc/generate
```

| Item | Valor |
| --- | --- |
| `Content-Type` da requisição | `application/json` |
| `Content-Type` da resposta | `text/xml` |
| `Content-Disposition` da resposta | `attachment; filename="CC_DIMCI_<num_certif>.xml"` |
| Sucesso | `200` com o XML DCC no corpo |
| Erro de validação | `400` com JSON `{"error": "<mensagem>"}` |
| Erro interno | `500` com JSON `{"error": "<mensagem>"}` |

**Base URL de produção** (exemplo): `https://sig-dimci.inmetro.gov.br/dcc/generate`.
O caminho da rota é sempre `/dcc/generate`; o host pode variar conforme o ambiente.

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
| `caracteristicas_item` | string | sim | Características adicionais do item. |
| `data_calibracao` | string | sim | Data da calibração, ISO 8601 (`YYYY-MM-DD`). |
| `data_emissao` | string | não | Data de emissão (`YYYY-MM-DD`). Se omitida, o XML inclui a declaração "Ver data da assinatura eletrônica presente no certificado". |
| `cmc` | boolean | sim | Indica se o certificado possui CMC. |
| `chefe_div` | string | sim | Nome do chefe da divisão. |
| `desc_chefe_div` | string | não | Cargo do chefe da divisão. Se fornecido, é sufixado com `" da " + nome_div`; senão usa `"Chefe da " + nome_div`. |
| `chefe_lab` | string | sim | Nome do chefe do laboratório. |
| `desc_chefe_lab` | string | não | Cargo do chefe do laboratório. Se fornecido, é sufixado com `" do " + nome_lab`; senão usa `"Chefe do " + nome_lab`. |
| `tecnico_executor` | string | sim | Nome do técnico executor. |
| `desc_tecnico_executor` | string | sim | Cargo/descrição do técnico executor. |
| `dcc_version` | string | não | Versão do schema (`3.3.0` ou `3.2.0`). Padrão: `3.3.0`. |
| `schema_version` | string | não | Alias alternativo para `dcc_version`. |

> A versão de schema é resolvida na ordem: `dcc_version` → `schema_version` → `3.3.0`.
> Valores não reconhecidos caem no padrão `3.3.0`.

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
  }
]
```

| Chave | Tipo | Descrição |
| --- | --- | --- |
| `name` | string | Nome do namespace. |
| `description` | string | Descrição do namespace. |
| `namespace` | string | Identificador do namespace. |
| `link` | string | URL da definição do namespace. |

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
  { "name": "Conversor Térmico PMJTC", "origem": "PTB", "certificado": "PTB 27812/2020", "cod_id": "PR 394" }
]
```

| Chave | Tipo | Descrição |
| --- | --- | --- |
| `name` | string | Nome do padrão. |
| `origem` | string | Origem do padrão. |
| `certificado` | string | Número do certificado do padrão. |
| `cod_id` | string | Código de identificação do padrão. |

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
| `relative_uncertainty_in_dcc` | boolean | não | Se `true`, adiciona também o bloco `dcc:relativeUncertainty` (schema 3.3.0). |
| `relative_unc_unit` | string | não | Unidade da incerteza relativa no bloco `dcc:relativeUncertainty`. Padrão: `\\micro\\one`. |

> Comportamento da incerteza relativa: quando `unc_relativa` é `true`, cada `unc` de entrada (em ppm) é
> convertida para valor absoluto com **dois algarismos significativos**
> (`unc_abs = unc * 1e-6 * value`). O resultado absoluto é sempre incluído em `si:expandedUncXMLList`;
> o valor relativo original é preservado opcionalmente em `dcc:relativeUncertainty`.

### 2.10 `indices` (opcional)

Array com os parâmetros adicionais (colunas de índice) que categorizam os resultados.

```json
"indices": [
  { "mensurando": "acdc", "label": "faixa", "name": "Faixa", "unit": "\\volt" },
  { "mensurando": "acdc", "label": "frequency", "name": "Frequência", "unit": "\\kilo\\hertz" }
]
```

| Chave | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `mensurando` | string | sim | `label` do mensurando ao qual o índice pertence. |
| `label` | string | sim | Identificador único do índice. |
| `name` | string | sim | Nome legível do índice. |
| `unit` | string | não | Unidade do índice (D-SI). Sem `unit`, o índice é tratado como rótulo (label). |
| `refType` | string | não | RefType do índice. |

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

> Os valores são convertidos internamente para string na saída XML. Recomenda-se enviar como string para
> preservar a representação exata (ex.: `"2.13"`).

### 2.12 `observacoes` (opcional)

Array de strings. Cada item vira um statement "Observação N" no XML.

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

A resposta é um XML válido contra `https://www.ptb.de/dcc/v3.3.0/dcc.xsd` (ou `3.2.0`). Elementos principais:

- `dcc:digitalCalibrationCertificate` (raiz, com `schemaVersion`).
- `dcc:administrativeData` (software, coreData, items, calibrationLaboratory, respPersons, customer, statements).
- `dcc:measurementResults` → `dcc:measurementResult` → `dcc:results` → `dcc:result` → `dcc:data` → `dcc:list`.

Na tabela de resultados (`dcc:list`), cada coluna é uma `dcc:quantity` com `si:realListXMLList`
(`si:valueXMLList` + `si:unitXMLList`). A coluna de resultado inclui também
`si:expandedUncXMLList` (`si:uncertaintyXMLList`, `si:coverageFactorXMLList`,
`si:coverageProbabilityXMLList`).

- `si:coverageProbabilityXMLList` é fixo em `0.9545`.
- Quando `nueff` está presente, uma `dcc:quantity` adicional é adicionada ao final da mesma `dcc:list`
  (ver §6).

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
- Adimensional: `\one` (usado para `nueff`).

---

## 6. Graus de liberdade efetivos (`nueff`)

Campo **opcional** por linha de resultado. Representa os graus de liberdade efetivos (νeff) associados à
incerteza do resultado.

**Regras:**

1. **Presença**: se `nueff` estiver presente em um resultado, todos os resultados do mesmo mensurando
   devem informá-lo.
2. **Comprimento**: o número de valores de `nueff` deve ser igual ao número de resultados do mensurando.
3. **Valores**: numéricos e **estritamente positivos** (`> 0`); aceita valores fracionários (ex.: `12.7`).
4. **Valores rejeitados** (geram erro `400`): `0`, negativos, `null`, string vazia, `NaN`, infinito,
   valores não numéricos.
5. **Ausência**: se `nueff` não for informado, nenhuma quantidade adicional é gerada (comportamento anterior preservado).

**Resultado no XML**: uma `dcc:quantity` adicional na mesma `dcc:list`, com:

```xml
<dcc:quantity>
  <dcc:name>
    <dcc:content lang="pt">Graus de liberdade efetivos</dcc:content>
    <dcc:content lang="en">Effective degrees of freedom</dcc:content>
  </dcc:name>
  <dcc:description>
    <dcc:content lang="pt">Graus de liberdade efetivos da incerteza padrão combinada, νeff, utilizados na determinação do fator de abrangência.</dcc:content>
    <dcc:content lang="en">Effective degrees of freedom of the combined standard uncertainty, νeff, used in the determination of the coverage factor.</dcc:content>
  </dcc:description>
  <si:realListXMLList>
    <si:valueXMLList>58.4 62.1</si:valueXMLList>
    <si:unitXMLList>\one</si:unitXMLList>
  </si:realListXMLList>
</dcc:quantity>
```

A estrutura `si:expandedUncXMLList` existente **não é alterada**.

---

## 7. Erros

A rota `/dcc/generate` retorna:

| Código | Situação | Corpo |
| --- | --- | --- |
| `400` | JSON ausente ou inválido | `{"error": "No JSON provided"}` / `{"error": "Invalid JSON: ..."}` |
| `400` | Falha de validação (ex.: `nueff` inválido) | `{"error": "<mensagem clara>"}` |
| `500` | Erro inesperado na geração | `{"error": "Erro ao gerar o DCC: ..."}` |

Mensagens de erro de `nueff` (exemplos):

- `O número de valores de 'nueff' (N) deve ser igual ao número de resultados associados (M).`
- `Valor inválido para 'nueff': '0'. Os graus de liberdade efetivos devem ser positivos.`
- `Valor inválido para 'nueff': 'nan'. Não são aceitos NaN ou infinito.`

---

## 8. Outros endpoints

Além do gerador, a aplicação expõe:

| Endpoint | Método | Descrição |
| --- | --- | --- |
| `/dcc/generate` | POST | JSON → XML DCC (principal). |
| `/dcc/upload_json` | GET/POST | Upload de arquivo JSON; encaminha para `/dcc/generate` e baixa o XML. |
| `/dcc/upload_xls` | GET/POST | Upload de planilha `.xlsx`; converte para JSON e gera o XML. |
| `/dcc/pdf_attach` | POST | Anexa um XML DCC a um PDF (PDF/A-3), recebendo `pdf_file` e `xml_file` (multipart). |
| `/dcc/validate_xml` | GET/POST | Valida um XML DCC contra o schema (upload de `xml_file`). |
| `/dcc/visualizar_dcc` | POST | Converte XML em HTML legível (upload de `xml_file`). |

Rotas de interface web (HTML): `/dcc/`, `/dcc/api_doc`, `/dcc/excel_guide`, `/dcc/exemplos`, `/dcc/faq`,
`/dcc/form_dcc`, `/dcc/publications`, `/dcc/introducao`.

---

## 9. Notas de implementação para um cliente

- Envie todos os campos de metadados como **string**, exceto `cmc` (boolean) e `unc_relativa` (boolean).
- `resultados[].value`, `unc`, `k` e `nueff` podem ser string ou número; use string para preservar o valor exato.
- A ordem das chaves no JSON é irrelevante.
- Para múltiplos mensurandos, repita o bloco em `mensurando`, referencie os índices em `indices` e
  agrupe os resultados por `mensurando` em `resultados`.
- A conversão da incerteza relativa para absoluta (ppm → absoluta) ocorre apenas quando
  `mensurando[].unc_relativa` é `true`.
