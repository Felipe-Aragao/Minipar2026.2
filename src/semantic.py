from __future__ import annotations
import sys
from fractions import Fraction
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from ast_nodes import (
    ASTNode, Program, VarDecl, Assignment, PrintStmt, IdentifierExpr, BinaryExpr,
    UnaryExpr, NumberExpr, StringExpr, BoolExpr, SeqBlock, ParBlock, IfStmt, WhileStmt,
    DoWhileStmt, ForStmt, BreakStmt, ContinueStmt, InputExpr,
    ClassDecl, FuncDecl, ReturnStmt, MethodCall, FuncCallExpr, PropertyAccess, PropertyAssign, NewExpr, ThisExpr,
    CChannelExpr, SendStmt, ReceiveExpr, ListLiteral, MatrixCreateExpr, IndexExpr, IndexAssign,
    ForkStmt, JoinStmt  
)

@dataclass
class Symbol:
    name: str
    type: str
    params: List[str] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)
    methods: Dict[str, List[str]] = field(default_factory=dict)

class SemanticAnalyzer:
    def __init__(self, *, emit_diagnostics: bool = True) -> None:
        self._scopes: List[Dict[str, Symbol]] = []
        self._has_errors = False
        self._emit_diagnostics = emit_diagnostics
        self.errors: List[dict] = []
        self.symbols: List[dict] = []
        self._scope_ids = [0]
        self._next_scope_id = 1
        self._current_function: Optional[str] = None
        self._current_class: Optional[str] = None
        self._classes: Dict[str, Symbol] = {}
        self._functions: Dict[str, Symbol] = {}
        self._loop_depth = 0
        
        # Controle de Isolamento de Memória para Paralelismo
        self._fork_scope_start: Optional[int] = None
        
        self._enter_scope()

    def _enter_scope(self) -> None:
        if self._scopes:
            self._scope_ids.append(self._next_scope_id)
            self._next_scope_id += 1
        self._scopes.append({})
    def _exit_scope(self) -> None:
        if len(self._scopes) > 1:
            self._scopes.pop()
            self._scope_ids.pop()

    def _get_context(self) -> str:
        return f" (Funcao: {self._current_function})" if self._current_function else ""

    def _define_symbol(self, name: str, type_: str, line: int, params: Optional[List[str]] = None) -> None:
        if name in self._scopes[-1]:
            self._report(line, f"Variavel '{name}' ja declarada.")
        else:
            self._scopes[-1][name] = Symbol(name=name, type=type_, params=params or [])
            self.symbols.append({"nome": name, "tipo": type_, "linha": line,
                                 "escopo": self._scope_ids[-1],
                                 "funcao": self._current_function, "classe": self._current_class,
                                 "parametros": list(params or [])})

    def _lookup(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self._scopes):
            if name in scope: return scope[name]
        return None

    def _report(self, line: int, message: str) -> None:
        self.errors.append({"fase": "semantica", "linha": line, "coluna": None,
                            "mensagem": message + self._get_context()})
        if self._emit_diagnostics:
            print(f"[ERRO SEMANTICO] Linha {line}{self._get_context()}: {message}", file=sys.stderr)
        self._has_errors = True

    def _infer_type(self, node: Optional[ASTNode]) -> str:
        if node is None: return "unknown"
        if isinstance(node, NumberExpr): return "number"
        if isinstance(node, StringExpr): return "string"
        if isinstance(node, BoolExpr): return "bool"
        if isinstance(node, InputExpr): return "string"
        if isinstance(node, CChannelExpr): return "c_channel"
        if isinstance(node, ForkStmt): return "task"
        if isinstance(node, JoinStmt): return "unknown"
        if isinstance(node, ReceiveExpr): return "string"
        if isinstance(node, ListLiteral): return "list"
        if isinstance(node, MatrixCreateExpr): return "matrix"
        if isinstance(node, NewExpr): return node.class_name
        if isinstance(node, ThisExpr): return self._current_class or "unknown"
        if isinstance(node, IdentifierExpr):
            sym = self._lookup(node.name)
            return sym.type if sym else "unknown"
        if isinstance(node, UnaryExpr):
            return "bool" if node.op == "!" else self._infer_type(node.operand)
        if isinstance(node, BinaryExpr):
            lt, rt = self._infer_type(node.left), self._infer_type(node.right)
            if node.op in ("==", "!=", "<", ">", "<=", ">=", "&&", "||"): return "bool"
            if node.op == "+" and (lt == "string" or rt == "string"): return "string"
            if node.op == "+" and (lt == "list" or rt == "list"): return "list"
            return "number"
        if isinstance(node, PropertyAccess):
            obj_type = self._infer_type(node.object)
            cls = self._classes.get(obj_type)
            if cls and node.property_name in cls.attributes: return cls.attributes[node.property_name]
            return "unknown"
        if isinstance(node, MethodCall):
            return "unknown"
        if isinstance(node, FuncCallExpr):
            if node.name in ("random", "exp", "time", "to_number", "to_int"): return "number"
            if node.name in ("range", "parse_ints"): return "list"
            if node.name in ("to_string", "fmt"): return "string"
            return "unknown"
        if isinstance(node, IndexExpr): return "unknown"
        return "unknown"

    def _types_compatible(self, declared: str, actual: str) -> bool:
        if declared in ("var", "unknown") or actual == "unknown": return True
        if declared == "int" and actual == "number": return True
        if declared == "number" and actual == "int": return True
        if declared == "task" and actual == "task": return True
        return declared == actual

    def _collect_declarations(self, program: Program) -> None:
        for stmt in program.statements:
            if isinstance(stmt, FuncDecl):
                self._functions[stmt.name] = Symbol(stmt.name, "FUNC", params=stmt.params)
            elif isinstance(stmt, ClassDecl):
                attrs = {a.name: a.type for a in stmt.attributes}
                methods = {m.name: m.params for m in stmt.methods}
                self._classes[stmt.name] = Symbol(stmt.name, "CLASS", attributes=attrs, methods=methods)

    def _check_memory_isolation(self, name: str, line: int) -> None:
        if self._fork_scope_start is None:
            return
        for index in range(len(self._scopes) - 1, -1, -1):
            if name in self._scopes[index]:
                if index < self._fork_scope_start:
                    self._report(line, f"Violacao de Isolamento: Variavel externa '{name}' nao pode ser alterada dentro de um fork. Use mensagens (canais) para compartilhar dados.")
                return

    def _constant_number(self, node: ASTNode) -> Optional[Fraction]:
        """Avalia apenas aritmética constante, sem executar código MiniPar."""
        if isinstance(node, NumberExpr):
            return Fraction(node.value)
        if isinstance(node, UnaryExpr) and node.op in ("+", "-"):
            value = self._constant_number(node.operand)
            if value is not None:
                return value if node.op == "+" else -value
        if isinstance(node, BinaryExpr) and node.op in ("+", "-", "*", "/", "%"):
            left = self._constant_number(node.left)
            right = self._constant_number(node.right)
            if left is not None and right is not None:
                if node.op == "+": return left + right
                if node.op == "-": return left - right
                if node.op == "*": return left * right
                if node.op == "/": return left / right
                return left - int(left / right) * right
        return None

    def _get_root_identifier(self, node: ASTNode) -> Optional[str]:
        """Desce pela árvore de propriedades ou índices até achar a variável raiz."""
        if isinstance(node, IdentifierExpr):
            return node.name
        elif isinstance(node, PropertyAccess):
            return self._get_root_identifier(node.object)
        elif isinstance(node, IndexExpr):
            return self._get_root_identifier(node.object)
        return None
    def validate_node(self, node: ASTNode) -> None:
        if node is None: return

        if isinstance(node, VarDecl):
            self.validate_node(node.init_value)
            actual_type = self._infer_type(node.init_value)
            declared_type = actual_type if node.type == "var" and actual_type != "unknown" else node.type
            if not self._types_compatible(declared_type, actual_type):
                self._report(node.line, f"Tipo incompativel em '{node.name}': esperado {declared_type}, recebido {actual_type}.")
            self._define_symbol(node.name, declared_type, node.line)
        
        elif isinstance(node, Assignment):
            sym = self._lookup(node.name)
            if sym is None:
                self._report(node.line, f"Variavel '{node.name}' nao declarada.")
            else:
                self._check_memory_isolation(node.name, node.line)
            self.validate_node(node.value)
            if sym and not self._types_compatible(sym.type, self._infer_type(node.value)):
                self._report(node.line, f"Tipo incompativel em atribuicao de '{node.name}'.")
                
        elif isinstance(node, ForkStmt):
            if node.destino:
                if node.destino.tipo == "core":
                    self.validate_node(node.destino.args[0])
                    arg_type = self._infer_type(node.destino.args[0])
                    if arg_type not in ("number", "int", "unknown"):
                        self._report(node.line, f"Alocacao 'core' requer expressao numerica inteira.")
                    else:
                        try:
                            value = self._constant_number(node.destino.args[0])
                        except ZeroDivisionError:
                            self._report(node.line, "Alocacao 'core' contem divisao por zero.")
                        else:
                            if value is not None and (value.denominator != 1 or value < 0):
                                self._report(node.line, "Alocacao 'core' requer inteiro nao negativo.")
                elif node.destino.tipo == "host":
                    self.validate_node(node.destino.args[0])
                    arg_type = self._infer_type(node.destino.args[0])
                    if len(node.destino.args) == 1:
                        if arg_type not in ("c_channel", "unknown"):
                             self._report(node.line, f"Alocacao 'host' com 1 argumento requer canal ('c_channel').")
                    elif len(node.destino.args) == 2:
                        self.validate_node(node.destino.args[1])
                        port_type = self._infer_type(node.destino.args[1])
                        if arg_type not in ("string", "unknown") or port_type not in ("number", "int", "unknown"):
                             self._report(node.line, f"Alocacao 'host' requer endereco IP ('string') e porta ('number').")

            old_fork_scope = self._fork_scope_start
            self._fork_scope_start = len(self._scopes)
            try:
                self.validate_node(node.body)
            finally:
                self._fork_scope_start = old_fork_scope

        elif isinstance(node, JoinStmt):
            args = getattr(node, "args", [])
            for arg in args:
                self.validate_node(arg)
                arg_type = self._infer_type(arg)
                if isinstance(arg, ListLiteral) or arg_type == "list":
                    self._report(node.line, f"'join' nao suporta lista de tarefas. Utilize a forma variadica 'join(t1, t2, ...)' ou a barreira 'join;'.")
                elif arg_type not in ("task", "unknown"):
                    self._report(node.line, f"'join' requer subtarefa do tipo 'task', recebido '{arg_type}'.")
        
        elif isinstance(node, PrintStmt):
            for arg in node.arguments: self.validate_node(arg)
        elif isinstance(node, SendStmt):
            self.validate_node(node.channel)
            self.validate_node(node.message)
        elif isinstance(node, CChannelExpr):
            self.validate_node(node.ip)
            self.validate_node(node.port)
        elif isinstance(node, ReceiveExpr):
            self.validate_node(node.channel)
        elif isinstance(node, ListLiteral):
            for e in node.elements: self.validate_node(e)
        elif isinstance(node, MatrixCreateExpr):
            self.validate_node(node.rows)
            self.validate_node(node.cols)
            self.validate_node(node.init_value)
        elif isinstance(node, IndexExpr):
            self.validate_node(node.object)
            self.validate_node(node.index)
        elif isinstance(node, IndexAssign):
            self.validate_node(node.target)
            self.validate_node(node.value)
            
            root_id = self._get_root_identifier(node.target)
            if root_id:
                self._check_memory_isolation(root_id, node.line)
        elif isinstance(node, IdentifierExpr):
            if self._lookup(node.name) is None:
                self._report(node.line, f"Variavel '{node.name}' nao declarada.")
        elif isinstance(node, BinaryExpr):
            self.validate_node(node.left)
            self.validate_node(node.right)
            if node.op in ("+", "-", "*", "/", "%"):
                lt, rt = self._infer_type(node.left), self._infer_type(node.right)
                if node.op != "+" and (lt not in ("number", "int", "var", "unknown") or rt not in ("number", "int", "var", "unknown")):
                    self._report(node.line, f"Operador '{node.op}' exige operandos numericos.")
        elif isinstance(node, UnaryExpr):
            self.validate_node(node.operand)
        elif isinstance(node, (SeqBlock, ParBlock)):
            self._enter_scope()
            for stmt in node.statements: self.validate_node(stmt)
            self._exit_scope()
        elif isinstance(node, IfStmt):
            self.validate_node(node.condition)
            self.validate_node(node.then_branch)
            if node.else_branch: self.validate_node(node.else_branch)
        elif isinstance(node, WhileStmt):
            self.validate_node(node.condition)
            self._loop_depth += 1
            self.validate_node(node.body)
            self._loop_depth -= 1
        elif isinstance(node, DoWhileStmt):
            self._loop_depth += 1
            self.validate_node(node.body)
            self._loop_depth -= 1
            self.validate_node(node.condition)
        elif isinstance(node, ForStmt):
            self._enter_scope()
            if node.iterator_name:
                self.validate_node(node.iterable)
                self._define_symbol(node.iterator_name, "var", node.line)
            else:
                self.validate_node(node.initializer)
                self.validate_node(node.condition)
                self.validate_node(node.increment)
            self._loop_depth += 1
            self.validate_node(node.body)
            self._loop_depth -= 1
            self._exit_scope()
        elif isinstance(node, (BreakStmt, ContinueStmt)):
            if self._loop_depth == 0:
                self._report(node.line, f"'{node.__class__.__name__.replace('Stmt', '').lower()}' usado fora de laco.")
        elif isinstance(node, ClassDecl):
            if node.superclass and node.superclass not in self._classes:
                self._report(node.line, f"Superclasse '{node.superclass}' nao declarada.")
            self._define_symbol(node.name, "CLASS", node.line)
            self._enter_scope()
            old_class = self._current_class
            self._current_class = node.name
            for attr in node.attributes: self.validate_node(attr)
            for method in node.methods: self.validate_node(method)
            self._current_class = old_class
            self._exit_scope()
        elif isinstance(node, FuncDecl):
            self._define_symbol(node.name, "FUNC", node.line, node.params)
            self._enter_scope()
            old_function = self._current_function
            self._current_function = node.name
            for p in node.params: self._define_symbol(p, "var", node.line)
            self.validate_node(node.body)
            self._current_function = old_function
            self._exit_scope()
        elif isinstance(node, ReturnStmt):
            if node.value: self.validate_node(node.value)
        elif isinstance(node, MethodCall):
            obj_type = self._infer_type(node.object)
            cls = self._classes.get(obj_type)
            if cls and node.method_name not in cls.methods:
                self._report(node.line, f"Metodo '{node.method_name}' nao declarado em '{obj_type}'.")
            elif cls and len(cls.methods[node.method_name]) != len(node.arguments):
                self._report(node.line, f"Metodo '{node.method_name}' espera {len(cls.methods[node.method_name])} argumento(s), recebeu {len(node.arguments)}.")
            self.validate_node(node.object)
            for arg in node.arguments: self.validate_node(arg)
        elif isinstance(node, FuncCallExpr):
            nativas = ("exp", "random", "range", "len", "to_number", "parse_ints", "time", "to_int", "to_string", "fmt")
            if node.name not in self._functions and node.name not in nativas:
                self._report(node.line, f"Funcao '{node.name}' nao declarada.")
            elif node.name in self._functions and len(self._functions[node.name].params) != len(node.arguments):
                self._report(node.line, f"Funcao '{node.name}' espera {len(self._functions[node.name].params)} argumento(s), recebeu {len(node.arguments)}.")
            
            elif node.name == "fmt" and len(node.arguments) != 2:
                self._report(node.line, f"Funcao 'fmt' espera 2 argumentos (valor, casas_decimais), recebeu {len(node.arguments)}.")
                
            for arg in node.arguments: self.validate_node(arg)
        elif isinstance(node, PropertyAccess):
            self.validate_node(node.object)
            obj_type = self._infer_type(node.object)
            cls = self._classes.get(obj_type)
            if cls and node.property_name not in cls.attributes:
                self._report(node.line, f"Atributo '{node.property_name}' nao declarado em '{obj_type}'.")
        elif isinstance(node, PropertyAssign):
            self.validate_node(node.object)
            self.validate_node(node.value)
            
            #Isolamento na raiz do objeto
            root_id = self._get_root_identifier(node.object)
            if root_id:
                self._check_memory_isolation(root_id, node.line)
                
            obj_type = self._infer_type(node.object)
            cls = self._classes.get(obj_type)
            if cls and node.property_name not in cls.attributes:
                self._report(node.line, f"Atributo '{node.property_name}' nao declarado em '{obj_type}'.")
        elif isinstance(node, NewExpr):
            if node.class_name not in self._classes:
                self._report(node.line, f"Classe '{node.class_name}' nao declarada.")
            for arg in node.arguments: self.validate_node(arg)
        elif isinstance(node, ThisExpr):
            pass
        elif isinstance(node, InputExpr):
            if node.prompt: self.validate_node(node.prompt)

    def analyze(self, program: Program) -> bool:
        self._collect_declarations(program)
        for stmt in program.statements: self.validate_node(stmt)
        return not self._has_errors
