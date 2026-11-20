-- Esquema do banco de dados do BiblioTech (SQLite)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS livro (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo           TEXT    NOT NULL,
    autor            TEXT    NOT NULL,
    isbn             TEXT    NOT NULL UNIQUE,
    editora          TEXT,
    ano_publicacao   INTEGER,
    quantidade_total INTEGER NOT NULL DEFAULT 1 CHECK (quantidade_total >= 0),
    criado_em        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS leitor (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT NOT NULL,
    cpf       TEXT NOT NULL UNIQUE,
    email     TEXT NOT NULL UNIQUE,
    telefone  TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS emprestimo (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    livro_id                INTEGER NOT NULL REFERENCES livro (id) ON DELETE RESTRICT,
    leitor_id               INTEGER NOT NULL REFERENCES leitor (id) ON DELETE RESTRICT,
    data_emprestimo         TEXT    NOT NULL,
    data_prevista_devolucao TEXT    NOT NULL,
    data_devolucao          TEXT
);

CREATE INDEX IF NOT EXISTS idx_emprestimo_livro  ON emprestimo (livro_id);
CREATE INDEX IF NOT EXISTS idx_emprestimo_leitor ON emprestimo (leitor_id);
