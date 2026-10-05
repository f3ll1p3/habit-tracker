# Habit Tracker

Sistema simples de acompanhamento de hábitos diários.
Projeto acadêmico de Engenharia de Software.

**Proposta de valor:** ajudar quem quer criar e manter hábitos no dia a dia —
cadastrar hábitos, marcar quando forem concluídos e acompanhar o progresso da semana.

**Stack:** Python 3 + Flask, PostgreSQL (Neon) via psycopg2, templates Jinja2 e CSS puro.
Hospedagem: Vercel (função serverless).

## Rodando no seu computador

1. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

2. Pegue a connection string do seu banco no painel do Neon
   (algo como `postgresql://usuario:senha@ep-xxx.neon.tech/neondb?sslmode=require`)
   e coloque na variável de ambiente `DATABASE_URL`:

   ```powershell
   $env:DATABASE_URL="postgresql://...?sslmode=require"
   ```

3. Crie as tabelas (só na primeira vez):

   ```bash
   python init_db.py
   ```

4. Suba o app:

   ```bash
   python app.py
   ```

   Abra http://localhost:5000.

## Publicando na Vercel

1. Suba o projeto para um repositório no GitHub.
2. Na Vercel, importe o repositório. O `vercel.json` já configura o runtime
   `@vercel/python` apontando para o `app.py`.
3. Em **Settings → Environment Variables**, crie:
   - `DATABASE_URL` — a connection string do Neon (a mesma do passo 2 acima).
   - `SECRET_KEY` — qualquer texto secreto, usado pelas mensagens do Flask.
4. Faça o deploy. As tabelas já foram criadas no passo `init_db.py`, então não
   é preciso rodar nada no servidor.

## Estrutura

```
app.py             servidor Flask: todas as rotas e a lógica
init_db.py         script que cria as tabelas no Neon (rodar uma vez)
schema.sql         CREATE TABLE das tabelas habitos e conclusoes (PostgreSQL)
requirements.txt   dependências (Flask, psycopg2-binary)
vercel.json        configuração do deploy serverless na Vercel
templates/         páginas HTML (Jinja2)
  base.html        moldura comum (fontes, CSS, mensagens)
  index.html       tela principal "Meus Hábitos"
  novo_habito.html formulário de cadastro
  historico.html   histórico e progresso de um hábito
static/style.css   identidade visual (paleta + tipografia do protótipo)
```

## Rotas

| Método | Rota | O que faz | Requisito |
|---|---|---|---|
| GET | `/` | Aba Hábitos: saudação, sequência e lista com os pontinhos da semana | RF02, RF04 |
| GET | `/progresso` | Aba Progresso: % da semana por hábito e média geral | RF04 |
| GET/POST | `/perfil` | Guarda o nome usado na saudação (não é login) | — |
| GET/POST | `/habitos/novo` | Mostra e processa o formulário de cadastro | RF01 |
| POST | `/habitos/<id>/concluir` | Marca o hábito como concluído hoje | RF03, RN01, RN02 |
| POST | `/habitos/<id>/desmarcar` | Desfaz a conclusão de hoje (só de hoje) | RF03 |
| GET | `/habitos/<id>/historico` | Mostra o histórico e a constância do hábito | RF04 |

## Banco de dados

**habitos** — `id SERIAL`, `nome TEXT`, `descricao TEXT`, `icone TEXT`, `criado_em DATE`

**conclusoes** — `id SERIAL`, `habito_id INTEGER`, `data DATE`, com `UNIQUE (habito_id, data)`

**usuario** — `id INTEGER` (sempre 1), `nome TEXT` — só o nome da saudação

A restrição `UNIQUE` é o que garante a **RN01**: o próprio banco recusa uma segunda
conclusão do mesmo hábito no mesmo dia. A coluna `data` atende a **RN02** e é a base
do histórico.

## Interface

Duas abas fixas no rodapé: **Hábitos** (marcar o dia) e **Progresso** (comparar
os hábitos). A paleta segue o protótipo, e o âmbar `#D98E3C` é exclusivo do
indicador do dia atual — nenhum outro elemento usa essa cor.

Na fileira de 7 bolinhas, só a de **hoje** é clicável: um toque marca, outro
desmarca. As bolinhas dos dias anteriores são apenas histórico, e a rota de
desmarcar tem a data de hoje no `WHERE`, então é impossível apagar dias passados
por ela.

As datas do app usam o horário de Brasília (UTC−3), não o do servidor: a Vercel
roda em UTC, e sem isso um hábito marcado depois das 21h cairia no dia seguinte.

## O que mudou do SQLite para o Postgres/Neon

| | Antes (SQLite) | Agora (Postgres/Neon) |
|---|---|---|
| Onde ficam os dados | arquivo `habitos.db` na pasta | banco na nuvem, no Neon |
| Biblioteca | `sqlite3` (vem com o Python) | `psycopg2-binary` (instalada) |
| Endereço do banco | caminho do arquivo no código | variável de ambiente `DATABASE_URL` |
| Id automático | `INTEGER PRIMARY KEY AUTOINCREMENT` | `SERIAL PRIMARY KEY` |
| Datas | `TEXT` (`"2026-09-28"`) | tipo `DATE` de verdade |
| Parâmetro na query | `?` | `%s` |
| Executar query | `conexao.execute(...)` | `cursor.execute(...)` |
| Erro da duplicata (RN01) | `sqlite3.IntegrityError` | `psycopg2.errors.UniqueViolation` + `rollback()` |
| Criação das tabelas | automática ao iniciar o app | uma vez, com `python init_db.py` |

Como a Vercel roda o app como função serverless (sem estado entre requisições),
cada rota abre a sua própria conexão e fecha no fim, dentro de um `try/finally` —
não existe conexão global guardada.

## Escopo

Implementado: RF01 a RF04, RN01, RN02, US01 a US05.

Fora do escopo deste projeto (possíveis expansões futuras): login/autenticação,
sistema social, ranking, gamificação, notificações, integrações com wearables ou
apps de saúde, inteligência artificial, metas complexas, recompensas, assinaturas
e pagamentos.
