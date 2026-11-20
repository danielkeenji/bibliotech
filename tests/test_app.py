"""Testes automatizados das regras de negócio e das rotas CRUD."""
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app  # noqa: E402
from models import (EmprestimoRepository, Leitor, LeitorRepository, Livro,  # noqa: E402
                    LivroRepository, RegraNegocioError)


@pytest.fixture
def app(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "teste.db")})
    with app.app_context():
        yield app


@pytest.fixture
def dados(app):
    livro = LivroRepository().salvar(Livro("Livro Teste", "Autor", "9788594318602", quantidade_total=1))
    leitor = LeitorRepository().salvar(Leitor("Fulano", "12345678901", "f@x.com"))
    return livro, leitor


def test_crud_livro(app):
    repo = LivroRepository()
    l = repo.salvar(Livro("A", "B", "1234567890"))
    assert repo.buscar_por_id(l.id).titulo == "A"
    l.titulo = "A2"
    repo.salvar(l)
    assert repo.buscar_por_id(l.id).titulo == "A2"
    repo.excluir(l.id)
    assert repo.buscar_por_id(l.id) is None


def test_isbn_duplicado(app, dados):
    with pytest.raises(RegraNegocioError):
        LivroRepository().salvar(Livro("Outro", "X", "9788594318602"))


def test_validacao_leitor(app):
    with pytest.raises(RegraNegocioError):
        LeitorRepository().salvar(Leitor("X", "123", "invalido"))


def test_emprestimo_e_devolucao(app, dados):
    livro, leitor = dados
    repo = EmprestimoRepository()
    e = repo.registrar(livro.id, leitor.id)
    assert LivroRepository().buscar_por_id(livro.id).quantidade_disponivel == 0
    with pytest.raises(RegraNegocioError):          # sem exemplares
        repo.registrar(livro.id, leitor.id)
    repo.registrar_devolucao(e.id)
    assert LivroRepository().buscar_por_id(livro.id).quantidade_disponivel == 1
    with pytest.raises(RegraNegocioError):          # devolução duplicada
        repo.registrar_devolucao(e.id)


def test_bloqueio_por_atraso(app, dados):
    livro, leitor = dados
    outro = LivroRepository().salvar(Livro("Outro", "Y", "1234567890", quantidade_total=2))
    repo = EmprestimoRepository()
    repo.registrar(livro.id, leitor.id, hoje=date.today() - timedelta(days=30))
    assert repo.listar("atrasados")
    with pytest.raises(RegraNegocioError, match="atraso"):
        repo.registrar(outro.id, leitor.id)


def test_limite_emprestimos(app, dados):
    _, leitor = dados
    repo = EmprestimoRepository()
    livro = LivroRepository().salvar(Livro("Muitos", "Z", "1111111111", quantidade_total=10))
    for _ in range(3):
        repo.registrar(livro.id, leitor.id)
    with pytest.raises(RegraNegocioError, match="limite"):
        repo.registrar(livro.id, leitor.id)


def test_nao_exclui_livro_com_emprestimo(app, dados):
    livro, leitor = dados
    EmprestimoRepository().registrar(livro.id, leitor.id)
    with pytest.raises(RegraNegocioError):
        LivroRepository().excluir(livro.id)


def test_rotas(app, dados):
    c = app.test_client()
    for url in ["/", "/livros", "/leitores", "/emprestimos", "/livros/novo", "/emprestimos/novo"]:
        assert c.get(url).status_code == 200
    r = c.post("/livros/novo", data={"titulo": "Via Web", "autor": "Teste", "isbn": "9780000000002",
                                     "quantidade_total": "2"}, follow_redirects=True)
    assert "Via Web" in r.get_data(as_text=True)
    livro, leitor = dados
    r = c.post("/emprestimos/novo", data={"livro_id": livro.id, "leitor_id": leitor.id}, follow_redirects=True)
    assert "registrado com sucesso" in r.get_data(as_text=True)
