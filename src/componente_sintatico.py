"""Contrato do componente que transforma tokens em AST."""
from abc import ABC, abstractmethod

from ast_nodes import Program
from lexer import Token
from parser import Parser


class ISintatico(ABC):
    @abstractmethod
    def analise_sintatica(self, tokens: list[Token]) -> Program:
        """Recebe tokens com marcador de fim e levanta ParseError em caso de erro."""


class C_Sintatico(ISintatico):
    def analise_sintatica(self, tokens: list[Token]) -> Program:
        return Parser(tokens, raise_errors=True).parse()
