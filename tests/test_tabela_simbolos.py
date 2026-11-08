"""Testes da tabela de símbolos e da integração com os escopos semânticos."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from componente_tabela_simbolos import C_TabelaSimbolos, ITabelaSimbolos, Symbol
from analise import analisar


def test_duplicata_nao_substitui_declaracao_original():
    tabela = C_TabelaSimbolos()
    assert isinstance(tabela, ITabelaSimbolos)
    original = Symbol("x", "number")
    assert tabela.declarar(original, linha=2, coluna=5)
    assert not tabela.declarar(Symbol("x", "string"))
    assert tabela.consultar("x") is original
    assert len(tabela.listar_simbolos()) == 1
    assert tabela.consultar("ausente") is None
    assert tabela.localizar_escopo("ausente") is None


def test_sombreamento_restauracao_e_historico_de_escopos():
    tabela = C_TabelaSimbolos()
    externo = Symbol("x", "number")
    interno = Symbol("x", "string")
    tabela.declarar(externo)
    tabela.entrar_escopo()
    tabela.declarar(interno, linha=3, coluna=4, funcao="f", classe="C")
    assert tabela.consultar("x") is interno
    assert tabela.localizar_escopo("x") == 1
    tabela.sair_escopo()
    assert tabela.consultar("x") is externo
    assert tabela.localizar_escopo("x") == 0
    tabela.entrar_escopo()
    tabela.declarar(Symbol("y", "number"))
    registros = tabela.listar_simbolos()
    assert [r["escopo"] for r in registros] == [0, 1, 2]
    assert registros[1] == dict(nome="x", tipo="string", linha=3, coluna=4,
                                escopo=1, funcao="f", classe="C", parametros=[])
    tabela.sair_escopo()
    tabela.sair_escopo()
    assert tabela.profundidade == 1


def test_exportacao_nao_permite_alterar_historico_e_instancias_sao_independentes():
    tabela = C_TabelaSimbolos()
    tabela.declarar(Symbol("f", "FUNC", params=["x"]))
    copia = tabela.listar_simbolos()
    copia[0]["nome"] = "alterado"
    copia[0]["parametros"].append("y")
    assert tabela.listar_simbolos()[0]["nome"] == "f"
    assert tabela.listar_simbolos()[0]["parametros"] == ["x"]
    assert C_TabelaSimbolos().listar_simbolos() == []


def test_semantico_exporta_declaracoes_e_mantem_erro_de_duplicata():
    resultado = analisar("seq { number x = 1; number x = 2; }")
    assert resultado["semantica"]["sucesso"] is False
    assert any("ja declarada" in e["mensagem"] for e in resultado["erros"])
    assert len([s for s in resultado["simbolos"] if s["nome"] == "x"]) == 1
