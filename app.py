"""BiblioTech - Sistema de Gerenciamento de Biblioteca (Flask + SQLite)."""
import os
from datetime import date
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, url_for

import database
from models import (EmprestimoRepository, Leitor, LeitorRepository, Livro, LivroRepository,
                    RegraNegocioError)


def _int_ou_none(valor: str):
    valor = (valor or "").strip()
    return int(valor) if valor.isdigit() else None


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-bibliotech"),
        DATABASE=os.environ.get("DATABASE", str(Path(app.root_path) / "bibliotech.db")),
    )
    if config:
        app.config.update(config)
    database.init_app(app)

    livros, leitores, emprestimos = LivroRepository(), LeitorRepository(), EmprestimoRepository()

    @app.template_filter("data_br")
    def data_br(d):
        return d.strftime("%d/%m/%Y") if d else "—"

    # ------------------------------------------------------------------ início
    @app.route("/")
    def index():
        return render_template("index.html", resumo=emprestimos.resumo(),
                               total_livros=len(livros.listar()), total_leitores=len(leitores.listar()),
                               atrasados=emprestimos.listar("atrasados"))

    # ------------------------------------------------------------------ UC01 livros
    @app.route("/livros")
    def livros_listar():
        busca = request.args.get("q", "")
        return render_template("livros/lista.html", livros=livros.listar(busca), busca=busca)

    @app.route("/livros/novo", methods=["GET", "POST"])
    @app.route("/livros/<int:livro_id>/editar", methods=["GET", "POST"])
    def livros_form(livro_id=None):
        livro = livros.buscar_por_id(livro_id) if livro_id else Livro("", "", "")
        if livro is None:
            abort(404)
        if request.method == "POST":
            f = request.form
            livro.titulo, livro.autor, livro.isbn = f["titulo"], f["autor"], f["isbn"]
            livro.editora = f.get("editora", "")
            livro.ano_publicacao = _int_ou_none(f.get("ano_publicacao"))
            livro.quantidade_total = _int_ou_none(f.get("quantidade_total")) or 0
            try:
                livros.salvar(livro)
                flash("Livro salvo com sucesso.", "sucesso")
                return redirect(url_for("livros_listar"))
            except RegraNegocioError as e:
                flash(str(e), "erro")
        return render_template("livros/form.html", livro=livro)

    @app.post("/livros/<int:livro_id>/excluir")
    def livros_excluir(livro_id):
        try:
            livros.excluir(livro_id)
            flash("Livro excluído.", "sucesso")
        except RegraNegocioError as e:
            flash(str(e), "erro")
        return redirect(url_for("livros_listar"))

    # ------------------------------------------------------------------ UC02 leitores
    @app.route("/leitores")
    def leitores_listar():
        busca = request.args.get("q", "")
        return render_template("leitores/lista.html", leitores=leitores.listar(busca), busca=busca)

    @app.route("/leitores/novo", methods=["GET", "POST"])
    @app.route("/leitores/<int:leitor_id>/editar", methods=["GET", "POST"])
    def leitores_form(leitor_id=None):
        leitor = leitores.buscar_por_id(leitor_id) if leitor_id else Leitor("", "", "")
        if leitor is None:
            abort(404)
        if request.method == "POST":
            f = request.form
            leitor.nome, leitor.cpf, leitor.email = f["nome"], f["cpf"], f["email"]
            leitor.telefone = f.get("telefone", "")
            try:
                leitores.salvar(leitor)
                flash("Leitor salvo com sucesso.", "sucesso")
                return redirect(url_for("leitores_listar"))
            except RegraNegocioError as e:
                flash(str(e), "erro")
        return render_template("leitores/form.html", leitor=leitor)

    @app.post("/leitores/<int:leitor_id>/excluir")
    def leitores_excluir(leitor_id):
        try:
            leitores.excluir(leitor_id)
            flash("Leitor excluído.", "sucesso")
        except RegraNegocioError as e:
            flash(str(e), "erro")
        return redirect(url_for("leitores_listar"))

    # ------------------------------------------------------------------ UC03/UC05 empréstimos
    @app.route("/emprestimos")
    def emprestimos_listar():
        filtro = request.args.get("filtro", "todos")
        busca = request.args.get("q", "")
        return render_template("emprestimos/lista.html", emprestimos=emprestimos.listar(filtro, busca),
                               filtro=filtro, busca=busca)

    @app.route("/emprestimos/novo", methods=["GET", "POST"])
    def emprestimos_novo():
        if request.method == "POST":
            try:
                emprestimos.registrar(_int_ou_none(request.form.get("livro_id")),
                                      _int_ou_none(request.form.get("leitor_id")))
                flash("Empréstimo registrado com sucesso.", "sucesso")
                return redirect(url_for("emprestimos_listar"))
            except RegraNegocioError as e:
                flash(str(e), "erro")
        return render_template("emprestimos/form.html",
                               livros=[l for l in livros.listar() if l.esta_disponivel()],
                               leitores=leitores.listar())

    @app.route("/emprestimos/<int:emprestimo_id>/editar", methods=["GET", "POST"])
    def emprestimos_editar(emprestimo_id):
        emp = emprestimos.buscar_por_id(emprestimo_id) or abort(404)
        if request.method == "POST":
            try:
                emprestimos.atualizar_prazo(emprestimo_id,
                                            date.fromisoformat(request.form["data_prevista_devolucao"]))
                flash("Prazo atualizado.", "sucesso")
                return redirect(url_for("emprestimos_listar"))
            except (RegraNegocioError, ValueError) as e:
                flash(str(e), "erro")
        return render_template("emprestimos/editar.html", emp=emp)

    # ------------------------------------------------------------------ UC04 devolução
    @app.post("/emprestimos/<int:emprestimo_id>/devolver")
    def emprestimos_devolver(emprestimo_id):
        try:
            emp = emprestimos.registrar_devolucao(emprestimo_id)
            atraso = emp.dias_atraso()
            msg = "Devolução registrada."
            if atraso:
                msg += f" Atenção: devolvido com {atraso} dia(s) de atraso."
            flash(msg, "sucesso")
        except RegraNegocioError as e:
            flash(str(e), "erro")
        return redirect(url_for("emprestimos_listar"))

    @app.post("/emprestimos/<int:emprestimo_id>/excluir")
    def emprestimos_excluir(emprestimo_id):
        emprestimos.excluir(emprestimo_id)
        flash("Registro de empréstimo excluído.", "sucesso")
        return redirect(url_for("emprestimos_listar"))

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
