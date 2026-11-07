"""Interface e implementação do componente de análise léxica."""
from abc import ABC, abstractmethod

from lexer import Lexer, Token


class ILexico(ABC):
    @abstractmethod
    def analise_lexica(self, codigo: str) -> list[Token]:
        """Retorna os tokens em ordem, incluindo o marcador de fim do arquivo.

        Caracteres desconhecidos geram tokens UNKNOWN. Uma string não terminada
        gera LexError com linha e coluna.
        """


class C_Lexico(ILexico):
    def analise_lexica(self, codigo: str) -> list[Token]:
        return Lexer(codigo).tokenize()
