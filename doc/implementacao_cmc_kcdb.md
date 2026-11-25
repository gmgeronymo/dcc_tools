# Análise e proposta de implementação — CMC/KCDB no dccGenerator

**Status:** implementado em 13/11/2026 e padronizado em `dcc:validXMLList` em 25/11/2026 (`flask/app/main.py`, `flask/app/test_cmc.py`).
**Diferenças em relação à proposta:** a API aceita **um ou mais** CMC IDs no campo `cmc_declaracao.cmc_id` (texto ou lista); os links são **sempre derivados** do ID (não há campo para enviar links) e `norm`/`data_verificacao` **não** são aceitos. O sufixo de versão `-X` (dígito) é removido do identificador usado no XML e no link; o ID é normalizado para maiúsculas.  
**Data:** 13/11/2026  
**Alvo:** `dcc_tools` — `flask/app/main.py`, `flask/app/test_cmc.py`, `certificado_pdf_template.html`  
**Certificado de referência:** `CC_DIMCI_9999_2026.XML` (DIMCI 9999/2026, simulado)  
**Hash SHA-256 do XML de referência:** `aa1b051f3f2afa8efa63a67de4023bb78e610aae9b73ca835c05107c85229e38`  
**Esquema:** DCC 3.3.0 / D-SI 2.2.1

---

## 1. Resumo executivo

O certificado já possui a marcação de CMC no formato recomendado pelo vocabulário DKD/PTB:

```xml
<dcc:statement id="inCMC" refType="basic_isInCMC">
  ...
  <dcc:reference>CIPM-MRA — Apêndice C / KCDB</dcc:reference>
  <dcc:link>https://www.bipm.org/kcdb/</dcc:link>
  ...
  <dcc:respAuthority>BIPM...</dcc:respAuthority>
</dcc:statement>
```

```xml
<dcc:quantity refType="basic_measuredValue">
  ...
  <dcc:measurementMetaData>
    <dcc:metaData refId="inCMC">
      <dcc:validXMLList>true</dcc:validXMLList>
    </dcc:metaData>
  </dcc:measurementMetaData>
</dcc:quantity>
```

A lacuna é que o `dcc:link` aponta para a **página inicial do KCDB**, não para a **entrada CMC específica**. O `dcc:statement` também não contém o **CMC ID** versionado.

**Decisão recomendada:** incluir o **CMC ID** e o **link permanente do BIPM** no `dcc:statement`, mantendo `valid=true` no resultado. **Não copiar a tabela de faixa/incerteza da CMC para o XML.** A CMC é uma capacidade publicada e versionada no KCDB; o XML deve referenciá-la, não duplicá-la.

---

## 2. Contexto e problema

O DCC 3.3.0 não possui campo nativo de CMC. A marcação é feita por:

1. `dcc:statement` com `refType="basic_isInCMC"` e um `id`;
2. `dcc:measurementMetaData/dcc:metaData` com `refId` apontando para esse `id`;
3. `dcc:validXMLList` sempre, inclusive para um ponto único (um booleano por valor).

O vocabulário `basic_isInCMC` define:

- `true`: o resultado está **na faixa coberta pela CMC** e a **incerteza declarada é maior ou igual à incerteza da CMC**;
- `false`: uma das duas condições não é atendida;
- ausência de `valid`: assume-se `false`;
- o `dcc:statement` **não deve conter** `dcc:validXMLList`;
- a autoridade responsável deve ser o BIPM ou o organismo de acreditação.

O problema atual não é a ausência do booleano, mas a **falta de um identificador específico e resolvível da CMC**. Com o link genérico, um consumidor não consegue:

- saber qual entrada do KCDB foi usada;
- verificar faixa, incerteza e versão da CMC;
- auditar a comparação `U_certificado ≥ U_CMC`;
- reproduzir a decisão em outro momento.

---

## 3. Decisão recomendada

### 3.1 Adotar

- `dcc:reference` adicional com o **CMC ID** versionado;
- `dcc:link` para o **link permanente** do BIPM;
- opcionalmente, `dcc:link` com `?type=json` ou `?type=xml`;
- opcionalmente, `dcc:norm` com `CIPM MRA-G-13`;
- opcionalmente, `dcc:date` com a data de verificação da CMC;
- manter `dcc:validXMLList` apenas no resultado;
- registrar no processo a faixa, a U_CMC, a data de consulta e a comparação.

### 3.2 Não adotar

- copiar a tabela completa da CMC para `dcc:data` como se fosse resultado;
- criar `refType` local para “valor da CMC”;
- usar `dcc:conformity` para CMC;
- colocar `dcc:validXMLList` dentro do `dcc:statement`;
- usar o CMC ID como `dcc:statement/@id`;
- usar a página inicial do KCDB como único link.

---

## 4. Justificativa — DKD/PTB e BIPM

### 4.1 DKD-E 7-2 §4.5

O *Good Practice* DKD-E 7-2 recomenda:

- `dcc:statement` com `refType="basic_isInCMC"`;
- `dcc:reference` apontando para o escopo de acreditação ou para a base do BIPM;
- `dcc:validXMLList` no resultado, no nível mais alto aplicável;
- `dcc:measurementMetaData` quando apenas parte dos pontos estiver coberta.

O exemplo para NMI usa apenas:

```xml
<dcc:reference>CIPM-MRA</dcc:reference>
```

O próprio documento antecipa que, no futuro, seria possível um link para uma base de CMC legível por máquina. Esse recurso já existe no BIPM.

> Observação: o exemplo do DKD-E 7-2 é baseado em versão antiga do esquema e coloca um marcador `valid` dentro do `statement`. O vocabulário atual (revisão de 22/04/2026) determina que o `statement` **não** contenha `dcc:validXMLList` e que o vínculo seja feito por `id`/`refId`. O gerador atual segue o formato novo.

### 4.2 Vocabulário `basic_isInCMC`

O vocabulário do DKD/PTB define que `valid=true` já expressa as duas condições metrológicas:

1. o resultado está dentro da faixa coberta pela CMC;
2. a incerteza declarada é maior ou igual à incerteza da CMC.

Portanto, o XML não precisa repetir a faixa e a U_CMC para afirmar a cobertura. Precisa, sim, **identificar a CMC** usada.

### 4.3 CMC IDs do BIPM

O BIPM atribui identificadores permanentes às CMCs, no formato:

```text
RMO-Area-A2-ID-V
```

Exemplo:

```text
SIM-EM-BR-000008UK-2
```

O link permanente é:

```text
https://si-digital-framework.org/kcdb-cmc/<CMC ID>
```

E há versões legíveis por máquina:

```text
https://si-digital-framework.org/kcdb-cmc/<CMC ID>?type=json
https://si-digital-framework.org/kcdb-cmc/<CMC ID>?type=xml
```

O documento *Quick start on CMC identifiers* (BIPM, 2024-02-27) informa que o JCRB recomenda o uso dos CMC IDs em documentação da qualidade e em **certificados de calibração, digitais ou não**.

### 4.4 CIPM MRA-G-13

O CMC ID é gerado e versionado pelo KCDB. O sufixo de versão (`-1`, `-2`, ..., `-Z`) faz parte do identificador. Se a CMC for revisada, o ID muda. O certificado deve preservar a versão usada na emissão.

### 4.5 Por que não copiar a tabela da CMC

- O DCC 3.3.0 não tem `refType` harmonizado para “faixa da CMC” ou “incerteza da CMC”.
- Uma cópia no XML pode ficar desatualizada em relação ao KCDB.
- Consumidores podem confundir a cópia com um resultado metrológico.
- A CMC é uma capacidade publicada, não um resultado da calibração.
- O KCDB já oferece JSON/XML estruturado; o XML do certificado deve referenciá-lo.

---

## 5. O que incluir no XML

### 5.1 Estrutura recomendada

```xml
<dcc:statement id="inCMC" refType="basic_isInCMC">
  <dcc:name>
    <dcc:content lang="pt">CIPM-MRA — CMC aplicável</dcc:content>
  </dcc:name>
  <dcc:description>
    <dcc:content lang="pt">Resultado coberto pela CMC identificada abaixo. Faixa e incerteza da CMC são as publicadas no KCDB; consulte o link permanente.</dcc:content>
  </dcc:description>
  <dcc:norm>CIPM MRA-G-13</dcc:norm> <!-- opcional -->
  <dcc:reference>CIPM-MRA — Apêndice C / KCDB</dcc:reference>
  <dcc:reference>SIM-EM-BR-000008UK-2</dcc:reference>
  <dcc:link>https://si-digital-framework.org/kcdb-cmc/SIM-EM-BR-000008UK-2</dcc:link>
  <dcc:link>https://si-digital-framework.org/kcdb-cmc/SIM-EM-BR-000008UK-2?type=json</dcc:link> <!-- opcional -->
  <dcc:declaration>
    <dcc:content lang="pt">Este certificado é consistente com as CMCs incluídas no Apêndice C do CIPM-MRA.</dcc:content>
  </dcc:declaration>
  <dcc:date>2026-11-13</dcc:date> <!-- opcional; definir como data de verificação -->
  <dcc:respAuthority>
    <dcc:name>
      <dcc:content lang="pt">BIPM</dcc:content>
    </dcc:name>
    <dcc:location>
      <dcc:city>Paris</dcc:city>
      <dcc:countryCode>FR</dcc:countryCode>
    </dcc:location>
  </dcc:respAuthority>
</dcc:statement>
```

A ordem dos filhos respeita o `xs:sequence` do `statementMetaDataType`:

```text
name, description, countryCode, convention, traceable, norm,
reference, link, declaration, valid/validXMLList, date, period,
respAuthority, conformity, data, nonSIDefinition, nonSIUnit, location
```

### 5.2 Resultado

Manter exatamente como está:

```xml
<dcc:quantity refType="basic_measuredValue">
  ...
  <dcc:measurementMetaData>
    <dcc:metaData refId="inCMC">
      <dcc:validXMLList>true</dcc:validXMLList>
    </dcc:metaData>
  </dcc:measurementMetaData>
</dcc:quantity>
```

Usar sempre `dcc:validXMLList`, inclusive para um ponto único, com um booleano por valor, na mesma ordem.

---

## 6. Estado atual do `dcc_tools`

### 6.1 O que já existe

Em `flask/app/main.py`:

- `CMC_REF_TYPE = 'basic_isInCMC'`;
- `CMC_ID_PATTERN` — valida o `id` interno do XML, **não** o CMC ID do KCDB;
- `CMC_STATEMENT_DEFAULTS` — nome, referência, link, descrição e autoridade;
- `resolve_cmc_config(dados)` — resolve `cmc`, `cmc_padrao`, `resultados[].in_cmc` e `cmc_declaracao`;
- `add_cmc_metadata(parent, ref_id, statuses)` — gera `measurementMetaData` com `validXMLList`;
- `add_cmc_statement(statements, dados, config, declaracao)` — gera o `statement` com `id`, `refType="basic_isInCMC"`, `reference`, `link`, `declaration` e `respAuthority`;
- `dccGen` integra a configuração ao XML.

Em `flask/app/test_cmc.py` já há testes para:

- ativação por `cmc`, `in_cmc` e `cmc_padrao`;
- erro para booleano inválido;
- erro para `id` inválido;
- statement sem duplicação;
- lista mista com `validXMLList`;
- ponto único com `validXMLList`;
- preservação do statement MRA.

### 6.2 O que falta

- campo para o **CMC ID** do KCDB;
- validação do formato `RMO-Area-A2-ID-V`;
- geração de um segundo `dcc:reference`;
- geração de link permanente derivado do CMC ID;
- suporte a múltiplos `dcc:link` (humano + JSON/XML);
- opção de `dcc:norm` e `dcc:date`;
- testes específicos de CMC ID/link;
- exibição do CMC ID no PDF/visualização.

### 6.3 Ponto de atenção

O `CMC_STATEMENT_DEFAULTS['link']` atual é:

```python
'link': 'https://www.bipm.org/kcdb/'
```

Esse link é genérico. Ele deve continuar como fallback para compatibilidade, mas, quando houver `cmc_id`, o link específico deve ter precedência.

---

## 7. Modelo de dados proposto

### 7.1 Entrada JSON

Manter os campos atuais e acrescentar, em `cmc_declaracao`:

| Campo | Tipo | Obrigatório | Descrição |
| :---- | :---- | :---- | :---- |
| `id` | string | não | `id` interno do `dcc:statement`; padrão `inCMC` |
| `nome` | string | não | Nome do statement |
| `referencia` | string | não | Referência geral (CIPM-MRA/KCDB) |
| `cmc_id` | string | recomendado | CMC ID do KCDB, com versão |
| `links` | array de strings | não | Links explícitos; se ausente, derivar do `cmc_id` |
| `link` | string | não | Compatibilidade: link principal |
| `descricao` | string | não | Texto humano do critério |
| `norm` | string | não | Ex.: `CIPM MRA-G-13` |
| `data_verificacao` | string `AAAA-MM-DD` | não | Data de consulta/verificação da CMC |
| `autoridade` | objeto | não | `nome`, `cidade`, `pais` |

Exemplo:

```json
{
  "cmc": true,
  "cmc_declaracao": {
    "id": "inCMC",
    "nome": "CIPM-MRA — CMC aplicável",
    "referencia": "CIPM-MRA — Apêndice C / KCDB",
    "cmc_id": "SIM-EM-BR-000008UK-2",
    "links": [
      "https://si-digital-framework.org/kcdb-cmc/SIM-EM-BR-000008UK-2",
      "https://si-digital-framework.org/kcdb-cmc/SIM-EM-BR-000008UK-2?type=json"
    ],
    "descricao": "Resultado coberto pela CMC identificada. Faixa e incerteza são as publicadas no KCDB.",
    "norm": "CIPM MRA-G-13",
    "data_verificacao": "2026-11-13",
    "autoridade": {
      "nome": "BIPM",
      "cidade": "Paris",
      "pais": "FR"
    }
  },
  "resultados": [
    {
      "in_cmc": true
    }
  ]
}
```

### 7.2 Regras de resolução

Em `resolve_cmc_config`:

1. `cmc_id` é opcional para compatibilidade.
2. Se `cmc_id` existir:
   - validar contra `KCDB_CMC_ID_PATTERN`;
   - normalizar para maiúsculas ou rejeitar minúsculas (recomendação: rejeitar, para evitar link inválido);
   - se `links` não existir, derivar `https://si-digital-framework.org/kcdb-cmc/<cmc_id>`;
   - se `link` existir e `links` não, usar `link` como principal;
   - se `links` existir, usar a lista;
   - validar que cada link contém o `cmc_id` no path;
   - exigir que a marcação (`in_cmc` ou `cmc_padrao`) esteja ativa; caso contrário, erro.
3. Se `cmc_id` não existir:
   - manter o comportamento atual (link genérico, statement apenas declarativo);
   - permitir `cmc=true` sem `in_cmc`, como hoje.
4. `cmc_declaracao.id` continua sendo validado por `CMC_ID_PATTERN` (XML `xs:ID`), separadamente do CMC ID.
5. `norm` e `data_verificacao` são opcionais; se presentes, validar formato.

### 7.3 Regex sugerida

```python
KCDB_CMC_ID_PATTERN = re.compile(
    r'^[A-Z]{2,10}-[A-Z]{1,5}-[A-Z]{2,4}-[A-Z0-9]{8}-[A-Z0-9]$'
)
```

Exemplos válidos:

```text
SIM-EM-BR-000008UK-2
EURAMET-EM-CH-00000GFB-7
APMP-EM-NZ-00000DA0-1
```

A parte do país pode ser `BIPM` (4 letras) para organizações internacionais. O sufixo de versão é obrigatório.

---

## 8. Alterações em `main.py`

### 8.1 Constantes

Acrescentar:

```python
KCDB_CMC_ID_PATTERN = re.compile(
    r'^[A-Z]{2,10}-[A-Z]{1,5}-[A-Z]{2,4}-[A-Z0-9]{8}-[A-Z0-9]$'
)
KCDB_CMC_BASE_URL = 'https://si-digital-framework.org/kcdb-cmc/'
```

Manter `CMC_ID_PATTERN` para o `id` interno do XML.

### 8.2 `resolve_cmc_config`

Acrescentar ao `config`:

```python
'cmc_id': None,
'links': [],
'norm': None,
'data_verificacao': None,
```

Ler de `cmc_declaracao`:

```python
cmc_id = declaracao.get('cmc_id')
links = declaracao.get('links')
norm = declaracao.get('norm')
data_verificacao = declaracao.get('data_verificacao')
```

Validar e derivar o link principal. Exemplo de lógica:

```python
if cmc_id:
    cmc_id = str(cmc_id).strip().upper()
    if not KCDB_CMC_ID_PATTERN.match(cmc_id):
        raise ValueError(
            "CMC ID inválido em 'cmc_declaracao.cmc_id': %r. "
            "Use o formato RMO-Area-País-ID-Versão." % (cmc_id,)
        )

    if not (config['enabled'] or config['statement']):
        raise ValueError(
            "'cmc_declaracao.cmc_id' exige cmc=True, in_cmc ou cmc_padrao."
        )

    if not links:
        links = [KCDB_CMC_BASE_URL + cmc_id]

    for link in links:
        if cmc_id not in link:
            raise ValueError(
                "O link %r não contém o CMC ID %r." % (link, cmc_id)
            )

    config['cmc_id'] = cmc_id
    config['links'] = [str(link).strip() for link in links]
```

Se `links` não for lista, erro claro. Se `link` antigo existir e `links` não, usar `[link]`.

### 8.3 `add_cmc_statement`

Substituir a emissão de um único `reference`/`link` por listas:

```python
campo_texto(statement, 'reference', config['referencia'])

if config.get('cmc_id'):
    campo_texto(statement, 'reference', config['cmc_id'])

for link in config.get('links', []):
    campo_texto(statement, 'link', link)
```

Se `norm` existir, emitir antes de `reference`:

```python
if config.get('norm'):
    campo_texto(statement, 'norm', config['norm'])
```

Se `data_verificacao` existir, emitir depois de `declaration` e antes de `respAuthority`:

```python
if config.get('data_verificacao'):
    campo_texto(statement, 'date', config['data_verificacao'])
```

Manter a ordem do XSD. Não emitir `dcc:validXMLList` no statement.

### 8.4 `dccGen`

Nenhuma mudança estrutural além de passar a configuração já resolvida para `add_cmc_statement`. A chamada atual:

```python
if cmc_config['statement']:
    add_cmc_statement(statements, dados, cmc_config, declaracao)
```

continua válida.

### 8.5 API

Se a API retornar metadados de geração, incluir:

- `cmc_id`;
- `cmc_links`;
- `cmc_norm`;
- `data_verificacao`;
- indicação de que a CMC é referência externa, não resultado.

Não fazer chamada de rede ao KCDB dentro de `dccGen`. A geração deve ser determinística e offline. Se houver verificação online, criar etapa separada, opcional e cacheada.

---

## 9. Validação e regras de consistência

| Regra | Ação |
| :---- | :---- |
| `cmc_id` com formato inválido | Erro |
| `cmc_id` com versão ausente | Erro |
| `cmc_id` em minúsculas | Erro (ou normalizar, se o time preferir) |
| `cmc_id` sem `in_cmc`/`cmc_padrao` | Erro |
| `links` vazio ou não-lista | Erro |
| Link sem o `cmc_id` no path | Erro |
| `id` interno inválido | Erro (já existe) |
| `cmc_id` sem `cmc=true` | Erro |
| `norm` vazio | Erro |
| `data_verificacao` fora de `AAAA-MM-DD` | Erro |
| `cmc_id` ausente com `cmc=true` | Permitir (compatibilidade), mas registrar aviso |
| `cmc_padrao=true` com CMC ID que não cobre todos os resultados | Decisão humana; o software não valida cobertura |

O software **não** deve calcular `true`/`false` a partir da CMC. A marcação é uma afirmação do laboratório; o software apenas transporta a decisão.

---

## 10. Testes

Arquivo: `flask/app/test_cmc.py`  
Execução:

```bash
cd flask/app
python -m unittest test_cmc.py -v
```

### 10.1 Testes de configuração

- `test_cmc_id_valido_resolve_config`;
- `test_cmc_id_invalido_gera_erro`;
- `test_cmc_id_sem_marcacao_gera_erro`;
- `test_cmc_id_normaliza_ou_rejeita_minusculas`;
- `test_cmc_id_deriva_link_permanente`;
- `test_cmc_id_com_links_explicitos`;
- `test_cmc_id_link_sem_id_gera_erro`;
- `test_cmc_id_nao_altera_id_interno`;
- `test_cmc_sem_id_mantem_compatibilidade`;
- `test_norm_e_data_validos`;
- `test_data_invalida_gera_erro`.

### 10.2 Testes de geração XML

- `test_statement_tem_reference_do_cmc_id`;
- `test_statement_tem_link_permanente`;
- `test_statement_tem_link_json_opcional`;
- `test_statement_nao_tem_valid`;
- `test_statement_mantem_declaracao_mra`;
- `test_statement_mantem_resp_authority_bipm`;
- `test_statement_com_norm_e_date`;
- `test_statement_com_id_interno_inCMC`;
- `test_measurement_metadata_continua_vinculado`;
- `test_validxml_list_continua_alinhado`.

### 10.3 Testes de schema e regressão

- `test_validation.py`: validar o XML gerado com CMC ID contra DCC 3.3.0;
- `test_visualizacao.py`: garantir que o CMC ID/link aparecem no PDF/HTML quando configurados;
- `test_cmc.py`: garantir que o comportamento antigo (sem `cmc_id`) não muda.

### 10.4 Casos de borda

- CMC ID com versão `-Z`;
- CMC ID de RMO com nome longo (`EURAMET`);
- país `BIPM`;
- link com `?type=json`;
- `cmc=true` sem `in_cmc` e sem `cmc_id` (comportamento antigo);
- `cmc=true` com `cmc_id` e sem `in_cmc` (erro);
- `cmc_padrao=false` com um ponto `true` e `cmc_id` presente.

---

## 11. PDF e visualização

Em `certificado_pdf_template.html`, o bloco de CMC já é exibido quando `payload.cmc` é verdadeiro. Acrescentar, quando disponível:

- CMC ID;
- link permanente (texto ou hiperlink);
- data de verificação, se configurada;
- nota: “Faixa e incerteza da CMC publicadas no KCDB; o link é a referência autoritativa.”

Não imprimir a tabela completa da CMC no PDF por padrão. Se o cliente exigir, criar um anexo/nota específica, deixando claro que se trata de cópia informativa.

---

## 12. Compatibilidade e migração

1. **Entradas antigas:** sem `cmc_id`, continuam gerando o statement atual com link genérico.
2. **Entradas novas:** com `cmc_id`, geram referência e link específicos.
3. **XML antigo:** consumidores que só leem `reference`/`link` continuam funcionando; o segundo `reference` e os links adicionais são extensões compatíveis.
4. **Schema:** não alterar o DCC 3.3.0; `reference` e `link` já são `maxOccurs="unbounded"`.
5. **Validação:** o XML com múltiplos `reference`/`link` deve continuar válido; testar com `test_validation.py`.

---

## 13. Checklist de implementação

- [ ] Adicionar `KCDB_CMC_ID_PATTERN` e `KCDB_CMC_BASE_URL`.
- [ ] Estender `cmc_declaracao` com `cmc_id`, `links`, `norm` e `data_verificacao`.
- [ ] Validar CMC ID e links em `resolve_cmc_config`.
- [ ] Emitir segundo `dcc:reference` com o CMC ID.
- [ ] Emitir link permanente derivado.
- [ ] Suportar múltiplos `dcc:link`.
- [ ] Emitir `dcc:norm` e `dcc:date` opcionais na ordem correta.
- [ ] Manter `dcc:validXMLList` fora do statement.
- [ ] Atualizar `test_cmc.py`.
- [ ] Atualizar `test_validation.py`.
- [ ] Atualizar `test_visualizacao.py` e o template PDF.
- [ ] Atualizar `doc/api_dcc_generator.md` com os novos campos.
- [ ] Atualizar `AGENTS.md`, se a convenção de CMC for documentada lá.
- [ ] Rodar `python -m unittest test_cmc.py -v`.
- [ ] Rodar `python -m unittest test_validation.py -v`.
- [ ] Rodar `python -m unittest test_visualizacao.py -v`.
- [ ] Validar um XML gerado contra DCC 3.3.0 + D-SI 2.2.1.

---

## 14. Decisões abertas

| ID | Decisão | Opções | Recomendação |
| :---- | :---- | :---- | :---- |
| C01 | `cmc_id` obrigatório quando `cmc=true`? | Sim / Não | Não bloquear entradas antigas; avisar. Para novos certificados, exigir por procedimento. |
| C02 | Normalizar minúsculas? | Normalizar / Rejeitar | Rejeitar, para evitar link ambíguo. |
| C03 | Incluir link JSON por padrão? | Sim / Não | Não; permitir via `links`. |
| C04 | Incluir `dcc:date`? | Sim / Não | Opcional; definir como data de verificação da CMC. |
| C05 | Incluir `dcc:norm`? | Sim / Não | Opcional; recomendado `CIPM MRA-G-13`. |
| C06 | Múltiplos CMC IDs por certificado? | Fase 1 não / Fase 2 sim | Fase 1: um `cmc_id` por certificado. Fase 2: um statement por CMC ID e vínculo por resultado. |
| C07 | CMC de acreditação (Cgcre) | Mesmo campo / campo separado | Usar `referencia`/`link`/`autoridade` existentes; `cmc_id` fica para KCDB. |
| C08 | Verificação online da CMC | No gerador / etapa separada | Etapa separada, opcional e cacheada; não no `dccGen`. |

---

## 15. Exemplo aplicado ao certificado DIMCI 9999/2026

Uma entrada candidata do INMETRO no KCDB:

| Campo | Valor |
| :---- | :---- |
| CMC ID | `SIM-EM-BR-000008UK-2` |
| Serviço | DC resistance standards and sources — intermediate values |
| Faixa | 1 Ω a 1000 Ω |
| U_CMC | 0,15 a 0,25 µΩ/Ω; tabela detalhada: 0,35 µΩ/Ω para 100 Ω |
| k / p | 2 / 95% |
| Método | Ponte automática de resistência |
| Condições | Potência 50 mW; banho de óleo a 23 °C |
| Link | `https://si-digital-framework.org/kcdb-cmc/SIM-EM-BR-000008UK-2` |

O certificado tem 99,996926 Ω, U = 0,68 µΩ/Ω, a 3 mA. A condição de incerteza é atendida em relação a 0,35 µΩ/Ω, mas a condição de potência da CMC (50 mW) precisa ser confrontada com a corrente de 3 mA (≈ 0,9 mW em 100 Ω). **A escolha da entrada aplicável é decisão técnica do laboratório; o exemplo serve para o formato, não para presumir cobertura.**

---

## 16. Referências

1. DKD-E 7-2, *Instructions on how to use the DCC schema to create a digital calibration certificate for weights and weight sets*, ed. 01/2024, rev. 1, §4.5.  
   `https://doi.org/10.7795/550.20240119B`
2. Vocabulário de `refType` do DKD/PTB, termo `isInCMC` (broader term `basic`), revisão de 22/04/2026.  
   `https://digilab.ptb.de/dkd/refType/vocab/index.php?tema=250`
3. BIPM, *Quick start on CMC identifiers*, 2024-02-27.  
   `https://www.bipm.org/documents/20126/43909385/QUICK_START_CMC-identifiers.pdf`
4. CIPM MRA-G-13, *Calibration and measurement capabilities in the context of the CIPM MRA*, v1.3, 25/11/2024.  
   `https://www.bipm.org/documents/20126/43742162/CIPM-MRA-G-13.pdf`
5. BIPM KCDB, CMC `SIM-EM-BR-000008UK-2`.  
   `https://si-digital-framework.org/kcdb-cmc/SIM-EM-BR-000008UK-2`
6. DKD-E 1-1, *Guia para a utilização do esquema DCC na elaboração de certificados digitais de calibração para resistores padrão*, ed. 07/2026, rev. 0.  
   `https://doi.org/10.7795/550.20260724`
7. ILAC-P14:09/2020, Anexo A; ILAC-P8:11/2023, cap. 7 — marcação de resultados fora do escopo de acreditação.

---

## Apêndice A — Resposta JSON/XML do KCDB

O link permanente retorna JSON ou XML com, entre outros:

- `kcdbCode`;
- `status`;
- `publicationDate`;
- `approvalDate`;
- `branchValue`;
- `serviceValue`;
- `subServiceValue`;
- `individualServiceValue`;
- `instrument`;
- `instrumentMethod`;
- `parameters`;
- `cmc` (limites e unidade);
- `cmcUncertainty` (limites e unidade);
- `coverageFactor`;
- `confidenceLevel`;
- `uncertaintyTable`;
- `traceabilitySource`.

Isso reforça que a faixa e a incerteza da CMC já estão disponíveis de forma estruturada no KCDB e não precisam ser copiadas para o DCC.

---

*Documento de apoio à implementação. Não altera o esquema DCC nem substitui a decisão técnica do laboratório sobre a CMC aplicável.*
