from __future__ import annotations
import sys
from typing import List
from lexer import Token, TokenType
from ast_nodes import (
    ASTNode, Program, VarDecl, Assignment, PrintStmt, SeqBlock, ParBlock, 
    BinaryExpr, UnaryExpr, NumberExpr, StringExpr, BoolExpr, IdentifierExpr, IfStmt, WhileStmt,
    DoWhileStmt, ForStmt, BreakStmt, ContinueStmt, InputExpr,
    ClassDecl, FuncDecl, ReturnStmt, MethodCall, FuncCallExpr, PropertyAccess, PropertyAssign, NewExpr, ThisExpr,
    CChannelExpr, SendStmt, ReceiveExpr, ListLiteral, MatrixCreateExpr, IndexExpr, IndexAssign,
    ForkStmt, JoinStmt, Destino  
)

class ParseError(Exception):
    """Erro sintático com posição, consumível por interfaces sem encerrar o processo."""
    def __init__(self, message: str, token: Token) -> None:
        super().__init__(message)
        self.line = token.line
        self.col = token.col


class Parser:
    def __init__(self, tokens: List[Token], *, raise_errors: bool = False) -> None:
        self._tokens = tokens
        self._raise_errors = raise_errors
        self._pos = 0

    def _error(self, message: str, token: Token = None) -> None:
        token = token or self._peek()
        if self._raise_errors:
            raise ParseError(message, token)
        print(f"[ERRO SINTATICO] Linha {token.line}: {message}", file=sys.stderr)
        sys.exit(1)

    def _peek(self) -> Token:
        if self._pos >= len(self._tokens): return self._tokens[-1]
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        token = self._tokens[self._pos]
        if self._pos < len(self._tokens): self._pos += 1
        return token

    def _match(self, token_type: TokenType) -> bool:
        if self._peek().type == token_type:
            self._advance()
            return True
        return False

    def _consume(self, token_type: TokenType, err_msg: str) -> Token:
        if self._peek().type == token_type: return self._advance()
        tok = self._peek()
        self._error(f"{err_msg} (Encontrado: {tok.lexeme!r})", tok)

    def _parse_var_decl(self, declared_type: str = "var", require_semicolon: bool = True) -> ASTNode:
        node = VarDecl(name="")
        node.line = self._peek().line
        node.col = self._peek().col
        node.type = declared_type
        node.name = self._consume(TokenType.IDENTIFIER, "Esperado nome da variavel").lexeme
        if self._match(TokenType.ASSIGN):
            node.init_value = self._parse_expression()
        if require_semicolon:
            self._consume(TokenType.SEMICOLON, "Esperado ';' apos declaracao de variavel")
        return node

    def _parse_assignment_tail(self, target: ASTNode, require_semicolon: bool = True) -> ASTNode:
        val = self._parse_expression()
        if require_semicolon:
            self._consume(TokenType.SEMICOLON, "Esperado ';'")
        if isinstance(target, IdentifierExpr): return Assignment(name=target.name, value=val, line=target.line, col=target.col)
        if isinstance(target, PropertyAccess): return PropertyAssign(object=target.object, property_name=target.property_name, value=val, line=target.line, col=target.col)
        if isinstance(target, IndexExpr): return IndexAssign(target=target, value=val, line=target.line, col=target.col)
        self._error("Atribuicao invalida")

    def _parse_print_stmt(self) -> ASTNode:
        token = self._tokens[self._pos - 1]
        node = PrintStmt(line=token.line, col=token.col)
        self._consume(TokenType.LPAREN, "Esperado '(' apos print")
        if self._peek().type != TokenType.RPAREN:
            node.arguments.append(self._parse_expression())
            while self._match(TokenType.COMMA):
                node.arguments.append(self._parse_expression())
        self._consume(TokenType.RPAREN, "Esperado ')' apos argumentos do print")
        self._consume(TokenType.SEMICOLON, "Esperado ';' apos print")
        return node

    def _parse_send_stmt(self) -> ASTNode:
        line = self._tokens[self._pos - 1].line
        col = self._tokens[self._pos - 1].col
        self._consume(TokenType.LPAREN, "Esperado '(' apos send")
        channel = self._parse_expression()
        self._consume(TokenType.COMMA, "Esperado ',' entre canal e mensagem")
        message = self._parse_expression()
        self._consume(TokenType.RPAREN, "Esperado ')'")
        self._consume(TokenType.SEMICOLON, "Esperado ';'")
        return SendStmt(channel=channel, message=message, line=line, col=col)

    def _parse_seq_block(self) -> ASTNode:
        node = SeqBlock(line=self._peek().line, col=self._peek().col)
        self._consume(TokenType.LBRACE, "Esperado '{' para iniciar bloco")
        while self._peek().type not in (TokenType.RBRACE, TokenType.END_OF_FILE):
            node.statements.append(self._parse_statement())
        self._consume(TokenType.RBRACE, "Esperado '}' para fechar bloco")
        return node

    def _parse_par_block(self) -> ASTNode:
        node = ParBlock(line=self._peek().line, col=self._peek().col)
        self._consume(TokenType.LBRACE, "Esperado '{' para iniciar bloco PAR")
        while self._peek().type not in (TokenType.RBRACE, TokenType.END_OF_FILE):
            node.statements.append(self._parse_statement())
        self._consume(TokenType.RBRACE, "Esperado '}' para fechar bloco PAR")
        return node
        
    # Analisador Sintático para Fork
    # Lê o destino opcional antes de distinguir um corpo em bloco de uma expressão.
    def _parse_fork(self) -> ASTNode:
        line = self._tokens[self._pos - 1].line
        col = self._tokens[self._pos - 1].col
        destino_obj = None

        if self._match(TokenType.CORE):
            destination_token = self._tokens[self._pos - 1]
            self._consume(TokenType.LPAREN, "Esperado '(' apos 'core'")
            destino_args = [self._parse_expression()]
            self._consume(TokenType.RPAREN, "Esperado ')' apos argumento do 'core'")
            destino_obj = Destino(tipo="core", args=destino_args, line=destination_token.line, col=destination_token.col)
        elif self._match(TokenType.HOST):
            destination_token = self._tokens[self._pos - 1]
            self._consume(TokenType.LPAREN, "Esperado '(' apos 'host'")
            destino_args = [self._parse_expression()]
            if self._match(TokenType.COMMA):
                destino_args.append(self._parse_expression())
            self._consume(TokenType.RPAREN, "Esperado ')' apos argumentos do 'host'")
            destino_obj = Destino(tipo="host", args=destino_args, line=destination_token.line, col=destination_token.col)
            
        # O corpo do fork pode ser um bloco ou uma expressão direta (como chamada de função)
        if self._peek().type == TokenType.LBRACE:
            body = self._parse_seq_block()
        else:
            body = self._parse_expression()
            
        return ForkStmt(destino=destino_obj, body=body, line=line, col=col)

    # Analisador Sintático para Join
    # Distingue a barreira sem argumentos da espera por tarefas identificadas.
    def _parse_join(self) -> ASTNode:
        line = self._tokens[self._pos - 1].line
        col = self._tokens[self._pos - 1].col
        args = []
        if self._match(TokenType.LPAREN):
            if self._peek().type != TokenType.RPAREN:
                args.append(self._parse_expression())
                while self._match(TokenType.COMMA):
                    args.append(self._parse_expression())
            self._consume(TokenType.RPAREN, "Esperado ')' apos parametros do join")
            
        return JoinStmt(args=args, line=line, col=col)

    def _parse_if_stmt(self) -> ASTNode:
        line = self._tokens[self._pos - 1].line
        col = self._tokens[self._pos - 1].col
        self._consume(TokenType.LPAREN, "Esperado '(' apos 'if'")
        condition = self._parse_expression()
        self._consume(TokenType.RPAREN, "Esperado ')' apos condicao do 'if'")
        then_branch = self._parse_statement()
        else_branch = self._parse_statement() if self._match(TokenType.ELSE) else None
        return IfStmt(condition=condition, then_branch=then_branch, else_branch=else_branch, line=line, col=col)

    def _parse_while_stmt(self) -> ASTNode:
        line = self._tokens[self._pos - 1].line
        col = self._tokens[self._pos - 1].col
        self._consume(TokenType.LPAREN, "Esperado '(' apos 'while'")
        condition = self._parse_expression()
        self._consume(TokenType.RPAREN, "Esperado ')' apos condicao")
        body = self._parse_statement()
        return WhileStmt(condition=condition, body=body, line=line, col=col)

    def _parse_do_while_stmt(self) -> ASTNode:
        line = self._tokens[self._pos - 1].line
        col = self._tokens[self._pos - 1].col
        body = self._parse_statement()
        self._consume(TokenType.WHILE, "Esperado 'while' apos bloco do")
        self._consume(TokenType.LPAREN, "Esperado '(' apos 'while'")
        condition = self._parse_expression()
        self._consume(TokenType.RPAREN, "Esperado ')' apos condicao")
        self._match(TokenType.SEMICOLON)
        return DoWhileStmt(body=body, condition=condition, line=line, col=col)

    def _parse_for_stmt(self) -> ASTNode:
        line = self._tokens[self._pos - 1].line
        col = self._tokens[self._pos - 1].col
        self._consume(TokenType.LPAREN, "Esperado '(' apos 'for'")
        initializer = condition = increment = iterator_name = iterable = None

        if self._match(TokenType.VAR):
            name_tok = self._consume(TokenType.IDENTIFIER, "Esperado variavel do for")
            if self._match(TokenType.IN):
                iterator_name = name_tok.lexeme
                iterable = self._parse_expression()
                self._consume(TokenType.RPAREN, "Esperado ')' apos iteravel")
                body = self._parse_statement()
                return ForStmt(
                    None, None, None, body, iterator_name, iterable, line, col=col,
                    iterator_location={"line": name_tok.line, "col": name_tok.col},
                )
            initializer = VarDecl(name=name_tok.lexeme, type="var", line=name_tok.line, col=name_tok.col)
            if self._match(TokenType.ASSIGN):
                initializer.init_value = self._parse_expression()
            self._consume(TokenType.SEMICOLON, "Esperado ';' apos inicializador do for")
        elif self._peek().type == TokenType.TYPE:
            type_tok = self._advance()
            initializer = self._parse_var_decl(type_tok.lexeme, require_semicolon=False)
            self._consume(TokenType.SEMICOLON, "Esperado ';' apos inicializador do for")
        elif not self._match(TokenType.SEMICOLON):
            target = self._parse_expression()
            if self._match(TokenType.ASSIGN):
                initializer = self._parse_assignment_tail(target, require_semicolon=False)
            else:
                initializer = target
            self._consume(TokenType.SEMICOLON, "Esperado ';' apos inicializador do for")

        if not self._match(TokenType.SEMICOLON):
            condition = self._parse_expression()
            self._consume(TokenType.SEMICOLON, "Esperado ';' apos condicao do for")

        if self._peek().type != TokenType.RPAREN:
            target = self._parse_expression()
            if self._match(TokenType.ASSIGN):
                increment = self._parse_assignment_tail(target, require_semicolon=False)
            else:
                increment = target
        self._consume(TokenType.RPAREN, "Esperado ')' apos for")
        body = self._parse_statement()
        return ForStmt(initializer, condition, increment, body, line=line, col=col)

    def _parse_class_decl(self) -> ASTNode:
        name_token = self._consume(TokenType.IDENTIFIER, "Esperado nome da classe")
        name = name_token.lexeme
        line, col = name_token.line, name_token.col
        superclass = self._consume(TokenType.IDENTIFIER, "Esperado nome da superclasse").lexeme if self._match(TokenType.EXTENDS) else None
        self._consume(TokenType.LBRACE, "Esperado '{' na classe")
        attrs, methods = [], []
        while self._peek().type not in (TokenType.RBRACE, TokenType.END_OF_FILE):
            if self._match(TokenType.VAR): attrs.append(self._parse_var_decl())
            elif self._match(TokenType.FUNC): methods.append(self._parse_func_decl())
            else: self._consume(TokenType.UNKNOWN, "Esperado 'var' ou 'func' na definicao da classe")
        self._consume(TokenType.RBRACE, "Esperado '}' no fim da classe")
        return ClassDecl(name=name, superclass=superclass, attributes=attrs, methods=methods, line=line, col=col)

    def _parse_func_decl(self) -> ASTNode:
        name_token = self._consume(TokenType.IDENTIFIER, "Esperado nome da funcao")
        name = name_token.lexeme
        line, col = name_token.line, name_token.col
        self._consume(TokenType.LPAREN, "Esperado '('")
        params = []
        param_locations = []
        if self._peek().type != TokenType.RPAREN:
            if self._peek().type == TokenType.TYPE:
                self._advance()
            parameter = self._consume(TokenType.IDENTIFIER, "Esperado parametro")
            params.append(parameter.lexeme)
            param_locations.append({"line": parameter.line, "col": parameter.col})
            while self._match(TokenType.COMMA):
                if self._peek().type == TokenType.TYPE:
                    self._advance()
                parameter = self._consume(TokenType.IDENTIFIER, "Esperado parametro")
                params.append(parameter.lexeme)
                param_locations.append({"line": parameter.line, "col": parameter.col})
        self._consume(TokenType.RPAREN, "Esperado ')'")
        body = self._parse_seq_block()
        return FuncDecl(name=name, params=params, body=body, line=line, col=col, param_locations=param_locations)

    def _parse_return_stmt(self) -> ASTNode:
        line = self._tokens[self._pos - 1].line
        col = self._tokens[self._pos - 1].col
        value = None if self._peek().type == TokenType.SEMICOLON else self._parse_expression()
        self._match(TokenType.SEMICOLON)
        return ReturnStmt(value=value, line=line, col=col)

    # Despacha a produção conforme o token inicial do comando.
    def _parse_statement(self) -> ASTNode:
        if self._match(TokenType.CLASS): return self._parse_class_decl()
        if self._match(TokenType.FUNC): return self._parse_func_decl()
        if self._match(TokenType.RETURN): return self._parse_return_stmt()
        if self._match(TokenType.BREAK):
            line = self._tokens[self._pos - 1].line
            col = self._tokens[self._pos - 1].col
            self._match(TokenType.SEMICOLON)
            return BreakStmt(line=line, col=col)
        if self._match(TokenType.CONTINUE):
            line = self._tokens[self._pos - 1].line
            col = self._tokens[self._pos - 1].col
            self._match(TokenType.SEMICOLON)
            return ContinueStmt(line=line, col=col)
        if self._match(TokenType.VAR): return self._parse_var_decl()
        if self._peek().type == TokenType.TYPE:
            type_tok = self._advance()
            return self._parse_var_decl(type_tok.lexeme)
        if self._match(TokenType.SEQ) or self._peek().type == TokenType.LBRACE: 
            if self._peek().type == TokenType.SEQ: self._advance()
            return self._parse_seq_block()
        if self._match(TokenType.PAR): return self._parse_par_block()
        
        # Inserção das novas instruções como comandos independentes
        if self._match(TokenType.FORK):
            node = self._parse_fork()
            if not isinstance(node.body, SeqBlock):
                self._consume(TokenType.SEMICOLON, "Esperado ';' apos instrucao fork")
            return node
        if self._match(TokenType.JOIN):
            node = self._parse_join()
            self._consume(TokenType.SEMICOLON, "Esperado ';' apos join")
            return node
            
        if self._match(TokenType.PRINT): return self._parse_print_stmt()
        if self._match(TokenType.SEND): return self._parse_send_stmt()
        if self._match(TokenType.IF): return self._parse_if_stmt()
        if self._match(TokenType.WHILE): return self._parse_while_stmt()
        if self._match(TokenType.DO): return self._parse_do_while_stmt()
        if self._match(TokenType.FOR): return self._parse_for_stmt()

        if self._peek().type in (TokenType.IDENTIFIER, TokenType.THIS, TokenType.NEW, TokenType.RECEIVE, TokenType.INPUT, TokenType.C_CHANNEL, TokenType.MATRIX, TokenType.LBRACKET):
            expr = self._parse_expression()
            if self._match(TokenType.ASSIGN):
                return self._parse_assignment_tail(expr)
            elif isinstance(expr, (MethodCall, FuncCallExpr)):
                self._consume(TokenType.SEMICOLON, "Esperado ';'")
                return expr
            self._error("Instrucao ou expressao isolada invalida")

        tok = self._peek()
        self._error(f"Instrucao nao reconhecida: {tok.lexeme!r}", tok)

    def _parse_expression(self) -> ASTNode:
        return self._parse_or()

    def _parse_or(self) -> ASTNode:
        expr = self._parse_and()
        while self._match(TokenType.OR):
            op_tok = self._tokens[self._pos - 1]
            expr = BinaryExpr(op=op_tok.lexeme, left=expr, right=self._parse_and(), line=op_tok.line, col=op_tok.col)
        return expr

    def _parse_and(self) -> ASTNode:
        expr = self._parse_comparison()
        while self._match(TokenType.AND):
            op_tok = self._tokens[self._pos - 1]
            expr = BinaryExpr(op=op_tok.lexeme, left=expr, right=self._parse_comparison(), line=op_tok.line, col=op_tok.col)
        return expr

    def _parse_comparison(self) -> ASTNode:
        expr = self._parse_term()
        while self._peek().type in (TokenType.EQ, TokenType.NEQ, TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE):
            op_tok = self._advance()
            node = BinaryExpr(op=op_tok.lexeme, left=expr, right=self._parse_term())
            node.line = op_tok.line
            node.col = op_tok.col
            expr = node
        return expr

    # A soma e a subtração consomem fatores completos, preservando a precedência de multiplicação e divisão.
    def _parse_term(self) -> ASTNode:
        expr = self._parse_factor()
        while self._peek().type in (TokenType.PLUS, TokenType.MINUS):
            op_tok = self._advance()
            node = BinaryExpr(op=op_tok.lexeme, left=expr, right=self._parse_factor())
            node.line = op_tok.line
            node.col = op_tok.col
            expr = node
        return expr

    def _parse_factor(self) -> ASTNode:
        expr = self._parse_unary()
        while self._peek().type in (TokenType.STAR, TokenType.SLASH, TokenType.MOD):
            op_tok = self._advance()
            node = BinaryExpr(op=op_tok.lexeme, left=expr, right=self._parse_unary())
            node.line = op_tok.line
            node.col = op_tok.col
            expr = node
        return expr

    def _parse_unary(self) -> ASTNode:
        if self._peek().type in (TokenType.MINUS, TokenType.PLUS, TokenType.NOT):
            op_tok = self._advance()
            node = UnaryExpr(op=op_tok.lexeme, operand=self._parse_unary())
            node.line = op_tok.line
            node.col = op_tok.col
            return node
        return self._parse_primary()

    # Os parênteses reiniciam a leitura de uma expressão completa dentro do agrupamento.
    def _parse_primary(self) -> ASTNode:
        tok = self._peek()
        node = None

        if self._match(TokenType.MATRIX):
            line = tok.line
            col = tok.col
            self._consume(TokenType.LPAREN, "Esperado '(' apos matrix")
            rows = self._parse_expression()
            self._consume(TokenType.COMMA, "Esperado ','")
            cols = self._parse_expression()
            self._consume(TokenType.COMMA, "Esperado ','")
            init_val = self._parse_expression()
            self._consume(TokenType.RPAREN, "Esperado ')'")
            node = MatrixCreateExpr(rows=rows, cols=cols, init_value=init_val, line=line, col=col)
        elif self._match(TokenType.LBRACKET):
            line = tok.line
            col = tok.col
            elements = []
            if self._peek().type != TokenType.RBRACKET:
                elements.append(self._parse_expression())
                while self._match(TokenType.COMMA): elements.append(self._parse_expression())
            self._consume(TokenType.RBRACKET, "Esperado ']'")
            node = ListLiteral(elements=elements, line=line, col=col)
        elif self._match(TokenType.C_CHANNEL):
            line = tok.line
            col = tok.col
            self._consume(TokenType.LPAREN, "Esperado '(' apos c_channel")
            ip = self._parse_expression()
            self._consume(TokenType.COMMA, "Esperado ',' entre ip e porta")
            port = self._parse_expression()
            self._consume(TokenType.RPAREN, "Esperado ')'")
            node = CChannelExpr(ip=ip, port=port, line=line, col=col)
        elif self._match(TokenType.RECEIVE):
            line = tok.line
            col = tok.col
            self._consume(TokenType.LPAREN, "Esperado '(' apos receive")
            channel = self._parse_expression()
            self._consume(TokenType.RPAREN, "Esperado ')'")
            node = ReceiveExpr(channel=channel, line=line, col=col)
        elif self._match(TokenType.INPUT):
            line = tok.line
            col = tok.col
            self._consume(TokenType.LPAREN, "Esperado '(' apos input")
            prompt = None if self._peek().type == TokenType.RPAREN else self._parse_expression()
            self._consume(TokenType.RPAREN, "Esperado ')' apos input")
            node = InputExpr(prompt=prompt, line=line, col=col)
        elif self._match(TokenType.NEW):
            line = tok.line
            col = tok.col
            class_name = self._consume(TokenType.IDENTIFIER, "Esperado nome da classe").lexeme
            self._consume(TokenType.LPAREN, "Esperado '('")
            args = []
            if self._peek().type != TokenType.RPAREN:
                args.append(self._parse_expression())
                while self._match(TokenType.COMMA): args.append(self._parse_expression())
            self._consume(TokenType.RPAREN, "Esperado ')'")
            node = NewExpr(class_name=class_name, arguments=args, line=line, col=col)
        elif self._match(TokenType.THIS):
            node = ThisExpr(line=tok.line, col=tok.col)
            
        # Inserção das novas instruções como expressões avaliadas    
        elif self._match(TokenType.FORK):
            node = self._parse_fork()
        elif self._match(TokenType.JOIN):
            node = self._parse_join()
            
        elif self._match(TokenType.NUMBER):
            node = NumberExpr(value=tok.lexeme, line=tok.line, col=tok.col)
        elif self._match(TokenType.STRING_LITERAL):
            node = StringExpr(value=tok.lexeme, line=tok.line, col=tok.col)
        elif self._match(TokenType.BOOL_LITERAL):
            node = BoolExpr(value=(tok.lexeme == "true"), line=tok.line, col=tok.col)
        elif self._match(TokenType.IDENTIFIER):
            name = tok.lexeme
            if self._match(TokenType.LPAREN):
                args = []
                if self._peek().type != TokenType.RPAREN:
                    args.append(self._parse_expression())
                    while self._match(TokenType.COMMA): args.append(self._parse_expression())
                self._consume(TokenType.RPAREN, "Esperado ')'")
                node = FuncCallExpr(name=name, arguments=args, line=tok.line, col=tok.col)
            else:
                node = IdentifierExpr(name=name, line=tok.line, col=tok.col)
        elif self._match(TokenType.LPAREN):
            node = self._parse_expression()
            self._consume(TokenType.RPAREN, "Esperado ')'")
        else:
            self._error("Expressao esperada", tok)

        while True:
            if self._match(TokenType.DOT):
                prop_tok = self._consume(TokenType.IDENTIFIER, "Esperado identificador apos '.'")
                if self._match(TokenType.LPAREN):
                    args = []
                    if self._peek().type != TokenType.RPAREN:
                        args.append(self._parse_expression())
                        while self._match(TokenType.COMMA): args.append(self._parse_expression())
                    self._consume(TokenType.RPAREN, "Esperado ')'")
                    node = MethodCall(object=node, method_name=prop_tok.lexeme, arguments=args, line=prop_tok.line, col=prop_tok.col)
                else:
                    node = PropertyAccess(object=node, property_name=prop_tok.lexeme, line=prop_tok.line, col=prop_tok.col)
            elif self._match(TokenType.LBRACKET):
                idx_tok = self._tokens[self._pos - 1]
                idx = self._parse_expression()
                self._consume(TokenType.RBRACKET, "Esperado ']'")
                node = IndexExpr(object=node, index=idx, line=idx_tok.line, col=idx_tok.col)
            else:
                break

        return node

    def parse(self) -> Program:
        prog = Program(line=self._peek().line, col=self._peek().col)
        while self._peek().type != TokenType.END_OF_FILE:
            stmt = self._parse_statement()
            if stmt: prog.statements.append(stmt)
        return prog
