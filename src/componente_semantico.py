"""Contrato do componente que valida uma AST e expõe símbolos e diagnósticos."""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ast_nodes import Program
from semantic import SemanticAnalyzer


@dataclass
class ResultadoSemantico:
    sucesso: bool
    simbolos: list[dict]
    erros: list[dict]


class ISemantico(ABC):
    @abstractmethod
    def analise_semantica(self, programa: Program) -> ResultadoSemantico:
        """Valida o programa e retorna os dados da análise."""


class C_Semantico(ISemantico):
    def __init__(self, *, emitir_diagnosticos: bool = False) -> None:
        self._emitir_diagnosticos = emitir_diagnosticos

    def analise_semantica(self, programa: Program) -> ResultadoSemantico:
        analisador = SemanticAnalyzer(emit_diagnostics=self._emitir_diagnosticos)
        sucesso = analisador.analyze(programa)
        return ResultadoSemantico(sucesso, analisador.symbols, analisador.errors)
