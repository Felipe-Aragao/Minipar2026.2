"""Interface e componente para otimização independente de máquina na AST."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import NamedTuple

from ast_nodes import Program


class ResultadoOtimizacao(NamedTuple):
    """Métricas e resultado da etapa de otimização independente."""
    programa_otimizado: Program
    nos_antes: int
    nos_depois: int
    transformacoes: list[str]


class IOtimizador(ABC):
    """Interface abstrata para otimizadores independentes de máquina."""

    @abstractmethod
    def otimizar(self, programa: Program) -> ResultadoOtimizacao:
        """Aplica transformações na AST e retorna o programa otimizado e métricas."""


class C_Otimizador(IOtimizador):
    """Componente concreto que orquestra as transformações do motor de otimização."""

    def otimizar(self, programa: Program) -> ResultadoOtimizacao:
        from optimizer import ASTOptimizer
        return ASTOptimizer().optimize(programa)
