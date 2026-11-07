"""Contrato de análise para a Web didática, sem arquivos, GCC ou execução.
"""
from lexer import Lexer, LexError, TokenType
from parser import Parser, ParseError
from semantic import SemanticAnalyzer
from tac import TACGenerator
from codegen import CppCodeGenerator


def analisar(codigo: str) -> dict:
    """Retorna dados JSON por fase; fases posteriores a um erro ficam vazias.

    ``semantica.sucesso`` é None enquanto a fase não foi executada. Posições
    são baseadas em 1; coluna None indica que o analisador não a conhece.
    Instâncias novas por chamada evitam mistura entre análises da Web.
    """
    resultado = {"tokens": [], "ast": None, "simbolos": [],
                 "semantica": {"sucesso": None}, "tac": "", "cpp": "", "erros": []}
    if not isinstance(codigo, str):
        raise TypeError("codigo deve ser uma string")

    fase = "lexica"
    try:
        tokens = Lexer(codigo).tokenize()
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
        programa = Parser(tokens, raise_errors=True).parse()
        resultado["ast"] = programa.to_dict()

        fase = "semantica"
        semantico = SemanticAnalyzer(emit_diagnostics=False)
        sucesso = semantico.analyze(programa)
        resultado["semantica"]["sucesso"] = sucesso
        resultado["simbolos"] = semantico.symbols
        resultado["erros"].extend(semantico.errors)
        if not sucesso:
            return resultado

        fase = "tac"
        resultado["tac"] = TACGenerator().generate_text(programa)

        fase = "codegen"
        try:
            resultado["cpp"] = CppCodeGenerator().to_cpp(programa)
        except Exception as erro:
            resultado["cpp"] = f"// Erro ao gerar C++: {erro}"
    except (LexError, ParseError) as erro:
        resultado["erros"].append({"fase": fase, "linha": erro.line,
                                    "coluna": erro.col, "mensagem": str(erro)})
    except NotImplementedError as erro:
        resultado["erros"].append({"fase": fase, "linha": None,
                                    "coluna": None, "mensagem": str(erro) or "Recurso ainda nao implementado."})
    return resultado
