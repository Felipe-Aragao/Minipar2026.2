"""Casos de integração das fases do front-end, sem compilar C++."""
from pathlib import Path
import re
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analise import analisar
from componente_lexico import C_Lexico
from lexer import TokenType


def test_lexico_preserva_posicoes_e_reinicia_entre_chamadas():
    lexico = C_Lexico()
    tokens = lexico.analise_lexica("# comentario\n  fork")
    assert [(t.type, t.lexeme, t.line, t.col) for t in tokens] == [
        (TokenType.FORK, "fork", 2, 3),
        (TokenType.END_OF_FILE, "", 2, 7),
    ]
    novo = lexico.analise_lexica("join")[0]
    assert (novo.type, novo.line, novo.col) == (TokenType.JOIN, 1, 1)


@pytest.mark.parametrize(
    ("declaracao", "destino", "tipo", "tac_destino"),
    [
        ("", "", None, ""),
        ("", "core(2)", "core", ", core 2"),
        ("", 'host("127.0.0.1", 5100)', "host", ', host "127.0.0.1", 5100'),
        ('var canal = c_channel("127.0.0.1", 5100);', "host(canal)", "host", ", host canal"),
    ],
)
def test_fork_e_join_geram_ast_e_tac(declaracao, destino, tipo, tac_destino):
    resultado = analisar(f"seq {{ {declaracao} fork {destino} {{ print(7); }} join; }}")
    assert resultado["erros"] == []
    fork, join = resultado["ast"]["statements"][0]["statements"][-2:]
    assert fork["node_type"] == "ForkStmt"
    if tipo is None:
        assert fork["destino"] is None
    else:
        assert fork["destino"]["tipo"] == tipo
    assert join["node_type"] == "JoinStmt"
    assert join["args"] == []

    linhas = resultado["tac"].splitlines()[-7:]
    inicio = re.fullmatch(r"FORK (\w+)" + re.escape(tac_destino), linhas[0])
    assert inicio
    salto = re.fullmatch(r"goto (\w+)", linhas[1])
    assert salto
    assert linhas[2:] == [inicio[1] + ":", "print 7", "END_TASK", salto[1] + ":", "JOIN ALL"]


def test_fork_com_expressao_mantem_o_resultado_da_subtarefa_no_tac():
    resultado = analisar("seq { task t = fork core(0) 2 * 3; var valor = join(t); }")
    assert resultado["erros"] == []
    tac = resultado["tac"]
    assert re.search(r"(?m)^(\w+) = 2 \* 3\nEND_TASK \1$", tac)
    assert re.search(r"(?m)^(\w+) = JOIN t\nvalor = \1$", tac)


@pytest.mark.parametrize(
    ("codigo", "fase"),
    [
        ("seq { fork core() { print(7); } }", "sintatica"),
        ("seq { fork core(0) { print(7); } join(1); }", "semantica"),
        ("seq { fork host(123) { print(7); } }", "semantica"),
        ('seq { fork host("localhost", "porta") { print(7); } }', "semantica"),
        ("seq { fork core(1.5) { print(7); } }", "semantica"),
        ("seq { var n = 0; fork { n = 1; } join; }", "semantica"),
    ],
)
def test_fork_ou_join_invalido_impede_geracao_de_tac(codigo, fase):
    resultado = analisar(codigo)
    assert resultado["erros"][0]["fase"] == fase
    assert resultado["tac"] == ""
    assert (resultado["ast"] is None) == (fase == "sintatica")
