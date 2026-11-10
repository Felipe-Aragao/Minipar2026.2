"""Regressões do isolamento e dos escopos de tarefas em blocos par."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analise import analisar


@pytest.mark.parametrize(
    ("declaracao", "escrita"),
    [
        ("var x = 0;", "x = 1;"),
        ("var x = [0];", "x[0] = 1;"),
        ("var x = [0];", "x.append(1);"),
        ("var x = matrix(1, 1, 0);", "x[0][0] = 1;"),
        ("var x = new C();", "x.valor = 1;"),
    ],
)
def test_par_rejeita_escrita_externa_com_posicao(declaracao, escrita):
    codigo = f"class C {{ var valor = 0; }} seq {{ {declaracao}\npar {{ seq {{ {escrita} }} }} }}"
    resultado = analisar(codigo)
    assert resultado["semantica"]["sucesso"] is False
    assert resultado["tac"] == ""
    assert len(resultado["erros"]) == 1
    erro = resultado["erros"][0]
    assert "Isolamento" in erro["mensagem"] and "um par" in erro["mensagem"]
    assert erro["linha"] == 2 and erro["coluna"] is not None


@pytest.mark.parametrize("codigo", [
    "seq { var x = 0; par { seq { var x = 1; x = 2; } seq { print(x); } } x = 3; }",
    "par { seq { var x = 1; x = 2; } seq { var x = 3; x = 4; } }",
    "seq { fork { var x = 1; par { seq { print(x); } } x = 2; } join; }",
])
def test_par_preserva_locais_leituras_e_contexto_externo(codigo):
    assert analisar(codigo)["erros"] == []


def test_declaracao_de_uma_tarefa_nao_vaza_para_a_irma():
    resultado = analisar("par { var x = 1; print(x); }")
    assert any("'x' nao declarada" in e["mensagem"] for e in resultado["erros"])


@pytest.mark.parametrize("tarefas", [
    "par { seq { x = 1; } }",
    "fork { x = 1; } join;",
])
def test_tarefa_filha_nao_escreve_em_local_da_tarefa_pai(tarefas):
    resultado = analisar(f"par {{ seq {{ var x = 0; {tarefas} }} }}")
    assert any("Isolamento" in e["mensagem"] for e in resultado["erros"])


def test_fork_aninhado_nao_remove_isolamento_do_par():
    resultado = analisar("seq { var x = 0; par { seq { fork { print(x); } join; x = 1; } } }")
    assert len(resultado["erros"]) == 1
    assert "um par" in resultado["erros"][0]["mensagem"]


@pytest.mark.parametrize('declaracao,uso', [
    ('var c = new C();', 'c.mudar();'),
    ('var c = new C(); var alias = c;', 'alias.mudar();'),
    ('var cs = [new C()];', 'cs[0].mudar();'),
    ('var cs = [new C()]; var alias = cs;', 'alias[0].mudar();'),
    ('var c = new C();', 'usar(c);'),
])
@pytest.mark.parametrize('tarefa', ['par { seq { USO } }', 'fork { USO } join;'])
def test_tarefa_rejeita_captura_de_objetos_externos(declaracao, uso, tarefa):
    codigo = ('class C { var valor = 0; func mudar() { this.valor = 7; } } '
              'func usar(c) { c.mudar(); } seq { ' + declaracao + tarefa.replace('USO', uso) + ' }')
    resultado = analisar(codigo)
    assert resultado['semantica']['sucesso'] is False
    assert any('Objeto externo' in e['mensagem'] for e in resultado['erros'])
    assert resultado['cpp'] == ''


def test_objeto_criado_na_propria_tarefa_continua_permitido():
    codigo = ('class C { var valor = 0; func mudar() { this.valor = 7; } } '
              'par { seq { var c = new C(); c.mudar(); print(c.valor); } }')
    assert analisar(codigo)['erros'] == []


def test_iterador_de_colecao_de_objetos_nao_pode_ser_capturado():
    codigo = ('class C { var valor = 0; func mudar() { this.valor = 7; } } '
              'seq { var cs = [new C()]; for (var c in cs) { '
              'fork { c.mudar(); } join; } }')
    resultado = analisar(codigo)
    assert any('Objeto externo' in e['mensagem'] for e in resultado['erros'])
