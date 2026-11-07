"""Casos de integração das fases do front-end, sem compilar C++."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

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


@pytest.mark.parametrize(
    ("chamada", "mensagem"),
    [
        ("len()", "espera 1 argumento, recebeu 0"),
        ('len("a", "b")', "espera 1 argumento, recebeu 2"),
        ("len(42)", "requer string, lista ou matriz"),
        ("len(true)", "requer string, lista ou matriz"),
        ('len(len("abc"))', "requer string, lista ou matriz"),
    ],
)
def test_len_invalido_preserva_ast_e_impede_tac(chamada, mensagem):
    resultado = analisar(f"seq {{\n    print({chamada});\n}}")
    assert resultado["ast"] is not None
    assert resultado["semantica"]["sucesso"] is False
    assert resultado["tac"] == ""
    assert len(resultado["erros"]) == 1
    erro = resultado["erros"][0]
    assert erro["fase"] == "semantica"
    assert erro["linha"] == 2
    assert mensagem in erro["mensagem"]


@pytest.mark.parametrize("valor", ['"abc"', "[1, 2, 3]", "matrix(2, 3, 0)"])
def test_len_aceita_colecoes_suportadas(valor):
    resultado = analisar(f"seq {{ print(len({valor})); }}")
    assert resultado["erros"] == []
    assert resultado["semantica"]["sucesso"] is True
    assert "call len, 1" in resultado["tac"]


def test_len_em_parametro_com_tipo_inferido():
    resultado = analisar('func tamanho(valor) { return len(valor); } seq { print(tamanho("abc")); }')
    assert resultado["erros"] == []


def test_len_tambem_valida_identificadores_dos_argumentos():
    resultado = analisar("seq { print(len(inexistente)); }")
    assert resultado["semantica"]["sucesso"] is False
    assert any("nao declarada" in erro["mensagem"] for erro in resultado["erros"])


@pytest.mark.parametrize(
    "marcado",
    [
        "seq { print(§faltando); }",
        "seq { §faltando = 3; }",
        'seq { number §x = "abc"; }',
        "seq { var x = 1; var §x = 2; }",
        "func f(a, b) { return a + b; } seq { print(§f(1)); }",
        "seq { print(§len()); }",
        'seq { var x = "s" §* 2; }',
        "seq { §fork core(1.5) { print(1); } }",
        "seq { §join(1); }",
        "class C { var x = 1; } seq { var c = new C(); print(c.§y); }",
        "class C { func f(a) {} } seq { var c = new C(); c.§f(); }",
        "seq {\n    §break;\n}",
        "seq {\n\t§continue;\n}",
        "seq { var c = §new Desconhecida(); }",
        "func f(a,\n    §a) {}",
        "seq { var a = [1]; fork { a.§append(2); } join; }",
        'seq { var texto = "á"; print(§faltando); }',
    ],
)
def test_diagnostico_semantico_aponta_o_token_responsavel(marcado):
    antes, depois = marcado.split("§")
    codigo = antes + depois
    resultado = analisar(codigo)
    assert len(resultado["erros"]) == 1
    erro = resultado["erros"][0]
    assert erro["fase"] == "semantica"
    assert erro["linha"] == antes.count("\n") + 1
    assert erro["coluna"] == len(antes.rsplit("\n", 1)[-1]) + 1


def test_ast_e_simbolos_preservam_posicoes_de_declaracao():
    resultado = analisar("seq {\n    var x = 1;\n}")
    declaracao = resultado["ast"]["statements"][0]["statements"][0]
    assert (declaracao["line"], declaracao["col"]) == (2, 9)
    assert (declaracao["init_value"]["line"], declaracao["init_value"]["col"]) == (2, 13)
    assert (resultado["simbolos"][0]["linha"], resultado["simbolos"][0]["coluna"]) == (2, 9)


def test_ast_criada_sem_coluna_continua_aceita():
    from ast_nodes import IdentifierExpr, PrintStmt, Program
    from componente_semantico import C_Semantico

    programa = Program(statements=[PrintStmt(arguments=[IdentifierExpr("x", 4)])])
    resultado = C_Semantico().analise_semantica(programa)
    assert resultado.sucesso is False
    assert resultado.erros[0]["linha"] == 4
    assert resultado.erros[0]["coluna"] is None


def test_coluna_do_iterador_na_tabela_de_simbolos():
    codigo = "seq { for (var item in [1, 2]) { print(item); } }"
    resultado = analisar(codigo)
    simbolo = next(s for s in resultado["simbolos"] if s["nome"] == "item")
    assert simbolo["coluna"] == codigo.index("item") + 1


def test_terminal_exibe_linha_e_coluna_do_erro_semantico():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(dir=root) as folder:
        fonte = Path(folder) / "erro_semantico.minipar"
        fonte.write_text("seq {\n    print(faltando);\n}", encoding="utf-8")
        processo = subprocess.run(
            [sys.executable, str(root / "main.py"), str(fonte)],
            cwd=root, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=10,
        )
    assert processo.returncode == 1
    assert "[ERRO SEMANTICO] Linha 2, coluna 11" in processo.stderr
    assert "Traceback" not in processo.stderr
