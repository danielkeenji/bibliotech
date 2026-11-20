"""Popula o banco com dados de exemplo para demonstração."""
from datetime import date, timedelta

from app import create_app
from models import EmprestimoRepository, Leitor, LeitorRepository, Livro, LivroRepository

LIVROS = [
    Livro("Dom Casmurro", "Machado de Assis", "9788594318602", "Principis", 1899, 3),
    Livro("O Cortiço", "Aluísio Azevedo", "9788508133048", "Ática", 1890, 2),
    Livro("Engenharia de Software", "Ian Sommerville", "9788543024974", "Pearson", 2018, 2),
    Livro("Código Limpo", "Robert C. Martin", "9788576082675", "Alta Books", 2009, 1),
    Livro("UML Essencial", "Martin Fowler", "9788560031382", "Bookman", 2005, 2),
]
LEITORES = [
    Leitor("Ana Paula Ribeiro", "123.456.789-01", "ana.ribeiro@email.com", "(43) 99911-2233"),
    Leitor("Bruno Henrique Costa", "234.567.890-12", "bruno.costa@email.com", "(43) 99822-3344"),
    Leitor("Carla Souza Lima", "345.678.901-23", "carla.lima@email.com", ""),
]

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        livros, leitores, emp = LivroRepository(), LeitorRepository(), EmprestimoRepository()
        if livros.listar():
            print("Banco já possui dados; nada a fazer.")
        else:
            ids_l = [livros.salvar(l).id for l in LIVROS]
            ids_r = [leitores.salvar(r).id for r in LEITORES]
            hoje = date.today()
            emp.registrar(ids_l[0], ids_r[0], hoje - timedelta(days=3))
            emp.registrar(ids_l[2], ids_r[1], hoje - timedelta(days=20))   # em atraso
            e = emp.registrar(ids_l[4], ids_r[2], hoje - timedelta(days=10))
            emp.registrar_devolucao(e.id, hoje - timedelta(days=2))
            print("Dados de exemplo inseridos.")
