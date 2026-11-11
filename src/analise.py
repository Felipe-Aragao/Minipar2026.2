"""Análise por fase para a interface Web didática."""
from __future__ import annotations

from componente_codegen import C_Codegen, ICodegen
from componente_lexico import C_Lexico, ILexico
from componente_otimizador import C_Otimizador, IOtimizador
from componente_semantico import C_Semantico, ISemantico
from componente_sintatico import C_Sintatico, ISintatico
from componente_tac import C_TAC, ITAC
from lexer import LexError, TokenType
from parser import ParseError


def analisar(codigo: str, otimizar: bool = False) -> dict:
    """Retorna dados JSON por fase; fases posteriores a um erro ficam vazias.

    ``semantica.sucesso`` é None enquanto a fase não foi executada. Posições
    são baseadas em 1; coluna None indica que o analisador não a conhece.
    Instâncias novas por chamada evitam mistura entre análises da Web.
    Quando ``otimizar=True``, aplica otimizações independentes de máquina na AST.
    """
    # A resposta conserva os artefatos das fases já concluídas quando uma fase posterior falha.
    resultado = {
        "tokens": [],
        "ast": None,
        "simbolos": [],
        "semantica": {"sucesso": None},
        "otimizacao": {
            "ativa": otimizar,
            "nos_antes": 0,
            "nos_depois": 0,
            "reducao_pct": 0.0,
            "transformacoes": [],
            "ast_original": None,
        },
        "tac": "",
        "cpp": "",
        "erros": [],
    }
    if not isinstance(codigo, str):
        raise TypeError("codigo deve ser uma string")

    fase = "lexica"
    try:
        lexico: ILexico = C_Lexico()
        tokens = lexico.analise_lexica(codigo)
        resultado["tokens"] = [
            {"tipo": t.type.name, "lexema": t.lexeme, "linha": t.line, "coluna": t.col}
            for t in tokens
        ]
        for token in tokens:
            if token.type == TokenType.UNKNOWN:
                resultado["erros"].append({
                    "fase": fase, "linha": token.line, "coluna": token.col,
                    "mensagem": f"Caractere nao reconhecido: {token.lexeme!r}"})
        if resultado["erros"]:
            return resultado

        fase = "sintatica"
        sintatico: ISintatico = C_Sintatico()
        programa = sintatico.analise_sintatica(tokens)
        resultado["ast"] = programa.to_dict()

        fase = "semantica"
        semantico: ISemantico = C_Semantico()
        validacao = semantico.analise_semantica(programa)
        resultado["semantica"]["sucesso"] = validacao.sucesso
        resultado["simbolos"] = validacao.simbolos
        resultado["erros"].extend(validacao.erros)
        if not validacao.sucesso:
            return resultado

        # A opção de otimização seleciona a AST usada tanto pelo TAC quanto pela geração de C++.
        programa_saida = programa
        if otimizar:
            fase = "otimizacao"
            resultado["otimizacao"]["ast_original"] = programa.to_dict()
            otimizador: IOtimizador = C_Otimizador()
            res_opt = otimizador.otimizar(programa)
            programa_saida = res_opt.programa_otimizado
            reducao = 0.0
            if res_opt.nos_antes > 0:
                reducao = round((1.0 - (res_opt.nos_depois / res_opt.nos_antes)) * 100.0, 1)
            resultado["otimizacao"].update({
                "ativa": True,
                "nos_antes": res_opt.nos_antes,
                "nos_depois": res_opt.nos_depois,
                "reducao_pct": reducao,
                "transformacoes": res_opt.transformacoes,
            })
            resultado["ast"] = programa_saida.to_dict()

        fase = "tac"
        gerador: ITAC = C_TAC()
        resultado["tac"] = gerador.gerar_texto(programa_saida)

        fase = "codegen"
        try:
            codegen: ICodegen = C_Codegen()
            resultado["cpp"] = codegen.gerar_texto(programa_saida)
        except Exception as erro:
            resultado["erros"].append({"fase": fase, "linha": None,
                                        "coluna": None, "mensagem": str(erro) or "Falha na geracao C++."})
    except (LexError, ParseError) as erro:
        resultado["erros"].append({"fase": fase, "linha": erro.line,
                                    "coluna": erro.col, "mensagem": str(erro)})
    except NotImplementedError as erro:
        resultado["erros"].append({"fase": fase, "linha": None,
                                    "coluna": None, "mensagem": str(erro) or "Recurso ainda nao implementado."})
    return resultado
