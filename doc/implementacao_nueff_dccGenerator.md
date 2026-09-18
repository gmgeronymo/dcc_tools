# Implementação de `nueff` no dccGenerator

## Objetivo

Adicionar ao `dccGenerator` suporte opcional aos **graus de liberdade efetivos** (`nueff` / `νeff`) dos resultados de medição.

A informação deverá ser incluída no DCC como uma nova `dcc:quantity`, dentro da mesma `dcc:list` que contém as demais quantidades do resultado.

A representação escolhida é:

```xml
<dcc:charsXMLList>
    ...
</dcc:charsXMLList>
```

Não alterar o schema DCC do PTB.

## Estrutura XML

Para um resultado que atualmente possui, por exemplo:

```text
Faixa
Tensão
Frequência
δu
```

adicionar `nueff` como uma nova `dcc:quantity`, preferencialmente imediatamente após a quantidade do resultado (`δu`).

Estrutura mínima:

```xml
<dcc:quantity>
    <dcc:name>
        <dcc:content lang="pt">Graus de liberdade efetivos</dcc:content>
    </dcc:name>

    <dcc:charsXMLList>
        58.4 62.1 inf 25.7 inf 103.6
    </dcc:charsXMLList>
</dcc:quantity>
```

**Nesta primeira implementação não incluir `dcc:description` nem qualquer outra informação adicional.**

Não incluir `si:unitXMLList`, pois `charsXMLList` é uma representação textual.

## Representação dos valores

A lista de `nueff` deve ser serializada como strings separadas por espaço.

Valores finitos:

```text
58.4 62.1 25.7 103.6
```

Quando `νeff = +∞`, utilizar:

```text
inf
```

Exemplo:

```xml
<dcc:charsXMLList>58.4 62.1 inf 25.7 inf 103.6</dcc:charsXMLList>
```

`inf` é a convenção da aplicação para representar `νeff = +∞`.

**Não utilizar `NaN`.**

**Não utilizar `INF`.**

**Não utilizar um número arbitrariamente grande para representar infinito.**

## Dados de entrada

Adicionar `nueff` ao modelo de dados utilizado pelo `dccGenerator`.

O campo deve ser opcional, preservando a compatibilidade com os arquivos de entrada existentes.

Exemplo conceitual:

```json
{
    "nueff": [58.4, 62.1, "inf", 25.7, "inf", 103.6]
}
```

O formato exato deve seguir a estrutura de entrada já existente no projeto. Não criar uma nova estrutura de dados se for possível incorporar `nueff` ao modelo atual de resultados.

## Correspondência dos valores

Os valores de `nueff` devem estar alinhados, por índice, aos pontos da tabela de resultados:

```text
resultado[0] → nueff[0]
resultado[1] → nueff[1]
resultado[2] → nueff[2]
...
```

Se o resultado possui `N` pontos, `nueff` deve possuir exatamente `N` valores.

Exemplo válido:

```text
resultado = [r1, r2, r3, r4]
nueff     = [12.4, 18.7, inf, 25.1]
```

Exemplo inválido:

```text
resultado = [r1, r2, r3, r4]
nueff     = [12.4, 18.7, inf]
```

Quando `nueff` for informado, validar o comprimento antes de gerar o XML.

## Ausência de `nueff`

Se o campo não estiver presente:

- não criar a `dcc:quantity` de `nueff`;
- não alterar o XML gerado atualmente;
- manter compatibilidade com entradas antigas.

## Conversão para XML

A camada de serialização deve converter os valores para strings.

Conceitualmente:

```python
def serialize_nueff(values):
    result = []

    for value in values:
        if is_infinite(value):
            result.append("inf")
        else:
            result.append(str(value))

    return " ".join(result)
```

Adaptar à arquitetura existente do `dccGenerator`.

Idealmente, o modelo interno deve representar infinito como `math.inf` e somente a camada de serialização deve convertê-lo para `inf`:

```text
modelo interno
    math.inf
       ↓
serialização DCC
       ↓
"inf"
```

Se o formato de entrada atual utilizar `"inf"` como string, a camada de conversão deve reconhecer esse valor.

## Criação da `dcc:quantity`

Reutilizar as funções existentes do `dccGenerator` para criação de:

- `dcc:quantity`;
- `dcc:name`;
- elementos XML.

Não duplicar lógica de geração XML já existente.

Estrutura mínima:

```xml
<dcc:quantity>
    <dcc:name>
        <dcc:content lang="pt">Graus de liberdade efetivos</dcc:content>
    </dcc:name>
    <dcc:charsXMLList>...</dcc:charsXMLList>
</dcc:quantity>
```

Não adicionar `si:realListXMLList`.

Não adicionar `si:unitXMLList`.

Não adicionar `dcc:description` nesta implementação.

## Validação

Implementar pelo menos:

### `nueff` ausente

Aceitar e não gerar a nova quantidade.

### Lista vazia

Rejeitar se `nueff` tiver sido explicitamente informado.

### Comprimento incompatível

Rejeitar se o número de valores de `nueff` for diferente do número de pontos do resultado.

### Valores finitos

Aceitar números inteiros e reais.

Exemplos:

```text
10
10.5
25.7
100.0
```

### Infinito

Aceitar `+∞` e representar no XML como:

```text
inf
```

### Valores negativos

Rejeitar valores menores que zero.

### `NaN`

Rejeitar `NaN`.

### `-inf`

Rejeitar `-inf`.

## Testes

Adicionar testes automatizados para:

### 1. `nueff` ausente

Verificar que o XML não contém a nova quantidade.

### 2. Somente valores finitos

Entrada:

```text
[12.5, 20.7, 35.2]
```

Esperar:

```xml
<dcc:charsXMLList>12.5 20.7 35.2</dcc:charsXMLList>
```

### 3. Valores finitos e infinitos

Entrada:

```text
[12.5, inf, 35.2, inf]
```

Esperar:

```xml
<dcc:charsXMLList>12.5 inf 35.2 inf</dcc:charsXMLList>
```

### 4. Somente infinito

Entrada:

```text
[inf, inf, inf]
```

Esperar:

```xml
<dcc:charsXMLList>inf inf inf</dcc:charsXMLList>
```

### 5. Comprimento incompatível

Verificar que a geração falha com erro claro.

### 6. Valores inválidos

Testar:

```text
-1
-inf
NaN
```

e verificar rejeição.

### 7. Compatibilidade retroativa

Executar os testes existentes do `dccGenerator` e garantir que certificados que não fornecem `nueff` continuem sendo gerados como antes.

## Validação do XML

Validar um DCC contendo `nueff` contra o schema oficial DCC 3.3.0:

```text
https://www.ptb.de/dcc/v3.3.0/dcc.xsd
```

Usar `dcc:charsXMLList` exatamente como definido pelo schema.

Não modificar o schema nem introduzir elementos em namespaces proprietários.

## Exemplo completo

Considerando:

```text
Faixa      Tensão    Frequência    δu       U       k       nueff
0.022 V    0.002 V   0.04 kHz     81       36      2.01    inf
0.022 V    0.002 V   0.06 kHz     98       37      2.01    120
0.022 V    0.002 V   0.3 kHz      48       73      2.17    18.4
```

gerar:

```xml
<dcc:quantity>
    <dcc:name>
        <dcc:content lang="pt">
            Graus de liberdade efetivos
        </dcc:content>
    </dcc:name>

    <dcc:charsXMLList>
        inf 120 18.4
    </dcc:charsXMLList>
</dcc:quantity>
```

## Critérios de aceitação

A implementação estará concluída quando:

1. `nueff` puder ser fornecido opcionalmente nos dados de entrada.
2. `nueff` for gerado como uma nova `dcc:quantity`.
3. A nova quantidade estiver na mesma `dcc:list` das demais quantidades do resultado.
4. A representação utilizada for `dcc:charsXMLList`.
5. Valores infinitos forem representados como `inf`.
6. `NaN`, `-inf` e valores negativos forem rejeitados.
7. O número de valores de `nueff` for validado contra o número de pontos do resultado.
8. A ausência de `nueff` mantiver o comportamento anterior.
9. Não houver `dcc:description` nesta primeira implementação.
10. Não houver `si:unitXMLList` para `nueff`.
11. O XML gerado for válido contra o schema DCC 3.3.0.
12. Os testes existentes do `dccGenerator` continuarem passando.
