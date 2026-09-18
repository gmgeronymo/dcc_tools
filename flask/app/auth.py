## Inmetro/Dimci/Diele/Lampe
# Autenticacao do dccGenerator
# - cadastro aberto de usuarios (login com usuario + senha)
# - cada usuario recebe uma API-KEY, recuperavel na area de perfil
# - login da interface web por usuario/senha; a sessao autoriza os servicos
# - armazenamento em SQLite (senha com hash; API-KEY guardada para exibicao)

# Author: Gean Marcos Geronymo

# This file is part of Inmetro DCC Tools.
#
# Inmetro DCC Tools is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Inmetro DCC Tools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Inmetro DCC Tools. If not, see <http://www.gnu.org/licenses/>.

import functools
import hashlib
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone

from flask import Response, g, redirect, request, session, url_for
from lxml import etree
from werkzeug.security import check_password_hash, generate_password_hash

# namespace da resposta XML de erro de autenticacao (nao e um DCC)
API_ERROR_NS = 'https://inmetro.gov.br/dcc/api'

# prefixo identificavel das chaves de usuario
API_KEY_PREFIX = 'dcc_'
# quantos caracteres iniciais da chave sao guardados (nao secretos) para identificacao
KEY_PREFIX_LENGTH = 12
# tamanho minimo da senha
MIN_PASSWORD_LENGTH = 8

USERNAME_RE = re.compile(r'^[A-Za-z0-9._@-]{1,64}$')


def _db_path():
    """Caminho do banco SQLite (configuravel via DCC_DB_PATH)."""
    return os.environ.get('DCC_DB_PATH') or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'dcc_auth.db'
    )


def _connect():
    conn = sqlite3.connect(_db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def hash_key(key):
    """Hash SHA-256 (hex) de uma API-KEY (usado apenas para busca)."""
    return hashlib.sha256((key or '').encode('utf-8')).hexdigest()


def generate_api_key():
    return API_KEY_PREFIX + secrets.token_urlsafe(32)


def _validate_username(username):
    username = (username or '').strip()
    if not username:
        raise ValueError("O nome de usuário é obrigatório.")
    if not USERNAME_RE.match(username):
        raise ValueError(
            "Nome de usuário inválido. Use até 64 caracteres: letras, números e . _ @ -"
        )
    return username


def _validate_password(password):
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            "A senha deve ter pelo menos %d caracteres." % MIN_PASSWORD_LENGTH
        )
    return password


# ---------------------------------------------------------------------------
# banco de dados
# ---------------------------------------------------------------------------

def init_db():
    conn = _connect()
    try:
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT,
                password_hash TEXT,
                api_key TEXT,
                api_key_hash TEXT UNIQUE,
                api_key_prefix TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                last_used_at TEXT
            )
            '''
        )
        _ensure_columns(conn)
        conn.execute('CREATE INDEX IF NOT EXISTS idx_users_api_key_hash ON users(api_key_hash)')
        conn.commit()
    finally:
        conn.close()


def _ensure_columns(conn):
    """Migra bancos criados por versoes anteriores."""
    existing = {row['name'] for row in conn.execute('PRAGMA table_info(users)')}
    for column, ddl in (
        ('password_hash', 'ALTER TABLE users ADD COLUMN password_hash TEXT'),
        ('api_key', 'ALTER TABLE users ADD COLUMN api_key TEXT'),
    ):
        if column not in existing:
            conn.execute(ddl)


# ---------------------------------------------------------------------------
# usuarios
# ---------------------------------------------------------------------------

def create_user(username, password, email=None, active=True):
    """Cria um usuario (usuario + senha) e gera a API-KEY.

    Retorna um dict com os dados do usuario, incluindo a API-KEY em texto puro.
    """
    username = _validate_username(username)
    _validate_password(password)
    email = (email or '').strip() or None

    api_key = generate_api_key()
    created_at = _now()

    conn = _connect()
    try:
        try:
            conn.execute(
                'INSERT INTO users '
                '(username, email, password_hash, api_key, api_key_hash, api_key_prefix, active, created_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    username,
                    email,
                    generate_password_hash(password),
                    api_key,
                    hash_key(api_key),
                    api_key[:KEY_PREFIX_LENGTH],
                    1 if active else 0,
                    created_at,
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError("Já existe um usuário com esse nome.")
    finally:
        conn.close()

    return {
        'username': username,
        'email': email,
        'api_key': api_key,
        'created_at': created_at,
    }


def authenticate(username, password):
    """Valida usuario e senha. Retorna a linha do usuario ou None."""
    if not username or not password:
        return None

    conn = _connect()
    try:
        row = conn.execute(
            'SELECT * FROM users WHERE username = ? AND active = 1',
            ((username or '').strip(),),
        ).fetchone()
    finally:
        conn.close()

    if row is None or not row['password_hash']:
        return None
    if not check_password_hash(row['password_hash'], password):
        return None
    return row


def list_users():
    conn = _connect()
    try:
        rows = conn.execute(
            'SELECT id, username, email, api_key_prefix, active, created_at, last_used_at '
            'FROM users ORDER BY username COLLATE NOCASE'
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def set_user_active(username, active):
    conn = _connect()
    try:
        cur = conn.execute(
            'UPDATE users SET active = ? WHERE username = ?',
            (1 if active else 0, (username or '').strip()),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def set_password(username, password):
    _validate_password(password)
    conn = _connect()
    try:
        cur = conn.execute(
            'UPDATE users SET password_hash = ? WHERE username = ?',
            (generate_password_hash(password), (username or '').strip()),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_user_by_api_key(api_key):
    if not api_key:
        return None
    conn = _connect()
    try:
        return conn.execute(
            'SELECT * FROM users WHERE api_key_hash = ? AND active = 1',
            (hash_key(api_key),),
        ).fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = _connect()
    try:
        return conn.execute(
            'SELECT * FROM users WHERE id = ? AND active = 1',
            (user_id,),
        ).fetchone()
    finally:
        conn.close()


def get_user_by_username(username):
    conn = _connect()
    try:
        return conn.execute(
            'SELECT * FROM users WHERE username = ? AND active = 1',
            ((username or '').strip(),),
        ).fetchone()
    finally:
        conn.close()


def regenerate_api_key(user_id):
    """Gera e persiste uma nova API-KEY para o usuario. Retorna a chave."""
    api_key = generate_api_key()
    conn = _connect()
    try:
        cur = conn.execute(
            'UPDATE users SET api_key = ?, api_key_hash = ?, api_key_prefix = ? WHERE id = ?',
            (api_key, hash_key(api_key), api_key[:KEY_PREFIX_LENGTH], user_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
    finally:
        conn.close()
    return api_key


def touch_user(user_id):
    conn = _connect()
    try:
        conn.execute('UPDATE users SET last_used_at = ? WHERE id = ?', (_now(), user_id))
        conn.commit()
    except sqlite3.Error:
        pass
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# sessao da interface web
# ---------------------------------------------------------------------------

def start_session(user):
    """Registra o usuario autenticado na sessao da interface web."""
    session.clear()
    session['user_id'] = user['id']
    session['username'] = user['username']
    session.permanent = True


def current_username():
    return session.get('username')


# ---------------------------------------------------------------------------
# protecao de rotas
# ---------------------------------------------------------------------------

def _is_browser_request():
    """Navegacao de pagina (HTML) x cliente de API.

    Requisicoes GET de rotas protegidas sao paginas; POST so e tratado como
    navegador quando o cliente declara explicitamente preferencia por HTML
    (formularios no browser enviam 'Accept: text/html'). Clientes de API que
    usam 'Accept: */*' ou 'application/xml'/'application/json' recebem XML.
    """
    if request.method == 'GET':
        return True
    return request.accept_mimetypes.best == 'text/html'


def _external(endpoint, fallback):
    try:
        return url_for(endpoint, _external=True)
    except Exception:
        return fallback


def authentication_required_xml():
    """Resposta XML (nao-DCC) avisando que o cadastro/API-KEY passou a ser exigido."""
    ns = API_ERROR_NS
    root = etree.Element(etree.QName(ns, 'autenticacaoNecessaria'), nsmap={None: ns})

    etree.SubElement(root, etree.QName(ns, 'codigo')).text = '401'
    for lang, text in (
        ('pt', 'A partir de agora o uso da API do DCC Generator requer cadastro e API-KEY.'),
        ('en', 'Using the DCC Generator API now requires registration and an API-KEY.'),
    ):
        el = etree.SubElement(root, etree.QName(ns, 'mensagem'))
        el.set('lang', lang)
        el.text = text

    cadastro = etree.SubElement(root, etree.QName(ns, 'cadastro'))
    etree.SubElement(cadastro, etree.QName(ns, 'url')).text = _external('register', '/dcc/register')
    etree.SubElement(cadastro, etree.QName(ns, 'metodo')).text = 'POST'
    etree.SubElement(cadastro, etree.QName(ns, 'contentType')).text = 'application/json'
    etree.SubElement(cadastro, etree.QName(ns, 'corpoExemplo')).text = (
        '{"username":"meu_usuario","password":"minha_senha","email":"eu@exemplo.com"}'
    )
    etree.SubElement(cadastro, etree.QName(ns, 'respostaExemplo')).text = (
        '{"username":"meu_usuario","api_key":"dcc_..."}'
    )
    for lang, text in (
        ('pt', 'Cadastre-se uma vez para obter a API-KEY. A chave também fica disponível '
               'na área de perfil após o login na interface web.'),
        ('en', 'Register once to obtain your API-KEY. The key is also available in the '
               'profile area after logging in to the web interface.'),
    ):
        el = etree.SubElement(cadastro, etree.QName(ns, 'orientacao'))
        el.set('lang', lang)
        el.text = text

    uso = etree.SubElement(root, etree.QName(ns, 'uso'))
    etree.SubElement(uso, etree.QName(ns, 'cabecalho')).text = 'X-API-Key'
    for lang, text in (
        ('pt', 'Ajuste o seu software para enviar o cabeçalho X-API-Key com a sua API-KEY '
               'em todas as requisições.'),
        ('en', 'Update your software to send the X-API-Key header with your API-KEY in '
               'all requests.'),
    ):
        el = etree.SubElement(uso, etree.QName(ns, 'instrucao'))
        el.set('lang', lang)
        el.text = text
    etree.SubElement(uso, etree.QName(ns, 'exemploCurl')).text = (
        'curl -X POST "%s" -H "X-API-Key: dcc_SUA_CHAVE" '
        '-H "Content-Type: application/json" --data @dados.json'
        % _external('generate_dcc', '/dcc/generate')
    )

    etree.SubElement(root, etree.QName(ns, 'documentacao')).text = _external('api_doc', '/dcc/api_doc')

    return etree.tostring(root, encoding='utf-8', xml_declaration=True, pretty_print=True)


def _unauthorized():
    """Navegador recebe redirect para o login; cliente de API recebe XML 401."""
    if _is_browser_request():
        return redirect(url_for('login', next=request.full_path, auth_required=1))
    return Response(authentication_required_xml(), status=401, mimetype='text/xml')


def require_auth(view):
    """Aceita: API-KEY de usuário (header X-API-Key) ou sessão da interface web."""
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key:
            user = get_user_by_api_key(api_key)
            if user is not None:
                g.api_user = user['username']
                g.user_id = user['id']
                touch_user(user['id'])
                return view(*args, **kwargs)

        user_id = session.get('user_id')
        if user_id is not None:
            user = get_user_by_id(user_id)
            if user is not None:
                g.api_user = user['username']
                g.user_id = user['id']
                return view(*args, **kwargs)
            # usuario removido ou revogado: encerra a sessao
            session.clear()

        return _unauthorized()

    return wrapped
