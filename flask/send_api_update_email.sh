#!/usr/bin/env bash
#
# Envia o comunicado de atualização da API do DCC Tools para os usuários
# cadastrados no banco SQLite de autenticação (dcc_auth.db).
#
# Usa a mesma camada SMTP do DCC Tools (flask/app/email_service.py), ou seja,
# as variáveis SMTP_* e DCC_EMAIL_ENABLED do arquivo flask/.env (ou do
# ambiente, quando executado dentro do container).
#
# Uso:
#   cd flask
#   ./send_api_update_email.sh --dry-run   # apenas exibe destinatários/mensagem
#   ./send_api_update_email.sh             # exibe e pede confirmação antes de enviar
#
# O script:
#   - lê o .env (sem sobrescrever variáveis já exportadas no ambiente);
#   - consulta somente usuários ativos com e-mail cadastrado;
#   - exibe a lista de e-mails e a mensagem completa;
#   - exige confirmação explícita (s/N);
#   - envia uma mensagem individual por destinatário (sem expor os demais e-mails);
#   - informa falhas e retorna código de saída diferente de zero se alguma falhar.
#
# Observação: a atualização já está em produção; não há data futura de implantação.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Aceita tanto flask/send_api_update_email.sh (host) quanto o script copiado
# para /app (container).
if [[ -d "$SCRIPT_DIR/app" ]]; then
    APP_DIR="$SCRIPT_DIR/app"
else
    APP_DIR="$SCRIPT_DIR"
fi

ENV_FILE="${DCC_ENV_FILE:-$SCRIPT_DIR/.env}"
PYTHON_BIN="${PYTHON:-python3}"

export DCC_APP_DIR="$APP_DIR"
export DCC_ENV_FILE="$ENV_FILE"
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

exec "$PYTHON_BIN" - "$@" <<'PY'
import os
import sqlite3
import sys
import textwrap


def load_env_file(path):
    """Carrega KEY=VALUE do .env sem sobrescrever o ambiente atual."""
    if not path or not os.path.isfile(path):
        return

    with open(path, 'r', encoding='utf-8') as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue

            key, value = line.split('=', 1)
            key = key.strip()
            if key.startswith('export '):
                key = key[7:].strip()
            if not key:
                continue

            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]

            os.environ.setdefault(key, value)


def find_database(app_dir):
    """Prefere DCC_DB_PATH existente; no host, cai para app/dcc_auth.db."""
    candidates = [
        os.environ.get('DCC_DB_PATH'),
        os.path.join(app_dir, 'dcc_auth.db'),
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return candidates[-1]


def list_recipients(db_path):
    if not os.path.isfile(db_path):
        raise FileNotFoundError(
            'Banco de autenticação não encontrado: %s' % db_path
        )

    conn = sqlite3.connect('file:%s?mode=ro' % db_path, uri=True)
    try:
        rows = conn.execute(
            """
            SELECT DISTINCT lower(email) AS email
              FROM users
             WHERE active = 1
               AND email IS NOT NULL
               AND trim(email) <> ''
             ORDER BY lower(email)
            """
        ).fetchall()
    finally:
        conn.close()

    return [row[0] for row in rows if row[0]]


SUBJECT = 'DCC Tools — atualização da API já em produção'

BODY = textwrap.dedent(r"""
Prezados(as) usuários(as),

Informamos que a API do DCC Tools foi atualizada. A mudança já está em produção:
a partir do envio deste e-mail, todas as novas gerações de DCC usam a nova versão.

O endpoint POST /dcc/generate, a autenticação por X-API-Key e o formato JSON de
entrada continuam os mesmos. A maior parte das mudanças é aditiva, mas alguns
comportamentos exigem atenção para evitar erros 400 ou falhas em integrações que
consomem o XML gerado.

Resumo das mudanças

1. Mudanças que exigem atenção

1.1 Geração apenas com o schema DCC 3.3.0
- dcc_version/schema_version aceitam apenas "3.3.0". Se omitido, o padrão continua 3.3.0.
- Valores "3.2.0" ou desconhecidos retornam 400.
- Certificados 3.2.0 já emitidos continuam válidos para validação e visualização.

1.2 Incerteza de medição no formato D-SI 2.2.1
- A incerteza expandida passa a ser emitida em
  si:measurementUncertaintyUnivariateXMLList/si:expandedMU (ponto único) ou
  si:expandedMUXMLList (lista de pontos).
- Integrações que leem o formato anterior (si:expandedUncXMLList) precisam ser ajustadas.

1.3 Incerteza relativa
- Quando unc_relativa=true, os valores de "unc" continuam sendo interpretados como relativos
  (ppm) e são convertidos para incerteza absoluta no XML.
- A incerteza absoluta é sempre emitida em expandedMU/expandedMUXMLList.
- O bloco dcc:relativeUncertainty é emitido apenas quando
  relative_uncertainty_in_dcc=true.
- A combinação relative_uncertainty_in_dcc=true com unc_relativa=false retorna 400.

1.4 Novos atributos e elementos no XML
- O XML passa a conter atributos refType e elementos adicionais (dcc:norm, identificações e
  definições de refTypes). Sistemas que validam listas fechadas de elementos/atributos ou que
  comparam o XML byte a byte devem ser revisados.
- Em dcc:coreData/dcc:identifications passa a existir uma identificação adicional para o número
  do certificado (refType="basic_certificateNumber"). Consumidores devem selecionar a
  identificação por refType ou nome, e não assumir que existe apenas uma.

1.5 Características do item opcionais
- caracteristicas_item deixou de ser obrigatório. Se omitido/vazio, o statement
  "Características do Item" não é emitido. O valor nominal estruturado pode ser usado
  isoladamente.

2. Novos recursos opcionais

2.1 Marcação de pontos dentro/fora da CMC
- resultados[].in_cmc (booleano opcional) por ponto.
- cmc_padrao (booleano opcional) para pontos sem in_cmc.
- cmc_declaracao (objeto opcional) para personalizar id, nome, referência, link, descrição e
  autoridade do statement.
- cmc_declaracao.cmc_id (texto ou lista) para referenciar entradas do KCDB; o link permanente é
  derivado do ID.
- O XML usa dcc:statement com refType="basic_isInCMC", dcc:valid (ponto único) ou
  dcc:validXMLList (vários pontos).

2.2 Rastreabilidade com certificado do padrão que também é DCC
- tabela_rastreabilidade[].hash_sha256 (SHA-256 do XML do DCC do padrão) e
  hash_procedure (padrão "sha256"; para assinatura XML, "c14n-sha256" ou
  "enveloped-c14n-sha256").

2.3 Valor nominal estruturado do item
- valor_nominal como objeto:
  {"valor": "100", "unidade": "\\kilo\\ohm", "nome": "Valor nominal", "descricao": "..."}.
- Também é aceito o formato legado valor_nominal escalar + valnom_unit.
- No XML: dcc:itemQuantity com refType="basic_nominalValue".

2.4 Referência normativa da declaração da incerteza
- Novo campo opcional declaracao_incerteza_norm (texto ou lista de textos).
- Cada valor é emitido como dcc:norm no usedMethod "Declaração da Incerteza de Medição".
- Exemplo:
  "declaracao_incerteza_norm": "JCGM 100:2008"

2.5 refTypes
- O namespace "basic" passou a ser padrão: o gerador o declara automaticamente.
  O cliente não precisa enviá-lo; se enviar, a definição não é duplicada.
- Novos refTypes básicos emitidos automaticamente:
  - basic_serialNumber no número de série;
  - basic_identificationNumber no código de identificação;
  - basic_certificateNumber no número do certificado;
  - basic_resultScope no statement da declaração ABNT NBR ISO/IEC 17025;
  - basic_calibrationMethod e basic_methodMeasurementUncertainty nos métodos e na incerteza.
- RefTypes de outros namespaces (por exemplo, electromagnetic) continuam exigindo a definição
  correspondente em refTypeDefinitions.

3. Visualização e documentação
- A visualização human-readable (/dcc/visualizar_dcc) passa a usar capa no modelo
  NIE-Dimci-014, coluna CMC (Sim/Não) por ponto, observação automática para pontos fora da CMC
  e exibição de "inf" como "∞".
- A documentação da API (/dcc/api_doc) e o guia para LLMs (/dcc/llm_doc) foram atualizados.
  O guia está na versão 2.13; o arquivo /dcc/llm_doc.md pode ser baixado e anexado a
  assistentes de IA.

4. Ações recomendadas
1. Ajustar clientes que ainda enviam dcc_version="3.2.0" ou versões desconhecidas.
2. Revisar integrações que consomem a incerteza no XML para o novo formato expandedMU.
3. Revisar payloads com relative_uncertainty_in_dcc e garantir unc_relativa=true.
4. Atualizar parsers/validadores de XML para os novos refType/dcc:norm e para a identificação
   adicional do número do certificado.
5. Testar a geração de DCC e as integrações que consomem o XML com a nova versão.

5. Compatibilidade e suporte
- Os payloads JSON existentes continuam válidos, exceto os casos citados de versão de schema
  e combinação inválida de incerteza relativa.
- A autenticação e o endpoint principal não mudam.
- Em caso de dúvidas, consulte /dcc/api_doc e /dcc/llm_doc ou entre em contato:
  Gean Marcos Geronymo — gmgeronymo@inmetro.gov.br

Atenciosamente,
Gean Marcos Geronymo
gmgeronymo@inmetro.gov.br
""").strip()


def ask_confirmation(prompt):
    """Le a confirmacao do terminal, mesmo quando o script vem por stdin/heredoc."""
    try:
        tty_in = open('/dev/tty', 'r')
        tty_out = open('/dev/tty', 'w')
    except OSError as exc:
        print()
        print('ERRO: não foi possível abrir o terminal interativo (/dev/tty): %s' % exc)
        print('Execute o script em um terminal interativo ou use --dry-run.')
        return ''

    try:
        tty_out.write(prompt)
        tty_out.flush()
        return tty_in.readline()
    finally:
        tty_in.close()
        tty_out.close()


def main():
    dry_run = '--dry-run' in sys.argv[1:]

    load_env_file(os.environ.get('DCC_ENV_FILE', ''))
    app_dir = os.environ['DCC_APP_DIR']

    # A camada de e-mail é a mesma usada na recuperação de senha.
    sys.path.insert(0, app_dir)
    import email_service

    db_path = find_database(app_dir)
    recipients = list_recipients(db_path)

    print('=' * 74)
    print('Comunicado: atualização da API do DCC Tools')
    print('=' * 74)
    print('Banco de dados: %s' % db_path)
    print('Destinatários ativos com e-mail cadastrado: %d' % len(recipients))
    if recipients:
        for address in recipients:
            print('  - %s' % address)
    else:
        print('  (nenhum)')
    print()
    print('Assunto: %s' % SUBJECT)
    print('-' * 74)
    print(BODY)
    print('-' * 74)

    if not recipients:
        print('Nenhum destinatário ativo com e-mail cadastrado. Nada a enviar.')
        return 1

    if dry_run:
        print('Modo --dry-run: nenhum e-mail será enviado.')
        return 0

    if not email_service.is_enabled():
        print('ERRO: envio de e-mail desabilitado ou incompleto.')
        print('Defina DCC_EMAIL_ENABLED, SMTP_HOST e SMTP_FROM em flask/.env')
        print('(ou no ambiente do container) antes de executar o script.')
        return 1

    answer = ask_confirmation(
        'Confirma o envio para %d destinatário(s)? [s/N] ' % len(recipients)
    )

    if answer.strip().lower() not in ('s', 'sim', 'y', 'yes'):
        print('Envio cancelado.')
        return 0

    sent = 0
    failed = []
    for address in recipients:
        if email_service.send_email(address, SUBJECT, BODY):
            sent += 1
            print('[ok] %s' % address)
        else:
            failed.append(address)
            print('[falha] %s' % address)

    print()
    print('Resumo: %d enviado(s), %d falha(s).' % (sent, len(failed)))
    if failed:
        print('Falhas: %s' % ', '.join(failed))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
PY
