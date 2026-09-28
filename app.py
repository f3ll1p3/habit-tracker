"""
Habit Tracker - aplicação Flask
================================

Como isso funciona, em poucas palavras:

  1. O navegador pede um endereço (ex.: http://localhost:5000/).
  2. O Flask olha os "@app.route(...)" abaixo e descobre qual função responde
     por aquele endereço. Essa função é chamada de ROTA.
  3. A função busca/grava dados no banco e devolve uma página HTML
     (render_template) ou manda o navegador para outro endereço (redirect).

BANCO DE DADOS: este app usava SQLite (um arquivo .db na própria pasta) e agora
usa PostgreSQL hospedado no Neon (um banco na nuvem, acessado pela internet).
As diferenças práticas estão comentadas ao longo do arquivo, marcadas com
"MUDOU:". As rotas e as regras de negócio continuam exatamente as mesmas.

Para rodar localmente:
    set DATABASE_URL=postgresql://...   (no PowerShell: $env:DATABASE_URL="...")
    python app.py                       ->  abre em http://localhost:5000
"""

import os
from datetime import date, timedelta

# MUDOU: antes era "import sqlite3" (biblioteca que já vem no Python).
# O Postgres precisa de uma biblioteca instalada: psycopg2 (veja requirements.txt).
import psycopg2
import psycopg2.extras

from flask import Flask, flash, redirect, render_template, request, url_for

# Lê o arquivo .env (onde estão DATABASE_URL e SECRET_KEY) quando rodamos
# no nosso computador, para não ter que digitar a senha no terminal.
# Na Vercel esse arquivo não existe: lá os valores vêm do painel do site,
# e estas linhas simplesmente não fazem nada.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Cria a aplicação Flask. O "__name__" diz ao Flask onde estão as pastas
# templates/ (HTML) e static/ (CSS).
#
# Na Vercel, é esta variável "app" que o servidor procura para rodar o site.
app = Flask(__name__)

# Chave usada pelo Flask para as mensagens temporárias (flash).
# MUDOU: na Vercel o app roda em vários "processos" diferentes, então a chave
# precisa ser a mesma em todos. Por isso ela vem de uma variável de ambiente
# (configurável no painel da Vercel), com um valor padrão para rodar local.
app.secret_key = os.environ.get("SECRET_KEY", "habit-tracker-projeto-academico")

# Nomes curtos dos dias da semana, na ordem segunda -> domingo,
# usados nos pontinhos do progresso semanal (US05).
DIAS_DA_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


# =====================================================================
# BANCO DE DADOS - funções auxiliares
# =====================================================================

def conectar():
    """Abre uma conexão nova com o Postgres do Neon.

    MUDOU (SQLite -> Postgres/Neon):

      * Antes: abríamos o arquivo habitos.db que estava na mesma pasta.
        Agora: conectamos pela internet a um banco hospedado no Neon, e o
        endereço dele vem da variável de ambiente DATABASE_URL
        (algo como: postgresql://usuario:senha@host.neon.tech/nome?sslmode=require).
        Guardar a senha em variável de ambiente, e não no código, é o certo:
        assim ela não vai parar no GitHub.

      * sslmode=require significa "só conecte com a conexão criptografada".
        O psycopg2 lê isso direto da URL; se por algum motivo a URL vier sem
        essa parte, nós acrescentamos abaixo para nunca conectar sem SSL.

      * RealDictCursor faz cada linha do resultado vir como um dicionário
        (habito["nome"] em vez de habito[1]). É o equivalente ao
        sqlite3.Row que usávamos antes, então o resto do código não mudou.

    IMPORTANTE (Vercel / serverless): cada requisição roda isolada e pode
    até rodar em uma máquina diferente, então NÃO existe conexão global
    guardada. Cada rota chama conectar() e fecha a conexão no fim.
    """
    url = os.environ.get("DATABASE_URL")

    if not url:
        raise RuntimeError(
            "A variável de ambiente DATABASE_URL não está definida. "
            "Coloque nela a connection string do Neon."
        )

    # Garante o SSL exigido pelo Neon mesmo se a URL vier sem sslmode.
    if "sslmode=" not in url:
        separador = "&" if "?" in url else "?"
        url = f"{url}{separador}sslmode=require"

    return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)


# MUDOU: a função criar_banco_se_nao_existir() foi removida.
# No SQLite dava para criar o arquivo do banco na hora em que o app subia.
# Com o Postgres o banco já existe lá no Neon e as tabelas são criadas uma
# única vez, rodando "python init_db.py" (que executa o schema.sql).


# =====================================================================
# FUNÇÕES DE APOIO (cálculo do progresso - RF04)
# =====================================================================

def inicio_da_semana(dia):
    """Devolve a segunda-feira da semana em que 'dia' está.

    Ex.: se hoje é quarta (dia 10), devolve a segunda (dia 8).
    'weekday()' dá 0 para segunda, 1 para terça ... 6 para domingo.
    """
    return dia - timedelta(days=dia.weekday())


def montar_semana(datas_concluidas, hoje):
    """Monta a lista de 7 pontinhos da semana atual (US05).

    Recebe o conjunto de datas em que o hábito foi concluído e devolve
    uma lista com um dicionário por dia da semana, já com o "estado"
    que o CSS vai usar para pintar o pontinho:

      concluido -> verde   (o hábito foi cumprido nesse dia)
      hoje      -> âmbar   (é o dia de hoje e ainda não foi cumprido)
      perdido   -> cinza   (dia que já passou e não foi cumprido)
      futuro    -> vazio   (dia que ainda não chegou)
    """
    segunda = inicio_da_semana(hoje)
    dias = []

    for posicao in range(7):
        dia = segunda + timedelta(days=posicao)

        if dia in datas_concluidas:
            estado = "concluido"
        elif dia == hoje:
            estado = "hoje"
        elif dia < hoje:
            estado = "perdido"
        else:
            estado = "futuro"

        dias.append({
            "sigla": DIAS_DA_SEMANA[posicao][0],   # só a primeira letra: S, T, Q...
            "nome": DIAS_DA_SEMANA[posicao],
            "data": dia.isoformat(),
            "estado": estado,
        })

    return dias


def porcentagem(concluidos, total):
    """Regra de três simples, protegida contra divisão por zero."""
    if total <= 0:
        return 0
    return round(concluidos * 100 / total)


# =====================================================================
# ROTAS
# =====================================================================

@app.route("/")
def index():
    """ROTA PRINCIPAL - tela "Meus Hábitos" (RF02 / RF04 / US02 / US05).

    Responde ao endereço "/" (a página inicial). Ela:
      1. busca todos os hábitos cadastrados;
      2. busca as conclusões da semana atual;
      3. calcula, para cada hábito, os 7 pontinhos e o "X/7 dias - Y%";
      4. entrega tudo para o template templates/index.html desenhar.
    """
    hoje = date.today()
    segunda = inicio_da_semana(hoje)
    domingo = segunda + timedelta(days=6)

    # MUDOU: no sqlite3 dava para escrever conexao.execute(...) direto.
    # No psycopg2 sempre criamos um "cursor" (o objeto que executa a consulta
    # e guarda o resultado). O "with" fecha o cursor sozinho, e o try/finally
    # garante que a conexão feche mesmo se der erro no meio.
    conexao = conectar()
    try:
        with conexao.cursor() as cursor:
            # (1) Todos os hábitos, do mais novo para o mais antigo.
            cursor.execute(
                "SELECT id, nome, descricao, criado_em FROM habitos ORDER BY id DESC"
            )
            habitos = cursor.fetchall()

            # (2) Todas as conclusões da semana atual, de uma vez só
            #     (mais rápido do que fazer uma consulta por hábito - RNF02,
            #     e ainda mais importante aqui, porque agora cada consulta
            #     viaja pela internet até o Neon).
            #
            # MUDOU: o marcador de parâmetro do SQLite era "?" e no Postgres
            # é "%s". A ideia é a mesma: a biblioteca coloca o valor no lugar
            # com segurança, protegendo contra SQL injection.
            cursor.execute(
                "SELECT habito_id, data FROM conclusoes WHERE data BETWEEN %s AND %s",
                (segunda, domingo),
            )
            conclusoes_da_semana = cursor.fetchall()
    finally:
        conexao.close()

    # Agrupa as conclusões por hábito: {1: {date(2026,9,28), ...}, 2: {...}}
    #
    # MUDOU: antes a data vinha como texto e precisávamos de
    # date.fromisoformat(...). Como a coluna agora é do tipo DATE, o psycopg2
    # já devolve um objeto date() do Python pronto para usar.
    concluidas_por_habito = {}
    for linha in conclusoes_da_semana:
        concluidas_por_habito.setdefault(linha["habito_id"], set()).add(linha["data"])

    # (3) Monta a lista que o HTML vai percorrer.
    lista = []
    for habito in habitos:
        datas = concluidas_por_habito.get(habito["id"], set())
        semana = montar_semana(datas, hoje)
        feitos_na_semana = len(datas)

        lista.append({
            "id": habito["id"],
            "nome": habito["nome"],
            "descricao": habito["descricao"],
            "inicial": habito["nome"][:1].upper(),   # letra do "ícone" do card
            "semana": semana,
            "feitos_na_semana": feitos_na_semana,
            "porcentagem_semana": porcentagem(feitos_na_semana, 7),
            "concluido_hoje": hoje in datas,          # deixa o checkbox marcado
        })

    # (4) render_template procura o arquivo em templates/ e preenche
    #     as {{ variáveis }} com o que passamos aqui.
    return render_template("index.html", habitos=lista, hoje=hoje)


@app.route("/habitos/novo", methods=["GET", "POST"])
def novo_habito():
    """ROTA DE CADASTRO (RF01 / US01).

    A mesma rota atende dois métodos:
      GET  -> o usuário só abriu a página: mostramos o formulário vazio.
      POST -> o usuário clicou em "Salvar": lemos os campos, validamos
              e gravamos no banco.
    """
    if request.method == "POST":
        # request.form pega o que foi digitado no formulário HTML.
        # .strip() remove espaços sobrando no começo/fim.
        nome = request.form.get("nome", "").strip()
        descricao = request.form.get("descricao", "").strip()

        # Critério da US01: nome e descrição são obrigatórios.
        if not nome or not descricao:
            flash("Preencha o nome e a descrição do hábito.", "erro")
            # Devolve o formulário já com o que a pessoa tinha digitado.
            return render_template("novo_habito.html", nome=nome, descricao=descricao)

        conexao = conectar()
        try:
            with conexao.cursor() as cursor:
                # MUDOU: "?" virou "%s", e a data vai como objeto date()
                # em vez de texto, porque a coluna agora é do tipo DATE.
                cursor.execute(
                    "INSERT INTO habitos (nome, descricao, criado_em) VALUES (%s, %s, %s)",
                    (nome, descricao, date.today()),
                )
            conexao.commit()     # confirma a gravação
        finally:
            conexao.close()      # serverless: nada de conexão aberta sobrando

        flash(f'Hábito "{nome}" cadastrado!', "sucesso")

        # redirect manda o navegador para a tela principal, onde o
        # hábito novo já aparece na lista (critério da US01).
        return redirect(url_for("index"))

    # Método GET: só mostra o formulário em branco.
    return render_template("novo_habito.html", nome="", descricao="")


@app.route("/habitos/<int:habito_id>/concluir", methods=["POST"])
def concluir(habito_id):
    """ROTA DE CONCLUSÃO (RF03 / US03 / RN01 / RN02).

    O <int:habito_id> no endereço vira o parâmetro habito_id da função:
    se o formulário enviar para /habitos/3/concluir, chega habito_id = 3.

    Aceita só POST porque essa ação MUDA dados (é o clique no checkbox).
    """
    hoje = date.today()   # RN02: guardamos a data da conclusão

    conexao = conectar()
    try:
        with conexao.cursor() as cursor:
            # Confere se o hábito realmente existe antes de gravar.
            cursor.execute("SELECT id FROM habitos WHERE id = %s", (habito_id,))
            habito = cursor.fetchone()

            if habito is None:
                flash("Hábito não encontrado.", "erro")
                return redirect(url_for("index"))

            try:
                cursor.execute(
                    "INSERT INTO conclusoes (habito_id, data) VALUES (%s, %s)",
                    (habito_id, hoje),
                )
                conexao.commit()
                flash("Hábito concluído hoje. Muito bem!", "sucesso")

            # RN01: o UNIQUE (habito_id, data) do schema.sql barrou a
            # segunda tentativa no mesmo dia, e o erro cai aqui.
            #
            # MUDOU: no SQLite esse erro era sqlite3.IntegrityError.
            # No Postgres é psycopg2.errors.UniqueViolation - mesma ideia,
            # nome diferente. A regra continua sendo garantida pelo BANCO,
            # não pelo Python.
            except psycopg2.errors.UniqueViolation:
                # MUDOU: no Postgres, depois de um erro a transação fica
                # "travada" e nada mais funciona nela até dar rollback,
                # que desfaz o INSERT recusado. No SQLite isso não era preciso.
                conexao.rollback()
                flash("Este hábito já foi concluído hoje.", "erro")
    finally:
        conexao.close()

    # Volta para a tela principal, que recarrega com o checkbox
    # já preenchido (feedback visual imediato - RF03 / RNF02).
    return redirect(url_for("index"))


@app.route("/habitos/<int:habito_id>/historico")
def historico(habito_id):
    """ROTA DE HISTÓRICO (RF04 / US04).

    Mostra, para UM hábito: a semana atual em pontinhos, a proporção de
    dias concluídos desde o cadastro e a lista das últimas conclusões.
    """
    hoje = date.today()
    segunda = inicio_da_semana(hoje)
    domingo = segunda + timedelta(days=6)

    conexao = conectar()
    try:
        with conexao.cursor() as cursor:
            cursor.execute(
                "SELECT id, nome, descricao, criado_em FROM habitos WHERE id = %s",
                (habito_id,),
            )
            habito = cursor.fetchone()

            if habito is None:
                flash("Hábito não encontrado.", "erro")
                return redirect(url_for("index"))

            # Todas as datas em que este hábito foi concluído, da mais recente
            # para a mais antiga (é o histórico completo - RN02 em ação).
            cursor.execute(
                "SELECT data FROM conclusoes WHERE habito_id = %s ORDER BY data DESC",
                (habito_id,),
            )
            linhas = cursor.fetchall()
    finally:
        conexao.close()

    # MUDOU: sem date.fromisoformat() - a coluna é DATE, então o psycopg2
    # já entrega objetos date() do Python.
    todas_as_datas = [linha["data"] for linha in linhas]

    # --- progresso da semana atual ---
    datas_da_semana = {d for d in todas_as_datas if segunda <= d <= domingo}
    semana = montar_semana(datas_da_semana, hoje)

    # --- progresso desde o cadastro ---
    criado_em = habito["criado_em"]                      # já vem como date()
    dias_desde_o_cadastro = (hoje - criado_em).days + 1  # +1 para contar o próprio dia
    total_concluido = len(todas_as_datas)

    dados = {
        "id": habito["id"],
        "nome": habito["nome"],
        "descricao": habito["descricao"],
        "criado_em": criado_em,
        "semana": semana,
        "feitos_na_semana": len(datas_da_semana),
        "porcentagem_semana": porcentagem(len(datas_da_semana), 7),
        "total_concluido": total_concluido,
        "dias_desde_o_cadastro": dias_desde_o_cadastro,
        "porcentagem_total": porcentagem(total_concluido, dias_desde_o_cadastro),
        "ultimas_datas": todas_as_datas[:14],   # as 14 conclusões mais recentes
    }

    return render_template("historico.html", habito=dados, hoje=hoje)


# =====================================================================
# INÍCIO DO PROGRAMA
# =====================================================================

# Este bloco só roda quando executamos "python app.py" no nosso computador.
# Na Vercel ele é ignorado: lá a plataforma importa a variável "app" acima e
# cuida do servidor sozinha.
if __name__ == "__main__":
    # debug=True recarrega o servidor sozinho quando salvamos um arquivo
    # e mostra os erros na tela (bom para desenvolver e apresentar).
    app.run(debug=True)
