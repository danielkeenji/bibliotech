"""Entidades do domínio e classes de acesso a dados (repositórios)."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from database import get_db

PRAZO_PADRAO_DIAS = 14
LIMITE_EMPRESTIMOS_POR_LEITOR = 3


class RegraNegocioError(Exception):
    """Erro de validação ou de regra de negócio, exibido ao usuário."""


# --------------------------------------------------------------------------- #
# Entidades
# --------------------------------------------------------------------------- #
@dataclass
class Livro:
    titulo: str
    autor: str
    isbn: str
    editora: str = ""
    ano_publicacao: Optional[int] = None
    quantidade_total: int = 1
    id: Optional[int] = None
    emprestados: int = 0

    @property
    def quantidade_disponivel(self) -> int:
        return max(self.quantidade_total - self.emprestados, 0)

    def esta_disponivel(self) -> bool:
        return self.quantidade_disponivel > 0

    def validar(self) -> None:
        if not self.titulo.strip():
            raise RegraNegocioError("O título é obrigatório.")
        if not self.autor.strip():
            raise RegraNegocioError("O autor é obrigatório.")
        isbn = self.isbn.replace("-", "").strip()
        if not isbn.isdigit() or len(isbn) not in (10, 13):
            raise RegraNegocioError("O ISBN deve ter 10 ou 13 dígitos.")
        if self.quantidade_total < 0:
            raise RegraNegocioError("A quantidade não pode ser negativa.")
        if self.ano_publicacao is not None and not 0 < self.ano_publicacao <= date.today().year:
            raise RegraNegocioError("Ano de publicação inválido.")


@dataclass
class Leitor:
    nome: str
    cpf: str
    email: str
    telefone: str = ""
    id: Optional[int] = None

    def validar(self) -> None:
        if not self.nome.strip():
            raise RegraNegocioError("O nome é obrigatório.")
        cpf = "".join(c for c in self.cpf if c.isdigit())
        if len(cpf) != 11:
            raise RegraNegocioError("O CPF deve ter 11 dígitos.")
        if "@" not in self.email or "." not in self.email.split("@")[-1]:
            raise RegraNegocioError("E-mail inválido.")


@dataclass
class Emprestimo:
    livro_id: int
    leitor_id: int
    data_emprestimo: date
    data_prevista_devolucao: date
    data_devolucao: Optional[date] = None
    id: Optional[int] = None
    livro_titulo: str = ""
    leitor_nome: str = ""

    @property
    def status(self) -> str:
        if self.data_devolucao:
            return "Devolvido"
        return "Atrasado" if self.esta_atrasado() else "Ativo"

    def esta_atrasado(self, hoje: Optional[date] = None) -> bool:
        hoje = hoje or date.today()
        return self.data_devolucao is None and hoje > self.data_prevista_devolucao

    def dias_atraso(self, hoje: Optional[date] = None) -> int:
        fim = self.data_devolucao or hoje or date.today()
        return max((fim - self.data_prevista_devolucao).days, 0)

    def registrar_devolucao(self, data: Optional[date] = None) -> None:
        if self.data_devolucao:
            raise RegraNegocioError("Este empréstimo já foi devolvido.")
        self.data_devolucao = data or date.today()


# --------------------------------------------------------------------------- #
# Repositórios (CRUD no banco)
# --------------------------------------------------------------------------- #
def _d(valor: Optional[str]) -> Optional[date]:
    return date.fromisoformat(valor) if valor else None


class LivroRepository:
    SELECT = """
        SELECT l.*, (SELECT COUNT(*) FROM emprestimo e
                     WHERE e.livro_id = l.id AND e.data_devolucao IS NULL) AS emprestados
        FROM livro l
    """

    @staticmethod
    def _to_entity(row: sqlite3.Row) -> Livro:
        return Livro(id=row["id"], titulo=row["titulo"], autor=row["autor"], isbn=row["isbn"],
                     editora=row["editora"] or "", ano_publicacao=row["ano_publicacao"],
                     quantidade_total=row["quantidade_total"], emprestados=row["emprestados"])

    def listar(self, busca: str = "") -> list[Livro]:
        termo = f"%{busca.strip()}%"
        rows = get_db().execute(
            self.SELECT + " WHERE l.titulo LIKE ? OR l.autor LIKE ? OR l.isbn LIKE ? ORDER BY l.titulo",
            (termo, termo, termo)).fetchall()
        return [self._to_entity(r) for r in rows]

    def buscar_por_id(self, livro_id: int) -> Optional[Livro]:
        row = get_db().execute(self.SELECT + " WHERE l.id = ?", (livro_id,)).fetchone()
        return self._to_entity(row) if row else None

    def salvar(self, livro: Livro) -> Livro:
        livro.validar()
        db = get_db()
        dados = (livro.titulo.strip(), livro.autor.strip(), livro.isbn.strip(),
                 livro.editora.strip(), livro.ano_publicacao, livro.quantidade_total)
        try:
            if livro.id is None:
                cur = db.execute("INSERT INTO livro (titulo, autor, isbn, editora, ano_publicacao, "
                                 "quantidade_total) VALUES (?, ?, ?, ?, ?, ?)", dados)
                livro.id = cur.lastrowid
            else:
                atual = self.buscar_por_id(livro.id)
                if atual and livro.quantidade_total < atual.emprestados:
                    raise RegraNegocioError(
                        f"Há {atual.emprestados} exemplar(es) emprestado(s); a quantidade "
                        "não pode ser menor que isso.")
                db.execute("UPDATE livro SET titulo=?, autor=?, isbn=?, editora=?, ano_publicacao=?, "
                           "quantidade_total=? WHERE id=?", dados + (livro.id,))
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            raise RegraNegocioError("Já existe um livro cadastrado com este ISBN.")
        return livro

    def excluir(self, livro_id: int) -> None:
        db = get_db()
        if db.execute("SELECT 1 FROM emprestimo WHERE livro_id = ? LIMIT 1", (livro_id,)).fetchone():
            raise RegraNegocioError("Não é possível excluir um livro que possui empréstimos registrados.")
        db.execute("DELETE FROM livro WHERE id = ?", (livro_id,))
        db.commit()


class LeitorRepository:
    @staticmethod
    def _to_entity(row: sqlite3.Row) -> Leitor:
        return Leitor(id=row["id"], nome=row["nome"], cpf=row["cpf"], email=row["email"],
                      telefone=row["telefone"] or "")

    def listar(self, busca: str = "") -> list[Leitor]:
        termo = f"%{busca.strip()}%"
        rows = get_db().execute(
            "SELECT * FROM leitor WHERE nome LIKE ? OR cpf LIKE ? OR email LIKE ? ORDER BY nome",
            (termo, termo, termo)).fetchall()
        return [self._to_entity(r) for r in rows]

    def buscar_por_id(self, leitor_id: int) -> Optional[Leitor]:
        row = get_db().execute("SELECT * FROM leitor WHERE id = ?", (leitor_id,)).fetchone()
        return self._to_entity(row) if row else None

    def salvar(self, leitor: Leitor) -> Leitor:
        leitor.validar()
        db = get_db()
        dados = (leitor.nome.strip(), leitor.cpf.strip(), leitor.email.strip().lower(), leitor.telefone.strip())
        try:
            if leitor.id is None:
                cur = db.execute("INSERT INTO leitor (nome, cpf, email, telefone) VALUES (?, ?, ?, ?)", dados)
                leitor.id = cur.lastrowid
            else:
                db.execute("UPDATE leitor SET nome=?, cpf=?, email=?, telefone=? WHERE id=?",
                           dados + (leitor.id,))
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            raise RegraNegocioError("Já existe um leitor com este CPF ou e-mail.")
        return leitor

    def excluir(self, leitor_id: int) -> None:
        db = get_db()
        if db.execute("SELECT 1 FROM emprestimo WHERE leitor_id = ? LIMIT 1", (leitor_id,)).fetchone():
            raise RegraNegocioError("Não é possível excluir um leitor que possui empréstimos registrados.")
        db.execute("DELETE FROM leitor WHERE id = ?", (leitor_id,))
        db.commit()


class EmprestimoRepository:
    SELECT = """
        SELECT e.*, l.titulo AS livro_titulo, r.nome AS leitor_nome
        FROM emprestimo e
        JOIN livro  l ON l.id = e.livro_id
        JOIN leitor r ON r.id = e.leitor_id
    """

    def __init__(self) -> None:
        self.livros = LivroRepository()
        self.leitores = LeitorRepository()

    @staticmethod
    def _to_entity(row: sqlite3.Row) -> Emprestimo:
        return Emprestimo(id=row["id"], livro_id=row["livro_id"], leitor_id=row["leitor_id"],
                          data_emprestimo=_d(row["data_emprestimo"]),
                          data_prevista_devolucao=_d(row["data_prevista_devolucao"]),
                          data_devolucao=_d(row["data_devolucao"]),
                          livro_titulo=row["livro_titulo"], leitor_nome=row["leitor_nome"])

    def listar(self, filtro: str = "todos", busca: str = "") -> list[Emprestimo]:
        termo = f"%{busca.strip()}%"
        rows = get_db().execute(
            self.SELECT + " WHERE (l.titulo LIKE ? OR r.nome LIKE ?) "
            "ORDER BY e.data_devolucao IS NOT NULL, e.data_prevista_devolucao",
            (termo, termo)).fetchall()
        itens = [self._to_entity(r) for r in rows]
        if filtro == "ativos":
            return [e for e in itens if e.data_devolucao is None]
        if filtro == "atrasados":
            return [e for e in itens if e.esta_atrasado()]
        if filtro == "devolvidos":
            return [e for e in itens if e.data_devolucao is not None]
        return itens

    def buscar_por_id(self, emprestimo_id: int) -> Optional[Emprestimo]:
        row = get_db().execute(self.SELECT + " WHERE e.id = ?", (emprestimo_id,)).fetchone()
        return self._to_entity(row) if row else None

    def registrar(self, livro_id: int, leitor_id: int, hoje: Optional[date] = None,
                  prazo_dias: int = PRAZO_PADRAO_DIAS) -> Emprestimo:
        hoje = hoje or date.today()
        livro = self.livros.buscar_por_id(livro_id)
        leitor = self.leitores.buscar_por_id(leitor_id)
        if livro is None or leitor is None:
            raise RegraNegocioError("Selecione um livro e um leitor válidos.")
        if not livro.esta_disponivel():
            raise RegraNegocioError(f"Não há exemplares disponíveis de \"{livro.titulo}\".")
        ativos = [e for e in self.listar("ativos") if e.leitor_id == leitor_id]
        if any(e.esta_atrasado(hoje) for e in ativos):
            raise RegraNegocioError(f"{leitor.nome} possui empréstimo em atraso e não pode pegar novos livros.")
        if len(ativos) >= LIMITE_EMPRESTIMOS_POR_LEITOR:
            raise RegraNegocioError(
                f"{leitor.nome} já atingiu o limite de {LIMITE_EMPRESTIMOS_POR_LEITOR} empréstimos ativos.")
        emp = Emprestimo(livro_id=livro_id, leitor_id=leitor_id, data_emprestimo=hoje,
                         data_prevista_devolucao=hoje + timedelta(days=prazo_dias))
        db = get_db()
        cur = db.execute("INSERT INTO emprestimo (livro_id, leitor_id, data_emprestimo, "
                         "data_prevista_devolucao) VALUES (?, ?, ?, ?)",
                         (livro_id, leitor_id, emp.data_emprestimo.isoformat(),
                          emp.data_prevista_devolucao.isoformat()))
        db.commit()
        emp.id = cur.lastrowid
        return emp

    def atualizar_prazo(self, emprestimo_id: int, nova_data: date) -> None:
        emp = self.buscar_por_id(emprestimo_id)
        if emp is None:
            raise RegraNegocioError("Empréstimo não encontrado.")
        if emp.data_devolucao:
            raise RegraNegocioError("Não é possível alterar o prazo de um empréstimo já devolvido.")
        if nova_data < emp.data_emprestimo:
            raise RegraNegocioError("A data prevista não pode ser anterior à data do empréstimo.")
        db = get_db()
        db.execute("UPDATE emprestimo SET data_prevista_devolucao = ? WHERE id = ?",
                   (nova_data.isoformat(), emprestimo_id))
        db.commit()

    def registrar_devolucao(self, emprestimo_id: int, data: Optional[date] = None) -> Emprestimo:
        emp = self.buscar_por_id(emprestimo_id)
        if emp is None:
            raise RegraNegocioError("Empréstimo não encontrado.")
        emp.registrar_devolucao(data)
        db = get_db()
        db.execute("UPDATE emprestimo SET data_devolucao = ? WHERE id = ?",
                   (emp.data_devolucao.isoformat(), emprestimo_id))
        db.commit()
        return emp

    def excluir(self, emprestimo_id: int) -> None:
        db = get_db()
        db.execute("DELETE FROM emprestimo WHERE id = ?", (emprestimo_id,))
        db.commit()

    def resumo(self) -> dict:
        todos = self.listar()
        return {
            "ativos": sum(1 for e in todos if e.data_devolucao is None),
            "atrasados": sum(1 for e in todos if e.esta_atrasado()),
            "devolvidos": sum(1 for e in todos if e.data_devolucao is not None),
        }
