"""
Cria as tabelas do Habit Tracker no banco Postgres do Neon.

Rode UMA VEZ, no seu computador, antes do primeiro uso:

    PowerShell:  $env:DATABASE_URL="postgresql://...?sslmode=require"
                 python init_db.py

Por que isso virou um script separado?
    Com SQLite, o app criava o arquivo do banco sozinho ao iniciar.
    Com Postgres na nuvem isso não pode acontecer a cada requisição:
    na Vercel o app sobe e desce a toda hora, e ficar tentando criar
    tabela seria lento e desnecessário. Então criamos as tabelas uma
    vez, à mão, com este script.

O schema.sql usa "CREATE TABLE IF NOT EXISTS", então rodar este script
de novo é seguro: ele não apaga nada que já esteja lá.
"""

import os

from app import conectar   # reaproveita a mesma função de conexão do app

PASTA_DO_PROJETO = os.path.dirname(os.path.abspath(__file__))
CAMINHO_SCHEMA = os.path.join(PASTA_DO_PROJETO, "schema.sql")


def criar_tabelas():
    with open(CAMINHO_SCHEMA, encoding="utf-8") as arquivo:
        script_sql = arquivo.read()

    conexao = conectar()
    try:
        with conexao.cursor() as cursor:
            cursor.execute(script_sql)   # executa todos os CREATE TABLE de uma vez
        conexao.commit()
    finally:
        conexao.close()

    print("Tabelas 'habitos' e 'conclusoes' prontas no banco do Neon.")


if __name__ == "__main__":
    criar_tabelas()
