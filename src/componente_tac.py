"""Geração de código intermediário de três endereços."""
from abc import ABC, abstractmethod

from ast_nodes import Program
from tac import TACGenerator


# Expõe o TAC em memória para a Web e em arquivo para a CLI e o executor de testes.
class ITAC(ABC):
    @abstractmethod
    def gerar_texto(self, programa: Program) -> str:
        """Gera o TAC em memória a partir de um programa validado."""

    @abstractmethod
    def gerar_arquivo(self, programa: Program, nome_saida: str) -> str:
        """Grava o TAC e devolve o caminho do arquivo."""


class C_TAC(ITAC):
    def gerar_texto(self, programa: Program) -> str:
        return TACGenerator().generate_text(programa)

    def gerar_arquivo(self, programa: Program, nome_saida: str) -> str:
        return TACGenerator().generate(programa, nome_saida)
