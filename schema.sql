-- ============================================================
-- Habit Tracker - estrutura do banco de dados (PostgreSQL / Neon)
--
-- Rode este arquivo para criar/atualizar as tabelas no Neon:
--     python init_db.py
--
-- Todos os comandos usam "IF NOT EXISTS", então rodar de novo é
-- seguro: nada é apagado e nada quebra se já existir.
--
-- MUDOU NA MIGRAÇÃO (SQLite -> PostgreSQL):
--   * "INTEGER PRIMARY KEY AUTOINCREMENT"  virou  "SERIAL PRIMARY KEY"
--     (é o jeito do Postgres de gerar o id sozinho, 1, 2, 3...).
--   * As datas eram TEXT ("2026-09-28") porque o SQLite não tem tipo de data.
--     O Postgres tem o tipo DATE de verdade, então agora usamos DATE.
--     Vantagem: o banco entende as datas, ordena e compara corretamente,
--     e o Python recebe objetos date() prontos, sem precisar converter.
-- ============================================================

-- ------------------------------------------------------------
-- Tabela HABITOS (RF01 / RF02)
-- Guarda cada hábito que o usuário cadastra.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS habitos (
    id         SERIAL PRIMARY KEY,   -- código único do hábito (gerado pelo Postgres)
    nome       TEXT NOT NULL,        -- ex.: "Beber água"
    descricao  TEXT NOT NULL,        -- ex.: "2 litros por dia"
    criado_em  DATE NOT NULL         -- data do cadastro
);

-- Coluna do ícone escolhido no cadastro (ex.: 'gota', 'livro', 'haltere').
-- Fica como ALTER separado para funcionar também em bancos que já existiam
-- antes desta tela, sem precisar apagar nada.
ALTER TABLE habitos ADD COLUMN IF NOT EXISTS icone TEXT NOT NULL DEFAULT 'estrela';

-- ------------------------------------------------------------
-- Tabela CONCLUSOES (RF03 / RF04)
-- Cada linha = "o hábito X foi concluído no dia Y".
--
-- RN02: toda conclusão guarda a data em que aconteceu,
--       é isso que permite montar o histórico depois.
--
-- RN01: a restrição UNIQUE (habito_id, data) faz o próprio banco
--       impedir que o mesmo hábito tenha duas conclusões no mesmo dia.
--       Funciona igual no Postgres e no SQLite; só muda o erro que o
--       Python recebe quando a regra é violada (veja o app.py).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conclusoes (
    id         SERIAL PRIMARY KEY,
    habito_id  INTEGER NOT NULL,     -- qual hábito foi concluído
    data       DATE NOT NULL,        -- em que dia

    UNIQUE (habito_id, data),        -- <- RN01: um registro por hábito por dia

    -- ON DELETE CASCADE: se um dia um hábito for apagado, as conclusões
    -- dele saem junto, sem deixar lixo no banco.
    FOREIGN KEY (habito_id) REFERENCES habitos (id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- Tabela USUARIO (saudação personalizada)
-- Guarda só o nome de quem usa o app, para a tela dizer
-- "Boa tarde, Fellipe". Não é login: não tem senha, não tem
-- autenticação, não controla acesso a nada. É só personalização.
--
-- A tabela tem no máximo UMA linha, sempre id = 1.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuario (
    id    INTEGER PRIMARY KEY DEFAULT 1,
    nome  TEXT NOT NULL,

    -- Trava que garante a linha única: id só pode valer 1.
    CONSTRAINT usuario_linha_unica CHECK (id = 1)
);
