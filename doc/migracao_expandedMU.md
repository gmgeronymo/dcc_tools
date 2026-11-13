# Migração de `si:expandedUnc` para `si:expandedMU` (D-SI 2.2.1)

**Status:** implementado parcialmente (12/11/2026)
**Escopo implementado:** validação da incerteza relativa, migração do bloco absoluto para
`expandedMU`, fim da geração com schema 3.2.0 e referências oficiais na documentação.
**Pendente:** conversão do valor relativo para `relative_unc_unit`, comunicação por e-mail e
remoção do suporte de leitura a formatos antigos (se desejado no futuro).

---

## 1. Contexto

O DCC 3.3.0 importa D-SI 2.2.1, que marca `si:expandedUnc` e `si:expandedUncXMLList` como
depreciados e indica `si:expandedMU` / `si:expandedMUXMLList` como substitutos.

| Legado | Substituto |
| --- | --- |
| `si:expandedUnc` | `si:measurementUncertaintyUnivariate/si:expandedMU` |
| `si:expandedUncXMLList` | `si:measurementUncertaintyUnivariateXMLList/si:expandedMUXMLList` |
| `si:uncertainty` | `si:valueExpandedMU` |
| `si:uncertaintyXMLList` | `si:valueExpandedMUXMLList` |

O DCC 3.2.0 importa D-SI 2.1.0, que não possui `expandedMU`. Por isso, a geração com 3.2.0 foi
descontinuada e retorna `400`.

## 2. O que foi implementado

### 2.1 Validação da incerteza relativa

- `relative_uncertainty_in_dcc=true` exige `unc_relativa=true`.
- A combinação `unc_relativa=false` + `relative_uncertainty_in_dcc=true` retorna `400` com
  mensagem clara.
- A regra está em `validate_relative_uncertainty()` e é chamada no início de `dccGen()`.

### 2.2 Incerteza absoluta em `expandedMU`

- Valor único (`si:real`, condições de influência):
  `si:measurementUncertaintyUnivariate/si:expandedMU`.
- Lista (`si:realListXMLList`, resultados):
  `si:measurementUncertaintyUnivariateXMLList/si:expandedMUXMLList`.
- `coverageProbability` continua fixa em `0.9545`.
- O formato legado não é mais gerado.

### 2.3 Fim do schema 3.2.0 para geração

- `SUPPORTED_DCC_VERSIONS` contém apenas `3.3.0`.
- `resolve_dcc_version()` retorna `400` para `3.2.0` e versões desconhecidas.
- Certificados 3.2.0 existentes continuam válidos para validação e visualização.
- O XSLT `hr_template.xsl` foi ajustado para ler os dois formatos, preservando a visualização de
  certificados antigos.

### 2.4 Referências oficiais

- `dcc:relativeUncertainty`: <https://wiki.dcc.ptb.de/dccrelativeUncertainty>
- `dcc:quantityType`: <https://wiki.dcc.ptb.de/en/dccquantityType>
- D-SI 2.2.1: <https://ptb.de/si/v2.2.1/SI_Format.xsd>
- DCC 3.3.0: <https://www.ptb.de/dcc/v3.3.0/dcc.xsd>

## 3. Fora do escopo desta implementação

- Conversão do valor exibido em `dcc:relativeUncertaintyXmlList` para `relative_unc_unit`.
  O comportamento atual preserva o valor original em ppm.
- Mensagem de comunicação aos usuários cadastrados.
- Campo `uncertainty_format` / opt-out para o formato `expandedUnc`.

## 4. Testes

- `test_uncertainty.py`: versão suportada e validação da incerteza relativa.
- `test_nueff.py`: verifica a emissão de `valueExpandedMUXMLList`.
- `test_auth.py`: verifica `expandedMU`, rejeição de 3.2.0 e de versão desconhecida, além da
  regra `unc_relativa`.

## 5. Validação manual

O XML gerado foi validado contra o XSD DCC 3.3.0 com `lxml` e não contém mais
`si:expandedUnc` / `si:expandedUncXMLList`.
