"""Motor de otimização independente de máquina para a AST da linguagem MiniPar."""
from __future__ import annotations

import copy
import math
from decimal import Decimal
from typing import Any, List, Optional

from ast_nodes import (
    ASTNode, Assignment, BinaryExpr, BoolExpr, BreakStmt, CChannelExpr, ClassDecl,
    ContinueStmt, DoWhileStmt, ForStmt, ForkStmt, FuncCallExpr, FuncDecl, IdentifierExpr,
    IfStmt, IndexAssign, IndexExpr, InputExpr, JoinStmt, ListLiteral, MatrixCreateExpr,
    MethodCall, NewExpr, NumberExpr, ParBlock, PrintStmt, Program, PropertyAccess,
    PropertyAssign, ReceiveExpr, ReturnStmt, SendStmt, SeqBlock, StringExpr, ThisExpr,
    UnaryExpr, VarDecl, WhileStmt
)
from componente_otimizador import ResultadoOtimizacao


class ASTOptimizer:
    """Aplica otimizações estáticas na AST sem alterar a semântica do programa."""

    def __init__(self) -> None:
        self.transformacoes: list[str] = []

    def count_nodes(self, node: Optional[ASTNode]) -> int:
        """Conta recursivamente o número total de nós AST presentes na árvore."""
        if node is None or not isinstance(node, ASTNode):
            return 0
        total = 1
        for _, val in vars(node).items():
            if isinstance(val, ASTNode):
                total += self.count_nodes(val)
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, ASTNode):
                        total += self.count_nodes(item)
        return total

    def is_pure(self, node: Optional[ASTNode]) -> bool:
        """Verifica se uma subexpressão não possui efeitos colaterais conhecidos."""
        if node is None:
            return True
        if isinstance(node, (NumberExpr, StringExpr, BoolExpr, IdentifierExpr, ThisExpr)):
            return True
        if isinstance(node, UnaryExpr):
            return self.is_pure(node.operand)
        if isinstance(node, BinaryExpr):
            return self.is_pure(node.left) and self.is_pure(node.right)
        if isinstance(node, ListLiteral):
            return all(self.is_pure(el) for el in node.elements)
        if isinstance(node, IndexExpr):
            return self.is_pure(node.object) and self.is_pure(node.index)
        if isinstance(node, PropertyAccess):
            return self.is_pure(node.object)
        return False

    def _contains_value_return(self, node: ASTNode) -> bool:
        if isinstance(node, ReturnStmt) and node.value is not None:
            return True
        for value in vars(node).values():
            children = value if isinstance(value, list) else [value]
            if any(isinstance(child, ASTNode) and self._contains_value_return(child) for child in children):
                return True
        return False

    def optimize(self, program: Program) -> ResultadoOtimizacao:
        """Executa passadas de otimização até atingir ponto fixo ou limite máximo."""
        self.transformacoes = []
        prog_copia = copy.deepcopy(program)
        total_antes = self.count_nodes(prog_copia)

        limite_passadas = 10
        for _ in range(limite_passadas):
            qtd_antes = len(self.transformacoes)
            prog_copia = self._transform_node(prog_copia)
            if len(self.transformacoes) == qtd_antes:
                break

        total_depois = self.count_nodes(prog_copia)
        return ResultadoOtimizacao(
            programa_otimizado=prog_copia,
            nos_antes=total_antes,
            nos_depois=total_depois,
            transformacoes=list(self.transformacoes),
        )

    # -------------------------------------------------------------------------
    # Travessia e Transformação
    # -------------------------------------------------------------------------
    def _transform_statements(self, statements: List[ASTNode]) -> List[ASTNode]:
        novos: List[ASTNode] = []
        for stmt in statements:
            transf = self._transform_node(stmt)
            if transf is None:
                continue
            # O bloco preserva seu escopo e, em par, uma única tarefa.
            novos.append(transf)
        return novos

    def _transform_node(self, node: Any) -> Any:
        if node is None or not isinstance(node, ASTNode):
            return node

        # 1. Transformação Bottom-up dos filhos
        if isinstance(node, Program):
            node.statements = self._transform_statements(node.statements)
            return node

        if isinstance(node, SeqBlock):
            node.statements = self._transform_statements(node.statements)
            return node

        if isinstance(node, ParBlock):
            # No ParBlock, cada elemento define uma thread independente; não inlinamos SeqBlocks
            node.statements = self._transform_statements(node.statements)
            return node

        if isinstance(node, VarDecl):
            if node.init_value:
                node.init_value = self._transform_node(node.init_value)
            return node

        if isinstance(node, Assignment):
            node.value = self._transform_node(node.value)
            return node

        if isinstance(node, PropertyAssign):
            node.object = self._transform_node(node.object)
            node.value = self._transform_node(node.value)
            return node

        if isinstance(node, IndexAssign):
            node.target = self._transform_node(node.target)
            node.value = self._transform_node(node.value)
            return node

        if isinstance(node, PrintStmt):
            node.arguments = [self._transform_node(arg) for arg in node.arguments]
            return node

        if isinstance(node, ReturnStmt):
            if node.value:
                node.value = self._transform_node(node.value)
            return node

        if isinstance(node, FuncDecl):
            # O backend infere o tipo de retorno pela AST original do corpo.
            if self._contains_value_return(node.body):
                return node
            node.body = self._transform_node(node.body) or SeqBlock(statements=[])
            return node

        if isinstance(node, ClassDecl):
            for method in node.methods:
                self._transform_node(method)
            return node

        if isinstance(node, FuncCallExpr):
            node.arguments = [self._transform_node(arg) for arg in node.arguments]
            return node

        if isinstance(node, MethodCall):
            node.object = self._transform_node(node.object)
            node.arguments = [self._transform_node(arg) for arg in node.arguments]
            return node

        if isinstance(node, ListLiteral):
            node.elements = [self._transform_node(e) for e in node.elements]
            return node

        if isinstance(node, IndexExpr):
            node.object = self._transform_node(node.object)
            node.index = self._transform_node(node.index)
            return node

        if isinstance(node, PropertyAccess):
            node.object = self._transform_node(node.object)
            return node

        if isinstance(node, WhileStmt):
            node.condition = self._transform_node(node.condition)
            node.body = self._transform_node(node.body) or SeqBlock(statements=[])
            if isinstance(node.condition, BoolExpr) and not node.condition.value:
                self.transformacoes.append(
                    f"Linha {node.line}: Eliminação de laço while (condição false inalcançável)"
                )
                return None
            return node

        if isinstance(node, DoWhileStmt):
            node.body = self._transform_node(node.body) or SeqBlock(statements=[])
            node.condition = self._transform_node(node.condition)
            return node

        if isinstance(node, ForStmt):
            if node.initializer:
                node.initializer = self._transform_node(node.initializer)
            if node.condition:
                node.condition = self._transform_node(node.condition)
            if node.increment:
                node.increment = self._transform_node(node.increment)
            node.body = self._transform_node(node.body) or SeqBlock(statements=[])
            return node

        if isinstance(node, ForkStmt):
            node.body = self._transform_node(node.body) or SeqBlock(statements=[])
            return node

        # Eliminação de Ramos Mortos em IfStmt
        if isinstance(node, IfStmt):
            node.condition = self._transform_node(node.condition)
            node.then_branch = self._transform_node(node.then_branch) or SeqBlock(statements=[])
            if node.else_branch:
                node.else_branch = self._transform_node(node.else_branch)

            if isinstance(node.condition, BoolExpr):
                if node.condition.value:
                    self.transformacoes.append(
                        f"Linha {node.line}: Eliminação de ramo morto em if (condição true, promovendo then_branch)"
                    )
                    return node.then_branch if isinstance(node.then_branch, SeqBlock) else SeqBlock(statements=[node.then_branch], line=node.line, col=node.col)
                else:
                    self.transformacoes.append(
                        f"Linha {node.line}: Eliminação de ramo morto em if (condição false)"
                    )
                    if node.else_branch is None:
                        return None
                    return node.else_branch if isinstance(node.else_branch, SeqBlock) else SeqBlock(statements=[node.else_branch], line=node.line, col=node.col)

            return node

        # UnaryExpr (Constant Folding)
        if isinstance(node, UnaryExpr):
            node.operand = self._transform_node(node.operand)
            op = node.op
            operand = node.operand

            if op in ("-", "+") and isinstance(operand, NumberExpr):
                try:
                    num_val = float(operand.value) if "." in operand.value else int(operand.value)
                    res = -num_val if op == "-" else num_val
                    if isinstance(res, int) and not (-(2**31) < num_val <= 2**31 - 1 and -(2**31) < res <= 2**31 - 1):
                        return node
                    if isinstance(res, float) and not math.isfinite(res):
                        return node
                    res_str = self._number_text(res)
                    self.transformacoes.append(
                        f"Linha {node.line}: Dobra de constantes unária '{op}{operand.value}' -> '{res_str}'"
                    )
                    return NumberExpr(value=res_str, line=node.line, col=node.col)
                except ValueError:
                    pass

            if op in ("!", "not") and isinstance(operand, BoolExpr):
                res_bool = not operand.value
                self.transformacoes.append(
                    f"Linha {node.line}: Dobra de constantes lógica '!{operand.value}' -> '{res_bool}'"
                )
                return BoolExpr(value=res_bool, line=node.line, col=node.col)

            return node

        # BinaryExpr: dobra apenas expressões literais comprovadamente válidas.
        if isinstance(node, BinaryExpr):
            node.left = self._transform_node(node.left)
            node.right = self._transform_node(node.right)
            left = node.left
            right = node.right
            op = node.op

            # 2.A: Constant Folding entre literais
            folded = self._fold_binary(op, left, right, node.line, node.col)
            if folded is not None:
                return folded

            return node

        return node

    # -------------------------------------------------------------------------
    # Regras de Constant Folding
    # -------------------------------------------------------------------------
    def _fold_binary(self, op: str, left: Any, right: Any, line: int, col: Optional[int]) -> Optional[ASTNode]:
        # Ambos NumberExpr
        if isinstance(left, NumberExpr) and isinstance(right, NumberExpr):
            try:
                is_float = ("." in left.value) or ("." in right.value)
                v_left = float(left.value) if is_float else int(left.value)
                v_right = float(right.value) if is_float else int(right.value)
                # Sem tipos inteiros explícitos, restringe a dobra ao int de 32 bits.
                if not is_float and not all(-(2**31) < v <= 2**31 - 1 for v in (v_left, v_right)):
                    return None

                # Operações Aritméticas
                if op == "+":
                    res = v_left + v_right
                elif op == "-":
                    res = v_left - v_right
                elif op == "*":
                    res = v_left * v_right
                elif op == "/":
                    if v_right == 0:
                        return None  # Preserva erro de divisão por zero em runtime
                    res = v_left / v_right if is_float else self._int_quotient(v_left, v_right)
                elif op == "%":
                    if v_right == 0:
                        return None
                    if is_float:
                        return None  # O backend C++ não aceita % entre doubles.
                    res = v_left - self._int_quotient(v_left, v_right) * v_right
                # Operações Relacionais
                elif op == "<":
                    return self._record_fold(f"{left.value} < {right.value}", v_left < v_right, line, col, is_bool=True)
                elif op == "<=":
                    return self._record_fold(f"{left.value} <= {right.value}", v_left <= v_right, line, col, is_bool=True)
                elif op == ">":
                    return self._record_fold(f"{left.value} > {right.value}", v_left > v_right, line, col, is_bool=True)
                elif op == ">=":
                    return self._record_fold(f"{left.value} >= {right.value}", v_left >= v_right, line, col, is_bool=True)
                elif op == "==":
                    return self._record_fold(f"{left.value} == {right.value}", v_left == v_right, line, col, is_bool=True)
                elif op == "!=":
                    return self._record_fold(f"{left.value} != {right.value}", v_left != v_right, line, col, is_bool=True)
                else:
                    return None

                # Formata número resultante
                if isinstance(res, float):
                    if not math.isfinite(res):
                        return None
                    res_str = self._number_text(res)
                else:
                    if not -(2**31) < res <= 2**31 - 1:
                        return None
                    res_str = str(res)

                return self._record_fold(f"{left.value} {op} {right.value}", res_str, line, col, is_bool=False)
            except Exception:
                return None

        # Ambos StringExpr
        if isinstance(left, StringExpr) and isinstance(right, StringExpr):
            if op == "+":
                concat = left.value + right.value
                self.transformacoes.append(
                    f"Linha {line}: Concatenação estática de strings '{left.value}' + '{right.value}' -> '{concat}'"
                )
                return StringExpr(value=concat, line=line, col=col)
            elif op == "==":
                return self._record_fold(f'"{left.value}" == "{right.value}"', left.value == right.value, line, col, is_bool=True)
            elif op == "!=":
                return self._record_fold(f'"{left.value}" != "{right.value}"', left.value != right.value, line, col, is_bool=True)

        # Ambos BoolExpr
        if isinstance(left, BoolExpr) and isinstance(right, BoolExpr):
            if op in ("&&", "and"):
                return self._record_fold(f"{left.value} {op} {right.value}", left.value and right.value, line, col, is_bool=True)
            elif op in ("||", "or"):
                return self._record_fold(f"{left.value} {op} {right.value}", left.value or right.value, line, col, is_bool=True)
            elif op == "==":
                return self._record_fold(f"{left.value} == {right.value}", left.value == right.value, line, col, is_bool=True)
            elif op == "!=":
                return self._record_fold(f"{left.value} != {right.value}", left.value != right.value, line, col, is_bool=True)

        return None

    def _record_fold(self, expr_str: str, res: Any, line: int, col: Optional[int], is_bool: bool) -> ASTNode:
        self.transformacoes.append(f"Linha {line}: Dobra de constantes '{expr_str}' -> '{res}'")
        if is_bool:
            return BoolExpr(value=bool(res), line=line, col=col)
        return NumberExpr(value=str(res), line=line, col=col)

    @staticmethod
    def _number_text(value: Any) -> str:
        if isinstance(value, float):
            text = format(Decimal(repr(value)), 'f')
            return text if '.' in text else text + '.0'
        return str(value)

    @staticmethod
    def _int_quotient(left: int, right: int) -> int:
        magnitude = abs(left) // abs(right)
        return -magnitude if (left < 0) != (right < 0) else magnitude
