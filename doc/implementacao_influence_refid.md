# Vínculo de resultados a condições de influência por `id`/`refId`

## Contexto

O schema DCC 3.3.0 permite associar uma `dcc:influenceCondition` a um
`dcc:measurementResult`, a uma `dcc:list` ou a uma `dcc:quantity` por meio de
`id`/`refId` ([PTB DCC Wiki — References with id and refId](https://wiki.dcc.ptb.de/en/id_refid)):

| Elemento com `id` | Elemento com `refId` | Significado |
| --- | --- | --- |
| `influenceCondition` (`iC_...`) | `(list/quantity)/measurementMetaData/metaData` | A condição se aplica à lista/quantidade. |

Antes desta implementação, a API só aceitava condições de influência globais, sem vínculo com
os resultados. Isso impedia representar, por exemplo, a temperatura média de cada ponto de
resistência de um certificado multi-temperatura.

## Mudanças na API

### `informacoes_pertinentes[].id` (opcional)

Identificador da condição. Vira `dcc:influenceCondition/@id`.

- Padrão: `[A-Za-z_][A-Za-z0-9._-]*` (`xs:ID`).
- Único no documento.
- Não pode coincidir com o `id` do statement de CMC (`inCMC` por padrão) quando o statement é
  emitido.
- Sem `id`, o XML continua sem o atributo (compatível com payloads antigos).

### `resultados[].refId` (opcional)

ID(s) de condições que se aplicam ao resultado. Aceita:

- string com IDs separados por espaço (`"iC_temp_1 iC_temp_2"`);
- lista de strings (`["iC_temp_1", "iC_temp_2"]`).

O gerador adiciona:

```xml
<dcc:measurementMetaData>
  <dcc:metaData refId="iC_temp_1"/>
</dcc:measurementMetaData>
```

na `dcc:quantity` do valor medido. Se a CMC também estiver marcada, a mesma
`dcc:measurementMetaData` contém dois `dcc:metaData` (CMC e condição), pois o schema permite
apenas um elemento `measurementMetaData` com uma lista de `metaData`.

### Agrupamento automático

Resultados do mesmo `mensurando` são agrupados pelo conjunto de `refId`:

- mesmo conjunto → mesmo `dcc:result` (tabela);
- conjuntos diferentes → blocos `dcc:result` separados, preservando a ordem de primeira
  ocorrência;
- sem `refId` → um único bloco, como antes.

Isso permite ao cliente escolher o nível de granularidade:

- **uma condição por ponto** e `refId` por resultado → uma tabela por ponto, com vínculo exato;
- **uma condição por grupo/tabela** e o mesmo `refId` em todos os pontos do grupo → uma tabela
  por grupo, com o vínculo no nível da tabela.

## Validação e erros

`/dcc/generate` retorna `400` com `{"error": "..."}` quando:

- `informacoes_pertinentes[].id` não segue o padrão ou está duplicado;
- `id` conflita com o `id` do statement de CMC;
- `resultados[].refId` tem tipo inválido, identificador sintaticamente inválido ou referencia
  um `id` não declarado em `informacoes_pertinentes`.

## Compatibilidade

- `id` e `refId` são opcionais; payloads antigos geram o mesmo XML de antes.
- O agrupamento por `refId` só atua quando há `refId`; sem ele, um bloco por mensurando.
- O `dcc:measurementMetaData` da CMC passou a reaproveitar o elemento existente, sem criar
  duplicatas; o comportamento e os testes de CMC foram preservados.

## Testes

`flask/app/test_influence_ref_ids.py` cobre:

- payload antigo sem `id`/`refId` (uma tabela por mensurando, sem metadados de refId);
- `id` na condição;
- agrupamento de resultados por `refId` e valores por grupo;
- `refId` em lista;
- coexistência de CMC e `refId` em um único `measurementMetaData`;
- erros de id inválido/duplicado/conflitante e refId desconhecido/tipo inválido.

Validação adicional: o XML gerado com `id`/`refId` foi validado contra o schema DCC 3.3.0 com
`validate_dcc_xml_upload`.
