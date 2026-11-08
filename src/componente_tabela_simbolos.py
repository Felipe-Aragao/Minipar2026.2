"""Gerenciamento da tabela de símbolos e dos escopos léxicos."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Symbol:
    name: str
    type: str
    params: List[str] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)
    methods: Dict[str, List[str]] = field(default_factory=dict)


class ITabelaSimbolos(ABC):
    @property
    @abstractmethod
    def profundidade(self) -> int:
        """Quantidade de escopos ativos, incluindo o global."""

    @abstractmethod
    def entrar_escopo(self) -> None: ...

    @abstractmethod
    def sair_escopo(self) -> None: ...

    @abstractmethod
    def declarar(self, simbolo: Symbol, *, linha: Optional[int] = None,
                 coluna: Optional[int] = None, funcao: Optional[str] = None,
                 classe: Optional[str] = None) -> bool:
        """Retorna False se o nome já existir no escopo atual, sem substituí-lo."""

    @abstractmethod
    def consultar(self, nome: str) -> Optional[Symbol]: ...

    @abstractmethod
    def localizar_escopo(self, nome: str) -> Optional[int]:
        """Índice do escopo ativo da declaração mais próxima; global = 0."""

    @abstractmethod
    def listar_simbolos(self) -> List[dict]:
        """Histórico das declarações, inclusive de escopos já encerrados."""


class C_TabelaSimbolos(ITabelaSimbolos):
    def __init__(self) -> None:
        self._escopos: List[Dict[str, Symbol]] = [{}]
        self._ids = [0]
        self._proximo_id = 1
        self._registros: List[dict] = []

    @property
    def profundidade(self) -> int:
        return len(self._escopos)

    def entrar_escopo(self) -> None:
        self._escopos.append({})
        self._ids.append(self._proximo_id)
        self._proximo_id += 1

    def sair_escopo(self) -> None:
        if self.profundidade > 1:
            self._escopos.pop()
            self._ids.pop()

    def declarar(self, simbolo: Symbol, *, linha: Optional[int] = None,
                 coluna: Optional[int] = None, funcao: Optional[str] = None,
                 classe: Optional[str] = None) -> bool:
        if simbolo.name in self._escopos[-1]:
            return False
        self._escopos[-1][simbolo.name] = simbolo
        self._registros.append({
            "nome": simbolo.name, "tipo": simbolo.type, "linha": linha,
            "coluna": coluna, "escopo": self._ids[-1], "funcao": funcao,
            "classe": classe, "parametros": list(simbolo.params),
        })
        return True

    def consultar(self, nome: str) -> Optional[Symbol]:
        indice = self.localizar_escopo(nome)
        return self._escopos[indice][nome] if indice is not None else None

    def localizar_escopo(self, nome: str) -> Optional[int]:
        for indice in range(self.profundidade - 1, -1, -1):
            if nome in self._escopos[indice]:
                return indice
        return None

    def listar_simbolos(self) -> List[dict]:
        return [dict(registro, parametros=list(registro["parametros"]))
                for registro in self._registros]
