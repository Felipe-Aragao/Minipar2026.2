from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

class ASTNode:
    line: int = 1
    col: Optional[int] = None

    def to_dict(self) -> dict:
        """Serializa o nó da AST e todos os seus filhos para JSON (Dicionário)."""
        result = {"node_type": self.__class__.__name__, "line": self.line, "col": self.col}
        for key, value in vars(self).items():
            if key in ("line", "col"):
                continue
            if isinstance(value, ASTNode):
                result[key] = value.to_dict()
            elif isinstance(value, list):
                result[key] = [v.to_dict() if isinstance(v, ASTNode) else v for v in value]
            else:
                result[key] = value
        return result


@dataclass
class Destino(ASTNode):
    tipo: str  # "core" ou "host"
    args: List[ASTNode]
    line: int = 1
    col: Optional[int] = None

@dataclass
class ForkStmt(ASTNode):
    destino: Destino
    body: ASTNode
    line: int = 1
    col: Optional[int] = None

@dataclass
class JoinStmt(ASTNode):
    args: List[ASTNode] = field(default_factory=list)
    line: int = 1
    col: Optional[int] = None


@dataclass
class NumberExpr(ASTNode):
    value: str
    line: int = 1
    col: Optional[int] = None

@dataclass
class StringExpr(ASTNode):
    value: str
    line: int = 1
    col: Optional[int] = None

@dataclass
class BoolExpr(ASTNode):
    value: bool
    line: int = 1
    col: Optional[int] = None

@dataclass
class IdentifierExpr(ASTNode):
    name: str
    line: int = 1
    col: Optional[int] = None

@dataclass
class BinaryExpr(ASTNode):
    op: str
    left: ASTNode
    right: ASTNode
    line: int = 1
    col: Optional[int] = None

@dataclass
class UnaryExpr(ASTNode):
    op: str
    operand: ASTNode
    line: int = 1
    col: Optional[int] = None

@dataclass
class VarDecl(ASTNode):
    name: str
    init_value: Optional[ASTNode] = None
    type: str = "var"
    line: int = 1
    col: Optional[int] = None

@dataclass
class Assignment(ASTNode):
    name: str
    value: ASTNode = None
    line: int = 1
    col: Optional[int] = None

@dataclass
class PrintStmt(ASTNode):
    arguments: List[ASTNode] = field(default_factory=list)
    line: int = 1
    col: Optional[int] = None

@dataclass
class SeqBlock(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)
    line: int = 1
    col: Optional[int] = None

@dataclass
class ParBlock(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)
    line: int = 1
    col: Optional[int] = None

@dataclass
class IfStmt(ASTNode):
    condition: ASTNode
    then_branch: ASTNode
    else_branch: Optional[ASTNode] = None
    line: int = 1
    col: Optional[int] = None

@dataclass
class WhileStmt(ASTNode):
    condition: ASTNode
    body: ASTNode
    line: int = 1
    col: Optional[int] = None

@dataclass
class DoWhileStmt(ASTNode):
    body: ASTNode
    condition: ASTNode
    line: int = 1
    col: Optional[int] = None

@dataclass
class ForStmt(ASTNode):
    initializer: Optional[ASTNode]
    condition: Optional[ASTNode]
    increment: Optional[ASTNode]
    body: ASTNode
    iterator_name: Optional[str] = None
    iterable: Optional[ASTNode] = None
    line: int = 1
    col: Optional[int] = None
    iterator_location: Optional[dict] = None

@dataclass
class BreakStmt(ASTNode):
    line: int = 1
    col: Optional[int] = None

@dataclass
class ContinueStmt(ASTNode):
    line: int = 1
    col: Optional[int] = None

@dataclass
class ClassDecl(ASTNode):
    name: str
    superclass: Optional[str]
    attributes: List[VarDecl]
    methods: List[FuncDecl]
    line: int = 1
    col: Optional[int] = None

@dataclass
class FuncDecl(ASTNode):
    name: str
    params: List[str]
    body: ASTNode
    line: int = 1
    col: Optional[int] = None
    param_locations: List[dict] = field(default_factory=list)

@dataclass
class ReturnStmt(ASTNode):
    value: Optional[ASTNode]
    line: int = 1
    col: Optional[int] = None

@dataclass
class MethodCall(ASTNode):
    object: ASTNode
    method_name: str
    arguments: List[ASTNode]
    line: int = 1
    col: Optional[int] = None

@dataclass
class FuncCallExpr(ASTNode):
    name: str
    arguments: List[ASTNode]
    line: int = 1
    col: Optional[int] = None

@dataclass
class PropertyAccess(ASTNode):
    object: ASTNode
    property_name: str
    line: int = 1
    col: Optional[int] = None

@dataclass
class PropertyAssign(ASTNode):
    object: ASTNode
    property_name: str
    value: ASTNode
    line: int = 1
    col: Optional[int] = None

@dataclass
class NewExpr(ASTNode):
    class_name: str
    arguments: List[ASTNode]
    line: int = 1
    col: Optional[int] = None

@dataclass
class ThisExpr(ASTNode):
    line: int = 1
    col: Optional[int] = None

@dataclass
class CChannelExpr(ASTNode):
    ip: ASTNode
    port: ASTNode
    line: int = 1
    col: Optional[int] = None

@dataclass
class SendStmt(ASTNode):
    channel: ASTNode
    message: ASTNode
    line: int = 1
    col: Optional[int] = None

@dataclass
class ReceiveExpr(ASTNode):
    channel: ASTNode
    line: int = 1
    col: Optional[int] = None

@dataclass
class InputExpr(ASTNode):
    prompt: Optional[ASTNode] = None
    line: int = 1
    col: Optional[int] = None

@dataclass
class ListLiteral(ASTNode):
    elements: List[ASTNode]
    line: int = 1
    col: Optional[int] = None

@dataclass
class MatrixCreateExpr(ASTNode):
    rows: ASTNode
    cols: ASTNode
    init_value: ASTNode
    line: int = 1
    col: Optional[int] = None

@dataclass
class IndexExpr(ASTNode):
    object: ASTNode
    index: ASTNode
    line: int = 1
    col: Optional[int] = None

@dataclass
class IndexAssign(ASTNode):
    target: ASTNode
    value: ASTNode
    line: int = 1
    col: Optional[int] = None

@dataclass
class Program(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)
    line: int = 1
    col: Optional[int] = None
