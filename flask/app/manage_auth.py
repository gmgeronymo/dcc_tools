#!/usr/bin/env python3
## Inmetro/Dimci/Diele/Lampe
# Gerenciamento de usuarios e API-KEYs do dccGenerator.
#
# Uso (a partir de flask/app/):
#   python manage_auth.py init-db
#   python manage_auth.py create-user <username> [--email <email>] [--password <senha>]
#   python manage_auth.py set-password <username> [--password <senha>]
#   python manage_auth.py list-users
#   python manage_auth.py revoke <username>
#   python manage_auth.py activate <username>
#
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

import argparse
import getpass
import sys

import auth


def _resolve_password(provided):
    if provided:
        return provided
    first = getpass.getpass('Senha: ')
    second = getpass.getpass('Confirme a senha: ')
    if first != second:
        raise ValueError('As senhas não coincidem.')
    return first


def cmd_init_db(args):
    auth.init_db()
    print('Banco de dados inicializado em: %s' % auth._db_path())


def cmd_create_user(args):
    auth.init_db()
    try:
        password = _resolve_password(args.password)
        user = auth.create_user(args.username, password, args.email, active=not args.inactive)
    except ValueError as e:
        print('Erro: %s' % e, file=sys.stderr)
        return 1
    print('Usuário criado: %s' % user['username'])
    print('API-KEY (também disponível na área de perfil):')
    print(user['api_key'])
    return 0


def cmd_set_password(args):
    auth.init_db()
    try:
        password = _resolve_password(args.password)
    except ValueError as e:
        print('Erro: %s' % e, file=sys.stderr)
        return 1
    if auth.set_password(args.username, password):
        print('Senha atualizada: %s' % args.username)
        return 0
    print('Usuário não encontrado: %s' % args.username, file=sys.stderr)
    return 1


def cmd_list_users(args):
    auth.init_db()
    users = auth.list_users()
    if not users:
        print('Nenhum usuário cadastrado.')
        return 0
    print('%-24s %-8s %-14s %-22s %s' % ('usuario', 'ativo', 'prefixo', 'criado_em', 'ultimo_uso'))
    for u in users:
        print('%-24s %-8s %-14s %-22s %s' % (
            u['username'],
            'sim' if u['active'] else 'nao',
            u['api_key_prefix'],
            u['created_at'],
            u['last_used_at'] or '-',
        ))
    return 0


def cmd_revoke(args):
    auth.init_db()
    if auth.set_user_active(args.username, False):
        print('Usuário revogado: %s' % args.username)
        return 0
    print('Usuário não encontrado: %s' % args.username, file=sys.stderr)
    return 1


def cmd_activate(args):
    auth.init_db()
    if auth.set_user_active(args.username, True):
        print('Usuário ativado: %s' % args.username)
        return 0
    print('Usuário não encontrado: %s' % args.username, file=sys.stderr)
    return 1


def build_parser():
    parser = argparse.ArgumentParser(description='Gerenciamento de usuários e API-KEYs do dccGenerator.')
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('init-db', help='Cria/atualiza as tabelas de autenticação.')

    p_create = sub.add_parser('create-user', help='Cria um usuário e exibe a API-KEY.')
    p_create.add_argument('username')
    p_create.add_argument('--email', default=None)
    p_create.add_argument('--password', default=None, help='Senha; se omitida, é solicitada.')
    p_create.add_argument('--inactive', action='store_true', help='Cria o usuário já desativado.')

    p_pass = sub.add_parser('set-password', help='Define/redefine a senha de um usuário.')
    p_pass.add_argument('username')
    p_pass.add_argument('--password', default=None, help='Senha; se omitida, é solicitada.')

    sub.add_parser('list-users', help='Lista os usuários cadastrados.')

    p_revoke = sub.add_parser('revoke', help='Desativa um usuário.')
    p_revoke.add_argument('username')

    p_activate = sub.add_parser('activate', help='Reativa um usuário.')
    p_activate.add_argument('username')

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        'init-db': cmd_init_db,
        'create-user': cmd_create_user,
        'set-password': cmd_set_password,
        'list-users': cmd_list_users,
        'revoke': cmd_revoke,
        'activate': cmd_activate,
    }
    return handlers[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
