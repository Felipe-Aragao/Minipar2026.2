# Gramática Formal BNF — Linguagem MiniPar 2026.2

**Projeto:** MiniPar-Improvement — Compilador da Linguagem MiniPar 2026.2 Orientada a Objetos
**Autores da base 2026.1:** Emanuele Vitória de Jesus Lima · Jose Lucas de Oliveira Quintela · Luiz Miguel de Melo Bomfim
**Instituição:** Universidade Federal de Alagoas — Instituto de Computação · Ciência da Computação
**Disciplina:** Compiladores — Prof. Arturo Hernandez Dominguez
**Repositório 2026.2:** https://github.com/Felipe-Aragao/Minipar2026.2
**Autores da base 2026.2:** Érico Almeida Bernardino · Felipe Lima Aragão · Lucas Trindade de Souza
**Base 2026.1:** https://github.com/luizwhirl/minipar-improvement

---

> Documento de referência da sintaxe MiniPar 2026.2. Usa notação EBNF (opcionais e repetições), mantendo o nome BNF do projeto.
> Aceitação sintática, validação semântica e geração de executável são etapas distintas.
> `fork`/`join` possuem representação no front-end e no TAC e execução local em C++.
> O runtime usa tarefas assíncronas e barreiras por thread. A execução remota via
> `host` permanece pendente e gera aviso de execução local.

---

## Sumário

1. [Notação utilizada](#1-notação-utilizada)
2. [Tokens (Análise Léxica)](#2-tokens-análise-léxica)
3. [Programa](#3-programa)
4. [Declarações](#4-declarações)
5. [Comandos](#5-comandos)
6. [Blocos Sequencial, Paralelo, Fork e Join](#6-blocos-sequencial-paralelo-fork-e-join)
7. [Estruturas de Controle](#7-estruturas-de-controle)
8. [Orientação a Objetos](#8-orientação-a-objetos)
9. [Funções](#9-funções)
10. [Expressões](#10-expressões)
11. [Comunicação por Canais](#11-comunicação-por-canais)
12. [Coleções](#12-coleções)
13. [Entrada e Saída](#13-entrada-e-saída)
14. [Tipos e Literais](#14-tipos-e-literais)
15. [Biblioteca Nativa](#15-biblioteca-nativa)
16. [Comentários](#16-comentários)
17. [Gramática Consolidada (BNF Completa)](#17-gramática-consolidada-bnf-completa)

---

## 1. Notação utilizada

| Símbolo | Significado |
|---------|-------------|
| `::=` | Definição de produção |
| `\|` | Alternativa (ou) |
| `{ x }` | Zero ou mais repetições de `x` |
| `[ x ]` | Opcional (zero ou uma ocorrência de `x`) |
| `( x )` | Agrupamento |
| `"token"` | Terminal literal (palavra reservada ou símbolo) |
| `<não-terminal>` | Símbolo não-terminal |

---

## 2. Tokens (Análise Léxica)

O analisador léxico (`src/lexer.py`) produz os seguintes tokens a partir do código-fonte.
Comentários iniciados por `#` são descartados pelo lexer antes da geração de tokens.

### 2.1 Palavras Reservadas

```
class  extends  new  func  var
if  else  while  do  for  in
break  continue  return
seq  par  fork  join  core  host  this
c_channel  send  receive  input  print  matrix
true  false
number  int  string  bool  void  list  dict  task
```

### 2.2 Literais

```bnf
<NUMBER>         ::= <digito> { <digito> } [ "." { <digito> } ]
<STRING_LITERAL> ::= '"' { <caractere> } '"'
<BOOL_LITERAL>   ::= "true" | "false"
<IDENTIFIER>     ::= ( <letra> | "_" ) { <letra> | <digito> | "_" }
```

### 2.3 Operadores

| Categoria | Tokens |
|-----------|--------|
| Aritméticos | `+`  `-`  `*`  `/`  `%` |
| Relacionais | `==`  `!=`  `<`  `>`  `<=`  `>=` |
| Lógicos | `&&`  `\|\|`  `!` |
| Atribuição | `=` |

### 2.4 Delimitadores

```
(  )  {  }  [  ]  .  ;  ,
```

### 2.5 Tipos declaráveis

```bnf
<tipo> ::= "number" | "int" | "string" | "bool" | "void" | "list" | "dict" | "task"
```

---

## 3. Programa

O programa MiniPar é uma sequência de zero ou mais declarações e comandos no nível global.

```bnf
<programa> ::= { <declaracao_global> | <comando> }

<declaracao_global> ::= <declaracao_classe>
                      | <declaracao_funcao>
                      | <declaracao_variavel>
```

---

## 4. Declarações

### 4.1 Declaração de Variável

```bnf
<declaracao_variavel> ::= "var" <IDENTIFIER> [ "=" <expressao> ] ";"
                        | <tipo> <IDENTIFIER> [ "=" <expressao> ] ";"
```

**Exemplos:**

```minipar
var x = 42;
var nome = "MiniPar";
number total = 0;
bool ativo = true;
task subtarefa = fork core(1) { calcular(); };
```

### 4.2 Declaração de Função

```bnf
<declaracao_funcao> ::= "func" <IDENTIFIER> "(" [ <lista_parametros> ] ")" <bloco_chaves>

<lista_parametros> ::= <parametro> { "," <parametro> }

<parametro> ::= [ <tipo> ] <IDENTIFIER>
```

**Exemplos:**

```minipar
func somar(a, b) {
    return a + b;
}

func calcular(number x, number y) {
    return x * y;
}
```

### 4.3 Declaração de Classe

```bnf
<declaracao_classe> ::= "class" <IDENTIFIER> [ "extends" <IDENTIFIER> ] "{"
                            { <membro_classe> }
                        "}"

<membro_classe> ::= "var" <IDENTIFIER> [ "=" <expressao> ] ";"
                        | <declaracao_funcao>
```

**Exemplos:**

```minipar
class Animal {
    var nome = "Animal";
    func falar() {
        print("...");
    }
}

class Cachorro extends Animal {
    func falar() {
        print("Au!");
    }
}
```

---

## 5. Comandos

```bnf
<comando> ::= <declaracao_variavel>
            | <atribuicao>
            | <bloco_seq>
            | <bloco_par>
            | <comando_fork>
            | <comando_join>
            | <comando_if>
            | <comando_while>
            | <comando_do_while>
            | <comando_for>
            | <comando_print>
            | <comando_send>
            | <comando_return>
            | <comando_break>
            | <comando_continue>
            | <chamada_funcao> ";"
            | <chamada_metodo> ";"
```

### 5.1 Atribuição

A atribuição suporta identificadores simples, propriedades de objetos e indexação de coleções:

```bnf
<atribuicao> ::= <alvo_atribuicao> "=" <expressao> ";"

<alvo_atribuicao> ::= <IDENTIFIER>
                    | <expressao_posfixo> "." <IDENTIFIER>
                    | <expressao_posfixo> "[" <expressao> "]"
```

**Exemplos:**

```minipar
x = 10;
objeto.campo = 42;
lista[0] = "primeiro";
```

### 5.2 Comando Print

```bnf
<comando_print> ::= "print" "(" [ <expressao> { "," <expressao> } ] ")" ";"
```

**Exemplos:**

```minipar
print("Olá, mundo!");
print("Valor:", x, "e", y);
```

### 5.3 Comando Return

```bnf
<comando_return> ::= "return" ( ";" | <expressao> [ ";" ] )
```

### 5.4 Comandos Break e Continue

```bnf
<comando_break>    ::= "break" [ ";" ]
<comando_continue> ::= "continue" [ ";" ]
```

> `break` e `continue` são válidos somente dentro de laços (`while`, `do-while`, `for`).
> O analisador semântico reporta erro se forem usados fora de laço.

---

## 6. Blocos Sequencial, Paralelo, Fork e Join

### 6.1 Bloco Sequencial (SEQ)

Executa os comandos internos em ordem, da mesma forma que um bloco tradicional.

```bnf
<bloco_seq> ::= [ "seq" ] <bloco_chaves>
```

O `seq` é opcional: blocos com chaves `{ }` são tratados como sequenciais por padrão.

### 6.2 Bloco Paralelo (PAR)

Cada comando interno é executado como uma `std::thread` independente em C++.
As threads são sincronizadas por `join()` ao final do bloco.
Cada tarefa possui escopo próprio: uma declaração não fica visível nas tarefas
irmãs. Leituras externas são permitidas, mas escritas diretas em variáveis,
índices ou propriedades externas são rejeitadas, assim como em `fork`.
O C++ usa captura por valor (`[=]() mutable`), preservando as variáveis locais
e os canais necessários à comunicação por mensagens.

```bnf
<bloco_par> ::= "par" "{" { <comando> } "}"
```

**Exemplo:**

```minipar
par {
    seq { print("Thread A"); }
    seq { print("Thread B"); }
    seq { print("Thread C"); }
}
```

### 6.3 Divisão em Subtarefas Paralelas (FORK)

A semântica pretendida de `fork` é dividir uma tarefa principal em subtarefas independentes executadas em paralelo. O compilador reconhece essa sintaxe, gera TAC e executa as tarefas localmente com `std::async`.
Conforme a especificação do MiniPar 2026.2, cada subtarefa criada via `fork` pode ser explicitamente alocada para:
- **Um núcleo da CPU** (`core(<expressao>)`), com solicitação de afinidade ao sistema operacional; ou
- **Um computador diferente** (`host(<expressao> [, <expressao>])`), com despacho remoto a implementar. A existência de canais TCP não implementa, por si só, o despacho de subtarefas.

O parser aceita `fork` como comando ou expressão. O semântico atribui o tipo `task` à expressão; a criação efetiva dessa referência e sua utilização em `join` dependem do back-end.

```bnf
<comando_fork>       ::= "fork" [ <alocacao_fork> ] ( <bloco_chaves> | <expressao> ";" )

<expressao_fork>     ::= "fork" [ <alocacao_fork> ] ( <bloco_chaves> | <expressao> )

<alocacao_fork>      ::= <destino_nucleo>
                       | <destino_computador>

<destino_nucleo>     ::= "core" "(" <expressao> ")"

<destino_computador> ::= "host" "(" <expressao> [ "," <expressao> ] ")"

<bloco_chaves>         ::= "{" { <comando> } "}"
```

**Exemplos:**

```minipar
# 1. Alocando subtarefas a núcleos distintos da CPU (Testes 8, 9 e 10)
var t1 = fork core(1) avaliar_lote("Professor", fatia1);
var t2 = fork core(2) avaliar_lote("Monitor 1", fatia2);
var t5 = fork core(5) {
    gerar_fractal_mandelbrot();
};

# 2. Alocando subtarefas a computadores diferentes na rede
var t_remota1 = fork host("192.168.1.10", 5001) {
    processar_subtarefa_A();
};
var t_remota2 = fork host(canal_computador_2) processar_subtarefa_B();
```

**Compatibilidade com o parser:** o corpo em bloco usa `{ ... }` diretamente;
`fork core(0) seq { ... }` não é aceito. Como comando, um fork com bloco não leva
`;` depois de `}`; em uma declaração (`var t = fork ... { ... };`), o `;` encerra
a declaração. O parser também aceita expressões que não são chamadas como corpo;
essa aceitação não garante que o back-end consiga executá-las como subtarefas.

### 6.4 Sincronização e Coleta de Subtarefas (JOIN)

A semântica pretendida de `join` é aguardar as subtarefas e, quando houver suporte a retorno, coletar resultados. O runtime implementa espera e obtenção do retorno com `shared_future`.

```bnf
<comando_join>   ::= "join" [ "(" [ <lista_argumentos> ] ")" ] ";"

<expressao_join> ::= "join" [ "(" [ <lista_argumentos> ] ")" ]
```

- `join;` ou `join();`: aguarda a finalização de todas as subtarefas registradas pela thread atual.
- `join(t1, t2, ...);` aguarda as subtarefas especificadas. Listas de tarefas são rejeitadas pelo semântico.
- `var res = join(t1);`: forma sintática aceita; o resultado é inferido como `unknown`. O runtime obtém o resultado da tarefa. Tarefas sem retorno produzem zero quando usadas como expressão.
- Como expressão, o parser também aceita `join`, `join()` e múltiplos argumentos. Múltiplos argumentos são aguardados na ordem escrita e a expressão produz o último resultado. A barreira sem argumentos produz zero.

**Exemplos:**

```minipar
# Coleta individual do retorno de cada subtarefa (Fork-Join com retorno)
var res1 = join(t1);
var res2 = join(t2);

# Sincronização de subtarefas individuais
join(t1, t2);

# Barreira global para todas as subtarefas disparadas no escopo
join;
```

---

## 7. Estruturas de Controle

### 7.1 If / Else

```bnf
<comando_if> ::= "if" "(" <expressao> ")" <comando>
                 [ "else" <comando> ]
```

**Exemplos:**

```minipar
if (x > 0) {
    print("positivo");
}

if (x > 0) {
    print("positivo");
} else {
    print("negativo ou zero");
}

# Encadeamento if-else-if
if (x > 0) {
    print("positivo");
} else if (x < 0) {
    print("negativo");
} else {
    print("zero");
}
```

### 7.2 While

```bnf
<comando_while> ::= "while" "(" <expressao> ")" <comando>
```

**Exemplo:**

```minipar
while (i < 10) {
    i = i + 1;
}
```

### 7.3 Do-While

```bnf
<comando_do_while> ::= "do" <comando> "while" "(" <expressao> ")" [ ";" ]
```

**Exemplo:**

```minipar
do {
    tentativas = tentativas + 1;
} while (tentativas < 5);
```

### 7.4 For

O `for` suporta tanto o estilo clássico (inicializador; condição; incremento) quanto o estilo iterador (`for var x in colecao`):

```bnf
<comando_for> ::= "for" "(" <for_classico> | <for_iterador> ")" <comando>

<for_classico> ::= [ <inicializador_for> ] ";" [ <expressao> ] ";" [ <incremento_for> ]

<inicializador_for> ::= "var" <IDENTIFIER> [ "=" <expressao> ]
                      | <tipo> <IDENTIFIER> [ "=" <expressao> ]
                      | <alvo_atribuicao> "=" <expressao>
                      | <expressao>

<incremento_for>    ::= <alvo_atribuicao> "=" <expressao>
                      | <expressao>

<for_iterador>      ::= "var" <IDENTIFIER> "in" <expressao>
```

**Exemplos:**

```minipar
# For clássico
for (var i = 0; i < 10; i = i + 1) {
    print(i);
}

# For iterador
for (var item in lista) {
    print(item);
}

# For com range()
for (var i in range(5)) {
    print(i);
}
```

---

## 8. Orientação a Objetos

### 8.1 Instanciação com new

```bnf
<expressao_new> ::= "new" <IDENTIFIER> "(" [ <lista_argumentos> ] ")"
```

**Exemplo:**

```minipar
var obj = new MinhaClasse();
var rede = new RedeNeural(0.5);
```

### 8.2 Acesso a Propriedades

```bnf
<acesso_propriedade> ::= <expressao_posfixo> "." <IDENTIFIER>
```

**Exemplo:**

```minipar
print(neuronio.peso);
```

### 8.3 Chamada de Método

```bnf
<chamada_metodo> ::= <expressao_posfixo> "." <IDENTIFIER> "(" [ <lista_argumentos> ] ")"
```

**Exemplo:**

```minipar
neuronio.treinar();
algoritmo.ordenar();
rede.feedforward(x1, x2);
```

### 8.4 Atribuição de Propriedade

```bnf
<atrib_propriedade> ::= <expressao_posfixo> "." <IDENTIFIER> "=" <expressao> ";"
```

**Exemplo:**

```minipar
this.peso = this.peso + 0.01;
obj.nome = "novo";
```

### 8.5 Referência a this

Dentro de métodos de uma classe, `this` refere-se à instância corrente.

```bnf
<expressao_this> ::= "this"
```

### 8.6 Herança

```bnf
<declaracao_classe> ::= "class" <IDENTIFIER> "extends" <IDENTIFIER> "{"
                            { <membro_classe> }
                        "}"
```

**Exemplo:**

```minipar
class Cachorro extends Animal {
    func latir() {
        print("Au!");
    }
}
```

---

## 9. Funções

### 9.1 Chamada de Função

```bnf
<chamada_funcao> ::= <IDENTIFIER> "(" [ <lista_argumentos> ] ")"

<lista_argumentos> ::= <expressao> { "," <expressao> }
```

### 9.2 Recursão

Funções podem se chamar recursivamente sem nenhuma sintaxe especial:

```minipar
func fatorial(n) {
    if (n <= 1) {
        return 1;
    }
    return n * fatorial(n - 1);
}
```

---

## 10. Expressões

As expressões seguem a hierarquia de precedência implementada no parser (da menor para a maior precedência):

```bnf
<expressao> ::= <expressao_ou>

<expressao_ou>  ::= <expressao_e> { "||" <expressao_e> }

<expressao_e>   ::= <expressao_comp> { "&&" <expressao_comp> }

<expressao_comp> ::= <expressao_termo>
                     { ( "==" | "!=" | "<" | ">" | "<=" | ">=" ) <expressao_termo> }

<expressao_termo> ::= <expressao_fator> { ( "+" | "-" ) <expressao_fator> }

<expressao_fator> ::= <expressao_unaria> { ( "*" | "/" | "%" ) <expressao_unaria> }

<expressao_unaria> ::= ( "-" | "+" | "!" ) <expressao_unaria>
                     | <expressao_posfixo>

<expressao_posfixo> ::= <expressao_primaria>
                        { "." <IDENTIFIER> [ "(" [ <lista_argumentos> ] ")" ]
                        | "[" <expressao> "]"
                        }

<expressao_primaria> ::= <NUMBER>
                       | <STRING_LITERAL>
                       | <BOOL_LITERAL>
                       | <IDENTIFIER> [ "(" [ <lista_argumentos> ] ")" ]
                       | "this"
                       | <expressao_new>
                       | <expressao_fork>
                       | <expressao_join>
                       | <expressao_c_channel>
                       | <expressao_receive>
                       | <expressao_input>
                       | <expressao_lista>
                       | <expressao_matrix>
                       | "(" <expressao> ")"
```

### Tabela de Precedência (maior nível = avaliado primeiro)

| Nível | Operadores | Associatividade |
|-------|-----------|-----------------|
| 7 (mais alta) | `()` `[]` `.` (posfixo) | esquerda |
| 6 | `!` `-` (unário) `+` (unário) | direita |
| 5 | `*` `/` `%` | esquerda |
| 4 | `+` `-` | esquerda |
| 3 | `==` `!=` `<` `>` `<=` `>=` | esquerda |
| 2 | `&&` | esquerda |
| 1 (mais baixa) | `\|\|` | esquerda |

---

## 11. Comunicação por Canais

A comunicação entre processos/computadores é feita via canais TCP implementados pela classe `MiniParChannel` no C++ gerado.

### 11.1 Criação de Canal

```bnf
<expressao_c_channel> ::= "c_channel" "(" <expressao> "," <expressao> ")"
```

O primeiro argumento é o endereço IP (string) e o segundo é a porta (número).

**Exemplo:**

```minipar
var canal = c_channel("127.0.0.1", 5000);
var canal_remoto = c_channel("192.168.1.10", 8080);
```

### 11.2 Envio de Mensagem (Send)

```bnf
<comando_send> ::= "send" "(" <expressao> "," <expressao> ")" ";"
```

O primeiro argumento é o canal e o segundo é a mensagem a enviar.

**Exemplo:**

```minipar
send(canal, "Hello Server");
send(canal, resultado);
```

### 11.3 Recebimento de Mensagem (Receive)

```bnf
<expressao_receive> ::= "receive" "(" <expressao> ")"
```

**Exemplo:**

```minipar
var mensagem = receive(canal);
var dado = receive(c_channel("127.0.0.1", 5000));
```

---

## 12. Coleções

### 12.1 Lista (Array)

```bnf
<expressao_lista> ::= "[" [ <expressao> { "," <expressao> } ] "]"
```

**Exemplos:**

```minipar
var vazio = [];
var numeros = [1, 2, 3, 4, 5];
var misto = [0, "texto", true];
```

### 12.2 Indexação

```bnf
<expressao_indice> ::= <expressao_posfixo> "[" <expressao> "]"
```

**Exemplo:**

```minipar
var primeiro = lista[0];
var ultimo = lista[len(lista) - 1];
```

### 12.3 Atribuição por Índice

```bnf
<atrib_indice> ::= <expressao_posfixo> "[" <expressao> "]" "=" <expressao> ";"
```

**Exemplo:**

```minipar
lista[0] = 99;
matriz[i][j] = "#";
```

### 12.4 Matriz (Matrix)

Cria uma matriz bidimensional de `linhas × colunas` inicializada com um valor padrão.

```bnf
<expressao_matrix> ::= "matrix" "(" <expressao> "," <expressao> "," <expressao> ")"
```

**Exemplo:**

```minipar
var tela = matrix(9, 9, " ");       # matriz 9×9 de espaços
var zeros = matrix(3, 3, 0);        # matriz 3×3 de zeros
```

---

## 13. Entrada e Saída

### 13.1 Saída (Print)

```bnf
<comando_print> ::= "print" "(" [ <expressao> { "," <expressao> } ] ")" ";"
```

Múltiplos argumentos são impressos separados por espaço seguidos de `\n`.

### 13.2 Entrada (Input)

```bnf
<expressao_input> ::= "input" "(" [ <expressao> ] ")"
```

Lê uma linha da entrada padrão (stdin). O argumento opcional é exibido como prompt antes da leitura.

**Exemplos:**

```minipar
var nome = input("Seu nome: ");
var valor = input();
var numero = to_number(input("Digite um número: "));
```

---

## 14. Tipos e Literais

### 14.1 Número

```bnf
<literal_numero> ::= <digito> { <digito> } [ "." { <digito> } ]
```

Representa inteiros e ponto flutuante. Internamente ambos são tratados como `double` no C++ gerado.

**Exemplos:** `0`, `42`, `3.14`, `0.5`

### 14.2 String

```bnf
<literal_string> ::= '"' { <caractere_string> } '"'

<caractere_string> ::= <qualquer_caractere_exceto_aspas_e_barra>
                     | "\\" "n"    # newline
                     | "\\" "t"    # tab
                     | "\\" '"'    # aspas duplas
                     | "\\" "\\"   # barra invertida
```

### 14.3 Booleano

```bnf
<literal_bool> ::= "true" | "false"
```

### 14.4 Identificador

```bnf
<IDENTIFIER> ::= ( <letra> | "_" ) { <letra> | <digito> | "_" }

<letra>  ::= "A" | ... | "Z" | "a" | ... | "z"
<digito> ::= "0" | ... | "9"
```

---

## 15. Biblioteca Nativa

A tabela distingue funções reconhecidas pelo analisador semântico daquelas traduzidas diretamente pelo gerador de código C++:

| Função MiniPar | Assinatura | Descrição |
|---------------|------------|-----------|
| `print(...)` | `print(expr, ...)` | Imprime na saída padrão |
| `input([prompt])` | `input()` / `input(expr)` | Lê linha do stdin |
| `time()` | `time()` → `number` | Traduzida para `__minipar_time()`, em segundos |
| `exp(x)` | `exp(number)` → `number` | Exponencial natural (eˣ) |
| `random()` | `random()` → `number` | Número aleatório entre 0 e 1 |
| `range(n)` / `range(a,b)` | `range(int)` → `list` | Gera sequência inteira |
| `len(col)` | `len(list\|string\|matrix)` → `number` | Exige um argumento. Devolve o comprimento da string ou lista e o número de linhas da matriz |
| `to_number(s)` | `to_number(string)` → `number` | Converte string para número |
| `to_int(x)` | `to_int(x)` → `number` (inferência atual) | Converte número ou string numérica e trunca em direção a zero; verifica a faixa de int |
| `to_string(v)` | `to_string(v)` → `string` | Traduzida para `__to_string`; aceita números, booleanos e strings |
| `parse_ints(s)` | `parse_ints(string)` → `list` | Parseia inteiros de string separados por espaço |
| `fmt(v, casas)` | `fmt(number, number)` → `string` | Formata casas decimais por `__fmt`; o semântico verifica dois argumentos |

### Métodos de Lista (acesso via ponto)

| Método | Descrição |
|--------|-----------|
| `.append(v)` / `.push_back(v)` | Adiciona elemento ao final |
| `.pop()` | Remove e retorna o último elemento |
| `.size()` | Retorna o tamanho da lista |

---

## 16. Comentários

```bnf
<comentario> ::= "#" { <qualquer_caractere> } <fim_de_linha>
```

Comentários iniciam com `#` e vão até o final da linha. São descartados pelo lexer.

**Exemplos:**

```minipar
# Isso é um comentário de linha inteira
var x = 10; # Comentário ao final da linha
```

---

## 17. Gramática Consolidada (BNF Completa)

A seguir a gramática completa em formato BNF, em ordem de definição:

```bnf
(* ============================================================ *)
(*       GRAMÁTICA BNF — LINGUAGEM MINIPAR 2026.2               *)
(*       Compilador: minipar-improvement                        *)
(*       Repositório: github.com/Felipe-Aragao/Minipar2026.2    *)
(* ============================================================ *)


(* ─── ESTRUTURA GLOBAL ─── *)

<programa> ::= { <declaracao_global> | <comando> }

<declaracao_global> ::= <declaracao_classe>
                      | <declaracao_funcao>
                      | <declaracao_variavel>


(* ─── DECLARAÇÕES ─── *)

<declaracao_variavel> ::= "var" <IDENTIFIER> [ "=" <expressao> ] ";"
                        | <tipo> <IDENTIFIER> [ "=" <expressao> ] ";"

<declaracao_funcao>   ::= "func" <IDENTIFIER> "(" [ <lista_parametros> ] ")" <bloco_chaves>

<lista_parametros>    ::= <parametro> { "," <parametro> }
<parametro>           ::= [ <tipo> ] <IDENTIFIER>

<declaracao_classe>   ::= "class" <IDENTIFIER> [ "extends" <IDENTIFIER> ]
                          "{" { <membro_classe> } "}"

<membro_classe>       ::= "var" <IDENTIFIER> [ "=" <expressao> ] ";"
                        | <declaracao_funcao>


(* ─── COMANDOS ─── *)

<comando> ::= <declaracao_variavel>
            | <atribuicao>
            | <bloco_seq>
            | <bloco_par>
            | <comando_fork>
            | <comando_join>
            | <comando_if>
            | <comando_while>
            | <comando_do_while>
            | <comando_for>
            | <comando_print>
            | <comando_send>
            | <comando_return>
            | <comando_break>
            | <comando_continue>
            | <chamada_funcao> ";"
            | <chamada_metodo> ";"

<atribuicao>        ::= <alvo_atribuicao> "=" <expressao> ";"
<alvo_atribuicao>   ::= <IDENTIFIER>
                      | <expressao_posfixo> "." <IDENTIFIER>
                      | <expressao_posfixo> "[" <expressao> "]"

<comando_print>     ::= "print" "(" [ <expressao> { "," <expressao> } ] ")" ";"
<comando_send>      ::= "send"  "(" <expressao> "," <expressao> ")" ";"
<comando_return>    ::= "return" ( ";" | <expressao> [ ";" ] )
<comando_break>     ::= "break" [ ";" ]
<comando_continue>  ::= "continue" [ ";" ]


(* ─── BLOCOS E PARALELISMO (SEQ, PAR, FORK, JOIN) ─── *)

<bloco_seq>          ::= [ "seq" ] <bloco_chaves>

<bloco_par>          ::= "par" "{" { <comando> } "}"

<comando_fork>       ::= "fork" [ <alocacao_fork> ] ( <bloco_chaves> | <expressao> ";" )

<expressao_fork>     ::= "fork" [ <alocacao_fork> ] ( <bloco_chaves> | <expressao> )

<alocacao_fork>      ::= <destino_nucleo>
                       | <destino_computador>

<destino_nucleo>     ::= "core" "(" <expressao> ")"

<destino_computador> ::= "host" "(" <expressao> [ "," <expressao> ] ")"

<bloco_chaves>         ::= "{" { <comando> } "}"

<comando_join>       ::= "join" [ "(" [ <lista_argumentos> ] ")" ] ";"

<expressao_join>     ::= "join" [ "(" [ <lista_argumentos> ] ")" ]


(* ─── ESTRUTURAS DE CONTROLE ─── *)

<comando_if>       ::= "if" "(" <expressao> ")" <comando> [ "else" <comando> ]

<comando_while>    ::= "while" "(" <expressao> ")" <comando>

<comando_do_while> ::= "do" <comando> "while" "(" <expressao> ")" [ ";" ]

<comando_for>      ::= "for" "(" <for_cabecalho> ")" <comando>

<for_cabecalho>    ::= <for_classico>
                     | <for_iterador>

<for_classico>     ::= [ <inicializador_for> ] ";" [ <expressao> ] ";" [ <incremento_for> ]

<inicializador_for> ::= "var"  <IDENTIFIER> [ "=" <expressao> ]
                      | <tipo> <IDENTIFIER> [ "=" <expressao> ]
                      | <alvo_atribuicao> "=" <expressao>
                      | <expressao>

<incremento_for>   ::= <alvo_atribuicao> "=" <expressao>
                     | <expressao>

<for_iterador>     ::= "var" <IDENTIFIER> "in" <expressao>


(* ─── ORIENTAÇÃO A OBJETOS ─── *)

<expressao_new>         ::= "new" <IDENTIFIER> "(" [ <lista_argumentos> ] ")"
<acesso_propriedade>    ::= <expressao_posfixo> "." <IDENTIFIER>
<chamada_metodo>        ::= <expressao_posfixo> "." <IDENTIFIER> "(" [ <lista_argumentos> ] ")"
<atrib_propriedade>     ::= <expressao_posfixo> "." <IDENTIFIER> "=" <expressao> ";"
<expressao_this>        ::= "this"


(* ─── COMUNICAÇÃO POR CANAIS ─── *)

<expressao_c_channel>   ::= "c_channel" "(" <expressao> "," <expressao> ")"
<expressao_receive>     ::= "receive" "(" <expressao> ")"
(* send já listado em <comando_send> *)


(* ─── COLEÇÕES ─── *)

<expressao_lista>   ::= "[" [ <expressao> { "," <expressao> } ] "]"
<expressao_indice>  ::= <expressao_posfixo> "[" <expressao> "]"
<atrib_indice>      ::= <expressao_posfixo> "[" <expressao> "]" "=" <expressao> ";"
<expressao_matrix>  ::= "matrix" "(" <expressao> "," <expressao> "," <expressao> ")"


(* ─── ENTRADA E SAÍDA ─── *)

<expressao_input>   ::= "input" "(" [ <expressao> ] ")"
(* print já listado em <comando_print> *)


(* ─── EXPRESSÕES (hierarquia de precedência) ─── *)

<expressao>          ::= <expressao_ou>

<expressao_ou>       ::= <expressao_e> { "||" <expressao_e> }

<expressao_e>        ::= <expressao_comp> { "&&" <expressao_comp> }

<expressao_comp>     ::= <expressao_termo>
                         { ( "==" | "!=" | "<" | ">" | "<=" | ">=" )
                           <expressao_termo> }

<expressao_termo>    ::= <expressao_fator> { ( "+" | "-" ) <expressao_fator> }

<expressao_fator>    ::= <expressao_unaria> { ( "*" | "/" | "%" ) <expressao_unaria> }

<expressao_unaria>   ::= ( "-" | "+" | "!" ) <expressao_unaria>
                       | <expressao_posfixo>

<expressao_posfixo>  ::= <expressao_primaria>
                         { "." <IDENTIFIER> [ "(" [ <lista_argumentos> ] ")" ]
                         | "[" <expressao> "]"
                         }

<expressao_primaria> ::= <NUMBER>
                       | <STRING_LITERAL>
                       | <BOOL_LITERAL>
                       | <IDENTIFIER> [ "(" [ <lista_argumentos> ] ")" ]
                       | "this"
                       | <expressao_new>
                       | <expressao_fork>
                       | <expressao_join>
                       | <expressao_c_channel>
                       | <expressao_receive>
                       | <expressao_input>
                       | <expressao_lista>
                       | <expressao_matrix>
                       | "(" <expressao> ")"

<lista_argumentos>   ::= <expressao> { "," <expressao> }
<chamada_funcao>     ::= <IDENTIFIER> "(" [ <lista_argumentos> ] ")"


(* ─── TIPOS E LITERAIS ─── *)

<tipo>           ::= "number" | "int" | "string" | "bool" | "void" | "list" | "dict" | "task"

<NUMBER>         ::= <digito> { <digito> } [ "." { <digito> } ]
<STRING_LITERAL> ::= '"' { <caractere_string> } '"'
<BOOL_LITERAL>   ::= "true" | "false"
<IDENTIFIER>     ::= ( <letra> | "_" ) { <letra> | <digito> | "_" }

<caractere_string> ::= <qualquer_char_exceto_aspas_e_barra>
                     | "\n" | "\t" | '\"' | "\\"

<letra>  ::= "A" | ... | "Z" | "a" | ... | "z"
<digito> ::= "0" | ... | "9"


(* ─── COMENTÁRIOS ─── *)

<comentario> ::= "#" { <qualquer_char> } <nova_linha>
(* Descartados pelo lexer — não aparecem na AST *)
```

---

## Notas de Implementação

### Inferência de Tipos

O analisador semântico (`src/semantic.py`) usa inferência simples de tipos com as seguintes regras:

| Expressão | Tipo inferido |
|-----------|--------------|
| Literal numérico | `number` |
| Literal string | `string` |
| Literal booleano | `bool` |
| Lista literal `[...]` | `list` |
| `matrix(...)` | `matrix` |
| `c_channel(...)` | `c_channel` |
| `fork ...` | `task` |
| `join(...)` | `unknown` (sem inferência do retorno da subtarefa) |
| `receive(...)` | `string` |
| `input(...)` | `string` |
| `time()` | `number` |
| `to_string(v)` | `string` |
| `fmt(v, casas)` | `string` |
| `to_int(x)` | `number` |
| `new Classe(...)` | `Classe` |
| `this` | nome da classe atual |
| `op` relacional / lógico | `bool` |
| `"a" + "b"` (concatenação) | `string` |
| Operação aritmética | `number` |
| Identificador | tipo declarado na tabela de símbolos |
| Desconhecido | `unknown` (compatível com qualquer tipo) |

### Regras Semânticas Verificadas

| Regra | Erro reportado |
|-------|---------------|
| Redeclaração no mesmo escopo | `Variável 'x' já declarada.` |
| Uso antes de declaração | `Variável 'x' não declarada.` |
| Incompatibilidade de tipos | `Tipo incompatível em atribuição de 'x'.` |
| Função não declarada | `Função 'f' não declarada.` |
| Aridade errada (função) | `Função 'f' espera N argumento(s), recebeu M.` |
| Classe não declarada | `Classe 'C' não declarada.` |
| Superclasse não declarada | `Superclasse 'S' não declarada.` |
| Método inexistente | `Método 'm' não declarado em 'C'.` |
| Atributo inexistente | `Atributo 'a' não declarado em 'C'.` |
| `break`/`continue` fora de laço | `'break' usado fora de laço de repetição.` |
| Tipo incompatível em `core(n)` | `Alocacao 'core' requer expressao numerica inteira.` |
| Constante fracionária ou negativa em `core(n)` | `Alocacao 'core' requer inteiro nao negativo.` |
| Divisão constante por zero em `core(n)` | `Alocacao 'core' contem divisao por zero.` |
| Escrita em variável externa à tarefa de fork ou par | Violação de isolamento, considerando o escopo da declaração |
| Destino inválido em `fork host(...)` | `Alocação 'host' requer canal ('c_channel') ou endereço IP ('string') e porta ('number').` |
| Argumento inválido em `join(...)` | `'join' requer subtarefa do tipo 'task'.` |

### Limites atuais da validação semântica

A verificação de isolamento cobre atribuições diretas, por índice e por propriedade
com raiz identificável. Leitura de variáveis externas é permitida. Declarações locais
homônimas não liberam escrita externa; cada tarefa de `par` ou `fork`, inclusive
aninhada, possui seu próprio limite, restaurado ao retornar à tarefa pai.
Não há análise completa de alias ou efeitos indiretos de funções e métodos.
A captura por valor copia escalares e vetores, mas não realiza cópia profunda dos
objetos representados por `shared_ptr`; os canais também mantêm sua identidade.

Em `core(n)`, constantes aritméticas devem representar inteiros não negativos:
`0`, `2.0` e `4 / 2` são aceitos; `-1`, `1.5` e `1 / 2` são rejeitados.
Valores dinâmicos, faixa de núcleos e disponibilidade exigirão validação no runtime.
`host(canal)` exige tipo de canal ou desconhecido; `host(ip, porta)` verifica tipos
string e numérico ou desconhecidos, sem validar endereço ou faixa de porta.
Os argumentos de `join` são verificados como `task`, `var` ou `unknown`.
Listas são rejeitadas com diagnóstico específico. Chamadas `append`, `push_back` e
`pop` em coleções externas também passam pela verificação de isolamento.

### Geração de Código C++20

| Construto MiniPar | Código C++ gerado |
|-------------------|------------------|
| `class C { ... }` | `class C { public: ... };` |
| `new C(args)` | `std::make_shared<C>(args)` |
| `obj.metodo(args)` | `obj->metodo(args)` |
| `obj.campo` | `obj->campo` |
| `par { a; b; }` | `std::vector<std::thread>` + `emplace_back` + `join` |
| `fork core(n) { ... }` | Tarefa assíncrona com captura por valor e solicitação de afinidade |
| `fork host(ip, porta) { ... }` | Aviso e execução local, com despacho remoto pendente |
| `join(t)` / `join;` | Obtenção do resultado ou espera das tarefas da thread atual |
| `c_channel(ip, porta)` | `std::make_shared<MiniParChannel>(ip, porta)` |
| `send(canal, msg)` | `canal->sendData(__to_string(msg))` |
| `receive(canal)` | `canal->receiveData()` |
| `[1, 2, 3]` | `__make_list(1, 2, 3)` → `std::vector<double>` |
| `["a", "b"]` | `__make_list(...)` → `std::vector<std::string>` |
| `s[i]` / `s[i] = "a"` | `__index` / `__set_index`, com verificação de índice |
| `matrix(l, c, v)` | `__make_matrix(l, c, v)` |
| `time()` | `__minipar_time()` |
| `exp(x)` | `std::exp(x)` |
| `random()` | `random_val()` |
| `to_number(s)` | `std::stod(s)` |
| `to_int(x)` | `__to_int(x)` |
| `to_string(v)` | `__to_string(v)` |
| `fmt(v, casas)` | `__fmt(v, casas)` |
| `len(x)` | `x.size()` |
| `range(n)` | `__minipar_range(n)` |
| `input(p)` | `input(p)` (helper C++) |

---

### Teste 11 e integração

O Teste 11 é um programa MiniPar que implementa um minicompilador de expressões
infixadas. A sintaxe já contempla classes, métodos, recursão, listas, strings,
indexação, operações aritméticas e parênteses. O programa de integração
`tests/teste11_tokenizador.minipar` usa essas construções para gerar tokens, AST,
tabela de símbolos, TAC e Assembly ARMv7, além de avaliar a expressão.

Os literais string agora geram `std::string`, permitindo armazenamento em variáveis,
atributos e retornos, comparação por conteúdo, concatenação e `len(s)`. `string s;`
inicializa uma string vazia. `s[i]` retorna uma string de um byte; `s[i] = texto`
exige exatamente um byte. Os índices são baseados em zero, inteiros não negativos
e dentro dos limites. Strings seguem a representação em bytes de `std::string`:
indexação e comprimento não contam caracteres Unicode completos.

Listas numéricas continuam sendo `std::vector<double>`; listas não vazias cujos
elementos são strings geram `std::vector<std::string>`, inclusive para tokens.
Listas heterogêneas não são suportadas. `[]` continua sendo lista numérica vazia;
para uma lista de strings vazia, é possível inicializar `[""]` e chamar `.pop()`.
A dedução usa os tipos C++ das expressões, não há uma nova sintaxe de tipo de lista.
O suporte foi exercitado por `tests/test_strings.minipar` e pelo Teste 11,
que usa métodos recursivos para construir e exibir a AST.

A emissão de ARMv7 é textual. Os três arquivos em `tests/arm/` deixam 22, -84 e 22
em `r8` para os exemplos do enunciado. A primeira e a terceira expressões são iguais.
A avaliação em MiniPar e os valores das instruções foram conferidos localmente.
A execução e a captura de evidências no CPUlator seguem como etapa de validação.
O emissor trabalha com inteiros de 32 bits e usa um registrador por nó até `r12`.
Divisão e decimais fracionários são aceitos na avaliação, com diagnóstico quando
a emissão ARMv7 estiver indisponível.

O terminal e `src/analise.py` encadeiam os mesmos contratos de front-end.

| Interface | Componente | Entrada e saída |
|---|---|---|
| `ILexico` | `C_Lexico` | Código fonte → lista de tokens |
| `ISintatico` | `C_Sintatico` | Tokens → AST |
| `ISemantico` | `C_Semantico` | AST → validação, símbolos e diagnósticos |
| `ITabelaSimbolos` | `C_TabelaSimbolos` | Declarações e escopos → consultas e histórico de símbolos |
| `ITAC` | `C_TAC` | AST validada → TAC em texto ou arquivo |

O analisador semântico utiliza `ITabelaSimbolos` para registrar declarações,
consultar o nome visível mais próximo e controlar a entrada e saída de escopos.
O componente rejeita duplicatas no mesmo escopo, permite nomes iguais em escopos
aninhados e mantém o histórico das declarações para a interface. A localização
da declaração visível também fundamenta a verificação de isolamento dos forks.
Cada análise cria sua própria tabela. Essa organização não altera a sintaxe.

A API preserva os resultados das fases concluídas e registra linha e coluna nos
erros léxicos, sintáticos e semânticos. Os nós da AST expõem `line` e `col`;
declarações na tabela de símbolos também incluem `linha` e `coluna`. As posições
começam em 1 e contam caracteres do código fonte, incluindo tabulações como um
caractere. Nós construídos diretamente por integrações antigas podem ter `col`
igual a `null` quando a posição original estiver indisponível. O TAC representa subtarefas em blocos `FORK`/`END_TASK`, com
`END_TASK operando` quando o corpo é uma expressão. `JOIN ALL` representa a
sincronização sem argumentos.

**Afinidade e portabilidade.** O runtime usa a API correspondente no Windows ou no
Linux e informa falhas de afinidade. O índice é remapeado pelo número de processadores
reportado pela máquina. Isso não garante que todos os processadores estejam permitidos
ao processo. O comando de compilação inclui `-lws2_32` apenas no Windows.
A validação desta integração foi executada no Windows.

Cada `print` emite sua linha por um `std::osyncstream` nomeado. Isso evita misturar
partes de linhas de threads diferentes e preserva a impressão de listas.
