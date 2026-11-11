"""Interface e implementação do componente de geração de código C++."""
from abc import ABC, abstractmethod

from ast_nodes import Program
from codegen import CppCodeGenerator


# Separa a geração de texto C++ da etapa que invoca o compilador nativo.
class ICodegen(ABC):
    @abstractmethod
    def gerar_codigo(self, programa: Program, nome_saida: str) -> bool:
        """Transpila a AST para C++20, grava o arquivo .cpp e compila via GCC (-O3)."""

    @abstractmethod
    def gerar_texto(self, programa: Program) -> str:
        """Gera o código-fonte C++ correspondente em memória (string)."""


class C_Codegen(ICodegen):
    def __init__(self) -> None:
        self._gerador = CppCodeGenerator()

    def gerar_codigo(self, programa: Program, nome_saida: str) -> bool:
        return self._gerador.generate(programa, nome_saida)

    def gerar_texto(self, programa: Program) -> str:
        return self._gerador.generate_text(programa)
