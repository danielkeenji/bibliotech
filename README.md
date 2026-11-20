# 📚 BiblioTech — Sistema Web de Gerenciamento de Biblioteca

Projeto das disciplinas **Projeto de Desenvolvimento de Software I e II** — Centro Universitário Filadélfia (UniFil).

**Autor:** Daniel Kenji Henrique (trabalho individual) — Engenharia de Software

O BiblioTech permite ao bibliotecário gerenciar o acervo de uma biblioteca: cadastro de livros e leitores, registro de empréstimos e devoluções e acompanhamento dos empréstimos em atraso.

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.10+ |
| Framework web | Flask 3 |
| Interface | HTML5, CSS3, Jinja2 |
| Banco de dados | SQLite 3 (relacional) |
| Testes | pytest |
| Diagramas | PlantUML |

## Funcionalidades (casos de uso)

| Caso de uso | CRUD |
|---|---|
| UC01 — Gerenciar Livros | Create, Read, Update, Delete |
| UC02 — Gerenciar Leitores | Create, Read, Update, Delete |
| UC03 — Registrar Empréstimo | Create |
| UC04 — Registrar Devolução | Update |
| UC05 — Consultar Empréstimos | Read, Update (prazo), Delete |

**Regras de negócio:** prazo de 14 dias; até 3 empréstimos ativos por leitor; leitor com atraso fica bloqueado; só empresta livro com exemplar disponível; livros e leitores com empréstimos não podem ser excluídos.

## Como executar

```bash
git clone https://github.com/danielkeenji/bibliotech.git
cd bibliotech
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python seed.py        # (opcional) dados de exemplo
python app.py         # abre em http://127.0.0.1:5000
```

O banco `bibliotech.db` é criado automaticamente na primeira execução.

## Testes

```bash
pytest
```

## Estrutura

```
app.py            # aplicação Flask e rotas (controladores)
models.py         # entidades, regras de negócio e repositórios (CRUD)
database.py       # conexão com o SQLite
schema.sql        # criação das tabelas
seed.py           # dados de exemplo
templates/        # páginas HTML (Jinja2)
static/           # CSS
tests/            # testes automatizados
docs/             # documentação (PDF) e diagramas (PlantUML + PNG)
```

## Documentação

A documentação completa (requisitos, casos de uso, DER, diagramas de atividade, classes e sequência) está em [`docs/BiblioTech_Documentacao.pdf`](docs/BiblioTech_Documentacao.pdf).
